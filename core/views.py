import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Q

from .forms import (
    CustomerSignUpForm, VendorSignUpForm, ServiceListingForm,
    BookingRequestForm, VendorBookingResponseForm, ReviewForm,
    CustomerProfileForm, VendorUserForm, VendorProfileEditForm,
    ServiceExtraFormSet, VendorServiceAreaFormSet, ListingImageFormSet,
    VendorPortfolioImageFormSet, MessageForm, FavoriteVendorForm
)
from .decorators import customer_required, vendor_required, admin_required
from .models import (
    ServiceCategory, ServiceListing, Booking, Review, VendorProfile, User,
    ServiceExtra, BookingExtra, VendorServiceArea, Conversation, Message,
    FavoriteVendor, VendorPortfolioImage
)
def home(request):
    """
    Public landing page for Eventora.
    """
    categories = ServiceCategory.objects.all()[:6]

    approved_vendors = list(VendorProfile.objects.filter(is_approved=True).select_related('service_category'))
    approved_vendors.sort(key=lambda v: v.average_rating() or 0, reverse=True)
    featured_vendors = approved_vendors[:4]

    testimonials = Review.objects.exclude(comment='').select_related('customer', 'vendor').order_by('-created_at')[:6]

    context = {
        'categories': categories,
        'featured_vendors': featured_vendors,
        'testimonials': testimonials,
    }
    return render(request, 'core/home.html', context)


def customer_signup(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Eventora, {user.username}!")
            return redirect('core:home')
    else:
        form = CustomerSignUpForm()
    return render(request, 'core/customer_signup.html', {'form': form})


def vendor_signup(request):
    if request.method == 'POST':
        form = VendorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to Eventora, {user.username}! Your vendor profile is "
                f"pending Admin approval before it appears publicly."
            )
            return redirect('core:home')
    else:
        form = VendorSignUpForm()
    return render(request, 'core/vendor_signup.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('core:home')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'core/login.html')


def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('core:home')

def forgot(request):
    return render(request,'forgot.html')          


@customer_required
def customer_dashboard(request):
    return render(request, 'core/customer_dashboard.html')


@vendor_required
def vendor_dashboard(request):
    listings = request.user.vendor_profile.listings.all()
    pending_bookings = Booking.objects.filter(
        vendor=request.user.vendor_profile,
        status=Booking.STATUS_PENDING
    )
    context = {
        'listings_count': listings.count(),
        'pending_bookings_count': pending_bookings.count(),
    }
    return render(request, 'core/vendor_dashboard.html', context)

def _calculate_total_booking_value():
    """
    Sums total_price() (base + extras) across all COMPLETED bookings.
    Done in Python since total_price() depends on related BookingExtra
    rows, which can't be summed directly via a single database aggregate.
    """
    completed = Booking.objects.filter(status=Booking.STATUS_COMPLETED).prefetch_related('selected_extras')
    return sum(b.total_price() for b in completed)


def _calculate_platform_revenue():
    """
    Sums platform_fee() across all COMPLETED bookings - the actual
    commission Eventora earns, as opposed to total transaction value.
    """
    completed = Booking.objects.filter(status=Booking.STATUS_COMPLETED).prefetch_related('selected_extras')
    return sum(b.platform_fee() for b in completed)



@admin_required
def admin_dashboard(request):
    context = {
        'total_customers': User.objects.filter(role=User.CUSTOMER).count(),
        'total_vendors': VendorProfile.objects.count(),
        'pending_vendors_count': VendorProfile.objects.filter(is_approved=False).count(),

        'total_listings': ServiceListing.objects.count(),
        'active_listings': ServiceListing.objects.filter(is_active=True).count(),

        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status=Booking.STATUS_PENDING).count(),
        'confirmed_bookings': Booking.objects.filter(status=Booking.STATUS_CONFIRMED).count(),
        'completed_bookings': Booking.objects.filter(status=Booking.STATUS_COMPLETED).count(),

        # Total booking value: the full amount customers paid across all
        # COMPLETED bookings (base price + extras). This is GROSS transaction
        # value flowing through the platform - NOT what Eventora itself earns.
        'total_booking_value': _calculate_total_booking_value(),
        'platform_revenue': _calculate_platform_revenue(),

        'total_reviews': Review.objects.count(),
        'platform_fee_percent': Booking.PLATFORM_FEE_PERCENT,
    }

    return render(request, 'core/admin_dashboard.html', context)


