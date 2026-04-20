from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile
import zipfile

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import geopandas as gpd
import requests
from tqdm import tqdm  # progress bar

from bats_ai.core.models import GRTSCells

logger = logging.getLogger(__name__)

"""
"id","description","short_name","mr_master_sample_id"
12,Mexico 10x10km Grid,Mexico,
14,Conus (Continental US) 10x10km Grid,Continental US,10
19,Canada 10x10km Grid,Canada,11
20,Alaska 10x10km Grid,Alaska,12
21,Puerto Rico 5x5km Grid,Puerto Rico,
15,Hawaii 5x5km Grid,Hawaii,13
22,Offshore Caribbean 10x10km Grid,Offshore Caribbean,
23,Offshore AKCAN 10x10km Grid,Offshore AKCAN,
24,Offshore CONUS 10x10km Grid,Offshore CONUS,
25,Offshore Hawaii 10x10km Grid,Offshore Hawaii,
26,Offshore Mexico 10x10km Grid,Offshore Mexico,
"""

LOCATION_SOURCES = {
    "CONUS": (
        "https://www.sciencebase.gov/catalog/file/get/5b7753bde4b0f5d578820455?facet=conus_mastersample_10km_GRTS",
        14,
        "CONUS",
        # Backup URL
        "https://data.kitware.com/api/v1/item/697cc601e7dea9be44ec5aee/download",
    ),
    # Optional regions (disabled by default). Include via --locations.
    "AKCAN": (
        "https://www.sciencebase.gov/catalog/file/get/5b7753a8e4b0f5d578820452?facet=akcan_mastersample_10km_GRTS",  # noqa: E501
        20,
        "Alaska/Canada",
        None,
    ),
    "HAWAII": (
        "https://www.sciencebase.gov/catalog/file/get/5b7753c2e4b0f5d578820457?facet=HI_mastersample_5km_GRTS",  # noqa: E501
        15,
        "Hawaii",
        None,
    ),
    "MEXICO": (
        "https://www.sciencebase.gov/catalog/file/get/5b7753d3e4b0f5d578820459?facet=mex_mastersample_10km_GRTS",  # noqa: E501
        12,
        "Mexico",
        None,
    ),
    "PUERTO_RICO": (
        "https://www.sciencebase.gov/catalog/file/get/5b7753d8e4b0f5d57882045b?facet=PR_mastersample_5km_GRTS",  # noqa: E501
        21,
        "Puerto Rico",
        None,
    ),
}

LOCATION_ID_TO_KEY = {str(config[1]): key for key, config in LOCATION_SOURCES.items()}

# Default to CONUS (sample_frame_id 14) only.
DEFAULT_LOCATIONS = ("CONUS",)


class Command(BaseCommand):
    help = "Download GRTS shapefiles, extract, and load into GRTSCells table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Batch size for database insertion",
        )
        parser.add_argument(
            "--locations",
            nargs="+",
            default=list(DEFAULT_LOCATIONS),
            help=(
                "Locations to import by key or sample frame ID "
                "(e.g. CONUS or 14). Defaults to CONUS only. "
                f"Keys: {', '.join(sorted(LOCATION_SOURCES.keys()))}"
            ),
        )

    def _download_file(self, url: str, zip_path: Path) -> None:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        with zip_path.open("wb") as f:
            f.write(response.content)

    def _normalize_location(self, location: str) -> str:
        normalized = location.strip().upper().replace("-", "_").replace(" ", "_")
        if normalized in LOCATION_SOURCES:
            return normalized
        if location.strip() in LOCATION_ID_TO_KEY:
            return LOCATION_ID_TO_KEY[location.strip()]
        raise CommandError(
            "Invalid location "
            f"'{location}'. Use a key ({', '.join(sorted(LOCATION_SOURCES.keys()))}) "
            f"or a sample frame ID ({', '.join(sorted(LOCATION_ID_TO_KEY.keys()))})."
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        selected_locations = options["locations"]
        selected_keys = []
        for location in selected_locations:
            location_key = self._normalize_location(location)
            if location_key not in selected_keys:
                selected_keys.append(location_key)
        shapefiles = [LOCATION_SOURCES[location_key] for location_key in selected_keys]

        # Track existing IDs to avoid duplicates
        existing_ids = set(GRTSCells.objects.values_list("id", flat=True))

        for url, sample_frame_id, name, backup_url in shapefiles:
            logger.info("Downloading shapefile for Location %s...", name)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)

                zip_path = tmpdir / "file.zip"
                try:
                    self._download_file(url, zip_path)
                except requests.RequestException as e:
                    logger.warning(
                        "Failed to download from primary URL: %s. Attempting backup URL...",
                        e,
                    )
                    if backup_url is None:
                        logger.warning("No backup URL provided, skipping this shapefile.")
                        continue
                    try:
                        self._download_file(backup_url, zip_path)
                    except requests.RequestException as e2:
                        raise CommandError(
                            f"Failed to download from backup URL as well: {e2}"
                        ) from e2
                logger.info("Downloaded to %s", zip_path)

                logger.info("Extracting zip file...")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(tmpdir)
                logger.info("Extraction complete.")

                # Look for shapefile in the extracted directory
                shp_files = [
                    os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")
                ]
                if not shp_files:
                    raise CommandError("No .shp file found in archive!")

                shp_path = shp_files[0]
                logger.info("Loading shapefile %s into GeoDataFrame...", shp_path)
                gdf = gpd.read_file(shp_path)

                # Ensure geometry is WGS84 for geom_4326 (EPSG:4326)
                if gdf.crs is not None:
                    gdf = gdf.to_crs(epsg=4326)
                else:
                    logger.warning("Shapefile CRS unknown; assuming EPSG:4326")

                records_to_create = []
                count_new = 0

                for idx, row in tqdm(
                    gdf.iterrows(),
                    total=len(gdf),
                    desc=f"Importing {sample_frame_id}",
                ):
                    # Hard fail if GRTS_ID is missing
                    if "GRTS_ID" not in row or row["GRTS_ID"] is None:
                        raise CommandError(f"Row {idx} missing required GRTS_ID field!")

                    grts_id = int(row["GRTS_ID"])
                    # fallback to first field
                    cell_id = int(row.get(next(iter(row.keys())), grts_id))

                    if grts_id in existing_ids:
                        continue

                    geom_4326 = row.geometry.wkt
                    centroid_4326 = row.geometry.centroid.wkt
                    if gdf.crs and gdf.crs.to_epsg() != 4326:
                        grts_geom = row.geometry.to_wkt()
                    else:
                        grts_geom = row.geometry.wkt

                    cell = GRTSCells(
                        id=cell_id,
                        grts_cell_id=grts_id,
                        sample_frame_id=sample_frame_id,
                        grts_geom=grts_geom,
                        geom_4326=geom_4326,
                        centroid_4326=centroid_4326,
                    )
                    records_to_create.append(cell)
                    count_new += 1

                    if len(records_to_create) >= batch_size:
                        with transaction.atomic():
                            GRTSCells.objects.bulk_create(records_to_create, ignore_conflicts=True)
                        records_to_create.clear()

                # Insert remaining records
                if records_to_create:
                    with transaction.atomic():
                        GRTSCells.objects.bulk_create(records_to_create, ignore_conflicts=True)

                logger.info(
                    "Finished importing shapefile for sample frame %s: %s new records",
                    sample_frame_id,
                    count_new,
                )

        logger.info("All shapefiles processed successfully.")
