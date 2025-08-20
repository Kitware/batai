from django_extensions.utils import InternalIPS

from .base import *

# Import these afterwards, to override
from resonant_settings.development.celery import *  # isort: skip
from resonant_settings.development.debug_toolbar import *  # isort: skip
from resonant_settings.testing.minio_storage import *  # isort: skip

INSTALLED_APPS += [
    'debug_toolbar',
    'django_browser_reload',
]
# Force WhiteNoice to serve static files, even when using 'manage.py runserver'
staticfiles_index = INSTALLED_APPS.index('django.contrib.staticfiles')
INSTALLED_APPS.insert(staticfiles_index, 'whitenoise.runserver_nostatic')

DATABASES = {
    **DATABASES,
    'mlflow': {
        **env.db_url('DJANGO_MLFLOW_DB_URL', engine='django.contrib.gis.db.backends.postgis'),
        'CONN_MAX_AGE': timedelta(minutes=10).total_seconds(),
    }
}

MLFLOW_BUCKET: str = env.str('DJANGO_MLFLOW_BUCKET')
MLFLOW_DB: str = env.str('DJANGO_MLFLOW_DB')
MLFLOW_ENDPOINT: str = env.str('DJANGO_MLFLOW_ENDPOINT')

# Include Debug Toolbar middleware as early as possible in the list.
# However, it must come after any other middleware that encodes the response's content,
# such as GZipMiddleware.
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.gzip.GZipMiddleware') + 1,
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)
# Should be listed after middleware that encode the response.
MIDDLEWARE += [
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

# DEBUG is not enabled for testing, to maintain parity with production.
# Also, do not directly reference DEBUG when toggling application features; it's more sustainable
# to add new settings as individual feature flags.
DEBUG = True

SECRET_KEY = 'insecure-secret'

# This is typically only overridden when running from Docker.
INTERNAL_IPS = InternalIPS(env.list('DJANGO_INTERNAL_IPS', cast=str, default=['127.0.0.1']))
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    'DJANGO_CORS_ALLOWED_ORIGIN_REGEXES',
    cast=str,
    default=[r'^http://localhost:\d+$', r'^http://127\.0\.0\.1:\d+$'],
)

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

OAUTH2_PROVIDER['ALLOWED_REDIRECT_URI_SCHEMES'] = ['http', 'https']
# In development, always present the approval dialog
OAUTH2_PROVIDER['REQUEST_APPROVAL_PROMPT'] = 'force'

SHELL_PLUS_IMPORTS = [
    'from bats_ai.tasks import tasks',
]
