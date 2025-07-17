from .production import *

# Import these afterwards, to override
from resonant_settings.testing.minio_storage import *  # isort: skip

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}

# TODO: why does this need to be set?
# CSRF_TRUSTED_ORIGINS = [f'https:/{BASE_HOST}', f'https://{BASE_HOST}']
