#!/usr/bin/env python3
"""
Management command to seed the database with sample data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from alx_travel_app.listings.models import Listing, Booking, Review
from decimal import Decimal
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        
        # Create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write('Created test user')
        
        # Create sample listings
        listings_data = [
            {
                'title': 'Beautiful Beach House',
                'description': 'A stunning beach house with ocean views and modern amenities.',
                'location': 'Malibu, California',
                'price_per_night': Decimal('250.00')
            },
            {
                'title': 'Mountain Cabin Retreat',
                'description': 'Cozy cabin in the mountains perfect for a peaceful getaway.',
                'location': 'Aspen, Colorado',
                'price_per_night': Decimal('180.00')
            },
            {
                'title': 'City Center Apartment',
                'description': 'Modern apartment in the heart of the city with great amenities.',
                'location': 'New York, NY',
                'price_per_night': Decimal('320.00')
            },
            {
                'title': 'Lakeside Cottage',
                'description': 'Charming cottage by the lake with fishing and boating access.',
                'location': 'Lake Tahoe, California',
                'price_per_night': Decimal('200.00')
            }
        ]
        
        for listing_data in listings_data:
            listing, created = Listing.objects.get_or_create(
                title=listing_data['title'],
                defaults=listing_data
            )
            if created:
                self.stdout.write(f'Created listing: {listing.title}')
        
        # Create sample bookings
        listings = Listing.objects.all()
        if listings.exists():
            listing = listings.first()
            check_in = date.today() + timedelta(days=7)
            check_out = check_in + timedelta(days=3)
            
            booking, created = Booking.objects.get_or_create(
                listing=listing,
                user=user,
                check_in=check_in,
                check_out=check_out
            )
            if created:
                self.stdout.write(f'Created booking for {listing.title}')
        
        # Create sample reviews
        for listing in listings[:2]:  # Add reviews to first two listings
            review, created = Review.objects.get_or_create(
                listing=listing,
                user=user,
                defaults={
                    'rating': 5,
                    'comment': 'Amazing place! Highly recommended.'
                }
            )
            if created:
                self.stdout.write(f'Created review for {listing.title}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded database!')
        )