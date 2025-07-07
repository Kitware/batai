FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

# Install system libraries for Python packages:
# * psycopg2
# hadolint ignore=DL3008
RUN set -ex \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libc6-dev \
        libpq-dev \
        libsndfile1-dev \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Only copy the pyproject.toml, it will still force all install_requires to be installed,
# but find_packages() will find nothing (which is fine). When Docker Compose mounts the real source
# over top of this directory, the .egg-link in site-packages resolves to the mounted directory
# and all package modules are importable.
COPY ./pyproject.toml /opt/django-project/pyproject.toml
COPY ./manage.py /opt/django-project/manage.py
COPY ./README.md /opt/django-project/README.md

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip

# Handle build environment for pip install
ARG BUILD_ENV

# If not bind mounted we need bats_ai for celery deployment
# The bind mount will override this directory
COPY ./ /opt/django-project/

# hadolint ignore=DL3013
RUN set -ex \
 # Default to 'dev' if BUILD_ENV is empty
 && BUILD_ENV="${BUILD_ENV:-dev}" \
 # Check for valid options and warn if unexpected
 && if [ "$BUILD_ENV" != "dev" ] && [ "$BUILD_ENV" != "prod" ]; then \
      echo "⚠️ WARNING: BUILD_ENV is set to '$BUILD_ENV' but should be 'dev' or 'prod'. Proceeding anyway with default of dev..."; \
    else \
      echo "Installing with BUILD_ENV='$BUILD_ENV'"; \
    fi \
 && if [ "$BUILD_ENV" = "prod" ]; then \
      pip install --no-cache-dir .["$BUILD_ENV"]; \
    else \
      pip install --no-cache-dir -e .["$BUILD_ENV"]; \
    fi
