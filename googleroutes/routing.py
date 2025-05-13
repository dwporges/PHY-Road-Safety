import logging
import os
from datetime import datetime
from typing import List

import fiona as fn
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiLineString, mapping

from ._utils._ext_checks import validate_file_extension
from ._utils._route_utils import _plot_routes, _get_routes_from_kml, _get_polyline_from_route
from .config import get_client, get_crs

logger = logging.getLogger(__name__)


# Set the path to the Google Maps API key

def get_directions(
        origin: str,
        destination: str,
        mode: str = 'driving',
        departure_time: datetime = None,
        arrival_time: datetime = None,
        alternatives: bool = False,
        region: str = 'uk'):
    """
    Get directions from origin to destination using Google Maps API.
    
    :param origin: str: Origin address or coordinates
    :param destination: str: Destination address or coordinates
    :param mode: str: Travel mode (driving, walking, bicycling, transit)
    :param departure_time: datetime: Departure time
    :param arrival_time: datetime: Arrival time
    :param alternatives: bool: Whether to return alternative routes
    :param region: str: Region code (e.g., 'uk', 'us')
    :return: dict: Directions response from Google Maps API
    """

    # Get Google Maps client
    client = get_client()

    # Get directions
    directions = client.directions(
        origin=origin,
        destination=destination,
        mode=mode,
        departure_time=departure_time,
        arrival_time=arrival_time,
        alternatives=alternatives,
        region=region
    )
    return directions


def generate_from_kml(routes_output: str, origins_fname: str, destination: str, mode: str = 'walking',
                      departure_time: datetime = None,
                      arrival_time: datetime = None, map_output: str = 'routes.html',
                      crs: str = None, plot_routes: bool = False, **kwargs) -> List | None:
    """
    Generate routes from a KML file

    :param routes_output: str: File name or path for routes output
    :param origins_fname: str: KML file name or path
    :param destination: str: Destination address
    :param mode: str: Travel mode
    :param departure_time: datetime: Departure time
    :param arrival_time: datetime: Arrival time
    :param map_output: str: Output map file name
    :param crs: str: Coordinate Reference System
    :param plot_routes: bool: Whether to plot routes or not
    :param kwargs: Optional arguments
    """

    glob_crs = get_crs()

    driver = kwargs.get('driver', None)
    if driver is None:
        raise ValueError('Driver could not be determined. Try specifying the driver as a kwarg.')

    logger.info('Generating routes...')
    coords = _get_routes_from_kml(origins_fname, destination, mode, departure_time, arrival_time)

    logger.info('Routes generated')

    # Generate MultiLineString geometry, transposing coordinates
    geometry = MultiLineString([[L[::-1] for L in sub] for sub in coords])

    logger.info('Geometry generated')

    # Generate schema for shapefile
    schema = {'geometry': 'LineString', 'properties': {'id': 'int'}}

    logger.info('Schema generated')

    logger.info(f'Saving routes to {routes_output}...')

    # Save routes to shapefile
    with fn.open(routes_output, 'w', driver=driver, schema=schema, crs=crs if crs else glob_crs) as c:
        c.writerecords([{'geometry': mapping(g), 'properties': {'id': i}} for i, g in enumerate(list(geometry.geoms))])

    logger.info('Routes saved')

    # Plot routes
    if plot_routes:
        _plot_routes(coords, mode, map_output)

    return


