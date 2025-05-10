import geopandas as gpd

def read_kml(fname: str=None, transpose: bool=False) -> list[list[str]]:
    """
    Read a KML file and return the coordinates of the geometries.
    
    :param fname: str: KML file name
    :param transpose: bool: If True, return coordinates as [lat, lng] instead of [lng, lat]
    :return: list[list[str]]: List of coordinates. Ordered as [lng, lat] by default.
    :raise: ValueError: If the KML file name is not provided
    """
    if fname:
        f = gpd.read_file(fname)
        if transpose:
            return [[geo.y, geo.x] for geo in f.geometry]
        return [[geo.x, geo.y] for geo in f.geometry]
    else:
        raise ValueError('KML file name is required')