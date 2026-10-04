from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Django's built-in password change views — battle-tested, secure,
    # handles old-password verification and session security for us.
    path('settings/password/', auth_views.PasswordChangeView.as_view(
        template_name='core/password_change.html',
        success_url='/settings/password/done/'
    ), name='password_change'),

    path('settings/password/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='core/password_change_done.html'
    ), name='password_change_done'),

    path('', include('core.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)