import os

import geopandas as gpd

from googleroutes._utils._ext_checks import FileExtensionError, \
    validate_file_extension
from ..config import set_crs, get_crs


@validate_file_extension()
def _convert_crs_file(source: str, destination: str, crs: str, engine: str = 'fiona', **kwargs) -> None:
    """
    Convert single file to a new CRS. Supports shapefiles, geopackages, and geojson files.
    :param source: str: Source file name
    :param destination: str: Destination file name
    :param crs: str: CRS
    :param engine: str: Engine to use for conversion
    :raise: FileExtensionError: If the file extension is not valid
    :return: None
    """
    # Choose the driver based on the destination file extension
    driver = kwargs.get('driver', None)
    if driver is None:
        raise ValueError('Driver could not be determined. Try specifying the driver as a kwarg.')

    gdf = gpd.read_file(source)
    gdf.to_crs(crs, inplace=True)
    gdf.to_file(destination, driver=driver, mode='w', engine=engine, crs=crs)
    print(f'Converted {source} to {crs}')

    return


def _convert_crs_directory(source: str, destination: str, crs: str, engine: str = 'fiona', **kwargs) -> None:
    """
    Convert all files in a directory to a new CRS. Supports shapefiles, geopackages, and geojson files.
    :param source: str: Source directory name
    :param destination: str: Destination directory name
    :param crs: str: CRS
    :param engine: str: Engine to use for conversion
    :param skip_invalid: bool: Skip invalid file extensions. Only use if you are sure that you know the files are valid, or you have files that should be skipped.
    :raise: FileExtensionError: If the file extension is not valid or if the source or destination is not a directory
    :return: None
    """
    print(source)
    if not os.path.isdir(source):
        raise FileExtensionError('Source is not a directory')
    if not os.path.isdir(destination):
        raise FileExtensionError('Destination is not a directory')

    for file in os.listdir(source):
        _convert_crs_file(os.path.join(source, file), os.path.join(destination, file), crs, engine=engine, **kwargs)

    return


def change_crs(crs: str) -> None:
    """
    Change the global CRS
    :param crs: str: CRS
    """
    set_crs(crs)

    return


def crs() -> str:
    """
    Get the global CRS
    :return: str: CRS
    """
    return get_crs()


def convert_crs(source: str, destination: str, crs: str, engine: str = 'fiona', skip_invalid: bool = False) -> None:
    """
    Convert shapefile to a new CRS. Supports shapefiles, geopackages, and geojson files.
    :param source: str: Source file name or directory
    :param destination: str: Destination file name
    :param crs: str: CRS
    :param engine: str: Engine to use for conversion
    :param skip_invalid: bool: Skip invalid file extensions. Only use if you are sure that you know the files are valid or you have files that should be skipped.
    :raise: FileExtensionError: If the file extension is not valid
    """
    if not os.path.exists(source):
        raise FileExtensionError('Source file does not exist')

    if not os.path.isdir(source):
        _convert_crs_file(source, destination, crs, engine)
    else:
        _convert_crs_directory(source, destination, crs, engine, skip_invalid=skip_invalid)

    return
