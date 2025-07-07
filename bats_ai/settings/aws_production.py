from .production import *

# Import these afterwards, to overrid
from resonant_settings.production.s3_storage import *  # isort: skip

STORAGES['default'] = {
    'BACKEND': 'storages.backends.s3.S3Storage',
}
