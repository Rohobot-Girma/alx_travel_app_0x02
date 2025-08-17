import uuid
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework import viewsets
from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer
import json

def json_from_request(request):
    return json.loads(request.body.decode("utf-8") or "{}")

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

CHAPA_INIT_URL = urljoin(settings.CHAPA_BASE_URL, "/v1/transaction/initialize")
CHAPA_VERIFY_URL_BASE = urljoin(settings.CHAPA_BASE_URL, "/v1/transaction/verify/")

def _auth_headers():
    return {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }

def _absolute_callback_url():
    # callback receives GET from Chapa then we verify server-side
    return urljoin(settings.SITE_BASE_URL, settings.CHAPA_CALLBACK_PATH)

@require_POST
def initiate_payment(request):
    """
    Body JSON:
    {
      "booking_id": 123,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "0912345678"   # optional but must be 10 digits if provided
    }
    """
    try:
        data = json_from_request(request)
        booking_id = data["booking_id"]
        email = data["email"]
        first_name = data["first_name"]
        last_name = data["last_name"]
        phone_number = data.get("phone_number")
    except KeyError as e:
        return HttpResponseBadRequest(f"Missing field: {e}")

    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        return HttpResponseBadRequest("Invalid booking_id")

    # create or reuse tx_ref per booking
    tx_ref = f"booking-{booking.id}-{uuid.uuid4().hex[:8]}"

    payment, _created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            "amount": booking.total_amount,  # adjust to your field
            "currency": "ETB",
            "tx_ref": tx_ref,
            "status": Payment.Status.PENDING,
        },
    )
    if not _created:
        # keep same reference if still pending; otherwise issue new one
        if payment.status != Payment.Status.PENDING:
            payment.tx_ref = tx_ref
            payment.status = Payment.Status.PENDING
            payment.save()

    # Build callback / return URLs (per docs)
    payload = {
        "amount": str(payment.amount),
        "currency": payment.currency,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": payment.tx_ref,
        "callback_url": _absolute_callback_url(),  # will receive tx info; we still verify
        "return_url": settings.CHAPA_RETURN_URL,   # where to redirect user after checkout
        "customization": {
            "title": "Booking payment",
            "description": f"Payment for booking #{booking.id}",
        },
    }
    if phone_number:
        payload["phone_number"] = phone_number

    try:
        r = requests.post(CHAPA_INIT_URL, json=payload, headers=_auth_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        payment.init_response = {"error": str(exc)}
        payment.status = Payment.Status.FAILED
        payment.save()
        return JsonResponse({"detail": "Failed to initialize payment", "error": str(exc)}, status=502)

    payment.init_response = data
    # The docs say redirect to data.checkout_url
    checkout_url = (
        data.get("data", {}).get("checkout_url")
        or data.get("checkout_url")
    )
    if not checkout_url:
        payment.status = Payment.Status.FAILED
        payment.save()
        return JsonResponse({"detail": "Chapa response missing checkout_url", "raw": data}, status=502)

    payment.checkout_url = checkout_url
    payment.save()

    return JsonResponse({
        "tx_ref": payment.tx_ref,
        "checkout_url": payment.checkout_url,
        "status": payment.status,
    }, status=201)

@csrf_exempt
@require_GET
def chapa_callback(request):
    """
    Chapa will hit this URL after payment completes.
    Per docs, it includes { trx_ref, ref_id, status }.
    We will always verify server-side using tx_ref.
    """
    tx_ref = request.GET.get("trx_ref") or request.GET.get("tx_ref")
    if not tx_ref:
        return HttpResponseBadRequest("Missing trx_ref")

    # Verify immediately
    return _verify_and_update(tx_ref)

@require_GET
def verify_payment(request):
    """
    Manual verify endpoint:
    /api/payments/verify/?tx_ref=booking-123-xxxx
    """
    tx_ref = request.GET.get("tx_ref")
    if not tx_ref:
        return HttpResponseBadRequest("Missing tx_ref")
    return _verify_and_update(tx_ref)

def _verify_and_update(tx_ref: str):
    url = urljoin(CHAPA_VERIFY_URL_BASE, tx_ref)
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}, timeout=30)
        r.raise_for_status()
        vdata = r.json()
    except requests.RequestException as exc:
        return JsonResponse({"detail": "Verification failed", "error": str(exc)}, status=502)

    # Example success structure varies; we trust 'status' and 'data.status'
    # Expected 'status' can be "success" and data.data.status may be "success" too.
    status_text = (
        vdata.get("data", {}).get("data", {}).get("status")
        or vdata.get("data", {}).get("status")
        or vdata.get("status")
    )
    # Find the payment by our reference
    try:
        payment = Payment.objects.get(tx_ref=tx_ref)
    except Payment.DoesNotExist:
        return JsonResponse({"detail": "No local payment for tx_ref", "verify": vdata}, status=404)

    mapped = Payment.Status.PENDING
    if isinstance(status_text, str):
        st = status_text.lower()
        if st in {"success", "completed", "paid"}:
            mapped = Payment.Status.SUCCESS
        elif st in {"failed", "declined"}:
            mapped = Payment.Status.FAILED
        elif st in {"canceled", "cancelled"}:
            mapped = Payment.Status.CANCELED

    previous = payment.status
    payment.mark(mapped, verify_response=vdata)

    if previous != Payment.Status.SUCCESS and mapped == Payment.Status.SUCCESS:
        # Trigger async email
        try:
            from .tasks import send_payment_success_email
            send_payment_success_email.delay(payment.id)
        except Exception:
            # Don’t break verify endpoint if Celery not ready
            pass

    return JsonResponse({
        "tx_ref": payment.tx_ref,
        "status": payment.status,
        "booking_id": payment.booking_id,
        "raw": vdata,
    }, status=200)