# ==========================================
# VENDOR: SERVICE LISTING MANAGEMENT
# ==========================================

@vendor_required
def my_services(request):
    listings = request.user.vendor_profile.listings.all()
    return render(request, 'core/my_services.html', {'listings': listings})


@vendor_required
def add_service(request):
    if request.method == 'POST':
        form = ServiceListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.vendor = request.user.vendor_profile
            listing.save()
            messages.success(request, "Service listing created successfully!")
            return redirect('core:my_services')
    else:
        form = ServiceListingForm()

    return render(request, 'core/add_service.html', {'form': form})


@vendor_required
def edit_service(request, listing_id):
    """
    Lets a vendor edit ONE of their own listings, and manage that listing's
    optional extras AND gallery photos on the same page via formsets.
    """
    listing = get_object_or_404(
        ServiceListing,
        id=listing_id,
        vendor=request.user.vendor_profile
    )

    if request.method == 'POST':
        form = ServiceListingForm(request.POST, request.FILES, instance=listing)
        extra_formset = ServiceExtraFormSet(request.POST, instance=listing)
        image_formset = ListingImageFormSet(request.POST, request.FILES, instance=listing)

        if form.is_valid() and extra_formset.is_valid() and image_formset.is_valid():
            form.save()
            extra_formset.save()
            image_formset.save()
            messages.success(request, "Service listing updated successfully!")
            return redirect('core:my_services')
    else:
        form = ServiceListingForm(instance=listing)
        extra_formset = ServiceExtraFormSet(instance=listing)
        image_formset = ListingImageFormSet(instance=listing)

    context = {
        'form': form,
        'listing': listing,
        'extra_formset': extra_formset,
        'image_formset': image_formset,
    }
    return render(request, 'core/edit_service.html', context)

@vendor_required
def delete_service(request, listing_id):
    listing = get_object_or_404(
        ServiceListing,
        id=listing_id,
        vendor=request.user.vendor_profile
    )
    listing.delete()
    messages.success(request, "Service listing deleted.")
    return redirect('core:my_services')


# ==========================================
# PUBLIC: BROWSE SERVICES (no login required)
# ==========================================

