from django.conf import settings
import djclick as click
import mlflow

from bats_ai.tasks.tasks import example_train


@click.command()
@click.option('--experiment-name', type=click.STRING, required=False, default='Default')
def command(experiment_name):
    click.echo('Finding experiment')
    mlflow.set_tracking_uri(settings.MLFLOW_ENDPOINT)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment:
        click.echo(f'Creating a log for experiment {experiment_name}')
        example_train.delay(experiment_name)
        # train_body(experiment_name)
    else:
        click.echo(
            f'Could not find experiment {experiment_name}.'
            ' Use the create experiment command to create a new experiement.'
        )
