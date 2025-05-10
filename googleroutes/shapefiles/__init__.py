"""
''googleroutes.shapefiles''
This module provides functions to handle shapefiles for geospatial data.
It includes functions to read, write, and manipulate shapefiles, as well as simple functions to generate shapefiles used to visualise school locations.
The following functions are present in the main ''googleroutes'' namespace:
- create_school_shapefile: Create a shapefile for school locations.
- create_multi_points_shapefile: Create a shapefile for multiple points.

"""

from . import shapefiles
from .shapefiles import *