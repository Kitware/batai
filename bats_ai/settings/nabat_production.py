from .base import *

# Import these afterwards, to override
from resonant_settings.production.https import *
from resonant_settings.production.s3_storage import *

SECRET_KEY: str = env.str('DJANGO_SECRET_KEY')

STORAGES['default'] = {
    'BACKEND': 'storages.backends.s3.S3Storage',
}

BASE_HOST = env.str('SERVERHOSTNAME', default='')
ALLOWED_HOSTS = [BASE_HOST, '.sciencebase.gov']
# This is so the client and communicate with django properly through the reverse proxy
CSRF_TRUSTED_ORIGINS = [f'https://{BASE_HOST}', f'https://{BASE_HOST}']
CORS_ALLOWED_ORIGINS = [f'https://{BASE_HOST}', f'https://{BASE_HOST}']

SECURE_SSL_REDIRECT = False

# Can be set to mount all URLs at a subpath
_proxy_subpath: str | None = env.str('DJANGO_BATAI_URL_PATH', default=None)
if _proxy_subpath:
    _proxy_subpath = f'/{_proxy_subpath.strip("/")}'
    FORCE_SCRIPT_NAME = _proxy_subpath
    # Work around https://code.djangoproject.com/ticket/36653
    STORAGES['staticfiles'].setdefault('OPTIONS', {})['base_url'] = f'{_proxy_subpath}/{STATIC_URL}'
