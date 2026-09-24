# Keycloak Testing for NABat Integration

The integration with the NABat platform requires some trickier auth to test fully. This directory contains some helpful tools for local development testing.

## Running with a local Keycloak server

In the top-level directory of the repository there is a docker compose file that can be used in conjunction with whichever docker compose files you already use for development. This means that you only need to spin up a local KC service when required. To chain docker compose files, simply use the `-f` flag multiple times. For example, with local development:

```bash
docker compose -f docker-compose.yml -f docker-compose-keycloak.yml up
```

## Keycloak Configuration

Keycloak configuration is defined in [NABAT-realm.json](./NABAT-realm.json). It sets up 2 clients: a proxy "NABat" and a client for the locally running BatAI application. It also sets up a test user (this would be the analog to your account with NABat). The username and password for this user are both `testuser`.

## Testing Local Keycloak Flow

Once your keycloak service is running alongside BatAI, you can simulate the keycloak login/token exchange workflow, start by running [./print-nabat-auth-url.sh](./print-nabat-auth-url.sh) to generate a URL.

Paste the URL into your browser, and if this is the first time you're going through the workflow or KC doesn't have an active token for `testuser` you'll need to log in as `testuser`. This will redirect to your local BatAI application and begin the login flow.

To verify this authentication flow works correctly, look at your server's logs. You should see a `200` response from the `/nabat/authorize` endpoint.

Since we don't actually have a proxied NABat application to run locally, this is about as far as we can go at the moment.
