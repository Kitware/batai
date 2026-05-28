# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "boto3",
#     "click",
# ]
#
# ///
"""Download WAV files from a vetting CSV and report their sample rates."""

from __future__ import annotations

from csv import DictReader
from dataclasses import dataclass
import json
from pathlib import Path
import random
import sys

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
import click

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from wav_sample_rates import (  # noqa: E402
    DEFAULT_ABOVE_SAMPLE_RATE_HZ,
    collect_sample_rates,
    print_sample_rate_counts,
    write_above_sample_rate_reports,
    write_sample_rate_summary,
)

DEFAULT_BUCKET = "nabat-public-acoustic-recordings"
DEFAULT_OUTPUT_DIR = Path("./csv_wav_check")


@dataclass(frozen=True)
class RunConfig:
    csv_path: Path
    count: int
    bucket: str
    file_key_column: str
    output_dir: Path
    download_dir: Path | None
    seed: int | None
    download_all: bool
    above_sample_rate_hz: int | None


def _read_file_keys(csv_path: Path, file_key_column: str) -> list[str]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = DictReader(f)
        if reader.fieldnames is None or file_key_column not in reader.fieldnames:
            available = ", ".join(reader.fieldnames or ())
            raise click.ClickException(
                f"Column {file_key_column!r} not found in {csv_path}. "
                f"Available columns: {available}"
            )
        keys = [row[file_key_column].strip() for row in reader if row.get(file_key_column)]
    if not keys:
        raise click.ClickException(f"No file keys found in {csv_path}")
    return keys


def _sample_file_keys(keys: list[str], count: int, seed: int | None) -> list[str]:
    if count > len(keys):
        click.echo(
            f"Requested {count} files but CSV has only {len(keys)}; using all rows.",
            err=True,
        )
        count = len(keys)
    rng = random.Random(seed)  # noqa: S311
    return rng.sample(keys, count)


def _local_path_for_key(download_dir: Path, file_key: str) -> Path:
    return download_dir / file_key


def _download_files(
    s3_client,
    bucket: str,
    file_keys: list[str],
    download_dir: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    download_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    failures: list[dict[str, str]] = []
    for file_key in file_keys:
        dest = _local_path_for_key(download_dir, file_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            s3_client.download_file(bucket, file_key, str(dest))
        except ClientError as exc:
            failures.append({"file_key": file_key, "error": str(exc)})
            click.echo(f"Failed to download {file_key}: {exc}", err=True)
            continue
        downloaded.append(file_key)
        click.echo(f"Downloaded {file_key}")
    return downloaded, failures


def _resolve_above_sample_rate_hz(config: RunConfig) -> int | None:
    if config.above_sample_rate_hz is not None:
        return config.above_sample_rate_hz
    if config.download_all:
        return DEFAULT_ABOVE_SAMPLE_RATE_HZ
    return None


@click.command()
@click.argument(
    "csv_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--count",
    "-n",
    default=100,
    show_default=True,
    type=int,
    help="Number of random files to download from the CSV.",
)
@click.option(
    "--bucket",
    default=DEFAULT_BUCKET,
    show_default=True,
    help="Public S3 bucket containing the WAV files.",
)
@click.option(
    "--file-key-column",
    default="file_key",
    show_default=True,
    help="CSV column name for the S3 object key.",
)
@click.option(
    "--output-dir",
    "-o",
    default=DEFAULT_OUTPUT_DIR,
    show_default=True,
    type=click.Path(path_type=Path),
    help="Directory for downloads and JSON output.",
)
@click.option(
    "--download-dir",
    default=None,
    type=click.Path(path_type=Path),
    help="Local directory for downloaded WAVs (default: <output-dir>/downloads).",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Random seed for reproducible file selection.",
)
@click.option(
    "--all",
    "download_all",
    is_flag=True,
    help="Download every file in the CSV (ignores --count and --seed).",
)
@click.option(
    "--above-sample-rate",
    "above_sample_rate_hz",
    type=click.IntRange(min=1),
    default=None,
    help=(
        "Write above_sample_rate_files.csv/json for rates strictly above "
        f"this value (Hz). With --all, defaults to {DEFAULT_ABOVE_SAMPLE_RATE_HZ} "
        "when omitted."
    ),
)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Sample WAVs from a vetting CSV, download from S3, and write sample rates."""
    run(RunConfig(**ctx.params))


def run(config: RunConfig) -> None:
    if not config.download_all and config.count < 1:
        raise click.ClickException("--count must be at least 1")

    above_threshold = _resolve_above_sample_rate_hz(config)
    if above_threshold is not None and above_threshold < 1:
        raise click.ClickException("--above-sample-rate must be at least 1")

    csv_path = config.csv_path.resolve()
    output_dir = config.output_dir.resolve()
    download_dir = (config.download_dir or output_dir / "downloads").resolve()

    all_keys = _read_file_keys(csv_path, config.file_key_column)
    if config.download_all:
        selected_keys = all_keys
        click.echo(f"Downloading all {len(selected_keys)} file(s) from CSV.")
    else:
        selected_keys = _sample_file_keys(all_keys, config.count, config.seed)

    s3_client = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    try:
        s3_client.head_bucket(Bucket=config.bucket)
    except ClientError as exc:
        raise click.ClickException(f"Could not access bucket {config.bucket!r}: {exc}") from exc

    click.echo(
        f"Downloading {len(selected_keys)} file(s) from s3://{config.bucket}/ to {download_dir}..."
    )
    downloaded_keys, download_failures = _download_files(
        s3_client, config.bucket, selected_keys, download_dir
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    selection_path = output_dir / "selected_files.json"
    selection_payload = {
        "csv_path": str(csv_path),
        "bucket": config.bucket,
        "download_all": config.download_all,
        "requested_count": len(selected_keys) if config.download_all else config.count,
        "seed": None if config.download_all else config.seed,
        "above_sample_rate_hz": above_threshold,
        "selected_file_keys": selected_keys,
        "downloaded_file_keys": downloaded_keys,
        "download_failures": download_failures,
    }
    with selection_path.open("w", encoding="utf-8") as f:
        json.dump(selection_payload, f, indent=2)
        f.write("\n")
    click.echo(f"Wrote selection manifest to {selection_path}")

    if not downloaded_keys:
        raise click.ClickException("No files were downloaded successfully")

    sample_rates_path = output_dir / "sample_rates.json"
    entries = collect_sample_rates(download_dir)
    summary = write_sample_rate_summary(entries, sample_rates_path)
    click.echo(f"Wrote {len(entries)} sample-rate entries to {sample_rates_path}")
    print_sample_rate_counts(summary)

    if above_threshold is not None:
        write_above_sample_rate_reports(entries, above_threshold, output_dir)


if __name__ == "__main__":
    main()
