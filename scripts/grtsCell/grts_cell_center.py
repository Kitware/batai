# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.0",
#     "geopandas>=1.0",
#     "typing-extensions>=4.12",
# ]
# ///
"""Look up the WGS84 centroid for a GRTS cell from a shapefile zip.

Latitude and longitude are from the polygon centroid in EPSG:4326.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

import click
import geopandas as gpd
from typing_extensions import TypedDict


class CellCenterResult(TypedDict, closed=True):
    """Centroid in EPSG:4326 for one GRTS cell.

    Uses PEP 728-style ``TypedDict(..., closed=True)`` via typing_extensions.
    """

    grts_cell_id: int
    latitude: float
    longitude: float


def _find_grts_column(gdf: gpd.GeoDataFrame) -> str:
    for name in ("GRTS_ID", "grts_id", "GRTSId"):
        if name in gdf.columns:
            return name
    raise click.ClickException(
        "No GRTS id column found; expected one of: GRTS_ID, grts_id, GRTSId. "
        f"Columns present: {', '.join(map(str, gdf.columns))}"
    )


def _load_gdf_from_shapefile_zip(zip_path: Path) -> gpd.GeoDataFrame:
    if not zip_path.is_file():
        raise click.ClickException(f"Not a file: {zip_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        shp_files = [p for p in tmp.rglob("*.shp") if p.is_file()]
        if not shp_files:
            raise click.ClickException("No .shp file found in the zip archive.")
        shp_path = shp_files[0]
        gdf = gpd.read_file(shp_path)

    if gdf.crs is not None:
        gdf = gdf.to_crs(epsg=4326)
    else:
        click.echo(
            "Warning: shapefile has no CRS; assuming coordinates are EPSG:4326.",
            err=True,
        )

    return gdf


def lookup_cell_center(zip_path: Path, grts_cell_id: int) -> CellCenterResult:
    gdf = _load_gdf_from_shapefile_zip(zip_path)
    col = _find_grts_column(gdf)
    # Normalize IDs for comparison (shapefiles may store as float)
    ids = gdf[col].dropna()
    try:
        mask = ids.astype("int64") == grts_cell_id
    except (ValueError, TypeError) as e:
        msg = f"Could not interpret {col} as integer ids: {e}"
        raise click.ClickException(msg) from e

    subset = gdf.loc[mask]
    if subset.empty:
        msg = f"No feature with {col}={grts_cell_id!r} in {zip_path}"
        raise click.ClickException(msg)
    if len(subset) > 1:
        n = len(subset)
        click.echo(
            f"Warning: {n} features matched {col}={grts_cell_id}; using the first.",
            err=True,
        )
    geom = subset.iloc[0].geometry
    c = geom.centroid
    lon, lat = float(c.x), float(c.y)
    return CellCenterResult(
        grts_cell_id=grts_cell_id,
        latitude=lat,
        longitude=lon,
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "shapefile_zip",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument("grts_cell_id", type=int)
@click.option(
    "--json/--no-json",
    "as_json",
    default=False,
    help="Print a single JSON object instead of plain text.",
)
def main(shapefile_zip: Path, grts_cell_id: int, as_json: bool) -> None:  # noqa: FBT001
    result = lookup_cell_center(shapefile_zip, grts_cell_id)
    if as_json:
        click.echo(json.dumps(dict(result), indent=2))
    else:
        click.echo(f"GRTS cell id: {result['grts_cell_id']}")
        click.echo(f"Latitude:  {result['latitude']:.8f}")
        click.echo(f"Longitude: {result['longitude']:.8f}")


if __name__ == "__main__":
    try:
        main()
    except click.ClickException as exc:
        click.echo(exc.format_message(), err=True)
        sys.exit(os.EX_USAGE if hasattr(os, "EX_USAGE") else 2)