def browse_services(request):
    """
    Public page - anyone (even logged-out visitors) can browse services.
    Supports combining MULTIPLE filters at once: category, search keyword,
    city, and min/max price range.
    """
    listings = ServiceListing.objects.filter(
        is_active=True,
        vendor__is_approved=True
    ).select_related('vendor', 'category')

    category_slug = request.GET.get('category', '')
    if category_slug:
        listings = listings.filter(category__slug=category_slug)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        listings = listings.filter(
            Q(title__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(vendor__business_name__icontains=search_query)
        )

    city = request.GET.get('city', '').strip()
    if city:
        listings = listings.filter(
            Q(vendor__city__iexact=city) | Q(vendor__service_areas__city__iexact=city)
        ).distinct()

    food_type = request.GET.get('food_type', '').strip()
    if food_type:
        listings = listings.filter(food_type=food_type)

    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    if min_price:
        try:
            listings = listings.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            listings = listings.filter(price__lte=float(max_price))
        except ValueError:
            pass

    categories = ServiceCategory.objects.all()

    home_cities = VendorProfile.objects.filter(
        is_approved=True
    ).exclude(city='').values_list('city', flat=True)
    served_cities = VendorServiceArea.objects.filter(
        vendor__is_approved=True
    ).values_list('city', flat=True)
    cities = sorted(set(list(home_cities) + list(served_cities)))

    context = {
        'listings': listings,
        'categories': categories,
        'cities': cities,
        'selected_category': category_slug,
        'search_query': search_query,
        'selected_city': city,
        'min_price': min_price,
        'max_price': max_price,
        'selected_food_type': food_type,
    }
    return render(request, 'core/browse_services.html', context)


def service_detail(request, listing_id):
    listing = get_object_or_404(
        ServiceListing,
        id=listing_id,
        is_active=True,
        vendor__is_approved=True
    )
    return render(request, 'core/service_detail.html', {'listing': listing})


# ==========================================
# CUSTOMER: BOOKING REQUESTS
# ==========================================

@customer_required
def request_booking(request, listing_id):
    """
    Lets a logged-in Customer fill out booking details for a specific
    listing. On valid submission, we do NOT save a Booking yet - instead
    we stash the validated data in the session and redirect to a checkout
    summary page, where the customer reviews everything before confirming.
    """
    listing = get_object_or_404(
        ServiceListing,
        id=listing_id,
        is_active=True,
        vendor__is_approved=True
    )

    if request.method == 'POST':
        form = BookingRequestForm(request.POST, listing=listing)
        if form.is_valid():
            # Stash validated, cleaned data in the session. We store
            # extras as a list of IDs (not model objects - sessions can
            # only hold JSON-serializable data).
            request.session['pending_booking'] = {
                'listing_id': listing.id,
                'event_date': form.cleaned_data['event_date'].isoformat(),
                'venue_name': form.cleaned_data['venue_name'],
                'venue_address': form.cleaned_data['venue_address'],
                'event_city': form.cleaned_data['event_city'],
                'customer_notes': form.cleaned_data['customer_notes'],
                'extra_ids': [e.id for e in form.cleaned_data['extras']],
            }
            return redirect('core:booking_checkout')
    else:
        form = BookingRequestForm(listing=listing)

    context = {
        'form': form,
        'listing': listing,
        'has_extras': listing.extras.filter(is_active=True).exists(),
    }
    return render(request, 'core/request_booking.html', context)


@customer_required
def booking_checkout(request):
    """
    Fake checkout / review screen. Shows a summary of the pending booking
    (staged in the session by request_booking) - listing, date, venue,
    extras, and total price - before anything is actually saved.

    Re-validates the listing is STILL active/approved and re-fetches
    extras fresh from the database (not trusting stale session data for
    pricing), so nothing stale or tampered-with slips through.
    """
    pending = request.session.get('pending_booking')
    if not pending:
        messages.error(request, "Your booking session expired or is invalid. Please start again.")
        return redirect('core:browse_services')

    listing = get_object_or_404(
        ServiceListing,
        id=pending['listing_id'],
        is_active=True,
        vendor__is_approved=True
    )

    selected_extras = ServiceExtra.objects.filter(
        id__in=pending['extra_ids'],
        listing=listing,
        is_active=True
    )
    extras_total = sum(e.price for e in selected_extras)
    total_price = listing.price + extras_total

    if request.method == 'POST':
        # Customer clicked "Confirm Booking" - NOW we actually create the record.
        booking = Booking.objects.create(
            customer=request.user,
            listing=listing,
            vendor=listing.vendor,
            event_date=pending['event_date'],
            venue_name=pending['venue_name'],
            venue_address=pending['venue_address'],
            event_city=pending['event_city'],
            customer_notes=pending['customer_notes'],
            status=Booking.STATUS_PENDING,
        )

        for extra in selected_extras:
            BookingExtra.objects.create(
                booking=booking,
                extra=extra,
                title_snapshot=extra.title,
                price_snapshot=extra.price,
            )

        # Clear the staged data now that it's been committed - prevents
        # accidentally re-submitting the same booking twice via back button.
        del request.session['pending_booking']

        messages.success(
            request,
            f"Booking request sent to {listing.vendor.business_name}! "
            f"You'll be notified once they respond."
        )
        return redirect('core:my_bookings')

    context = {
        'listing': listing,
        'pending': pending,
        'selected_extras': selected_extras,
        'total_price': total_price,
    }
    return render(request, 'core/booking_checkout.html', context)

@customer_required
def my_bookings(request):
    bookings = Booking.objects.filter(customer=request.user).select_related('listing', 'vendor')
    return render(request, 'core/my_bookings.html', {'bookings': bookings})


@customer_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

    if booking.status in [Booking.STATUS_PENDING, Booking.STATUS_CONFIRMED]:
        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        messages.success(request, "Booking cancelled.")
    else:
        messages.error(request, "This booking can no longer be cancelled.")

    return redirect('core:my_bookings')


# ==========================================
# VENDOR: MANAGE BOOKING REQUESTS
# ==========================================

@vendor_required
def booking_requests(request):
    bookings = Booking.objects.filter(
        vendor=request.user.vendor_profile
    ).select_related('customer', 'listing')
    return render(request, 'core/booking_requests.html', {'bookings': bookings})


@vendor_required
def respond_booking(request, booking_id, action):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        vendor=request.user.vendor_profile
    )

    if booking.status != Booking.STATUS_PENDING:
        messages.error(request, "This booking has already been responded to.")
        return redirect('core:booking_requests')

    if request.method == 'POST':
        form = VendorBookingResponseForm(request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)

            if action == 'accept':
                booking.status = Booking.STATUS_CONFIRMED
                messages.success(request, "Booking confirmed!")
            elif action == 'reject':
                booking.status = Booking.STATUS_REJECTED
                messages.success(request, "Booking rejected.")

            booking.save()
            return redirect('core:booking_requests')
    else:
        form = VendorBookingResponseForm(instance=booking)

    context = {'form': form, 'booking': booking, 'action': action}
    return render(request, 'core/respond_booking.html', context)


