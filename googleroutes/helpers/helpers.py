import os
import shutil




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



            
