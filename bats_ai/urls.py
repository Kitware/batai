import os

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from bats_ai.core.rest import rest
from .api import api

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='bats-ai', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Core URL patterns
base_urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls')),
    path('admin/', admin.site.urls),
    path('api/v1/s3-upload/', include('s3_file_field.urls')),
    path('api/v1/dynamic/', include(rest.urls)),
    path('api/v1/', api.urls),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
    path('', include('django_large_image.urls')),
]

# Add subpath prefix if SUBPATH is defined
subpath = os.environ.get("SUBPATH", "").strip("/")
if subpath:
    urlpatterns = [path(f"{subpath}/", include(base_urlpatterns))]
else:
    urlpatterns = base_urlpatterns

# Add debug toolbar if in DEBUG mode
if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
