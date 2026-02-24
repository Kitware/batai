from .base import *

# Import these afterwards, to override
from resonant_settings.production.email import *
from resonant_settings.development.minio_storage import *

SECRET_KEY: str = env.str('DJANGO_SECRET_KEY')

ALLOWED_HOSTS: list[str] = env.list('DJANGO_ALLOWED_HOSTS', cast=str)

SECURE_SSL_REDIRECT = False  # disable because we are using a reverse proxy (traefik that does it)

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}
BASE_HOST = env.str('SERVERHOSTNAME', default='')
# This is so the client and communicate with django properly through the reverse proxy
CSRF_TRUSTED_ORIGINS = [f'https://{BASE_HOST}']
