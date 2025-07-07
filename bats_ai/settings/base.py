from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import django_stubs_ext
from environ import Env

django_stubs_ext.monkeypatch()

env = Env()

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

ROOT_URLCONF = 'bats_ai.urls'

INSTALLED_APPS = [
    # Install local apps first, to ensure any overridden resources are found first
    'bats_ai.core.apps.CoreConfig',
    # Apps with overrides
    'auth_style',
    'resonant_settings.allauth_support',
    # Everything else
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_filters',
    'drf_yasg',
    'oauth2_provider',
    'resonant_utils',
    's3_file_field',
    # Bat AI
    'django.contrib.gis',
    'django_large_image',
    'django_celery_results',
]

MIDDLEWARE = [
    # CorsMiddleware must be added before other response-generating middleware,
    # so it can potentially add CORS headers to those responses too.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoiseMiddleware must be directly after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # GZipMiddleware can be after WhiteNoiseMiddleware, as WhiteNoise performs its own compression
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Internal datetimes are timezone-aware, so this only affects rendering and form input
TIME_ZONE = 'UTC'

DATABASES = {
    'default': {
        **env.db_url('DJANGO_DATABASE_URL', engine='django.contrib.gis.db.backends.postgis'),
        'CONN_MAX_AGE': timedelta(minutes=10).total_seconds(),
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    # Inject the default storage in particular run configurations
    'default': None,
    'staticfiles': {
        # CompressedManifestStaticFilesStorage does not work properly with drf-
        # https://github.com/axnsan12/drf-yasg/issues/761
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

STATIC_ROOT = BASE_DIR / 'staticfiles'
# Django staticfiles auto-creates any intermediate directories, but do so here to prevent warnings.
STATIC_ROOT.mkdir(exist_ok=True)

# Django's docs suggest that STATIC_URL should be a relative path,
# for convenience serving a site on a subpath.
STATIC_URL = 'static/'

# Make Django and Allauth redirects consistent, but both may be changed.
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

CORS_ALLOWED_ORIGINS: list[str] = env.list('DJANGO_CORS_ALLOWED_ORIGINS', cast=str, default=[])
CORS_ALLOWED_ORIGIN_REGEXES: list[str] = env.list(
    'DJANGO_CORS_ALLOWED_ORIGIN_REGEXES', cast=str, default=[]
)

WSGI_APPLICATION = 'bats_ai.wsgi.application'
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
CELERY_RESULT_BACKEND = 'django-db'

# TODO once upstream releases this as a module, import this config
SHELL_PLUS_PRINT_SQL = True
SHELL_PLUS_PRINT_SQL_TRUNCATE = None
RUNSERVER_PLUS_PRINT_SQL_TRUNCATE = None
