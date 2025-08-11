# ========================
# Build Stage (Vue + Env)
# ========================
FROM node:lts-alpine AS build-stage

# Build-time args
ARG VITE_APP_API_ROOT
ARG VITE_APP_OAUTH_API_ROOT
ARG VITE_APP_OAUTH_CLIENT_ID
ARG VITE_APP_LOGIN_REDIRECT
ARG DJANGO_BATAI_URL_PATH
ARG DJANGO_MINIO_STORAGE_URL

# Set environment for build
ENV VITE_APP_API_ROOT=${VITE_APP_API_ROOT}
ENV VITE_APP_OAUTH_API_ROOT=${VITE_APP_OAUTH_API_ROOT}
ENV VITE_APP_OAUTH_CLIENT_ID=${VITE_APP_OAUTH_CLIENT_ID}
ENV VITE_APP_LOGIN_REDIRECT=${VITE_APP_LOGIN_REDIRECT}
ENV VITE_APP_SUBPATH=${DJANGO_BATAI_URL_PATH}
ENV DJANGO_MINIO_STORAGE_URL=${DJANGO_MINIO_STORAGE_URL}
WORKDIR /app

# Copy full client code
COPY ./client .

# Run Vue build
RUN npm ci \
  && npm run build

# ========================
# Nginx Stage
# ========================
FROM nginx:alpine AS production-stage

# Build-time ARG to get DJANGO_BATAI_URL_PATH
ARG DJANGO_BATAI_URL_PATH
ARG DJANGO_MINIO_STORAGE_URL
ENV DJANGO_MINIO_STORAGE_URL=${DJANGO_MINIO_STORAGE_URL}

# Clean default site
RUN rm -rf /usr/share/nginx/html/*

# Copy build output
COPY --from=build-stage /app/dist /tmp/dist

# If DJANGO_BATAI_URL_PATH is set, copy dist to subfolder and rewrite nginx config
COPY prod/nginx/nginx.subpath.template /nginx.subpath.template
COPY prod/nginx/nginx.subpath.nominio.template /nginx.subpath.nominio.template
COPY prod/nginx/nginx.nominio.template /nginx.nominio.template
COPY prod/nginx/nginx.template /nginx.template

# hadolint ignore=SC2016
RUN if [ -n "$DJANGO_BATAI_URL_PATH" ]; then \
        echo "Copying Vue build to /usr/share/nginx/html/${DJANGO_BATAI_URL_PATH}"; \
        mkdir -p /usr/share/nginx/html/${DJANGO_BATAI_URL_PATH}; \
        cp -r /tmp/dist/* /usr/share/nginx/html/${DJANGO_BATAI_URL_PATH}/; \
        if [ -n "$DJANGO_MINIO_STORAGE_URL" ]; then \
            envsubst '${DJANGO_BATAI_URL_PATH}' < /nginx.subpath.template > /etc/nginx/nginx.conf; \
        else \
            envsubst '${DJANGO_BATAI_URL_PATH}' < /nginx.subpath.nominio.template > /etc/nginx/nginx.conf; \
        fi; \
    else \
        echo "No DJANGO_BATAI_URL_PATH set. Using root-level nginx config"; \
        cp -r /tmp/dist/* /usr/share/nginx/html/; \
        if [ -n "$DJANGO_MINIO_STORAGE_URL" ]; then \
            cp /nginx.template /etc/nginx/nginx.conf; \
        else \
            cp /nginx.nominio.template /etc/nginx/nginx.conf; \
        fi; \
    fi

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
