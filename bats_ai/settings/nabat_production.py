from .base import *

# Import these afterwards, to override
from resonant_settings.production.https import *  # isort: skip
from resonant_settings.production.s3_storage import *  # isort: skip

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
