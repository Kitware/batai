# bats-ai

## Deployment with Docker (recommended quickstart)

This was a bit rushed so the deployment utilizes a single
docker file `docker-compose.prod.yml` in the root of the directory

I wanted some simple instructions below to configure the deployment

Be sure to use the proper hostname (batdetectai.kitware.com) in
all locations that require it.

## Docker Compose Differences

I created a `client` service which has it's own Dockerfile and
builds the vue client app.
The `client` service also uses a reverse proxy to route
`/api`, `/admin` fields to the django server.
The client will need to be built with a different Client ID
for accessing the server.

### git lfs

Remember to `git lfs pull` to download the onnx model used for inference in the repo.
The onnx model file is in the `/assets` folder and is bind mounted into the containers

### Copy templated environment File

Copy over the ./dev/.env.prod.docker-compose.template
to `.env` and change the default passwords for fields

### Initial Setup for Deployment

1. Run `docker compose -f docker-compose.prod.yml run --rm django ./manage.py migrate`
2. Run `docker compose -f docker-compose.prod.yml run --rm django ./manage.py createsuperuser`
   and follow the prompts to create your own user
3. Run `docker compose  -f docker-compose.prod.yml run \
                    --rm django ./manage.py makeclient \
                    --username your.super.user@email.address \
                    --uri https://batdetectai.kitware.com/`
4. Run `docker compose -f docker-compose.prod.yml run \
         --rm django ./manage.py loaddata species`
   to load species data into the database
5. Run `docker compose -f docker-compose.prod.yml run --rm django ./manage.py collectstatic`
   to collect the static files
6. Run `docker compose -f docker-compose.prod.yml up` to start the server
   add `-d` for a silent version to run in the background
7. **OPTIONAL** Change the ID in the `./client/env.production` to a custom ID - this will
   probably require a `docker compose -f docker-compose.prod.yml build` \
   to build the app afterwards.  This Id is used to indetify the application and
   isn't required to be changed especially if the building of the client is done
   outside of deployment.
8. After creating the basic application log into the django admin `batdetectai.kitware.com/admin`
   and change the ApplicationId to the ID in the `./client.env.production`
9. Test logging in/out and uploading data to the server.

### GRTS Cell Id support

Make sure that there is the grts.csv in the /opt/batai/dev/grtsCells folder

Then run `docker compose -f docker-compose.prod.yml run \
   --rm django ./manage.py importGRTSCells /opt/django-project/dev/csv/grts.csv`

It may take a few minutes to upload because it is loading
around 500k rows into the DB.

### system.d service

Service that will automatically start and launch the server
Create this at `/etc/systemd/system` using sudo

```systemd
[Unit]
Description=batai-server
Requires=docker.service
After=docker.service

[Service]
ExecStartPre=/bin/sleep 10
Environment=PATH=/usr/bin:/sbin:/usr/sbin:/usr/local/sbin:/usr/local/bin
Restart=always
User=bryon
Group=docker
TimeoutStartSec=300
RestartSec=20
WorkingDirectory=/opt/batai
# Shutdown container (if running) when unit is started
ExecStartPre=docker compose down
# Start container when unit is started
ExecStart=docker compose -f docker-compose.prod.yml up
# Stop container when unit is stopped
ExecStop=docker compose down

[Install]
WantedBy=multi-user.target
```

After run `sudo systemctl enable batai.service`
Then to start you can use `sudo systemctl start batai.service`
Stopping: `sudo systemctl stop batai.service`

### URI Redirect Errors

If when logging in you're getting redirect URI errors go into the
django-admin interface and make sure you have the trailing '/' on the URL.

### User Management

There is no email server connected up so users need to be
individually approved and their email verified by an admin

## Using AWS S3

In order to use AWS S3 as your storage service, you'll need
to make sure to start the Django application with the correct configuration.

As a starting point for configuring your environment, see [dev/.env.prod.s3.template](dev/.env.prod.s3/template)
for a list of environment variables that you'll need to populate for your deployment.

- `DJANGO_SETTINGS_MODULE` this should be set to `bats_ai.settings.aws_production`. This tells Django which set of settings to use for the web server. The `aws_production` module  will configure S3 settings.
- `DJANGO_DATABASE_URL` this will be a postgres connection string, e.g. `postgres://user:password@postgres:5432/django`
- `DJANGO_CELERY_BROKER_URL` is used to make sure django can send tasks to the `celery` service.
   For example, if using [RabbitMQ](https://www.rabbitmq.com/), it might look like this: `amqp://rabbitmq:5672`
- `AWS_*` and `DJANGO_STORAGE_BUCKET_NAME` are used to make sure the application can connect to your S3 bucket
- `APPLICATION_CLIENT_ID`: This is used to register the front-end Vue single-page app as an Oauth application.
- `NABAT_API_URL`: the location of the NABat GraphQL endpoint used to retrieve information about files in NABat.
- `VITE_APP_API_ROUTE`: this tells the Vue application where the backend (Django) API can be found.
- `DJANGO_BATAI_URL_PATH`: this allows the Django application to be mounted at a subpath in a URL. It is used by the Django application itself and the nginx configuration at nginx.subpath.template
