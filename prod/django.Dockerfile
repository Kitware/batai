FROM ghcr.io/astral-sh/uv:debian

# Make Python more friendly to running in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project

COPY ./ /opt/django-project/
RUN uv sync --no-dev
