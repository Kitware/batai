from __future__ import annotations

from csv import DictReader
import logging
from pathlib import Path

import djclick as click

from bats_ai.core.models import Recording

logger = logging.getLogger(__name__)


@click.command()
@click.argument(
    "manifest",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "id_map",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--recording-name-column", default="file_key")
@click.option("--recording-sample-frame-column", default="sample_frame")
@click.option(
    "--map-sample-frame-name",
    default="short_name",
)
@click.option("--map-sample-frame-id", default="id")
def update_sample_frame_id(  # noqa: PLR0913
    manifest: Path,
    id_map: Path,
    recording_name_column: str,
    recording_sample_frame_column: str,
    map_sample_frame_name: str,
    map_sample_frame_id: str,
):
    sample_frame_map = {}
    with open(id_map) as map_file:
        map_reader = DictReader(map_file)
        for line in map_reader:
            sample_frame_map[line[map_sample_frame_name]] = line[map_sample_frame_id]

    with open(manifest) as manifest_file:
        manifest_reader = DictReader(manifest_file)
        for line in manifest_reader:
            recording_name = line[recording_name_column]
            recording_sample_frame = line[recording_sample_frame_column]
            recording = Recording.objects.filter(name=recording_name).first()
            if not recording:
                logger.info("No recording found with name %s. Skipping...", recording_name)
                continue
            new_sample_frame_id = sample_frame_map.get(recording_sample_frame)
            if not new_sample_frame_id:
                logger.info(
                    "Could not determine sample frame ID for %s. Skipping...",
                    recording_sample_frame,
                )
                continue
            recording.sample_frame_id = new_sample_frame_id
            recording.save(update_fields=["sample_frame_id"])
