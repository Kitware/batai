import os

from resonant_settings._env import env

from .base import *

# Note that this pulls a lot of information out of the environment
# variable DJANGO_MINIO_STORAGE_URL including the scheme (http or https)
# access key, secret, and bucket name.
# Additionally, the DJANGO_MINIO_STORAGE_MEDIA_URL must be set to
# populate the MINIO_STORAGE_MEDIA_URL setting.


SECRET_KEY: str = env.str('DJANGO_SECRET_KEY')

BASE_HOST = 'batdetectai.kitware.com'
if 'SERVERHOSTNAME' in os.environ:
    BASE_HOST = os.environ['SERVERHOSTNAME']
ALLOWED_HOSTS = [BASE_HOST]
CSRF_TRUSTED_ORIGINS = [f'https:/{BASE_HOST}', f'https://{BASE_HOST}']
CORS_ORIGIN_WHITELIST = [f'https:/{BASE_HOST}', f'https://{BASE_HOST}']
