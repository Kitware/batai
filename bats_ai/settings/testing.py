from .base import *

# Import these afterwards, to override
from resonant_settings.testing.minio_storage import *  # isort: skip

SECRET_KEY = 'insecure-secret'

# Use a fast, insecure hasher to speed up tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

STORAGES['default'] = {
    'BACKEND': 'minio_storage.storage.MinioMediaStorage',
}
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'test-django-storage'

# Testing will set EMAIL_BACKEND to use the memory backend
