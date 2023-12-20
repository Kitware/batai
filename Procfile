release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT bats_ai.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app bats_ai.celery worker --loglevel INFO --without-heartbeat
