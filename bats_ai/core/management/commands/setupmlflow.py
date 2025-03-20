import boto3
from django.conf import settings
import djclick as click
import psycopg2
from psycopg2 import extensions, sql


@click.command()
def setupmlflow():
    db_name = settings.MLFLOW_PG_DB if settings.MLFLOW_PG_DB else 'mlflow'
    bucket_name = settings.MLFLOW_BUCKET if settings.MLFLOW_BUCKET else 'mlflow'

    click.echo(f'Creating database {db_name} for mlflow')
    default_db = settings.DATABASES['default']
    host = default_db['HOST']
    user = default_db['USER']
    password = default_db['PASSWORD']
    conn = psycopg2.connect(f"dbname='postgres' user='{user}' password='{password}' host='{host}'")
    # We cannot use CREATE DATABASE in a transaction
    conn.set_isolation_level(extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cursor:
        cursor.execute(sql.SQL('SELECT 1 FROM pg_database WHERE datname = %s'), (db_name,))
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE {sql.Identifier(db_name).as_string(cursor)}')
            click.echo(f'Created database {db_name} for mlflow')
        else:
            click.echo(f'Database {db_name} already exists')
    conn.close()

    click.echo(f'Creating storage bucket {bucket_name} for mlflow artifacts')
    access_key = settings.MINIO_STORAGE_ACCESS_KEY
    secret_key = settings.MINIO_STORAGE_SECRET_KEY
    storage_endpoint: str = settings.MINIO_STORAGE_ENDPOINT
    if not storage_endpoint.startswith('http'):
        storage_endpoint = f'http://{storage_endpoint}'
    s3_client = boto3.client(
        's3',
        endpoint_url=storage_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    if not any([bucket['Name'] == bucket_name for bucket in s3_client.list_buckets()['Buckets']]):
        s3_client.create_bucket(Bucket=bucket_name)
        click.echo(f'Created bucket {bucket_name} for mlflow artifacts')
    else:
        click.echo(f'Bucket {bucket_name} already exists')
