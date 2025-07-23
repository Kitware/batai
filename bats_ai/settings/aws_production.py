from .production import *

# Import these afterwards, to overrid
from resonant_settings.production.s3_storage import *  # isort: skip

STORAGES['default'] = {
    'BACKEND': 'storages.backends.s3.S3Storage',
}
BASE_HOST = env.str('SERVERHOSTNAME', default='')
# This is so the client and communicate with django properly through the reverse proxy
CSRF_TRUSTED_ORIGINS = [f'https://{BASE_HOST}']
