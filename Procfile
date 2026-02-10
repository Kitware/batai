release: python ./manage.py migrate
# Set `graceful_timeout` to shorter than the 30 second limit imposed by Heroku restarts
# Set `timeout` to shorter than the 30 second limit imposed by the Heroku router
web: gunicorn --bind 0.0.0.0:$PORT --graceful-timeout 25 --timeout 15 bats_ai.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app bats_ai.celery worker --loglevel INFO --without-heartbeat --concurrency 1
