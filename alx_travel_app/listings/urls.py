from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet, initiate_payment, chapa_callback, verify_payment

router = DefaultRouter()
router.register(r'listings', ListingViewSet)
router.register(r'bookings', BookingViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path("api/payments/initiate/", initiate_payment, name="payments_initiate"),
    path("api/payments/callback/", chapa_callback, name="payments_callback"),
    path("api/payments/verify/", verify_payment, name="payments_verify"),
]
