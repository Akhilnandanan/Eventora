from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    """
    Custom User model for Eventora.
    """

    CUSTOMER = 'customer'
    VENDOR = 'vendor'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (VENDOR, 'Vendor'),
        (ADMIN, 'Admin'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=CUSTOMER,
        help_text="Determines what type of account this is and what dashboard/permissions apply."
    )

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Superusers are always Eventora admins
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

    def is_customer(self):
        return self.role == self.CUSTOMER

    def is_vendor(self):
        return self.role == self.VENDOR

    def is_admin_role(self):
        return self.role == self.ADMIN


class ServiceCategory(models.Model):
    """
    Represents a type of event service (Photography, Catering, DJ, etc.).

    Why its own model? So Admins can add/edit/remove categories from
    Django Admin WITHOUT touching code, and so every vendor/listing
    references the SAME consistent set of categories (no typos, no duplicates).
    """

    name = models.CharField(max_length=100, unique=True)

    # Slug = a URL-friendly version of the name, e.g. "Wedding Planner" -> "wedding-planner"
    # Used later for clean category URLs like /services/category/wedding-planner/
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    # Bootstrap Icons class name (e.g. "bi-camera") — used to show a little icon
    # next to the category on the browse page. Optional, purely cosmetic.
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional Bootstrap Icons class, e.g. 'bi-camera-fill'"
    )

    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate the slug from the name if it wasn't set manually.
        # This runs every time save() is called, BEFORE the row is written to DB.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"
        ordering = ['name']  # Always return categories alphabetically sorted


