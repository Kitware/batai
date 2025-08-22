from django.conf import settings
import djclick as click
from mlflow import MlflowClient


@click.option('--name', type=click.STRING, required=True, help='a name for the mlflow experiment')
@click.option(
    '--description',
    type=click.STRING,
    required=False,
    help='a description for the mlflow experiment',
)
@click.command()
def command(name, description: str | None = None):
    mlflow_client = MlflowClient(tracking_uri=settings.MLFLOW_ENDPOINT)

    experiment_tags = {
        'project-name': 'batsai',
    }
    if description:
        experiment_tags['mlflow.note.content'] = description

    mlflow_client.create_experiment(name=name, tags=experiment_tags)
