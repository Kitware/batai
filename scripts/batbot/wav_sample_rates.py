# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
#
# ///
"""List sample rates for all WAV files under a folder (recursive)."""

from __future__ import annotations

from csv import DictWriter
import json
from pathlib import Path
import wave

import click

DEFAULT_ABOVE_SAMPLE_RATE_HZ = 256_000


def _read_sample_rate_hz(wav_path: Path) -> int:
    with wave.open(str(wav_path), "rb") as wav_file:
        return wav_file.getframerate()


def collect_sample_rates(root: Path) -> list[dict[str, int | str | None]]:
    """Walk *root* and return an ordered list of path + sample rate entries."""
    wav_paths = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".wav")
    entries: list[dict[str, int | str | None]] = []
    for wav_path in wav_paths:
        relative_path = wav_path.relative_to(root).as_posix()
        try:
            sample_rate_hz = _read_sample_rate_hz(wav_path)
        except (wave.Error, OSError) as exc:
            entries.append(
                {
                    "path": relative_path,
                    "sample_rate_hz": None,
                    "error": str(exc),
                }
            )
            continue
        entries.append(
            {
                "path": relative_path,
                "sample_rate_hz": sample_rate_hz,
            }
        )
    return entries


def count_sample_rates(
    entries: list[dict[str, int | str | None]],
) -> dict[str, int | list[dict[str, int]]]:
    """Return per-rate file counts and how many entries failed to read."""
    counts: dict[int, int] = {}
    error_count = 0
    for entry in entries:
        rate = entry.get("sample_rate_hz")
        if rate is None:
            error_count += 1
            continue
        counts[int(rate)] = counts.get(int(rate), 0) + 1
    return {
        "sample_rate_counts": [
            {"sample_rate_hz": rate, "count": count} for rate, count in sorted(counts.items())
        ],
        "error_count": error_count,
        "total_files": len(entries),
    }


def entries_above_sample_rate(
    entries: list[dict[str, int | str | None]],
    threshold_hz: int,
) -> list[dict[str, int | str]]:
    """Return entries whose sample rate is strictly greater than *threshold_hz*."""
    return [
        {
            "path": str(entry["path"]),
            "sample_rate_hz": int(entry["sample_rate_hz"]),
        }
        for entry in entries
        if entry.get("sample_rate_hz") is not None and int(entry["sample_rate_hz"]) > threshold_hz
    ]


def write_above_sample_rate_reports(
    entries: list[dict[str, int | str | None]],
    threshold_hz: int,
    output_dir: Path,
) -> list[dict[str, int | str]]:
    """Write JSON and CSV lists of files strictly above *threshold_hz*."""
    high_rate_files = entries_above_sample_rate(entries, threshold_hz)
    payload = {
        "above_sample_rate_hz": threshold_hz,
        "count": len(high_rate_files),
        "files": high_rate_files,
    }
    json_path = output_dir / "above_sample_rate_files.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    csv_path = output_dir / "above_sample_rate_files.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = DictWriter(f, fieldnames=["path", "sample_rate_hz"])
        writer.writeheader()
        writer.writerows(high_rate_files)

    click.echo(
        f"Wrote {len(high_rate_files)} file(s) with sample rate > {threshold_hz} Hz "
        f"to {json_path} and {csv_path}"
    )
    return high_rate_files


def write_sample_rate_summary(
    entries: list[dict[str, int | str | None]],
    output_path: Path,
) -> dict[str, int | list[dict[str, int]]]:
    """Write full sample-rate JSON (entries + counts) to *output_path*."""
    summary = count_sample_rates(entries)
    payload = {"entries": entries, **summary}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return summary


def print_sample_rate_counts(summary: dict[str, int | list[dict[str, int]]]) -> None:
    if summary["sample_rate_counts"]:
        click.echo("Sample rate counts:")
        for item in summary["sample_rate_counts"]:
            click.echo(f"  {item['sample_rate_hz']} Hz: {item['count']}")
    if summary["error_count"]:
        click.echo(
            f"{summary['error_count']} file(s) could not be read as WAV",
            err=True,
        )


@click.command()
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default="./sample_rates.json",
    show_default=True,
    type=click.Path(path_type=Path),
    help="JSON file for all entries plus per-rate counts.",
)
@click.option(
    "--above-sample-rate",
    "above_sample_rate_hz",
    type=click.IntRange(min=1),
    default=None,
    help=(
        "Write above_sample_rate_files.csv/json for files strictly above "
        "this value (Hz), e.g. --above-sample-rate 256000."
    ),
)
def main(folder: Path, output_path: Path, above_sample_rate_hz: int | None) -> None:
    """Recursively find WAV files and write their sample rates to JSON."""
    folder = folder.resolve()
    output_path = output_path.resolve()
    output_dir = output_path.parent

    entries = collect_sample_rates(folder)
    summary = write_sample_rate_summary(entries, output_path)
    click.echo(f"Wrote {len(entries)} sample-rate entries to {output_path}")
    print_sample_rate_counts(summary)

    if above_sample_rate_hz is not None:
        write_above_sample_rate_reports(entries, above_sample_rate_hz, output_dir)


if __name__ == "__main__":
    main()
