from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from bats_ai.core.rest import rest

from .api import api

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls')),
    path('admin/', admin.site.urls),
    path('api/v1/s3-upload/', include('s3_file_field.urls')),
    path('api/v1/dynamic/', include(rest.urls)),
    path('api/v1/', api.urls),
    path('', include('django_large_image.urls')),
]

if settings.DEBUG:
    import debug_toolbar.toolbar

    urlpatterns += [
        *debug_toolbar.toolbar.debug_toolbar_urls(),
        path('__reload__/', include('django_browser_reload.urls')),
    ]
