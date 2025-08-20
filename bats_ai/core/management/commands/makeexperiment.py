from django.conf import settings
from django.contrib.auth.models import User
import djclick as click
from mlflow import MlflowClient


@click.option(
    '--username',
    type=click.STRING,
    required=True,
    help='superuser username for mlflow experiment creation',
)
@click.option('--name', type=click.STRING, required=True, help='a name for the mlflow experiment')
@click.option(
    '--description',
    type=click.STRING,
    required=False,
    help='a description for the mlflow experiment',
)
@click.command()
def command(username, name, description: str | None = None):
    user = None
    if username:
        user = User.objects.get(username=username)
    else:
        first_user = User.objects.first()
        if first_user:
            user = user

    if user:
        mlflow_client = MlflowClient(tracking_uri=settings.MLFLOW_ENDPOINT)

        experiment_tags = {
            'project-name': 'batsai',
        }
        if description:
            experiment_tags['mlflow.note.content'] = description

        mlflow_client.create_experiment(name=name, tags=experiment_tags)
