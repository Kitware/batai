from __future__ import annotations

from pathlib import Path

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)
from configurations import values


class BatsAiMixin(ConfigMixin):
    WSGI_APPLICATION = 'bats_ai.wsgi.application'
    ROOT_URLCONF = 'bats_ai.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    @staticmethod
    def mutate_configuration(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'bats_ai.core.apps.CoreConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            'django.contrib.gis',
        ]

        configuration.MIDDLEWARE = [
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
            engine='django.db.backends.postgresql',
            conn_max_age=600,
        )
        db_dict = db_val.value
        return db_dict


class DevelopmentConfiguration(BatsAiMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(BatsAiMixin, TestingBaseConfiguration):
    pass


class ProductionConfiguration(BatsAiMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(BatsAiMixin, HerokuProductionBaseConfiguration):
    pass
