import logging
import os
import tempfile
import urllib
from urllib.request import urlretrieve
import zipfile

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import geopandas as gpd
from tqdm import tqdm  # progress bar

from bats_ai.core.models import GRTSCells

logger = logging.getLogger(__name__)

SHAPEFILES = [
    (
        'https://www.sciencebase.gov/catalog/file/get/5b7753bde4b0f5d578820455?facet=conus_mastersample_10km_GRTS',  # noqa: E501
        14,
        'CONUS',
        # Backup URL
        'https://data.kitware.com/api/v1/item/697cc601e7dea9be44ec5aee/download',  # noqa: E501
    ),  # CONUS
    # Removed other regions for now because of sciencebase.gov being down
    # (
    #     'https://www.sciencebase.gov/catalog/file/get/5b7753a8e4b0f5d578820452?facet=akcan_mastersample_10km_GRTS',  # noqa: E501
    #     20,
    #     'Alaska/Canada',
    # ),  # Alaska/Canada
    # (
    #     'https://www.sciencebase.gov/catalog/file/get/5b7753c2e4b0f5d578820457?facet=HI_mastersample_5km_GRTS',  # noqa: E501
    #     15,
    #     'Hawaii',
    # ),  # Hawaii
    # (
    #     'https://www.sciencebase.gov/catalog/file/get/5b7753d3e4b0f5d578820459?facet=mex_mastersample_10km_GRTS',  # noqa: E501
    #     12,
    #     'Mexico',
    # ),  # Mexico
    # (
    #     'https://www.sciencebase.gov/catalog/file/get/5b7753d8e4b0f5d57882045b?facet=PR_mastersample_5km_GRTS',  # noqa: E501
    #     21,
    #     'Puerto Rico',
    # ),  # Puerto Rico
]


class Command(BaseCommand):
    help = 'Download GRTS shapefiles, extract, and load into GRTSCells table.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', type=int, default=5000, help='Batch size for database insertion'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']

        # Track existing IDs to avoid duplicates
        existing_ids = set(GRTSCells.objects.values_list('id', flat=True))

        for url, sample_frame_id, name, backup_url in SHAPEFILES:
            logger.info(f'Downloading shapefile for Location {name}...')
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, 'file.zip')
                try:
                    urlretrieve(url, zip_path)
                except urllib.error.URLError as e:
                    logger.warning(f'Failed to download from primary URL: {e}. \
                            Attempting backup URL...')
                    if backup_url is None:
                        logger.warning('No backup URL provided, skipping this shapefile.')
                        continue
                    try:
                        urlretrieve(backup_url, zip_path)
                    except urllib.error.URLError as e2:
                        raise CommandError(
                            f'Failed to download from backup URL as well: {e2}'
                        ) from e2
                logger.info(f'Downloaded to {zip_path}')

                logger.info('Extracting zip file...')
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(tmpdir)
                logger.info('Extraction complete.')

                # Look for shapefile in the extracted directory
                shp_files = [
                    os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith('.shp')
                ]
                if not shp_files:
                    raise CommandError('No .shp file found in archive!')

                shp_path = shp_files[0]
                logger.info(f'Loading shapefile {shp_path} into GeoDataFrame...')
                gdf = gpd.read_file(shp_path)

                # Ensure geometry is WGS84 for geom_4326 (EPSG:4326)
                if gdf.crs is not None:
                    gdf = gdf.to_crs(epsg=4326)
                else:
                    logger.warning('Shapefile CRS unknown; assuming EPSG:4326')

                records_to_create = []
                count_new = 0

                for idx, row in tqdm(
                    gdf.iterrows(), total=len(gdf), desc=f'Importing {sample_frame_id}'
                ):
                    # Hard fail if GRTS_ID is missing
                    if 'GRTS_ID' not in row or row['GRTS_ID'] is None:
                        raise CommandError(f'Row {idx} missing required GRTS_ID field!')

                    grts_id = int(row['GRTS_ID'])
                    cell_id = int(row.get(list(row.keys())[0], grts_id))  # fallback to first field

                    if grts_id in existing_ids:
                        continue

                    geom_4326 = row.geometry.wkt
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

                logger.info(f'Finished importing shapefile for sample frame\
                        {sample_frame_id}: {count_new} new records')

        logger.info('All shapefiles processed successfully.')
