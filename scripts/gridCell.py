import click
import geopandas as gpd
from shapely.geometry import Point, shape
import fiona
import json
import pyproj


# Global variable for the shapefile location
SHAPEFILE_PATH = './conus_mastersample_10km_attributed.shp'
target_crs = 'epsg:5070'
source_crs = 'epsg:4326'
# Load the shapefile using fiona
with fiona.open(SHAPEFILE_PATH, 'r') as shp:

    # Create a coordinate transformer
    transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
    geometries = [shape(feature['geometry']) for feature in shp]


def get_gridcell_id(latitude, longitude, geometries):
    x, y = transformer.transform(longitude, latitude)
    point = Point(x, y)
    for index, geom in enumerate(geometries):
        if point.within(geom):
            print(f'Found index {index}')
            return index  # Returning index as an example, modify as needed
    return None

@click.command()
@click.argument('latitude', type=float)
@click.argument('longitude', type=float)
def main(latitude, longitude):
    gridcell_id = get_gridcell_id(latitude, longitude, geometries)

    if gridcell_id is not None:
        click.echo(f'The gridcell ID is: {gridcell_id}')
    else:
        click.echo('Point not found in any grid cell.')

if __name__ == '__main__':
    main()
