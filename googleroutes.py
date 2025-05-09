import pandas as pd
import geopandas as gpd
import googlemaps as gm
from pprint import pprint
import folium as fm
from shapely.geometry import Point, Polygon, MultiLineString, LineString, mapping
import fiona as fn
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import shutil as sh
from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)

def depracated(func):
    """
    Deprecated decorator for functions
    """
    def wrapper(*args, **kwargs):
        print(f'{func.__name__} is deprecated')
        return func(*args, **kwargs)
    return wrapper

@depracated
def cache(func):
    """
    Cache decorator for functions
    """
    cache.cache_ = {}
    def wrapper(origins_fname, destination, mode='walking', departure_time=None, arrival_time=None, map_output='routes.html', routes_output='routes.pkl', driver='ESRI Shapefile'):
        if origins_fname not in cache.cache_:
            cache.cache_[origins_fname] = func(origins_fname, destination, mode='walking', departure_time=None, arrival_time=None, map_output='routes.html', routes_output='routes.pkl', driver='ESRI Shapefile')
        return cache.cache_[origins_fname]
    return wrapper

def start_client(api_key: str=None, crs: str='epsg:4326') -> None:
    """
    Start a Google Maps client
    :param api_key: str: API key
    """
    if api_key:
        global client, glob_crs

        # Start Google Maps client
        client = gm.Client(key=api_key)

        # Set global CRS
        glob_crs = crs
        return
    else:
        raise ValueError('API key is required')
    
def change_crs(crs: str=None) -> None:
    """
    Change the global CRS
    :param crs: str: CRS
    """
    if not crs:
        raise ValueError('CRS is required')
    global glob_crs
    glob_crs = crs
    return
    
def read_kml(fname: str=None, transpose: bool=False) -> list[list[str]]:
    if fname:
        f = gpd.read_file(fname)
        if transpose:
            return [[geo.y, geo.x] for geo in f.geometry]
        return [[geo.x, geo.y] for geo in f.geometry]
    else:
        raise ValueError('KML file name is required')

def get_polyline_from_route(route: dict) -> list[list[str]]:
    """
    Get steps from a route
    :param route: dict: Route
    """

    assert route != [], 'Route is empty'
    # Get steps from route
    steps = route[0]['legs'][0]['steps']
    steps_polyline = []

    # Get polyline from steps
    for step in steps:
            step_polyline = [point for point in gm.convert.decode_polyline(step['polyline']['points'])]
            step_lats, step_lngs = zip(*[(point['lat'], point['lng']) for point in step_polyline])
            for step_lat, step_lng in zip(step_lats, step_lngs):
                steps_polyline.append([step_lat, step_lng])
    return steps_polyline

# Get routes from a KML file
def get_routes(fname: str, destination: str, mode: str='walking', departure_time: datetime=None, arrival_time: datetime=None) -> list[list[list[str]]]:
    """
    Get routes from a KML file
    :param fname: str: KML file name
    :param destination: str: Destination address
    :param mode: str: Travel mode
    """
    # Read KML file
    origins = read_kml(fname, transpose=True)
    
    # Get routes
    routes = [client.directions(origin=origin, destination=destination, mode=mode, region='uk', alternatives=True, departure_time=departure_time, arrival_time=arrival_time) for origin in origins]

    # Get polylines from routes in list format
    routes_polyline = [get_polyline_from_route(route) for route in routes if route != []]

    return routes_polyline

# Plot routes on a map
def plot_routes(routes: list[list[list[str]]], mode: str='walking', output: str='routes.html') -> None:
    """
    Plot routes from a KML file
    :param routes: list[list[list[str]]]: Routes
    :param mode: str: Travel mode
    :param output: str: Output file name
    """
    # Generate folium map
    m = fm.Map(location=[routes[0][0][0], routes[0][0][1]], zoom_start=13)

    # Add routes to map
    for route in routes:
        fm.Marker([route[0][0], route[0][1]], popup='Start').add_to(m)
        fm.PolyLine(route, color='blue', weight=10, opacity=0.7).add_to(m)

    # Save map
    m.save(output)

    return

