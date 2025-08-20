import os

from django.conf import settings
import djclick as click
import mlflow
import mlflow.onnx as mlflow_onnx
import onnx


@click.command()
def command():
    relative = ('..',) * 5
    asset_path = os.path.abspath(os.path.join(__file__, *relative, 'assets'))
    onnx_filename = os.path.join(asset_path, 'model.mobilenet.onnx')
    onnx_model = onnx.load(onnx_filename)

    mlflow.set_tracking_uri(settings.MLFLOW_ENDPOINT)
    mlflow.set_experiment('default')
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        click.echo(f'Run ID: {run_id}')
        mlflow_onnx.log_model(
            onnx_model=onnx_model,
            artifact_path='onnx_model',
            # save_as_external_data=True,
        )
        model_uri = f'runs:/{run_id}/onnx_model'
        result = mlflow.register_model(model_uri=model_uri, name='prototype')
        click.echo(f'Registered {model_uri} version {result.version}')
