from .production import *

# Import these afterwards, to overrid
# from resonant_settings.production.s3_storage import *  # isort: skip
STORAGES['default'] = {
    'BACKEND': 'storages.backends.s3.S3Storage',
}
BASE_HOST = env.str('SERVERHOSTNAME', default='')
ALLOWED_HOSTS = [BASE_HOST, '.sciencebase.gov']
# This is so the client and communicate with django properly through the reverse proxy
CSRF_TRUSTED_ORIGINS = [f'https://{BASE_HOST}', f'https://{BASE_HOST}']
CORS_ORIGIN_WHITELIST = [f'https://{BASE_HOST}', f'https://{BASE_HOST}']

AWS_S3_REGION_NAME = env.str('AWS_DEFAULT_REGION')
AWS_STORAGE_BUCKET_NAME = env.str('DJANGO_STORAGE_BUCKET_NAME')
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_MAX_MEMORY_SIZE = 5 * 1024 * 1024
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_EXPIRE = 3600 * 6  # 6 hours

SECURE_SSL_REDIRECT = False