# Main generation function
# This function generates routes from a KML file, destination address and travel mode and saves them to a shapefile and a map
# The shapefile is useful for further analysis in GIS software



def generate(origins_fname: str, destination: str, mode: str='walking', departure_time: datetime=None, arrival_time: datetime=None, map_output: str='routes.html', routes_output: str='routes.pkl', driver: str='ESRI Shapefile', crs: str=None) -> List | None:
    """
    Generate routes from a KML file
    :param origins_fname: str: KML file name
    :param destination: str: Destination address
    :param mode: str: Travel mode
    :param departure_time: datetime: Departure time
    :param arrival_time: datetime: Arrival time
    :param map_output: str: Output map file name
    :param routes_output: str: Output routes file name
    """
    # Get routes

    logger.info('Generating routes...')
    coords = get_routes(origins_fname, destination, mode, departure_time, arrival_time)

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
    plot_routes(coords, mode, map_output)

    return

def generate_from_isochrones(dataframe: gpd.GeoDataFrame,
                             school_coords_column: tuple[str, str]=('CENTER_LON', 'CENTER_LAT'),
                             mode: str='walking', 
                             geometry_column: str=None, 
                             schools_column: str='school',
                             departure_time: datetime=None, arrival_time: datetime=None, 
                             map_output: str='routes.html', 
                             routes_output: str=None, 
                             driver: str='ESRI Shapefile', 
                             crs: str=None) -> None:
    """
    Generate routes from a GeoDataFrame
    :param dataframe: gpd.GeoDataFrame: GeoDataFrame with isochrones and school coordinates
    :param school_coords_column: tuple[str, str]: School coordinates column name. Provide in the order LONG, LAT
    :param mode: str: Travel mode
    :param geometry_column: str: Geometry column name
    :param schools_column: str: Schools column name. If not provided, the default is 'schools'
    :param departure_time: datetime: Departure time
    :param arrival_time: datetime: Arrival time
    :param map_output: str: Output map file name
    :param routes_output: str: Output routes folder name
    :param driver: str: Driver to use for saving shapefile
    :param crs: str: CRS to use for saving shapefile
    """

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
                raise ValueError(f'{routes_output} is not a valid directory (hint: routes_output contains a \'.\' but should be a directory and not a file)')
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
        origins = [pair[::-1] for pair in np.asarray(df.geometry.loc[i].exterior.coords.xy).T.tolist()] # Yummy one-liner :)
        # Get destination coordinates
        destination = [row[school_coords_column[1]], row[school_coords_column[0]]]
        # Get school name
        school_name  = row[schools_column]

        # Get routes
        logger.info(f'Generating routes for {school_name}...')

        logger.debug(f'Origins: {origins}')
        logger.debug(f'Destination: {destination}')
        logger.debug(f'School coords from df: {row[school_coords_column[1]], row[school_coords_column[0]]}')
        logger.debug(f'Isochrone coords: {df.geometry.loc[i]}')

        routes = [client.directions(origin=origin, destination=destination, mode=mode, region='uk', alternatives=True, departure_time=departure_time, arrival_time=arrival_time) for origin in origins]

        # Get polylines from routes in list format
        coords = [get_polyline_from_route(route) for route in routes if route != []]

        logger.debug(f'Routes generated')
        
        # Generate MultiLineString geometry, transposing coordinates
        geometry = MultiLineString([[L[::-1] for L in sub] for sub in coords])

        logger.debug(f'Geometry generated')

        # Generate schema for shapefile
        schema = {'geometry': 'LineString', 'properties': {'id': 'int'}}

        logger.debug(f'Schema generated')
            
        logger.info(f'Saving routes to {routes_output}/{school_name}{ext}...')
            

        # Save routes to shapefile
        with fn.open(os.path.join(routes_output, school_name)+ext, 'w', driver=driver, schema=schema, crs=crs if crs else glob_crs) as c:
            c.writerecords([{'geometry': mapping(g), 'properties': {'id': i}} for i, g in enumerate(list(geometry.geoms))])
        
        logger.debug(f'Routes saved')

        # Plot routes
        plot_routes(coords, mode, map_output)

    return


