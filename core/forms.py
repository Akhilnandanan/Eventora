from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from .models import User, VendorProfile, ServiceCategory, ServiceListing, Booking, Review, ServiceExtra, VendorServiceArea, ListingImage, VendorPortfolioImage, Message, FavoriteVendor
class CustomerSignUpForm(UserCreationForm):
    """
    Signup form for Customers.
    """
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = User.CUSTOMER
        if commit:
            user.save()
        return user


class VendorSignUpForm(UserCreationForm):
    """
    Signup form for Vendors.

    service_category offers a dropdown of existing categories PLUS an
    "Other" option. If "Other" is chosen, other_category_name (shown/hidden
    via JS) lets the vendor type a new category, which gets created as a
    real ServiceCategory row - so it becomes a genuine, reusable category
    other vendors can also select later, not just a one-off text label.
    """
    email = forms.EmailField(required=True)
    business_name = forms.CharField(max_length=200, required=True)

    OTHER_CHOICE_VALUE = '__other__'

    service_category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.all(),
        required=False,
        empty_label="Select your primary service category"
    )
    other_category_name = forms.CharField(
        max_length=100,
        required=False,
        label="Or type a new category",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Fireworks Display'})
    )

    city = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('service_category')
        other_name = cleaned_data.get('other_category_name', '').strip()

        if not category and not other_name:
            raise forms.ValidationError("Please select a category or enter a new one.")

        if other_name:
            # Use get_or_create to avoid race conditions and duplicate categories
            new_category, created = ServiceCategory.objects.get_or_create(
                name__iexact=other_name,
                defaults={'name': other_name}
            )
            cleaned_data['resolved_category'] = new_category
        else:
            cleaned_data['resolved_category'] = category

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = User.VENDOR

        if commit:
            user.save()
            VendorProfile.objects.create(
                user=user,
                business_name=self.cleaned_data['business_name'],
                service_category=self.cleaned_data['resolved_category'],
                city=self.cleaned_data['city'],
            )
        return user


class ServiceListingForm(forms.ModelForm):
    """
    Form vendors use to create/edit their service listings.

    'category' is now NOT required at the model-field level - we validate
    it ourselves in clean(), same "Other" pattern as VendorSignUpForm,
    so a vendor can either pick an existing category or type a new one.
    """

    other_category_name = forms.CharField(
        max_length=100,
        required=False,
        label="Or type a new category",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Fireworks Display'})
    )

    class Meta:
        model = ServiceListing
        fields = ['category', 'title', 'description', 'price', 'price_unit', 'food_type', 'cover_image', 'is_active']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_unit': forms.Select(attrs={'class': 'form-select'}),
            'food_type': forms.Select(attrs={'class': 'form-select'}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        other_name = cleaned_data.get('other_category_name', '').strip()

        if not category and not other_name:
            raise forms.ValidationError("Please select a category or enter a new one.")

        if other_name:
            # Use get_or_create to avoid race conditions and duplicate categories
            new_category, created = ServiceCategory.objects.get_or_create(
                name__iexact=other_name,
                defaults={'name': other_name}
            )
            cleaned_data['category'] = new_category

        return cleaned_data


class BookingRequestForm(forms.ModelForm):
    """
    Form a CUSTOMER fills out to request a booking for a specific listing.

    'extras' is a checkbox list of that SPECIFIC listing's active extras -
    scoped via the listing= argument passed in from the view, so a customer
    can never select an extra belonging to a different listing/vendor.
    """

    extras = forms.ModelMultipleChoiceField(
        queryset=ServiceExtra.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    class Meta:
        model = Booking
        fields = ['event_date', 'venue_name', 'venue_address', 'event_city', 'customer_notes']
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'venue_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Grand Palace Banquet Hall'}),
            'venue_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'event_city': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, listing=None, **kwargs):
        super().__init__(*args, **kwargs)
        if listing:
            self.fields['extras'].queryset = listing.extras.filter(is_active=True)
        self.fields['customer_notes'].required = False




class VendorBookingResponseForm(forms.ModelForm):
    """
    Form a VENDOR uses to respond to a booking (accept/reject) with an
    optional note.
    """

    class Meta:
        model = Booking
        fields = ['vendor_response_note']
        widgets = {
            'vendor_response_note': forms.Textarea(attrs={'rows': 2}),
        }


class ReviewForm(forms.ModelForm):
    """
    Form a Customer uses to leave a review for a COMPLETED booking.
    """

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Share your experience...'}),
        }


class CustomerProfileForm(forms.ModelForm):
    """
    Lets a Customer edit their own basic account details.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']


class VendorUserForm(forms.ModelForm):
    """
    The User-level portion of a Vendor's editable profile (name, contact info).
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class VendorProfileEditForm(forms.ModelForm):
    """
    The VendorProfile-level portion of a Vendor's editable profile.
    Deliberately excludes 'user' and 'is_approved'.
    """

    class Meta:
        model = VendorProfile
        fields = ['business_name', 'business_description', 'service_category', 'city', 'address']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business Name'}),
            'service_category': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primary City'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell clients about your services, experience, and style...'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Studio/Office Address'}),
        }
ServiceExtraFormSet = inlineformset_factory(
    ServiceListing,
    ServiceExtra,
    fields=['title', 'price', 'is_active'],
    widgets={
        'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Extra Hour Coverage'}),
        'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price'}),
        'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    },
    extra=2,
    can_delete=True
)


VendorServiceAreaFormSet = inlineformset_factory(
    VendorProfile,
    VendorServiceArea,
    fields=['city'],
    widgets={
        'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Pune'}),
    },
    extra=2,
    can_delete=True
)


ListingImageFormSet = inlineformset_factory(
    ServiceListing,
    ListingImage,
    fields=['image', 'caption'],
    widgets={
        'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional caption'}),
    },
    extra=2,
    can_delete=True
)


VendorPortfolioImageFormSet = inlineformset_factory(
    VendorProfile,
    VendorPortfolioImage,
    fields=['image', 'caption'],
    widgets={
        'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional caption'}),
    },
    extra=3,
    can_delete=True
)


class MessageForm(forms.ModelForm):
    """
    Form for sending a message in a conversation.
    """
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...'
            })
        }


class FavoriteVendorForm(forms.ModelForm):
    """
    Form for adding a vendor to favorites with optional notes.
    """
    class Meta:
        model = FavoriteVendor
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Add notes about this vendor (optional)...'
            })
        }