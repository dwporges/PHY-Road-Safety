from datetime import datetime
from ._file_parser import read_kml
import folium as fm
from ..config import get_client



def _get_polyline_from_route(route: dict) -> list[list[str]]:
    """
    Get steps from a route
    :param route: dict: Route
    """

    if route is None:
         raise ValueError('Route is None')
    if not route:
         raise ValueError('Route is empty')
    if route == {}:
         raise ValueError('Route is empty')
    
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


def _get_routes_from_kml(fname: str, destination: str, mode: str='walking', region: str='uk', departure_time: datetime=None, arrival_time: datetime=None) -> list[list[list[str]]]:
    """
    Get routes from a KML file
    :param fname: str: KML file name
    :param destination: str: Destination address
    :param mode: str: Travel mode
    """

    client = get_client()

    # Read KML file
    origins = read_kml(fname, transpose=True)
    
    # Get routes
    routes = [client.directions(origin=origin, destination=destination, mode=mode, region=region, alternatives=True, departure_time=departure_time, arrival_time=arrival_time) for origin in origins]

    # Get polylines from routes in list format
    routes_polyline = [_get_polyline_from_route(route) for route in routes if route != []]

    return routes_polyline


def _plot_routes(routes: list[list[list[str]]], mode: str='walking', output: str='routes.html') -> None:
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