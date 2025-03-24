import pandas as pd
import geopandas as gpd
import googlemaps as gm
from pprint import pprint
import folium as fm
from shapely.geometry import Point, Polygon, MultiLineString, LineString, mapping
import fiona as fn
from datetime import datetime, timedelta

def start_client(api_key: str=None, crs: str='epsg:4326') -> None:
    """
    Start a Google Maps client
    :param api_key: str: API key
    """
    if api_key:
        global client
        client = gm.Client(key=api_key)
        global cache
        cache = {}

        global glob_crs
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
def generate(origins_fname: str, destination: str, mode: str='walking', departure_time: datetime=None, arrival_time: datetime=None, map_output: str='routes.html', routes_output: str='routes.pkl', access_cache: bool=False, generate_cache: bool=False) -> None:
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

    # Get routes from KML file
    if access_cache and not generate_cache:
        assert cache, 'Cache is empty'
        if origins_fname in cache.keys():
            coords = cache[origins_fname]
    elif access_cache and generate_cache:
        if origins_fname in cache.keys():
            coords = cache[origins_fname]
        else:
            coords = get_routes(origins_fname, destination, mode, departure_time, arrival_time)
            cache[origins_fname] = coords
    elif generate_cache:
        coords = get_routes(origins_fname, destination, mode, departure_time, arrival_time)
        cache[origins_fname] = coords
    else:
        coords = get_routes(origins_fname, destination, mode, departure_time, arrival_time)
    
    # Generate MultiLineString geometry, transposing coordinates
    geometry = MultiLineString([[L[::-1] for L in sub] for sub in coords])

    # Generate schema for shapefile
    schema = {'geometry': 'LineString', 'properties': {'id': 'int'}}

    print(routes_output)

    # Save routes to shapefile
    with fn.open(routes_output, 'w', 'ESRI Shapefile', schema, crs=glob_crs) as c:
        c.writerecords([{'geometry': mapping(g), 'properties': {'id': i}} for i, g in enumerate(list(geometry.geoms))])

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



        


