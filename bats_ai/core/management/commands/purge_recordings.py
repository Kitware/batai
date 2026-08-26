"""Management command to remove recordings from the system."""

from __future__ import annotations

import logging
from pathlib import Path

import djclick as click

from bats_ai.core.models import Recording

logger = logging.getLogger(__name__)

exclude_help = "A newline-delimited list of recording IDs to keep"
batch_size_help = "The number of recordings to delete at a time. Lower it for memory-limited"
dry_run_help = "If true, report number of recordings that would be deleted,"
" systems instead of deleting recordings."


def delete_recordings(to_delete, batch_size: int, total_deleted_stats: dict):
    total_deleted_count = 0
    while True:
        batch_ids = list(to_delete[:batch_size].values_list("pk", flat=True))
        if not batch_ids:
            break
        total_deleted, deleted_stats = Recording.objects.filter(pk__in=batch_ids).delete()
        total_deleted_count += total_deleted
        for key in deleted_stats:
            if key in total_deleted_stats:
                total_deleted_stats[key] += deleted_stats[key]
            else:
                total_deleted_stats[key] = deleted_stats[key]
    return total_deleted_count


@click.command()
@click.option(
    "--exclude", type=click.Path(exists=True, dir_okay=False, path_type=Path), help=exclude_help
)
@click.option("--batch-size", type=click.INT, default=1000, help=batch_size_help)
@click.option("--dry-run", type=click.BOOL, is_flag=True, help=dry_run_help)
def purge_recordings(exclude: Path, batch_size: int, dry_run):
    to_skip = set()
    if exclude:
        with open(exclude) as f:
            lines = f.readlines()
            for recording_id in lines:
                stripped_id = recording_id.strip()
                if stripped_id:
                    to_skip.add(int(stripped_id))
    if to_skip:
        logger.info("Purging all recordings. %d recordings will be skipped...", len(to_skip))
    else:
        logger.info("Purging all recordings...")

    total_deleted_stats = {}
    total_deleted_count = 0
    to_delete = Recording.objects.exclude(pk__in=to_skip).order_by("pk")
    if dry_run:
        total_deleted_count = to_delete.count()
    else:
        total_deleted_count = delete_recordings(to_delete, batch_size, total_deleted_stats)

    if dry_run:
        logger.info("Done. %d recordings would have been deleted.", total_deleted_count)
    else:
        logger.info("Done. Deleted %d objects.", total_deleted_count)
        for key, value in total_deleted_stats.items():
            logger.info("\t %d instances of %s deleted.", value, key)
