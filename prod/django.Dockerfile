FROM ghcr.io/astral-sh/uv:debian

# Make Python more friendly to running in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Install system libraries for Python packages:
# hadolint ignore=DL3008
RUN set -ex \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libc6-dev \
        libgdal32 \
        libgdal-dev \
        libsndfile1-dev \
        ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project

COPY ./ /opt/django-project/
RUN uv sync --no-dev
