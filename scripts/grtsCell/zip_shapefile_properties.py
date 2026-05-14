# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.0",
#     "geopandas>=1.0",
#     "typing-extensions>=4.12",
# ]
# ///
"""List attribute columns and basic metadata for a shapefile inside a zip.

Reads only schema where possible; uses the same zip extraction pattern as
``grts_cell_center.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from typing import NotRequired
import zipfile

import click
import geopandas as gpd
from typing_extensions import TypedDict


class PropertyColumn(TypedDict, closed=True):
    """One non-geometry attribute column."""

    name: str
    dtype: str


class ShapefileZipReport(TypedDict, closed=True):
    """Serializable summary of a shapefile layer in a zip archive."""

    zip_path: str
    shapefile: str
    crs: str | None
    geometry_column: str
    feature_count: NotRequired[int]
    properties: list[PropertyColumn]


def _find_shapefiles(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.shp") if p.is_file())


def _pick_shp(root: Path, inner: str | None) -> Path:
    shps = _find_shapefiles(root)
    if not shps:
        raise click.ClickException("No .shp file found in the zip archive.")
    if inner is None:
        if len(shps) > 1:
            rels = "\n".join(f"  - {p.relative_to(root)}" for p in shps)
            raise click.ClickException(
                "Multiple .shp files in the zip; choose one with --inner PATH "
                "(path or basename inside the archive), for example:\n" + rels
            )
        return shps[0]

    inner_norm = inner.replace("\\", "/").strip("/")
    for p in shps:
        rel = p.relative_to(root).as_posix()
        if rel == inner_norm or p.name == inner_norm or rel.endswith(inner_norm):
            return p
    raise click.ClickException(
        f"No .shp matched --inner {inner!r}. Paths in archive:\n"
        + "\n".join(f"  - {p.relative_to(root).as_posix()}" for p in shps)
    )


def _feature_count(shp_path: Path) -> int | None:
    try:
        import pyogrio

        return int(pyogrio.read_info(str(shp_path))["features"])
    except Exception:
        try:
            import fiona

            with fiona.open(str(shp_path)) as src:
                return len(src)
        except Exception:
            return None


def inspect_shapefile_zip(zip_path: Path, inner: str | None) -> ShapefileZipReport:
    if not zip_path.is_file():
        raise click.ClickException(f"Not a file: {zip_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        shp_path = _pick_shp(tmp, inner)
        rel_inside = shp_path.relative_to(tmp).as_posix()

        gdf = gpd.read_file(shp_path, rows=0)
        geom_name = gdf.geometry.name
        props: list[PropertyColumn] = []
        for col in gdf.columns:
            if col == geom_name:
                continue
            props.append(PropertyColumn(name=str(col), dtype=str(gdf[col].dtype)))

        crs_str = gdf.crs.to_string() if gdf.crs is not None else None
        n = _feature_count(shp_path)

    report: ShapefileZipReport = ShapefileZipReport(
        zip_path=str(zip_path.resolve()),
        shapefile=rel_inside,
        crs=crs_str,
        geometry_column=str(geom_name),
        properties=props,
    )
    if n is not None:
        report["feature_count"] = n
    return report


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "shapefile_zip",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--inner",
    type=str,
    default=None,
    help=("Path or basename of a .shp inside the zip when more than one exists."),
)
@click.option(
    "--json/--no-json",
    "as_json",
    default=False,
    help="Print a JSON object (includes feature_count when available).",
)
def main(shapefile_zip: Path, inner: str | None, as_json: bool) -> None:
    report = inspect_shapefile_zip(shapefile_zip, inner)
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    click.echo(f"Zip: {report['zip_path']}")
    click.echo(f"Shapefile (in archive): {report['shapefile']}")
    click.echo(f"CRS: {report['crs']!r}")
    click.echo(f"Geometry column: {report['geometry_column']}")
    if "feature_count" in report:
        click.echo(f"Feature count: {report['feature_count']}")
    click.echo("Attribute columns (properties):")
    for p in report["properties"]:
        click.echo(f"  - {p['name']}: {p['dtype']}")


if __name__ == "__main__":
    try:
        main()
    except click.ClickException as exc:
        click.echo(exc.format_message(), err=True)
        sys.exit(os.EX_USAGE if hasattr(os, "EX_USAGE") else 2)
