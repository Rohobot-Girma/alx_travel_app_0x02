
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Listing(models.Model):
    """Represents a travel listing."""
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Booking(models.Model):
    """Represents a booking for a listing by a user."""
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} booking for {self.listing.title}"


class Review(models.Model):
    """User review for a listing."""
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} by {self.user.username} on {self.listing.title}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ETB")  # ETB or USD per docs
    tx_ref = models.CharField(max_length=64, unique=True)  # your unique reference
    chapa_ref_id = models.CharField(max_length=64, blank=True)  # Chapa ref (ref_id)
    checkout_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    # Raw API echoes (useful for audit/debug)
    init_response = models.JSONField(null=True, blank=True)
    verify_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def mark(self, status: str, verify_response: dict | None = None):
        self.status = status
        if verify_response is not None:
            self.verify_response = verify_response
            # capture chapa ref if present
            ref_id = (
                    verify_response.get("data", {}).get("data", {}).get("reference")
                    or verify_response.get("data", {}).get("reference")
                    or verify_response.get("reference")
            )
            if ref_id:
                self.chapa_ref_id = ref_id
        self.save()

    def __str__(self):
        return f"{self.tx_ref} [{self.status}]"
