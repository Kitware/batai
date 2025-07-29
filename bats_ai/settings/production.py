from .base import *

# Import these afterwards, to override
from resonant_settings.production.https import *  # isort: skip

WSGI_APPLICATION = 'bats_ai.wsgi.application'

SECRET_KEY: str = env.str('DJANGO_SECRET_KEY')

# This only needs to be defined in production. Testing will add 'testserver'. In development
# (specifically when DEBUG is True), 'localhost' and '127.0.0.1' will be added.
ALLOWED_HOSTS: list[str] = env.list('DJANGO_ALLOWED_HOSTS', cast=str)
