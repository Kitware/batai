# ========================
# Build Stage (Vue + Env)
# ========================
FROM node:lts-alpine AS build-stage

# Build-time args
ARG VITE_APP_API_ROOT
ARG VITE_APP_OAUTH_API_ROOT
ARG VITE_APP_OAUTH_CLIENT_ID
ARG VITE_APP_LOGIN_REDIRECT
ARG SUBPATH

# Set environment for build
ENV VITE_APP_API_ROOT=${VITE_APP_API_ROOT}
ENV VITE_APP_OAUTH_API_ROOT=${VITE_APP_OAUTH_API_ROOT}
ENV VITE_APP_OAUTH_CLIENT_ID=${VITE_APP_OAUTH_CLIENT_ID}
ENV VITE_APP_LOGIN_REDIRECT=${VITE_APP_LOGIN_REDIRECT}
ENV VITE_APP_SUBPATH=${SUBPATH}

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

# Build-time ARG to get SUBPATH
ARG SUBPATH

# Clean default site
RUN rm -rf /usr/share/nginx/html/*

# Copy build output
COPY --from=build-stage /app/dist /tmp/dist

# If SUBPATH is set, copy dist to subfolder and rewrite nginx config
COPY prod/nginx/nginx.subpath.template /nginx.subpath.template
COPY prod/nginx/nginx.conf /nginx.conf

# hadolint ignore=SC2016
RUN if [ -n "$SUBPATH" ]; then \
        echo "Copying Vue build to /usr/share/nginx/html/${SUBPATH}"; \
        mkdir -p /usr/share/nginx/html/${SUBPATH}; \
        cp -r /tmp/dist/* /usr/share/nginx/html/${SUBPATH}/; \
        envsubst '${SUBPATH}' < /nginx.subpath.template > /etc/nginx/nginx.conf; \
    else \
        echo "No SUBPATH set. Using default nginx.conf"; \
        cp /nginx.conf /etc/nginx/nginx.conf; \
        cp -r /tmp/dist/* /usr/share/nginx/html/; \
    fi

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
