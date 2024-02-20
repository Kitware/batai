# bats-ai

## Deployment with Docker (recommended quickstart)

This was a bit rushed so the deployment utilizes a single docker file `docker-compose.prod.yml` in the root of the directory

I wanted some simple instructions below to configure the deployment

Be sure to use the proper hostname (batdetectai.kitware.com) in all locations that require it.

## Docker Compose Differences

I created a `client` service which has it's own Dockerfile and builds the vue client app.  The `client` service also uses a reverse proxy to route `/api`, `/admin` fields to the django server.
The client will need to be built with a different Client ID for accessing the server.

### Initial Setup for Deployment

1. Run `docker compose run --rm django ./manage.py migrate`
2. Run `docker compose run --rm django ./manage.py createsuperuser`
   and follow the prompts to create your own user
3. Run  `docker compose run --rm django ./manage.py makeclient \
                            --username your.super.user@email.address \
                            --uri https://batdetectai.kitware.com/`
4. Run `docker compose run --rm django ./manage.py collectstatic` to collect the static files
5. Run `docker compose -f docker-compose.prod.yml up` to start the server add `-d` for a silent version to run in the background
6. Copy over the ./dev/.env.prod.docker-compose.template to `./dev/.env.prod.docker-compose.template` and change the default passwords
7. Change the ID in the `./client/env.production` to a custom ID
8. After creating the basic application log into the django admin `batdetectai.kitware.com/admin` and change the ApplicationId to the ID in the `./client.env.production`
9. Test logging in/out and uploading data to the server.

### system.d service

Service that will automatically start and launch the server