def generate_from_isochrones(dataframe: gpd.GeoDataFrame,
                             school_coords_column: tuple[str, str] = ('CENTER_LON', 'CENTER_LAT'),
                             mode: str = 'walking',
                             geometry_column: str = None,
                             schools_column: str = 'school',
                             departure_time: datetime = None, arrival_time: datetime = None,
                             driver: str = 'ESRI Shapefile',
                             crs: str = None,
                             routes_output: str = None,
                             map_output: str = 'routes.html',
                             plot_routes: bool = False) -> None:
    """
    Generate routes from a GeoDataFrame

    :param dataframe: gpd.GeoDataFrame: GeoDataFrame with isochrones and school coordinates
    :param school_coords_column: tuple[str, str]: School coordinates column name. Provide in the order LONG, LAT
    :param mode: str: Travel mode
    :param geometry_column: str: Geometry column name
    :param schools_column: str: Schools column name. If not provided, the default is 'schools'
    :param departure_time: datetime: Departure time
    :param arrival_time: datetime: Arrival time
    :param driver: str: Driver to use. Options are 'ESRI Shapefile', 'GPKG' and 'GeoJson'
    :param routes_output: str: Output routes folder name
    :param map_output: str: Output map file name
    :param crs: str: CRS to use for saving shapefile
    :param plot_routes: bool: Whether to plot routes or not
    """

    glob_crs = get_crs()

    client = get_client()

    df = dataframe.copy()

    # Check if geometry column is provided
    if geometry_column is not None:
        try:
            df.geometry = df[geometry_column]
        except KeyError:
            raise KeyError(f'{geometry_column} column not found in dataframe')
    elif 'geometry' in df.columns:
        try:
            df.geometry = df['geometry']
        except KeyError:
            raise KeyError('No geometry column found in dataframe')
    else:
        logger.info('No geometry column provided, using default geometry column')

    # Check if schools column is provided and valid
    try:
        schools = df[schools_column]
        if not isinstance(schools, pd.Series):
            raise ValueError(f'{schools_column} column is not a valid Series')
    except KeyError:
        raise KeyError(f'{schools_column} column not found in dataframe')

    # Check if school coordinates column is provided and valid
    if len(school_coords_column) != 2:
        raise ValueError(f'{school_coords_column} column is not a valid Series')
    if school_coords_column[0] not in df.columns or school_coords_column[1] not in df.columns:
        raise ValueError(f'{school_coords_column} column is not a valid Series')

    if routes_output is not None:
        if not os.path.isdir(routes_output):
            if '.' in routes_output:
                raise ValueError(
                    f'{routes_output} is not a valid directory (hint: routes_output contains a \'.\' but should be a directory and not a file)')
            else:
                raise ValueError(f'{routes_output} is not a valid directory or does not exist')

    # Check if driver is valid and set file extension
    match driver:
        case 'ESRI Shapefile':
            ext = '.shp'
        case 'GPKG':
            ext = '.gpkg'
        case 'GeoJSON':
            ext = '.geojson'
        case _:
            raise ValueError(f'{driver} is not a valid driver. Supported drivers are ESRI Shapefile, GPKG and GeoJSON')

    for i, row in df.iterrows():
        # Get school coordinates
        origins = [pair[::-1] for pair in
                   np.asarray(df.geometry.loc[i].exterior.coords.xy).T.tolist()]  # Yummy one-liner :)
        # Get destination coordinates
        destination = [row[school_coords_column[1]], row[school_coords_column[0]]]
        # Get school name
        school_name = row[schools_column]

        # Get routes
        logger.info(f'Generating routes for {school_name}...')

        logger.debug(f'Origins: {origins}')
        logger.debug(f'Destination: {destination}')
        logger.debug(f'School coords from df: {row[school_coords_column[1]], row[school_coords_column[0]]}')
        logger.debug(f'Isochrone coords: {df.geometry.loc[i]}')

        routes = [client.directions(origin=origin, destination=destination, mode=mode, region='uk', alternatives=True,
                                    departure_time=departure_time, arrival_time=arrival_time) for origin in origins]

        # Get polylines from routes in list format
        coords = [_get_polyline_from_route(route) for route in routes if route != []]

        logger.debug(f'Routes generated')

        # Generate MultiLineString geometry, transposing coordinates
        geometry = MultiLineString([[L[::-1] for L in sub] for sub in coords])

        logger.debug(f'Geometry generated')

        # Generate schema for shapefile
        schema = {'geometry': 'LineString', 'properties': {'id': 'int'}}

        logger.debug(f'Schema generated')

        logger.info(f'Saving routes to {routes_output}/{school_name}{ext}...')

        # Save routes to shapefile
        with fn.open(os.path.join(routes_output, school_name) + ext, 'w', driver=driver, schema=schema,
                     crs=crs if crs else glob_crs) as c:
            c.writerecords(
                [{'geometry': mapping(g), 'properties': {'id': i}} for i, g in enumerate(list(geometry.geoms))])

        logger.debug(f'Routes saved')

        # Plot routes
        if plot_routes:
            _plot_routes(coords, mode, map_output)

    return