@vendor_required
def mark_booking_completed(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        vendor=request.user.vendor_profile
    )

    if booking.status == Booking.STATUS_CONFIRMED:
        booking.status = Booking.STATUS_COMPLETED
        booking.save()
        messages.success(request, "Booking marked as completed.")
    else:
        messages.error(request, "Only confirmed bookings can be marked completed.")

    return redirect('core:booking_requests')


# ==========================================
# CUSTOMER: REVIEWS
# ==========================================

@customer_required
def add_review(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        customer=request.user,
        status=Booking.STATUS_COMPLETED
    )

    if hasattr(booking, 'review'):
        messages.error(request, "You've already reviewed this booking.")
        return redirect('core:my_bookings')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.vendor = booking.vendor
            review.customer = request.user
            review.save()
            messages.success(request, "Thank you for your review!")
            return redirect('core:my_bookings')
    else:
        form = ReviewForm()

    return render(request, 'core/add_review.html', {'form': form, 'booking': booking})


# ==========================================
# PUBLIC: VENDOR PROFILE PAGE
# ==========================================

def vendor_public_profile(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, id=vendor_id)

    # Check authorization if unapproved
    is_owner = request.user.is_authenticated and hasattr(request.user, 'vendor_profile') and request.user.vendor_profile == vendor
    is_admin = request.user.is_authenticated and request.user.is_admin_role()

    if not vendor.is_approved and not (is_owner or is_admin):
        raise Http404("This vendor profile is currently not available.")

    listings = vendor.listings.filter(is_active=True)
    reviews = vendor.reviews.all().select_related('customer')

    # Check if vendor is in user's wishlist
    is_favorited = False
    if request.user.is_authenticated and request.user.is_customer():
        is_favorited = FavoriteVendor.objects.filter(
            customer=request.user,
            vendor=vendor
        ).exists()

    context = {
        'vendor': vendor,
        'listings': listings,
        'reviews': reviews,
        'is_favorited': is_favorited,
        'is_owner': is_owner,
        'is_admin': is_admin,
    }
    return render(request, 'core/vendor_public_profile.html', context)


# ==========================================
# ADMIN: VENDOR APPROVAL & DIRECTORY
# ==========================================

@admin_required
def vendor_approval_queue(request):
    pending_vendors = VendorProfile.objects.filter(is_approved=False).select_related('user', 'service_category')
    return render(request, 'core/vendor_approval_queue.html', {'vendors': pending_vendors})


