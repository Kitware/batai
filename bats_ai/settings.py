from __future__ import annotations

import os
from pathlib import Path

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)
from composed_configuration._configuration import _BaseConfiguration
from configurations import values


class BatsAiMixin(ConfigMixin):
    WSGI_APPLICATION = 'bats_ai.wsgi.application'
    ROOT_URLCONF = 'bats_ai.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    FILE_UPLOAD_HANDLERS = [
        'django.core.files.uploadhandler.TemporaryFileUploadHandler',
    ]
    CELERY_RESULT_BACKEND = 'django-db'

    CELERY_BEAT_SCHEDULE = {
        'delete-expired-exported-files-daily': {
            'task': 'bats_ai.tasks.periodic.delete_expired_exported_files',
            'schedule': 86400,  # every 24 hours (in seconds)
        },
    }

    @staticmethod
    def mutate_configuration(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'bats_ai.core.apps.CoreConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            'django.contrib.gis',
            'django_celery_results',
        ]

        configuration.MIDDLEWARE = [
            'corsheaders.middleware.CorsMiddleware',
            'django.middleware.common.CommonMiddleware',
            'allauth.account.middleware.AccountMiddleware',
        ] + configuration.MIDDLEWARE

    @property
    def DATABASES(self):  # noqa
        db_val = values.DatabaseURLValue(
            alias='default',
            environ_prefix='DJANGO',
            environ_name='DATABASE_URL',
            environ_required=True,
            # Additional kwargs to DatabaseURLValue are passed to dj-database-url
            engine='django.contrib.gis.db.backends.postgis',
            conn_max_age=600,
        )
        db_dict = db_val.value
        return db_dict


class DevelopmentConfiguration(BatsAiMixin, DevelopmentBaseConfiguration):
    SECRET_KEY = 'secretkey'  # Dummy value for local development configuration

    baseHost = 'localhost'
    if 'SERVERHOSTNAME' in os.environ:
        baseHost = os.environ['SERVERHOSTNAME']

    DEFAULT_FILE_STORAGE = 'minio_storage.storage.MinioMediaStorage'
    MINIO_STORAGE_ENDPOINT = values.Value(
        'localhost:9000',
    )
    MINIO_STORAGE_USE_HTTPS = values.BooleanValue(False)
    MINIO_STORAGE_ACCESS_KEY = values.SecretValue()
    MINIO_STORAGE_SECRET_KEY = values.SecretValue()
    MINIO_STORAGE_MEDIA_BUCKET_NAME = values.Value(
        environ_name='STORAGE_BUCKET_NAME',
        environ_required=True,
    )
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
    MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY = 'READ_WRITE'
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
    MINIO_STORAGE_MEDIA_URL = f'http://{baseHost}:9000/django-storage'


class TestingConfiguration(BatsAiMixin, TestingBaseConfiguration):
    pass


class KitwareConfiguration(BatsAiMixin, _BaseConfiguration):
    subpath = os.environ.get('SUBPATH', '').strip('/')

    # If SUBPATH is non-empty, prefix URLs accordingly, else use defaults
    STATIC_URL = f'/{subpath}/static/' if subpath else '/static/'
    LOGIN_URL = f'/{subpath}/accounts/login/' if subpath else '/accounts/login/'
    USE_X_FORWARDED_HOST = True  # If behind a proxy
    SECRET_KEY = values.SecretValue()
    baseHost = 'batdetectai.kitware.com'
    if 'SERVERHOSTNAME' in os.environ:
        baseHost = os.environ['SERVERHOSTNAME']
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FILE_STORAGE = 'minio_storage.storage.MinioMediaStorage'
    MINIO_STORAGE_ENDPOINT = values.Value(
        'minio:9000',
    )
    MINIO_STORAGE_USE_HTTPS = values.BooleanValue(False)
    MINIO_STORAGE_ACCESS_KEY = values.SecretValue()
    MINIO_STORAGE_SECRET_KEY = values.SecretValue()
    MINIO_STORAGE_MEDIA_BUCKET_NAME = values.Value(
        environ_name='STORAGE_BUCKET_NAME',
        environ_required=True,
    )
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
    MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY = 'READ_WRITE'
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
    MINIO_STORAGE_MEDIA_URL = f'https://{baseHost}/django-storage'
    ALLOWED_HOSTS = [baseHost]
    CSRF_TRUSTED_ORIGINS = [f'https://{baseHost}', f'https://{baseHost}']
    CORS_ORIGIN_WHITELIST = [f'https://{baseHost}', f'https://{baseHost}']


class ProductionConfiguration(BatsAiMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(BatsAiMixin, HerokuProductionBaseConfiguration):
    pass


class AwsProductionConfiguration(BatsAiMixin, _BaseConfiguration):
    SUBPATH = os.environ.get('SUBPATH', '').strip('/')

    # If SUBPATH is non-empty, prefix URLs accordingly, else use defaults
    STATIC_URL = f'/{SUBPATH}/static/' if SUBPATH else '/static/'
    LOGIN_URL = f'/{SUBPATH}/accounts/login/' if SUBPATH else '/accounts/login/'

    DEFAULT_FILE_STORAGE = 'storages.backends.s3.S3Storage'
    baseHost = '[batdetectai.kitware.com](http://batdetectai.kitware.com/)'
    if 'SERVERHOSTNAME' in os.environ:
        baseHost = os.environ['SERVERHOSTNAME']
    ALLOWED_HOSTS = [baseHost]
    CSRF_TRUSTED_ORIGINS = [f'https://{baseHost}', f'https://{baseHost}']
    CORS_ORIGIN_WHITELIST = [f'https://{baseHost}', f'https://{baseHost}']

    AWS_S3_REGION_NAME = values.Value()
    AWS_STORAGE_BUCKET_NAME = values.Value()
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_MAX_MEMORY_SIZE = 5 * 1024 * 1024
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_EXPIRE = 3600 * 6  # 6 hours
