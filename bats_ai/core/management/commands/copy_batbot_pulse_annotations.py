"""
Management command to duplicate the batbot model's pulse annotations for a user.

Useful for generating training data to improve Batbot's ability to detect pulses.
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.core.management.base import CommandError
import djclick as click

from bats_ai.core.models import Annotations
from bats_ai.core.utils.batbot_annotations import BATBOT_ANNOTATION_MODEL

logger = logging.getLogger(__name__)

COPY_COMMENT = "Copy of batbot pulse annotation"


@click.command()
@click.argument("username")
@click.option("--batch-size", default=5000)
def copy_batbot_pulse_annotations(username: str, batch_size: int = 5000):
    logger.info("Finding user with username %s...", username)
    new_owner = User.objects.filter(username=username).first()
    if not new_owner:
        raise CommandError(f"No user found with username {username}")

    logger.info("Finding all pulse annotations created by batbot...")
    batbot_pulse_annotations = (
        Annotations.objects.filter(model=BATBOT_ANNOTATION_MODEL)
        .order_by("recording_id")
        .iterator(chunk_size=batch_size)
    )

    total_count = 0

    copies = []
    current_recording_id = None
    skip_recording = False
    for original in batbot_pulse_annotations:
        if original.recording_id != current_recording_id:
            current_recording_id = original.recording_id
            # This check attempts to prevent multiple runs of this command
            # from creating redundant copies for the given user. This is not
            # perfect, since it relies on the editable "comments" field, and
            # lazily checks for the existence of any annotation for the given
            # recording that was created by a run of this command. There are 2
            # existing concerns that are unlikely to cause trouble in the short
            # term, but should be noted:
            #
            # 1. "comments" are editable. If a user edits all the comments
            # for their copied annotations for a given recording, a re-run of
            # this command will duplicate the annotations again.
            #
            # 2. If a run of this command is interrupted and a strict subset of
            # annotations for a given recording has been saved, then whichever annotations
            # for that recording have not been copied WILL NOT be copied by a subsequent run.
            copied_already = Annotations.objects.filter(
                owner=new_owner, comments=COPY_COMMENT, recording_id=current_recording_id
            ).exists()
            skip_recording = copied_already
        if skip_recording:
            continue
        else:
            # Create a new annotation object and add it to copies
            copies.append(
                Annotations(
                    recording_id=original.recording_id,
                    owner=new_owner,
                    start_time=original.start_time,
                    end_time=original.end_time,
                    low_freq=original.low_freq,
                    high_freq=original.high_freq,
                    type=original.type,
                    comments=COPY_COMMENT,
                    model="",
                    confidence=original.confidence,
                )
            )
        if len(copies) >= batch_size:
            logger.info("Saving %d copied annotations...", len(copies))
            total_count += len(copies)
            Annotations.objects.bulk_create(copies)
            copies = []

    if len(copies) > 0:
        logger.info("Saving %d copied annotations...", len(copies))
        total_count += len(copies)
        Annotations.objects.bulk_create(copies)

    logger.info("Done. Copied %d annotations.", total_count)
