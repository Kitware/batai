# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "batbot",
#     "click",
# ]
#
# [tool.uv.sources]
# batbot = { git = "https://github.com/Kitware/batbot" }
# ///
import json
from os.path import exists

import click

import batbot
from batbot import log


def pipeline_filepath_validator(ctx, param, value):
    if not exists(value):
        log.error(f'Input filepath does not exist: {value}')
        ctx.exit()
    return value


@click.command('fetch')
@click.option(
    '--config',
    help='Which ML model to use for inference',
    default=None,
    type=click.Choice(['usgs']),
)
def fetch(config):
    """
    Fetch the required machine learning ONNX model for the classifier
    """
    batbot.fetch(config=config)


@click.command('pipeline')
@click.argument(
    'filepath',
    nargs=1,
    type=str,
    callback=pipeline_filepath_validator,
)
@click.option(
    '--config',
    help='Which ML model to use for inference',
    default=None,
    type=click.Choice(['usgs']),
)
@click.option(
    '--output',
    help='Path to output JSON (if unspecified, results are printed to screen)',
    default=None,
    type=str,
)
# @click.option(
#     '--classifier_thresh',
#     help='Classifier confidence threshold',
#     default=int(classifier.CONFIGS[None]['thresh'] * 100),
#     type=click.IntRange(0, 100, clamp=True),
# )
def pipeline(
    filepath,
    config,
    output,
    # classifier_thresh,
):
    """
    Run the BatBot pipeline on an input WAV filepath.  An example output of the JSON
    can be seen below.

    .. code-block:: javascript

            {
                '/path/to/file.wav': {
                    'classifier': 0.5,
                }
            }
    """
    if config is not None:
        config = config.strip().lower()
    # classifier_thresh /= 100.0

    score = batbot.pipeline(
        filepath,
        config=config,
        # classifier_thresh=classifier_thresh,
    )

    data = {
        filepath: {
            'classifier': score,
        }
    }

    log.debug('Outputting results...')
    if output:
        with open(output, 'w') as outfile:
            json.dump(data, outfile)
    else:
        print(data)


@click.command('batch')
@click.argument(
    'filepaths',
    nargs=-1,
    type=str,
)
@click.option(
    '--config',
    help='Which ML model to use for inference',
    default=None,
    type=click.Choice(['usgs']),
)
@click.option(
    '--output',
    help='Path to output JSON (if unspecified, results are printed to screen)',
    default=None,
    type=str,
)
# @click.option(
#     '--classifier_thresh',
#     help='Classifier confidence threshold',
#     default=int(classifier.CONFIGS[None]['thresh'] * 100),
#     type=click.IntRange(0, 100, clamp=True),
# )
def batch(
    filepaths,
    config,
    output,
    # classifier_thresh,
):
    """
    Run the BatBot pipeline in batch on a list of input WAV filepaths.
    An example output of the JSON can be seen below.

    .. code-block:: javascript

            {
                '/path/to/file1.wav': {
                    'classifier': 0.5,
                },
                '/path/to/file2.wav': {
                    'classifier': 0.8,
                },
                ...
            }
    """
    if config is not None:
        config = config.strip().lower()
    # classifier_thresh /= 100.0

    log.debug(f'Running batch on {len(filepaths)} files...')

    score_list = batbot.batch(
        filepaths,
        config=config,
        # classifier_thresh=classifier_thresh,
    )

    data = {}
    for filepath, score in zip(filepaths, score_list):
        data[filepath] = {
            'classifier': score,
        }

    log.debug('Outputting results...')
    if output:
        with open(output, 'w') as outfile:
            json.dump(data, outfile)
    else:
        print(data)


@click.command('example')
def example():
    """
    Run a test of the pipeline on an example WAV with the default configuration.
    """
    batbot.example()


@click.group()
def cli():
    """
    BatBot CLI
    """
    pass


cli.add_command(fetch)
cli.add_command(pipeline)
cli.add_command(batch)
cli.add_command(example)


if __name__ == '__main__':
    cli()
