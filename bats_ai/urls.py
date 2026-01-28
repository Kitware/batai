from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .api import api

base_urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls')),
    path('admin/', admin.site.urls),
    path('api/v1/s3-upload/', include('s3_file_field.urls')),
    path('api/v1/', api.urls),
]


# Support mounting within a sub-path
if settings.BATAI_URL_PATH:
    urlpatterns = [path(f'{settings.BATAI_URL_PATH}/', include(base_urlpatterns))]
else:
    urlpatterns = base_urlpatterns

if settings.DEBUG:
    import debug_toolbar.toolbar

    urlpatterns += [
        *debug_toolbar.toolbar.debug_toolbar_urls(),
        path('__reload__/', include('django_browser_reload.urls')),
    ]
