import os

from environ import Env
from resonant_settings.production.s3_storage import *

from .base import *

env = Env()

AWS_S3_REGION_NAME = env.str('DJANGO_AWS_S3_REGION_NAME')
AWS_STORAGE_BUCKET_NAME = env.str('DJANGO_AWS_STORAGE_BUCKET_NAME')
