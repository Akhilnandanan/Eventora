import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from core.models import (
    User, ServiceCategory, VendorProfile, VendorServiceArea,
    ServiceListing, ServiceExtra, Booking, BookingExtra, Review
)


class Command(BaseCommand):
    help = "Seeds the database with realistic demo data for Eventora (categories, vendors, listings, bookings, reviews)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help="Delete previously seeded demo data before creating new data.",
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write("Removing previously seeded demo data...")
            User.objects.filter(username__startswith='demo_').delete()
            self.stdout.write(self.style.WARNING("Old demo data removed."))

        self.stdout.write("Seeding Eventora demo data...\n")

        categories = self.seed_categories()
        vendors = self.seed_vendors(categories)
        customers = self.seed_customers()
        self.seed_bookings_and_reviews(vendors, customers)

        self.print_credentials(vendors, customers)

    # ==========================================
    # CATEGORIES
    # ==========================================
    def seed_categories(self):
        category_data = [
            ("Photography", "bi-camera-fill"),
            ("Catering", "bi-cup-hot-fill"),
            ("Wedding Planner", "bi-heart-fill"),
            ("DJ", "bi-disc-fill"),
            ("Decoration", "bi-flower1"),
            ("Makeup Artist", "bi-brush-fill"),
            ("Live Music", "bi-music-note-beamed"),
            ("Car Rental", "bi-car-front-fill"),
        ]
        categories = []
        for name, icon in category_data:
            cat, _ = ServiceCategory.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name), 'icon': icon}
            )
            categories.append(cat)
        self.stdout.write(self.style.SUCCESS(f"  Created/verified {len(categories)} categories."))
        return categories

    # ==========================================
    # VENDORS
    # ==========================================
    def seed_vendors(self, categories):
        cities = ["Mumbai", "Pune", "Bengaluru", "Delhi", "Hyderabad", "Chennai", "Kochi", "Jaipur"]

        vendor_templates = [
            ("Shutter Stories Photography", "Photography", "Capturing candid moments with a cinematic touch. Specializing in weddings and pre-wedding shoots."),
            ("Royal Feast Catering", "Catering", "Multi-cuisine catering with a focus on authentic regional flavors, serving events of all sizes."),
            ("Dream Day Events", "Wedding Planner", "Full-service wedding planning from venue selection to day-of coordination."),
            ("BeatDrop DJ Services", "DJ", "High-energy DJ sets with professional sound and lighting for weddings and parties."),
            ("Bloom & Petal Decor", "Decoration", "Elegant floral and thematic decor for weddings, birthdays, and corporate events."),
            ("Glow Studio Makeup", "Makeup Artist", "Bridal and party makeup artistry with premium, long-lasting products."),
        ]

        vendors = []
        for i, (business_name, cat_name, description) in enumerate(vendor_templates, start=1):
            username = f"demo_vendor{i}"
            category = next((c for c in categories if c.name == cat_name), categories[0])
            home_city = random.choice(cities)

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@example.com",
                    'role': User.VENDOR,
                    'first_name': business_name.split()[0],
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()

            profile, _ = VendorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'business_name': business_name,
                    'business_description': description,
                    'service_category': category,
                    'city': home_city,
                    'is_approved': True,
                }
            )

            # Add 1-2 extra service areas, distinct from home city
            other_cities = [c for c in cities if c != home_city]
            for area_city in random.sample(other_cities, k=min(2, len(other_cities))):
                VendorServiceArea.objects.get_or_create(vendor=profile, city=area_city)

            # Create 1-2 listings per vendor
            listing_titles = [
                f"{cat_name} Package — Basic",
                f"{cat_name} Package — Premium",
            ]
            price_units = ['per_event', 'per_hour', 'per_day']
            for title in listing_titles[:random.choice([1, 2])]:
                listing, _ = ServiceListing.objects.get_or_create(
                    vendor=profile,
                    title=title,
                    defaults={
                        'category': category,
                        'description': f"{description} This package covers {title.split('—')[-1].strip().lower()} tier service.",
                        'price': random.choice([5000, 8000, 12000, 15000, 25000, 35000]),
                        'price_unit': random.choice(price_units),
                        'is_active': True,
                    }
                )
                # Add a random extra to some listings
                if random.choice([True, False]):
                    ServiceExtra.objects.get_or_create(
                        listing=listing,
                        title="Extra Hour Coverage",
                        defaults={'price': 2000, 'is_active': True}
                    )

            vendors.append({'user': user, 'profile': profile, 'password': 'demo1234'})

        self.stdout.write(self.style.SUCCESS(f"  Created/verified {len(vendors)} vendors with listings."))
        return vendors

    # ==========================================
    # CUSTOMERS
    # ==========================================
    def seed_customers(self):
        customer_names = ["Aditi Sharma", "Rohan Mehta", "Priya Nair", "Karan Kapoor"]
        customers = []
        for i, full_name in enumerate(customer_names, start=1):
            username = f"demo_customer{i}"
            first, last = full_name.split()
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@example.com",
                    'role': User.CUSTOMER,
                    'first_name': first,
                    'last_name': last,
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()
            customers.append({'user': user, 'password': 'demo1234'})

        self.stdout.write(self.style.SUCCESS(f"  Created/verified {len(customers)} customers."))
        return customers

    # ==========================================
    # BOOKINGS + REVIEWS
    # ==========================================
    def seed_bookings_and_reviews(self, vendors, customers):
        review_comments = [
            "Absolutely wonderful experience, highly recommend!",
            "Professional, punctual, and exceeded our expectations.",
            "Great value for the price, would book again.",
            "The team was fantastic to work with throughout our event.",
        ]

        booking_count = 0
        review_count = 0

        for vendor_data in vendors:
            profile = vendor_data['profile']
            listings = list(profile.listings.all())
            if not listings:
                continue

            for customer_data in random.sample(customers, k=min(2, len(customers))):
                customer = customer_data['user']
                listing = random.choice(listings)
                event_date = date.today() + timedelta(days=random.randint(-60, 60))

                status = random.choice([
                    Booking.STATUS_PENDING,
                    Booking.STATUS_CONFIRMED,
                    Booking.STATUS_COMPLETED,
                ])

                booking, created = Booking.objects.get_or_create(
                    customer=customer,
                    listing=listing,
                    vendor=profile,
                    event_date=event_date,
                    defaults={
                        'event_city': profile.city,
                        'venue_name': "Grand Celebration Hall",
                        'status': status,
                        'is_paid': status == Booking.STATUS_COMPLETED,
                    }
                )
                if created:
                    booking_count += 1

                    if status == Booking.STATUS_COMPLETED:
                        Review.objects.get_or_create(
                            booking=booking,
                            defaults={
                                'vendor': profile,
                                'customer': customer,
                                'rating': random.randint(4, 5),
                                'comment': random.choice(review_comments),
                            }
                        )
                        review_count += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {booking_count} bookings and {review_count} reviews."))

    # ==========================================
    # PRINT CREDENTIALS
    # ==========================================
    def print_credentials(self, vendors, customers):
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("DEMO LOGIN CREDENTIALS"))
        self.stdout.write("=" * 50)

        self.stdout.write("\nVENDORS (all passwords: demo1234):")
        for v in vendors:
            self.stdout.write(f"  {v['user'].username}  —  {v['profile'].business_name}")

        self.stdout.write("\nCUSTOMERS (all passwords: demo1234):")
        for c in customers:
            self.stdout.write(f"  {c['user'].username}  —  {c['user'].first_name} {c['user'].last_name}")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("These credentials are also saved in DEMO_CREDENTIALS.md")
        self.stdout.write("=" * 50 + "\n")