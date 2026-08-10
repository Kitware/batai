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


@click.command()
@click.argument("username")
def copy_batbot_pulse_annotations(username: str):
    logger.info("Finding user with username %s...", username)
    new_owner = User.objects.filter(username=username).first()
    if not new_owner:
        raise CommandError(f"No user found with username {username}")

    logger.info("Finding all pulse annotations created by batbot...")
    batbot_pulse_annotations = list(
        Annotations.objects.filter(model=BATBOT_ANNOTATION_MODEL).prefetch_related("species")
    )

    copies = [
        Annotations(
            recording=original.recording,
            owner=new_owner,
            start_time=original.start_time,
            end_time=original.end_time,
            low_freq=original.low_freq,
            high_freq=original.high_freq,
            type=original.type,
            comments="Copy of batbot pulse annotation",
            model="",
            confidence=original.confidence,
        )
        for original in batbot_pulse_annotations
    ]

    logger.info("Saving %d new annotations...", len(copies))
    created = Annotations.objects.bulk_create(copies)

    logger.info("Copying species info...")
    for original, copy in zip(batbot_pulse_annotations, created, strict=True):
        copy.species.set(original.species.all())

    logger.info("Done")
