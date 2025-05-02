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
        libgdal32 \
        libgdal-dev \
        libpq-dev \
        libsndfile1-dev \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Only copy the setup.py, it will still force all install_requires to be installed,
# but find_packages() will find nothing (which is fine). When Docker Compose mounts the real source
# over top of this directory, the .egg-link in site-packages resolves to the mounted directory
# and all package modules are importable.
COPY ./setup.py /opt/django-project/setup.py

# TODO: TEMPORARY FOR SSL VERIFICATION
COPY ./dev/sciencebase-fullchain.crt /usr/local/share/ca-certificates/sciencebase-fullchain.crt
RUN update-ca-certificates

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip

RUN set -ex \
 && pip install --no-cache-dir -e .[dev]