@admin_required
def approve_vendor(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    vendor.is_approved = True
    vendor.save()
    messages.success(request, f"{vendor.business_name} has been approved.")
    return redirect('core:vendor_approval_queue')


@admin_required
def unapprove_vendor(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, id=vendor_id, is_approved=True)
    vendor.is_approved = False
    vendor.save()
    messages.success(request, f"{vendor.business_name} has been unapproved and hidden from public listings.")
    return redirect('core:vendor_directory')


@admin_required
def reject_vendor(request, vendor_id):
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    business_name = vendor.business_name
    vendor.delete()
    messages.success(request, f"{business_name}'s application has been rejected.")
    return redirect('core:vendor_approval_queue')


@admin_required
def vendor_directory(request):
    vendors = VendorProfile.objects.all().select_related('user', 'service_category')
    return render(request, 'core/vendor_directory.html', {'vendors': vendors})


@admin_required
def all_bookings_overview(request):
    bookings = Booking.objects.all().select_related('customer', 'listing', 'vendor')

    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    context = {
        'bookings': bookings,
        'status_filter': status_filter,
        'status_choices': Booking.STATUS_CHOICES,
    }
    return render(request, 'core/all_bookings_overview.html', context)


# ==========================================
# PROFILE & SETTINGS
# ==========================================

@customer_required
def customer_profile(request):
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('core:customer_profile')
    else:
        form = CustomerProfileForm(instance=request.user)

    return render(request, 'core/customer_profile.html', {'form': form})

@vendor_required
def vendor_settings(request):
    """
    Lets a Vendor edit their User info, business info, cities served, AND
    their public portfolio gallery, including uploading multiple photos at once.
    """
    vendor_profile = request.user.vendor_profile

    if request.method == 'POST':
        user_form = VendorUserForm(request.POST, request.FILES, instance=request.user)
        profile_form = VendorProfileEditForm(request.POST, instance=vendor_profile)
        area_formset = VendorServiceAreaFormSet(request.POST, instance=vendor_profile)
        portfolio_formset = VendorPortfolioImageFormSet(request.POST, request.FILES, instance=vendor_profile)

        # Get multiple files uploaded via bulk_portfolio_photos field
        bulk_photos = request.FILES.getlist('bulk_portfolio_photos')

        if user_form.is_valid() and profile_form.is_valid() and area_formset.is_valid() and portfolio_formset.is_valid():
            user_form.save()
            profile_form.save()
            area_formset.save()
            portfolio_formset.save()

            added_count = 0
            if bulk_photos:
                for photo in bulk_photos:
                    VendorPortfolioImage.objects.create(
                        vendor=vendor_profile,
                        image=photo
                    )
                    added_count += 1

            if added_count > 0:
                messages.success(request, f"Business settings updated and {added_count} portfolio photo(s) added!")
            else:
                messages.success(request, "Your business settings have been updated.")
            return redirect('core:vendor_settings')
    else:
        user_form = VendorUserForm(instance=request.user)
        profile_form = VendorProfileEditForm(instance=vendor_profile)
        area_formset = VendorServiceAreaFormSet(instance=vendor_profile)
        portfolio_formset = VendorPortfolioImageFormSet(instance=vendor_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'area_formset': area_formset,
        'portfolio_formset': portfolio_formset,
    }
    return render(request, 'core/vendor_settings.html', context)
@admin_required
def user_directory(request):
    users = User.objects.all().order_by('-created_at')

    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)

    context = {
        'users': users,
        'role_filter': role_filter,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'core/user_directory.html', context)


@admin_required
def toggle_user_active(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    role_filter = request.GET.get('role', '')

    redirect_url = 'core:user_directory'

    if target_user.role == User.ADMIN:
        messages.error(request, "You cannot deactivate an Admin account from here.")
    elif target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        target_user.is_active = not target_user.is_active
        target_user.save()
        status = "activated" if target_user.is_active else "deactivated"
        messages.success(request, f"{target_user.username} has been {status}.")

    if role_filter:
        return redirect(f"/admin-panel/users/?role={role_filter}")
    return redirect(redirect_url)



@customer_required
def booking_payment(request, booking_id):
    """
    Fake payment page for a CONFIRMED booking. No real payment gateway -
    this exists purely to simulate the UX of paying for a service after
    the vendor has agreed to it.

    Ownership + status checks: only the booking's own customer can pay,
    and only for a booking that's actually confirmed and not yet paid -
    prevents paying twice or paying for a pending/rejected booking.
    """
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        customer=request.user,
        status=Booking.STATUS_CONFIRMED,
        is_paid=False
    )

    if request.method == 'POST':
        # Fake payment "processing" - no real card validation happens.
        # We just generate a fake reference and mark it paid.
        booking.is_paid = True
        booking.payment_reference = 'PAY-' + ''.join(
            random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8)
        )
        booking.save()
        messages.success(request, "Payment successful! Your booking is confirmed and paid.")
        return redirect('core:my_bookings')

    return render(request, 'core/booking_payment.html', {'booking': booking})


# ==========================================
# MESSAGING SYSTEM
# ==========================================

@customer_required
def conversation_list(request):
    """
    Shows all conversations for the logged-in customer.
    """
    conversations = Conversation.objects.filter(
        customer=request.user
    ).select_related('vendor__user', 'vendor__service_category')

    context = {
        'conversations': conversations,
    }
    return render(request, 'core/conversation_list.html', context)


