from __future__ import annotations

import logging
from csv import DictReader
from pathlib import Path

import djclick as click
from django.contrib.auth.models import User

from bats_ai.core.models import Recording, RecordingTag

logger = logging.getLogger(__name__)


def _get_or_create_tags(entry: dict, tag_keys: list[str], owner: User):
    tags = []
    for key in tag_keys:
        tag_text = entry.get(key)
        if not tag_text:
            continue
        tag, _created = RecordingTag.objects.get_or_create(user=owner, text=tag_text)
        tags.append(tag)
    return tags


@click.command()
@click.argument(
    "manifest",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "file_key",
)
@click.argument(
    "tags",
)
@click.option(
    "--owner",

)
def update_vetter_tags(manifest: Path, file_key: str, tags: str, owner: str):
    tag_keys = tags.split(",")
    tag_owner = None
    if owner is None:
        tag_owner = User.objects.filter(is_superuser=True).first()
    else:
        tag_owner = User.objects.filter(username=owner).first()
    if not tag_owner:
        raise click.ClickException("Could not find a user for tag ownership")
    with open(manifest) as manifest_file:
        reader = DictReader(manifest_file)
        if not reader.fieldnames:
            raise click.ClickException(f"Manifest file {manifest} does not have column headers")
        if file_key not in reader.fieldnames:
            raise click.ClickException(f"Column header {file_key} does not exist in {manifest}")
        for key in tag_keys:
            if key not in reader.fieldnames:
                raise click.ClickException(f"Column header {key} does not exist in {manifest}")
        for entry in reader:
            file_name = entry[file_key]
            recording = Recording.objects.filter(name=file_name).first()
            if not recording:
                continue

            new_tags = _get_or_create_tags(entry, tag_keys, tag_owner)
            recording.tags.set(new_tags)
