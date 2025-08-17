from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment

@shared_task
def send_payment_success_email(payment_id: int):
    payment = Payment.objects.select_related("booking").get(id=payment_id)
    booking = payment.booking
    recipient = booking.user.email  # adjust to your booking/user model
    subject = f"Payment received for Booking #{booking.id}"
    body = (
        f"Hi {booking.user.first_name},\n\n"
        f"We've received your payment of {payment.amount} {payment.currency} "
        f"for booking #{booking.id} (tx_ref: {payment.tx_ref}).\n\n"
        f"Thank you!"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
