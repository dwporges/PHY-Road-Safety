"""
''googleroutes._utils''

This module provides utility functions for handling geospatial data.
It includes functions to check file extensions, choose drivers for file formats, and parse files.
The following functions are present in the main ''googleroutes'' namespace:

"""



from . import _ext_checks
from . import _file_parser
from . import _route_utils
from ._ext_checks import *
from ._file_parser import *
from ._route_utils import *