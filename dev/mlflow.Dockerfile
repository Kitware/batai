FROM ghcr.io/mlflow/mlflow:v2.20.3


# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir boto3==1.37.11 psycopg2-binary==2.9.10
