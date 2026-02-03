# Build Instructions

## Client Build Command

Leaving DJANGO_MINIO_STORAGE_URL blank will use the template that doesn't
include the minio routing.  This should make it so minIO isn't required in
the docker compose

```bash
docker build\
    --build-arg BUILD_ENV=prod\
    --build-arg DJANGO_BATAI_URL_PATH=${DJANGO_BATAI_URL_PATH}\
    --build-arg VITE_APP_API_ROOT=${VITE_APP_API_ROOT}\
    --build-arg VITE_APP_LOGIN_REDIRECT=${VITE_APP_LOGIN_REDIRECT}\
    -t ${AWS_IMAGE_LATEST}\
    --pull -f ${DOCKER_FILE_LOCATION} .
```

## Django/Celery Build Command

```bash
docker build\
    --build-arg BUILD_ENV=prod\
    --build-arg DJANGO_BATAI_URL_PATH=${DJANGO_BATAI_URL_PATH}\
    -t ${AWS_IMAGE_LATEST}\
    --pull -f ${DOCKER_FILE_LOCATION} .
```
