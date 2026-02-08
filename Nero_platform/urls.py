from django.contrib import admin
from django.urls import path, include
import os
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('patients/', include('patients.urls')),
    path('clinics/', include('clinics.urls')),
    path('chat/', include('chat.urls')),
    path('recommendations/', include('recommendations.urls')),
    path('posts/', include('posts.urls')),
    path('reviews/', include('reviews.urls')),
]
if settings.DEBUG or os.environ.get('SERVE_MEDIA') == '1':
    # In development it's useful to serve media files from Django.
    # For safety, this is enabled when DEBUG=True or when explicitly
    # requested via the environment variable `SERVE_MEDIA=1`.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Also allow serving static files when explicitly requested in development
    if settings.DEBUG or os.environ.get('SERVE_STATIC') == '1':
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])