from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def customer_required(view_func):
    """
    Only allows logged-in users with role='customer' to access the view.
    Vendors and unapproved roles get redirected with an error message —
    they do NOT get a generic Django 403 page, which is a worse user experience.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to continue.")
            return redirect('core:login')

        if not request.user.is_customer():
            messages.error(request, "This page is only accessible to Customers.")
            return redirect('core:home')

        return view_func(request, *args, **kwargs)
    return wrapper


def vendor_required(view_func):
    """
    Only allows logged-in users with role='vendor' to access the view.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to continue.")
            return redirect('core:login')

        if not request.user.is_vendor():
            messages.error(request, "This page is only accessible to Vendors.")
            return redirect('core:home')

        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    Only allows logged-in users with role='admin' to access the view.
    Note: this checks OUR custom role field, not Django's is_staff/is_superuser,
    because Eventora's "Admin" is a business role, not necessarily a Django
    staff account (though in practice they'll usually overlap).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to continue.")
            return redirect('core:login')

        if not request.user.is_admin_role():
            messages.error(request, "This page is only accessible to Admins.")
            return redirect('core:home')

        return view_func(request, *args, **kwargs)
    return wrapper