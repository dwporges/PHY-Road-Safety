import os
import shutil
from shapely import wkt
from shapely import buffer
from shapely.geometry import shape, Point, LineString
import geopandas as gpd
import pandas as pd




def move_geodb_shp(source: str, destination: str) -> None:
    """
    Helper function to extract shapefiles from a geodatabase and move them to a new location
    
    :param src: str: Source file name
    :param dest: str: Destination file name
    """
    # Move shapefile to new location
    for fname in os.listdir(source):
        if fname.endswith('.shp'):
            shutil.move(os.path.join(source, fname), os.path.join(destination, fname))


def collisions_per_route(
        routes_dataset: gpd.GeoDataFrame | pd.DataFrame,
        collisions_dataset: gpd.GeoDataFrame | pd.DataFrame,
        routes_id_column: str = 'id',
        routes_geometry_column: str = None,
        collisions_geometry_column: str = None,
        buffer_size: float | int = 10,
        routes_crs: str = None,
        collisions_crs: str = None,
) -> pd.DataFrame:
    """
    Create a shapefile with the number of collisions per route

    :param routes_dataset: gpd.GeoDataFrame | pd.DataFrame: DataFrame containing the routes
    :param collisions_dataset: gpd.GeoDataFrame | pd.DataFrame: DataFrame containing the collisions
    :param routes_id_column: str: Column name for route ID
    :param routes_geometry_column: str: Column name for route geometry
    :param collisions_geometry_column: str: Column name for collision geometry
    :param buffer_size: float | int: Buffer size in units of the CRS of the routes dataframe
    :param routes_crs: str: CRS of the routes dataframe
    :param collisions_crs: str: CRS of the collisions dataframe
    :return: pd.DataFrame: DataFrame with the number of collisions per route. The DataFrame will have two columns: 'id' and 'collisions_count', the 'id' column will match the id column of the routes dataframe, and the 'collisions_count' column will contain the number of collisions for each route.
    """

    if routes_geometry_column is None:
        try:
            routes = routes_dataset.geometry
            routes_geometry_column = 'geometry'
        except AttributeError:
            raise AttributeError('Routes dataset does not have a geometry column and routes_geometry_column is not specified')
    else:
        routes = routes_dataset[routes_geometry_column]

    if collisions_geometry_column is None:
        try:
            collisions = collisions_dataset.geometry
            collisions_geometry_column = 'geometry'
        except AttributeError:
            raise AttributeError('Collisions dataset does not have a geometry column and collisions_geometry_column is not specified')
    else:
        collisions = collisions_dataset[collisions_geometry_column]


    if not type(routes[0])== LineString:
        try:
            routes = routes.apply(wkt.loads)
            if routes_crs is None:
                raise AttributeError('Routes dataset does not have a CRS and routes_crs is not specified. This happened because routes_dataset was supplied as a pandas DataFrame without the support for a crs')
        except Exception as e:
            raise TypeError(f'Routes dataset is not a valid LineString. Must be a shapely.geometry.LineString or be written in a format accessible to shapely.wkt.loads. Error: {e}')

    if not type(collisions[0])== Point:
        try:
            collisions = collisions.apply(wkt.loads)
            if collisions_crs is None:
                raise AttributeError('Collisions dataset does not have a CRS and collisions_crs is not specified. This happened because collisions_dataset was supplied as a pandas DataFrame without the support for a crs')
        except Exception as e:
            raise TypeError(f'Collisions dataset is not a valid Point. Must be a shapely.geometry.Point or be written in a format accessible to shapely.wkt.loads. Error: {e}')


    routes = gpd.GeoDataFrame(routes).set_geometry(routes_geometry_column, crs=routes_crs)
    collisions = gpd.GeoDataFrame(collisions).set_geometry(collisions_geometry_column, crs=collisions_crs)

    # Check if the routes and collisions are in the same CRS
    if routes.crs != collisions.crs:
        print(
            f'Warning: Routes and collisions datasets are not in the same CRS. Converting the collisions dataset to the CRS of the routes dataset: {routes.crs}.')
        collisions = collisions.to_crs(routes.crs)


    buffers = buffer(routes, distance=buffer_size)

    # Create empty GeoDataFrame to store results
    results = pd.DataFrame(columns=[routes_id_column, 'collisions_count'], dtype=int)
    results[routes_id_column] = routes_dataset[routes_id_column]

    # Create empty list to store collisions count
    collisions_count = []

    # Iterate over each buffer and count the number of collisions within it
    for i, buf in buffers.iterrows():
        collisions_count.append(sum(buf.geometry.contains(point) for point in collisions.geometry))


    results['collisions_count'] = pd.Series(collisions_count, index=results.index)

    return results



def main():
    routes_dataset = gpd.read_file('../../data/all/small/27700/geodb/Abbey Lane Primary.gpkg')
    collisions_dataset = gpd.read_file('../../data/merged_road_casualty_statistics_2019-2023.csv')



    #collisions_dataset.geometry = collisions_dataset.geometry.apply(wkt.loads)

    routes_id_column = 'id'

    collisions = collisions_per_route(routes_dataset=routes_dataset, collisions_dataset=collisions_dataset, routes_id_column=routes_id_column, buffer_size=50, collisions_crs='epsg:27700')

    print(collisions)


if __name__ == '__main__':
    main()







            
