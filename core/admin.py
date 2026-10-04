from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, VendorProfile, ServiceCategory, ServiceListing, Booking, Review, ServiceExtra, BookingExtra, VendorServiceArea, ListingImage, VendorPortfolioImage, Conversation, Message, FavoriteVendor


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'is_staff', 'is_active')

    fieldsets = UserAdmin.fieldsets + (
        ('Eventora Role Info', {'fields': ('role', 'phone_number', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Eventora Role Info', {'fields': ('role', 'phone_number')}),
    )


class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ServiceListingInline(admin.TabularInline):
    model = ServiceListing
    extra = 0
    fields = ('title', 'category', 'price', 'price_unit', 'is_active')
class VendorServiceAreaInline(admin.TabularInline):
    model = VendorServiceArea
    extra = 1
    fields = ('city',)

class VendorPortfolioImageInline(admin.TabularInline):
    model = VendorPortfolioImage
    extra = 1
    fields = ('image', 'caption')

class ServiceExtraInline(admin.TabularInline):
    model = ServiceExtra
    extra = 0
    fields = ('title', 'price', 'is_active')

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    fields = ('image', 'caption')

class BookingExtraInline(admin.TabularInline):
    model = BookingExtra
    extra = 0
    readonly_fields = ('title_snapshot', 'price_snapshot')
    can_delete = False


class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'service_category', 'city', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'service_category', 'city')
    search_fields = ('business_name', 'user__username', 'user__email')
    inlines = [ServiceListingInline, VendorServiceAreaInline, VendorPortfolioImageInline]


class ServiceListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'vendor', 'category', 'price', 'price_unit', 'food_type', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'price_unit', 'food_type')
    search_fields = ('title', 'vendor__business_name')
    inlines = [ServiceExtraInline, ListingImageInline]

class BookingAdmin(admin.ModelAdmin):
    list_display = ('customer', 'listing', 'vendor', 'event_date', 'status', 'is_paid', 'created_at')
    list_filter = ('status', 'event_date')
    search_fields = ('customer__username', 'listing__title', 'vendor__business_name')
    inlines = [BookingExtraInline]


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'customer', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('vendor__business_name', 'customer__username')


class ServiceExtraAdmin(admin.ModelAdmin):
    list_display = ('listing', 'title', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'listing__title')


class BookingExtraAdmin(admin.ModelAdmin):
    list_display = ('booking', 'extra', 'title_snapshot', 'price_snapshot')
    readonly_fields = ('title_snapshot', 'price_snapshot')


class VendorServiceAreaAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'city')
    search_fields = ('city', 'vendor__business_name')


class ListingImageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'caption', 'created_at')
    search_fields = ('caption', 'listing__title')


class VendorPortfolioImageAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'caption', 'created_at')
    search_fields = ('caption', 'vendor__business_name')


class ConversationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'vendor', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('customer__username', 'vendor__business_name')
    readonly_fields = ('created_at', 'updated_at')


class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'content_preview', 'created_at')
    list_filter = ('created_at', 'customer_read', 'vendor_read')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


class FavoriteVendorAdmin(admin.ModelAdmin):
    list_display = ('customer', 'vendor', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer__username', 'vendor__business_name')
    readonly_fields = ('created_at',)


admin.site.register(User, CustomUserAdmin)
admin.site.register(ServiceCategory, ServiceCategoryAdmin)
admin.site.register(VendorProfile, VendorProfileAdmin)
admin.site.register(ServiceListing, ServiceListingAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(ServiceExtra, ServiceExtraAdmin)
admin.site.register(BookingExtra, BookingExtraAdmin)
admin.site.register(VendorServiceArea, VendorServiceAreaAdmin)
admin.site.register(ListingImage, ListingImageAdmin)
admin.site.register(VendorPortfolioImage, VendorPortfolioImageAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(FavoriteVendor, FavoriteVendorAdmin)