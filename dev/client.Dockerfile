# ========================
# Build Stage (Vue + Env)
# ========================
FROM node:18 AS build-stage

WORKDIR /app

# Build-time args
ARG VITE_APP_API_ROOT
ARG VITE_APP_OAUTH_API_ROOT
ARG VITE_APP_OAUTH_CLIENT_ID
ARG VITE_APP_LOGIN_REDIRECT
ARG SUBPATH

# Copy and install dependencies
COPY client/package*.json ./
RUN npm install

# Copy full client code
COPY client .

# Log and write .env.production
RUN echo "SUBPATH=${SUBPATH}" && \
    echo "VITE_APP_API_ROOT=${VITE_APP_API_ROOT}" >> .env.production && \
    echo "VITE_APP_OAUTH_API_ROOT=${VITE_APP_OAUTH_API_ROOT}" >> .env.production && \
    echo "VITE_APP_OAUTH_CLIENT_ID=${VITE_APP_OAUTH_CLIENT_ID}" >> .env.production && \
    echo "VITE_APP_LOGIN_REDIRECT=${VITE_APP_LOGIN_REDIRECT}" >> .env.production && \
    echo "VITE_APP_SUBPATH=${SUBPATH}" >> .env.production

# Set environment for build
ENV VITE_APP_API_ROOT=${VITE_APP_API_ROOT}
ENV VITE_APP_OAUTH_API_ROOT=${VITE_APP_OAUTH_API_ROOT}
ENV VITE_APP_OAUTH_CLIENT_ID=${VITE_APP_OAUTH_CLIENT_ID}
ENV VITE_APP_LOGIN_REDIRECT=${VITE_APP_LOGIN_REDIRECT}
ENV SUBPATH=${SUBPATH}
ENV VITE_APP_SUBPATH=${SUBPATH}

# Run Vue build
RUN npm run build

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
COPY nginx/nginx.subpath.template /nginx.subpath.template
COPY nginx/nginx.conf /nginx.conf

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
