# Use official Node.js image as the base image
FROM node:16 as build-stage

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY client/package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY client .

# Build the Vue.js application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app from build stage to nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Expose port 80 to the outer world
EXPOSE 80

# Command to run nginx
CMD ["nginx", "-g", "daemon off;"]
