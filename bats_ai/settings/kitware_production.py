from .production import *

# Import these afterwards, to override
from resonant_settings.production.email import *  # isort: skip
from resonant_settings.testing.minio_storage import *  # isort: skip
from environ import Env

env = Env()
SECURE_SSL_REDIRECT = False  # disable because we are using a reverse proxy (traefik that does it)

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}
BASE_HOST = env.str('SERVERHOSTNAME', default='')
# This is so the client and communicate with django properly through the reverse proxy
CSRF_TRUSTED_ORIGINS = [f'https://{BASE_HOST}']
