from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),

    # Authentication
    path('signup/customer/', views.customer_signup, name='customer_signup'),
    path('signup/vendor/', views.vendor_signup, name='vendor_signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('forgot/', views.forgot, name='forgot'),


    # Dashboards
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/vendor/', views.vendor_dashboard, name='vendor_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    # Vendor: service listing management
    path('vendor/services/', views.my_services, name='my_services'),
    path('vendor/services/add/', views.add_service, name='add_service'),
    path('vendor/services/<int:listing_id>/edit/', views.edit_service, name='edit_service'),
    path('vendor/services/<int:listing_id>/delete/', views.delete_service, name='delete_service'),

    # Public: browse services
    path('services/', views.browse_services, name='browse_services'),
    path('services/<int:listing_id>/', views.service_detail, name='service_detail'),

    # Customer: bookings
    
    path('services/<int:listing_id>/book/', views.request_booking, name='request_booking'),
    path('booking/checkout/', views.booking_checkout, name='booking_checkout'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('my-bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('my-bookings/<int:booking_id>/pay/', views.booking_payment, name='booking_payment'),

    # Vendor: manage booking requests
    path('vendor/bookings/', views.booking_requests, name='booking_requests'),
    path('vendor/bookings/<int:booking_id>/respond/<str:action>/', views.respond_booking, name='respond_booking'),
    path('vendor/bookings/<int:booking_id>/complete/', views.mark_booking_completed, name='mark_booking_completed'),


    # Reviews
    path('my-bookings/<int:booking_id>/review/', views.add_review, name='add_review'),

    # Public vendor profile
    path('vendors/<int:vendor_id>/', views.vendor_public_profile, name='vendor_public_profile'),


    # Admin: vendor approval & directory
    path('admin-panel/vendors/pending/', views.vendor_approval_queue, name='vendor_approval_queue'),
    path('admin-panel/vendors/<int:vendor_id>/approve/', views.approve_vendor, name='approve_vendor'),
    path('admin-panel/vendors/<int:vendor_id>/reject/', views.reject_vendor, name='reject_vendor'),
    path('admin-panel/vendors/<int:vendor_id>/unapprove/', views.unapprove_vendor, name='unapprove_vendor'),
    path('admin-panel/vendors/', views.vendor_directory, name='vendor_directory'),
    path('admin-panel/bookings/', views.all_bookings_overview, name='all_bookings_overview'),
    path('admin-panel/users/', views.user_directory, name='user_directory'),
    path('admin-panel/users/<int:user_id>/toggle-active/', views.toggle_user_active, name='toggle_user_active'),


    # Profile & settings
    path('profile/', views.customer_profile, name='customer_profile'),
    path('vendor/settings/', views.vendor_settings, name='vendor_settings'),

    # Messaging System
    path('messages/', views.conversation_list, name='conversation_list'),
    path('messages/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('vendor/messages/', views.vendor_conversation_list, name='vendor_conversation_list'),
    path('vendor/messages/<int:conversation_id>/', views.vendor_conversation_detail, name='vendor_conversation_detail'),
    path('vendors/<int:vendor_id>/message/', views.start_conversation, name='start_conversation'),

    # Wishlist / Favorites
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:vendor_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:favorite_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/edit/<int:favorite_id>/', views.edit_favorite_notes, name='edit_favorite_notes'),

]