class VendorProfile(models.Model):
    """
    Extra business-specific information that ONLY vendors need.

    CHANGE FROM PHASE 2: service_category is now a ForeignKey to
    ServiceCategory instead of a plain CharField. This is the vendor's
    PRIMARY/main category (e.g. "I am primarily a Photographer"),
    while individual ServiceListings can still technically differ if
    a vendor offers cross-category packages later.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_profile',
        limit_choices_to={'role': User.VENDOR},
    )

    business_name = models.CharField(max_length=200)
    business_description = models.TextField(blank=True)

    # CHANGED: was CharField, now a proper relationship
    service_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,  # Prevents deleting a category that vendors depend on
        related_name='vendors',
        help_text="Primary category this vendor operates in."
    )

    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)

    is_approved = models.BooleanField(
        default=False,
        help_text="Vendor listings only appear publicly after Admin approval."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} — {self.service_category}"
    

    def average_rating(self):
        """
        Returns the average star rating across all reviews for this vendor,
        rounded to 1 decimal place. Returns None if there are no reviews yet
        (so templates can show "No reviews yet" instead of "0.0").
        """
        reviews = self.reviews.all()
        if not reviews.exists():
            return None
        total = sum(review.rating for review in reviews)
        return round(total / reviews.count(), 1)

    def review_count(self):
        return self.reviews.count()

    class Meta:
        verbose_name = "Vendor Profile"
        verbose_name_plural = "Vendor Profiles"


class VendorPortfolioImage(models.Model):
    """
    A photo of the vendor's past work, shown on their PUBLIC PROFILE page
    (not tied to any specific ServiceListing). Represents their general
    portfolio/history, e.g. a photographer showing highlights across many
    different past events.
    """

    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='portfolio_images'
    )
    image = models.ImageField(upload_to='vendor_portfolio/')
    caption = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vendor Portfolio Image"
        verbose_name_plural = "Vendor Portfolio Images"
        ordering = ['-created_at']

    def __str__(self):
        return f"Portfolio image for {self.vendor.business_name}"

class VendorServiceArea(models.Model):
    """
    An ADDITIONAL city a vendor is willing to serve, beyond their primary
    VendorProfile.city (which represents where they're based/HQ'd).

    Example: a vendor based in Mumbai (VendorProfile.city) might also
    travel to Pune and Thane for events — those go here.
    """

    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='service_areas'
    )
    city = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Vendor Service Area"
        verbose_name_plural = "Vendor Service Areas"
        unique_together = ('vendor', 'city')  # Prevents the same city being added twice for one vendor
        ordering = ['city']

    def __str__(self):
        return f"{self.vendor.business_name} → {self.city}"
    
class ServiceListing(models.Model):
    """
    An individual bookable service/package offered by a vendor.

    This is what Customers will actually browse and eventually book.
    One VendorProfile can have MANY ServiceListings (ForeignKey, not OneToOne).
    """

    PRICE_UNIT_CHOICES = [
        ('per_event', 'Per Event'),
        ('per_hour', 'Per Hour'),
        ('per_day', 'Per Day'),
        ('per_person', 'Per Person'),
    ]

    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,   # If vendor account is deleted, their listings go too
        related_name='listings'
    )

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='listings',
        help_text="Category this specific listing belongs to."
    )

    title = models.CharField(
        max_length=200,
        help_text="E.g. 'Wedding Photography — Full Day Coverage'"
    )
    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base price in INR (₹)"
    )
    price_unit = models.CharField(max_length=20, choices=PRICE_UNIT_CHOICES, default='per_event')

    cover_image = models.ImageField(
        upload_to='service_listings/',
        blank=True,
        null=True,
        help_text="Main image customers see in listing cards."
    )

    # Vendor can temporarily hide a listing without deleting it (e.g. fully booked season)
    FOOD_TYPE_CHOICES = [
        ('not_applicable', 'Not Applicable'),
        ('veg', 'Vegetarian'),
        ('non_veg', 'Non-Vegetarian'),
        ('both', 'Both Veg & Non-Veg'),
    ]
    food_type = models.CharField(
        max_length=20,
        choices=FOOD_TYPE_CHOICES,
        default='not_applicable',
        help_text="Only relevant for food/catering listings."
    )

    # Vendor can temporarily hide a listing without deleting it (e.g. fully booked season)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive listings are hidden from public browsing."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} — {self.vendor.business_name}"

    def is_publicly_visible(self):
        """
        Convenience method: a listing is only visible to the public if
        BOTH the listing itself is active AND the vendor is admin-approved.
        We centralize this logic here so every view/template uses the
        SAME rule — avoids inconsistent visibility bugs later.
        """
        return self.is_active and self.vendor.is_approved

    class Meta:
        verbose_name = "Service Listing"
        verbose_name_plural = "Service Listings"
        ordering = ['-created_at']  # Newest listings first

class ListingImage(models.Model):
    """
    An ADDITIONAL photo for a ServiceListing, shown in a gallery on the
    listing's detail page. The listing's main cover_image (used on browse
    cards) stays unchanged - this is purely supplementary.
    """

    listing = models.ForeignKey(
        ServiceListing,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    image = models.ImageField(upload_to='listing_gallery/')
    caption = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Listing Image"
        verbose_name_plural = "Listing Images"
        ordering = ['created_at']

    def __str__(self):
        return f"Image for {self.listing.title}"


class Booking(models.Model):
    """
    Represents a Customer's request to book a specific ServiceListing
    for a specific event date.

    Lifecycle:
        pending -> confirmed -> completed
                -> rejected
        pending/confirmed -> cancelled
    """

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_REJECTED = 'rejected'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings_made',
        limit_choices_to={'role': User.CUSTOMER},
    )

    listing = models.ForeignKey(
        ServiceListing,
        on_delete=models.CASCADE,
        related_name='bookings'
    )

    # Denormalized reference for convenience/query speed — the vendor is
    # ALWAYS listing.vendor, but storing it directly here means we can
    # filter "all bookings for this vendor" without an extra join through
    # ServiceListing every single time. Small, deliberate trade-off.
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='bookings_received'
    )

    event_date = models.DateField(help_text="The date the customer needs this service for.")

   

    venue_name = models.CharField(
        max_length=200,
        help_text="e.g. 'Grand Palace Banquet Hall'"
    )
    venue_address = models.TextField(
        help_text="Full venue address"
    )
    event_city = models.CharField(
        max_length=100,
        help_text="City where the event will take place"
    )

    customer_notes = models.TextField(
        blank=True,
        help_text="Any other special requests (optional)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

# Vendor can leave a short note when accepting/rejecting (e.g. reason for rejection)
    vendor_response_note = models.TextField(blank=True)

    # Fake payment tracking - no real payment gateway is involved.
    # Payment only becomes possible once status='confirmed' (see views.py).
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(
        max_length=20,
        blank=True,
        help_text="Fake payment reference generated on mock payment completion."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Percentage Eventora keeps as a platform fee from each completed booking.
    # Change this single value to adjust the fee platform-wide.
    PLATFORM_FEE_PERCENT = 10

    def total_price(self):
        """
        Base listing price + sum of all selected extras' snapshotted prices.
        This is the full amount the CUSTOMER pays - not what the platform
        or vendor individually earns from it.
        """
        extras_total = sum(e.price_snapshot for e in self.selected_extras.all())
        return self.listing.price + extras_total

    def platform_fee(self):
        """
        The portion of total_price() that Eventora (the platform) keeps
        as a commission. The remainder goes to the vendor.
        """
        return round(self.total_price() * self.PLATFORM_FEE_PERCENT / 100, 2)

    def vendor_payout(self):
        """
        The portion of total_price() the VENDOR actually receives, after
        the platform fee is deducted.
        """
        return self.total_price() - self.platform_fee()

    def __str__(self):
        return f"{self.customer.username} → {self.listing.title} ({self.status})"

    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def is_confirmed(self):
        return self.status == self.STATUS_CONFIRMED

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ['-created_at']  # Newest bookings first


class Review(models.Model): 
    """
    A Customer's review + star rating for a COMPLETED booking.

    Linking to Booking (not directly to Vendor) proves the reviewer
    actually had a real, finished service experience with this vendor.
    """

    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review',
        help_text="Each completed booking can have AT MOST one review."
    )

    # Denormalized for the same reason as Booking.vendor — lets us query
    # "all reviews for this vendor" directly, without joining through
    # booking -> listing -> vendor every time.
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_written'
    )

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating}★ by {self.customer.username} for {self.vendor.business_name}"

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ['-created_at']



class ServiceExtra(models.Model):
    """
    An optional add-on a vendor can offer on top of a base ServiceListing
    (e.g. "+1 Hour Coverage", "+Drone Shots"). Purely optional — a listing
    can have zero extras and still work exactly as it does today.
    """

    listing = models.ForeignKey(
        ServiceListing,
        on_delete=models.CASCADE,
        related_name='extras'
    )

    title = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive extras are hidden from customers but kept for past booking records."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (+₹{self.price})"

    class Meta:
        verbose_name = "Service Extra"
        verbose_name_plural = "Service Extras"
        ordering = ['title']


class BookingExtra(models.Model):
    """
    Records which extras a customer selected on a specific Booking, with
    the title/price SNAPSHOTTED at the time of booking.

    Why snapshot instead of just linking to ServiceExtra? If a vendor later
    changes an extra's price (or deletes it), a booking made last month
    should still show what the customer actually agreed to pay — not
    silently change. This is the same "preserve historical accuracy"
    principle we already used for Booking.vendor (denormalized in Phase 5).
    """

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='selected_extras'
    )
    extra = models.ForeignKey(
        ServiceExtra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking_selections',
        help_text="Reference to the original extra, if it still exists."
    )

    title_snapshot = models.CharField(max_length=150)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.title_snapshot} (+₹{self.price_snapshot})"

    class Meta:
        verbose_name = "Booking Extra"
        verbose_name_plural = "Booking Extras"


class Conversation(models.Model):
    """
    Represents a conversation between a customer and a vendor.
    Only one conversation can exist between a specific customer and vendor.
    """
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations',
        limit_choices_to={'role': User.CUSTOMER}
    )
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        unique_together = ('customer', 'vendor')  # Prevent duplicate conversations
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat: {self.customer.username} ↔ {self.vendor.business_name}"

    def last_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.first()

    def unread_count(self, user):
        """Count unread messages for a specific user"""
        if user.is_customer():
            return self.messages.filter(vendor_read=False).count()
        else:
            return self.messages.filter(customer_read=False).count()

    def unread_count_customer(self):
        """Count unread messages for customer (sent by vendor)"""
        return self.messages.filter(vendor_read=False).count()

    def unread_count_vendor(self):
        """Count unread messages for vendor (sent by customer)"""
        return self.messages.filter(customer_read=False).count()


class Message(models.Model):
    """
    An individual message within a conversation.
    Tracks read status for both customer and vendor.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    customer_read = models.BooleanField(default=False)
    vendor_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['-created_at']

    def __str__(self):
        sender_name = self.sender.username
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{sender_name}: {preview}"


class FavoriteVendor(models.Model):
    """
    Allows customers to save vendors to their wishlist/favorites for later reference.
    """
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_vendors',
        limit_choices_to={'role': User.CUSTOMER}
    )
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(
        blank=True,
        help_text="Personal notes about this vendor (e.g., 'Great for weddings', 'Good price')"
    )

    class Meta:
        verbose_name = "Favorite Vendor"
        verbose_name_plural = "Favorite Vendors"
        unique_together = ('customer', 'vendor')  # Prevent duplicate favorites
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.username} ❤️ {self.vendor.business_name}"