@vendor_required
def vendor_conversation_list(request):
    """
    Shows all conversations for the logged-in vendor.
    """
    conversations = Conversation.objects.filter(
        vendor=request.user.vendor_profile
    ).select_related('customer')

    context = {
        'conversations': conversations,
    }
    return render(request, 'core/vendor_conversation_list.html', context)


@customer_required
def conversation_detail(request, conversation_id):
    """
    Shows the chat interface for a specific conversation (customer view).
    """
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        customer=request.user
    )

    # Mark all messages as read for customer
    conversation.messages.filter(customer_read=False).update(customer_read=True)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.customer_read = True  # Sender has read it
            message.save()
            conversation.updated_at = message.created_at
            conversation.save()
            messages.success(request, "Message sent!")
            return redirect('core:conversation_detail', conversation_id=conversation.id)
    else:
        form = MessageForm()

    context = {
        'conversation': conversation,
        'messages': conversation.messages.all(),
        'form': form,
    }
    return render(request, 'core/conversation_detail.html', context)


@vendor_required
def vendor_conversation_detail(request, conversation_id):
    """
    Shows the chat interface for a specific conversation (vendor view).
    """
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        vendor=request.user.vendor_profile
    )

    # Mark all messages as read for vendor
    conversation.messages.filter(vendor_read=False).update(vendor_read=True)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.vendor_read = True  # Sender has read it
            message.save()
            conversation.updated_at = message.created_at
            conversation.save()
            messages.success(request, "Message sent!")
            return redirect('core:vendor_conversation_detail', conversation_id=conversation.id)
    else:
        form = MessageForm()

    context = {
        'conversation': conversation,
        'messages': conversation.messages.all(),
        'form': form,
    }
    return render(request, 'core/vendor_conversation_detail.html', context)


@customer_required
def start_conversation(request, vendor_id):
    """
    Starts a new conversation with a vendor (or opens existing one).
    """
    vendor = get_object_or_404(VendorProfile, id=vendor_id, is_approved=True)

    # Check if conversation already exists
    conversation, created = Conversation.objects.get_or_create(
        customer=request.user,
        vendor=vendor
    )

    if created:
        messages.success(request, f"Conversation started with {vendor.business_name}!")
    else:
        messages.info(request, f"Resuming conversation with {vendor.business_name}.")

    return redirect('core:conversation_detail', conversation_id=conversation.id)


# ==========================================
# WISHLIST / FAVORITES
# ==========================================

@customer_required
def wishlist(request):
    """
    Shows all favorited vendors for the logged-in customer.
    """
    favorites = FavoriteVendor.objects.filter(
        customer=request.user
    ).select_related('vendor__user', 'vendor__service_category')

    context = {
        'favorites': favorites,
    }
    return render(request, 'core/wishlist.html', context)


@customer_required
def add_to_wishlist(request, vendor_id):
    """
    Adds a vendor to the customer's wishlist.
    """
    vendor = get_object_or_404(VendorProfile, id=vendor_id, is_approved=True)

    favorite, created = FavoriteVendor.objects.get_or_create(
        customer=request.user,
        vendor=vendor
    )

    if created:
        messages.success(request, f"{vendor.business_name} added to your wishlist!")
    else:
        messages.info(request, f"{vendor.business_name} is already in your wishlist.")

    return redirect('core:wishlist')


@customer_required
def remove_from_wishlist(request, favorite_id):
    """
    Removes a vendor from the customer's wishlist.
    """
    favorite = get_object_or_404(
        FavoriteVendor,
        id=favorite_id,
        customer=request.user
    )
    vendor_name = favorite.vendor.business_name
    favorite.delete()
    messages.success(request, f"{vendor_name} removed from your wishlist.")

    return redirect('core:wishlist')


@customer_required
def edit_favorite_notes(request, favorite_id):
    """
    Edits the notes for a favorited vendor.
    """
    favorite = get_object_or_404(
        FavoriteVendor,
        id=favorite_id,
        customer=request.user
    )

    if request.method == 'POST':
        form = FavoriteVendorForm(request.POST, instance=favorite)
        if form.is_valid():
            form.save()
            messages.success(request, "Notes updated successfully!")
            return redirect('core:wishlist')
    else:
        form = FavoriteVendorForm(instance=favorite)

    context = {
        'form': form,
        'favorite': favorite,
    }
    return render(request, 'core/edit_favorite_notes.html', context)

