from django.conf import settings
import djclick as click
from mlflow import MlflowClient
from sklearn.datasets import load_diabetes
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


@click.command()
def command():
    click.echo("Running Mlflow experiment")

    client = MlflowClient(tracking_uri=settings.MLFLOW_ENDPOINT)
