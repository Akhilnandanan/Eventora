# Eventora — Event Service Marketplace

Eventora is a full-stack Django web application that connects customers with professional event service providers — photographers, caterers, decorators, DJs, wedding planners, and more. Customers browse vendors by category, city, and price, book services with optional add-ons, and leave reviews after their event. Vendors manage their listings, respond to booking requests, and build a public portfolio. Admins operate the platform through a custom-built dashboard.

This project was built as a college project to demonstrate full-stack web development skills using Django, without relying on Django REST Framework or a separate frontend framework — everything is server-rendered with Bootstrap 5.

---

## Tech Stack

- **Backend:** Python, Django
- **Database:** SQLite
- **Frontend:** Bootstrap 5, HTML, CSS, vanilla JavaScript
- **Templating:** Django Templates

---

## Key Features

### Authentication & Roles

- Custom User model with three roles: Customer, Vendor, Admin
- Separate signup flows for Customers and Vendors
- Role-based dashboards and custom permission decorators (not just `@login_required`)

### For Customers

- Browse and search services by category, city, keyword, and price range
- View vendor public profiles, including portfolio galleries and reviews
- Book a service with optional add-ons (extras) and venue details
- Review booking before confirming (fake checkout flow)
- Track bookings through their full lifecycle (Pending → Confirmed → Completed/Cancelled)
- Simulated payment step after vendor confirms a booking
- Leave a star rating + written review after a completed booking

### For Vendors

- Manage multiple service listings, each with its own price, category, and optional add-ons
- Upload a photo gallery per listing, plus a general portfolio gallery on their public profile
- Declare a primary city plus additional cities served
- Accept or reject incoming booking requests
- Mark confirmed bookings as completed
- Edit business details and account settings in one place

### For Admins

- Custom-built admin dashboard (separate from Django Admin) with live platform stats
- Vendor approval queue — approve, reject, or unapprove vendors
- Full vendor and user directories with filtering
- Platform-wide bookings overview with status filtering
- User account activation/deactivation (safe alternative to deletion)

---

## Project Structure

This project intentionally uses a **single Django app** (`core`) rather than splitting into multiple apps, to keep the codebase simple and easy to navigate for a project of this scope.

```
Eventora/
├── manage.py
├── requirements.txt
├── Eventora/              # Project settings, root URLs
└── core/                  # The one app — everything lives here
    ├── models.py          # User, VendorProfile, ServiceListing, Booking, Review, etc.
    ├── views.py
    ├── forms.py
    ├── urls.py
    ├── admin.py
    ├── decorators.py      # Custom role-based permission decorators
    ├── templates/core/
    └── static/core/
```

---

## Getting Started (Local Development)

1. Clone the repository and navigate into it:

   ```bash
   git clone https://github.com/Akhilnandanan/Eventora.git
   cd Eventora
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:

   ```bash
   python manage.py migrate
   ```

5. Load demo data (vendors, customers, listings):

   ```bash
   python manage.py seed_demo_data
   ```

   Demo logins are listed in [`DEMO_CREDENTIALS.md`](DEMO_CREDENTIALS.md).

6. Create a superuser (Admin account):

   ```bash
   python manage.py createsuperuser
   ```

   After creating it, log into `/admin/`, find your user under **Users**, and set their **Role** to **Admin**.

7. Run the development server:

   ```bash
   python manage.py runserver
   ```

8. Visit `http://127.0.0.1:8000/` in your browser.

---

## Security Notes

- Every privileged view is protected by custom decorators (`@customer_required`, `@vendor_required`, `@admin_required`) in addition to Django's authentication system — role checks happen on every request, not just at login.
- Ownership is enforced at the query level everywhere sensitive data is accessed (e.g. a vendor can only ever fetch/edit their own listings and bookings — never another vendor's, even by guessing an ID in the URL).
- Sensitive fields (like `is_approved` on vendor profiles, or `status` on bookings) are never exposed as editable form fields — they're only ever set server-side by the application logic.

---

## Notes

- This project runs entirely on a local SQLite database and is intended for local development and demonstration purposes only.
- The payment step on the booking flow is a **simulated/fake payment interface** — no real payment gateway is integrated.
- The demo accounts in `DEMO_CREDENTIALS.md` use a shared throwaway password. Don't run the seed command on a public deployment.
