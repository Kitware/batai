FROM ghcr.io/astral-sh/uv:debian

# Make Python more friendly to running in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Make uv install content in well-known locations
ENV UV_PROJECT_ENVIRONMENT=/var/lib/venv \
  UV_CACHE_DIR=/var/cache/uv/cache \
  UV_PYTHON_INSTALL_DIR=/var/cache/uv/bin \
  # The uv cache and environment are expected to be mounted on different volumes,
  # so hardlinks won't work
  UV_LINK_MODE=symlink


# Install system libraries for Python packages:
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
