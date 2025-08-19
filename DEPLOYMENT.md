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

Figure out the proper template to use.  This is either
`./prod/.env.kitware-production.template` or `./prod/.env.aws-production.template`
Copy over the chosen .env file to `./prod/.env.production`
and change the default passwords for fields

### Initial Setup for Deployment

1. Run `source ./dev/export-env.sh ./prod/env.production` to load environment varaibles for the
production docker compose file
2. Run `docker compose -f ./prod/docker-compose.prod.yml run --rm django ./manage.py migrate`
3. Run `docker compose -f ./prod/docker-compose.prod.yml run --rm django ./manage.py createsuperuser`
   and follow the prompts to create your own user
4. Run `docker compose  -f ./prod/docker-compose.prod.yml run \
                    --rm django ./manage.py makeclient \
                    --username your.super.user@email.address \
                    --uri https://batdetectai.kitware.com/`
5. Run `docker compose -f docker-compose.prod.yml run \
         --rm django ./manage.py loaddata species`
   to load species data into the database
6. Run `docker compose -f ./prod/docker-compose.prod.yml run --rm django ./manage.py collectstatic`
   to collect the static files
7. Run `docker compose -f ./prod/docker-compose.prod.yml up` to start the server
   add `-d` for a silent version to run in the background
8. **OPTIONAL** Change the `APPLICATION_CLIENT_ID` and the `VITE_APP_OAUTH_CLIENT_ID` in
   the `./prod/env.production` to a custom ID - this will
   probably require a `docker compose -f ./prod/docker-compose.prod.yml build` \
   to build the app afterwards.  This Id is used to indetify the application and
   isn't required to be changed especially if the building of the client is done
   outside of deployment.
9. After creating the basic application log into the django admin `batdetectai.kitware.com/admin`
10. Test logging in/out and uploading data to the server.

### GRTS Cell Id support

Then run `docker compose -f ./prod/docker-compose.prod.yml run \
   --rm django ./manage.py loadGRTS`

It may take a few minutes to upload because it is downloading and loading a bunch of data into the database.
This includes the CONUS GRTS cells, the Alaska/Canada GRTS Cells and the Hawaii GRTSCells.
There will be progress bar for each shapefile it is processing and loading.

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
ExecStart=source ./dev/export-env.sh ./prod/env.production && docker compose -f ./prod/docker-compose.prod.yml up
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

- `DJANGO_SETTINGS_MODULE` this should be set to `bats_ai.settings.aws_production`. This tells Django which set of
   settings to use for the web server. The `aws_production` module  will configure S3 settings.
- `DJANGO_DATABASE_URL` this will be a postgres connection string, e.g. `postgres://user:password@postgres:5432/django`
- `DJANGO_CELERY_BROKER_URL` is used to make sure django can send tasks to the `celery` service.
   For example, if using [RabbitMQ](https://www.rabbitmq.com/), it might look like this: `amqp://rabbitmq:5672`
- `AWS_*` and `DJANGO_STORAGE_BUCKET_NAME` are used to make sure the application can connect to your S3 bucket
- `APPLICATION_CLIENT_ID`: This is used to register the front-end Vue single-page app as an Oauth application.
- `NABAT_API_URL`: the location of the NABat GraphQL endpoint used to retrieve information about files in NABat.
- `VITE_APP_API_ROUTE`: this tells the Vue application where the backend (Django) API can be found.
- `DJANGO_BATAI_URL_PATH`: this allows the Django application to be mounted at a subpath in a URL.
   It is used by the Django application itself and the nginx configuration at nginx.subpath.template
