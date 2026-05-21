# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
# ]
#
# ///
"""List sample rates for all WAV files under a folder (recursive)."""

from __future__ import annotations

import json
from pathlib import Path
import wave

import click


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
    help="JSON file to write (ordered by path).",
)
def main(folder: Path, output_path: Path) -> None:
    """Recursively find WAV files and write their sample rates to JSON."""
    folder = folder.resolve()
    entries = collect_sample_rates(folder)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")
    click.echo(f"Wrote {len(entries)} entries to {output_path}")


if __name__ == "__main__":
    main()