# Generates a single point shapefile for a lat, lng pair
# This is useful for generating shapefiles for schools
def create_school_shapefile(lat: str | float, lng: str | float, output: str='schools.shp') -> None:
    """
    Create a shapefile for a school
    :param lat: str | float: Latitude
    :param lng: str | float: Longitude
    :param output: str: Output file name
    """
    # Generate Point geometry
    geometry = Point(float(lng), float(lat))

    # Generate schema for shapefile
    schema = {
        'geometry': 'Point',
        'properties': {'id': 'int'}
    }

    # Save school coords to shapefile
    with fn.open(output, 'w', 'ESRI Shapefile', schema, crs=glob_crs) as c:
        for i, line in enumerate(geometry):
            c.write({'geometry':mapping(line), 'properties': {'id': i}})

    return

def create_multi_points_shapefile(stats19_data: pd.DataFrame, id_column: str, output: str='schools.shp') -> None:
    """
    Create a shapefile for multiple points
    :param stats19_data: pd.DataFrame: Stats19 data
    :param output: str: Output file name
    """

    schema = {
        'geometry': 'Point',
        'properties': {'id': 'str'}
    }

    with fn.open(output, 'w', 'ESRI Shapefile', schema, crs=glob_crs) as c:
        c.writerecords([{'geometry': mapping(Point(float(row['Longitude']), float(row['Latitude']))), 'properties': {'id': row[id_column]}} for i, row in stats19_data.iterrows()])  

    return

def move_geodb_shp(src: str, dst: str) -> None:
    """
    Helper function to extract shapefiles from a geodatabase and move them to a new location
    :param src: str: Source file name
    :param dest: str: Destination file name
    """
    # Move shapefile to new location
    for f in os.listdir(src):
        if f.endswith('.shp'):
            sh.move(os.path.join(src, f), os.path.join(dst, f))
            
    return

def convert_crs(src: str, dst: str, crs: str, engine: str='fiona') -> None:
    """
    Convert shapefile to a new CRS
    :param src: str: Source file name or directory
    :param dest: str: Destination file name
    :param crs: str: CRS
    :param engine: str: Engine to use for conversion
    """
    if not os.path.isdir(src):
        assert src.lower().endswith('.shp') or src.lower().endswith('.gpkg'), 'Source file must be a shapefile or geopackage'

        f = gpd.read_file(src)
        f.to_crs(crs, inplace=True)
        f.to_file(f'{dst}', driver='ESRI Shapefile', mode='w', engine=engine, crs=crs)
        print(f'Converted {src} to {crs}')

        return
    
    for file in os.listdir(src):
        # Check if file is a shapefile
        # Skip if file is not a shapefile

        driver = None

        match file.split('.')[-1].lower():
            case 'shp':
                driver = 'ESRI Shapefile'
            case 'gpkg':
                driver = 'GPKG'
            case 'geojson':
                driver = 'GeoJSON'
            case _:
                continue

        gdf = gpd.read_file(f'{src}/{file}')
        gdf.to_crs(crs, inplace=True)
        gdf.to_file(f'{dst}/{file}', driver=driver, mode='w', engine=engine, crs=crs)
        print(f'Converted {file} to {crs}')

    return


def main():
    """
    Main function to run the script
    """

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    
    # Load environment variables
    load_dotenv()

    # Get API key from environment variables
    api_key = os.getenv('API_KEY')

    isochrones = gpd.read_file('data/isochrones/iso1.gpkg')

    isotest = isochrones.iloc[7:8]
    print(isotest)

    start_client(api_key, crs='epsg:4326')

    generate_from_isochrones(isotest, routes_output='data/all/test', driver='GPKG')


if __name__ == '__main__': 
    main()