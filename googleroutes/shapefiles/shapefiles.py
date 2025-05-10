import fiona as fn
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, mapping

from ..config import get_crs


def create_school_shapefile(lat: str | float, lng: str | float, output: str = 'school.shp') -> None:
    """
    Create a shapefile for a school

    :param lat: str | float: Latitude
    :param lng: str | float: Longitude
    :param output: str: Output file name
    """
    # Get the CRS from the config
    glob_crs = get_crs()

    # Generate Point geometry
    geometry = Point(float(lng), float(lat))

    # Generate schema for shapefile
    schema = {
        'geometry': 'Point',
        'properties': {'id': 'int'}
    }

    # Save school coords to shapefile
    with fn.open(output, 'w', 'ESRI Shapefile', schema, crs=glob_crs) as c:
        c.write({'geometry': mapping(geometry), 'properties': {'id': int(1)}})

    return


def create_multi_points_shapefile(dataframe: pd.DataFrame | gpd.GeoDataFrame, id_column: str,
                                  output: str = 'schools.shp', longitude_column: str = 'Longitude',
                                  latitude_column: str = 'Latitude') -> None:
    """
    Create a shapefile for multiple points

    :param dataframe: pd.DataFrame | gpd.GeoDataFrame: DataFrame containing the data
    :param id_column: str: Column name for ID
    :param output: str: Output file name
    :param longitude_column: str: Column name for Longitude
    :param latitude_column: str: Column name for Latitude
    """
    # Get the CRS from the config
    glob_crs = get_crs()

    # Generate Point geometry
    geometry = [Point(float(row[longitude_column]), float(row[latitude_column])) for i, row in dataframe.iterrows()]

    # Generate schema for shapefile
    schema = {
        'geometry': 'Point',
        'properties': {'id': 'str'}
    }

    with fn.open(output, 'w', 'ESRI Shapefile', schema, crs=glob_crs) as c:
        c.writerecords([{'geometry': mapping(point), 'properties': {'id': row[id_column]}} for point, i, row in
                        zip(geometry, dataframe.iterrows())])

    return
