import os
from typing import List, Callable, Any
import functools


class FileExtensionError(Exception):
    """
    Custom exception for file extension errors.
    """
    def __init__(self, ext: str, message: str=None):
        self.ext = ext
        if message:  # If a custom message is provided, use it
            self.message = message
        else:  # Otherwise, generate a default message
            if ext == "":
                self.message = "File has no extension, or an extensionless file is not permitted."
            else:
                self.message = f"Invalid file extension: {ext}"
        super().__init__(self.message)



def validate_file_extension(valid_extensions: List[str]=None) -> Callable:
    """
    Decorator to validate file extensions and inject the appropriate driver.
    
    :param valid_extensions: List of valid file extensions. Default: ['.geojson', '.gpkg', '.shp']
    :return: Callable: Decorated function
    
    Supported keyword arguments when calling decorated functions:
    - skip_invalid (bool): If True, allows processing files with invalid extensions
    - driver (str): Override the automatically detected driver
    """
    if valid_extensions is None:
        valid_extensions = ['.geojson', '.gpkg', '.shp']
    
    valid_extensions = _format_valid_extensions(valid_extensions)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(filepath: str, *args, **kwargs):
            # Get skip_invalid from kwargs
            skip_invalid = kwargs.get('skip_invalid', False)

            print(skip_invalid)

            if not os.path.exists(filepath):
                raise FileExtensionError('', f"File or directory does not exist: {filepath}")

            # Check file extension
            _, ext = os.path.splitext(filepath)
            ext = ext.lower()

            print(f"File extension: {ext}")

            
            if ext not in valid_extensions:
                if skip_invalid:
                    # If skip_invalid is True, just return the function
                    return None
                else:
                    # If the extension is not valid and skip_invalid is False, raise an error
                    message = f"Invalid file extension: {ext}. Supported extensions: {', '.join(valid_extensions)}"
                    raise FileExtensionError(ext, message)
            
            # Determine driver if not provided
            if 'driver' not in kwargs:
                try:
                    kwargs['driver'] = choose_driver(filepath)
                except FileExtensionError:
                    # If we can't determine driver but extension is valid, 
                    # let the function handle it
                    pass
            
            return func(filepath, *args, **kwargs)
        
        return wrapper
    
    return decorator



def _format_valid_extensions(valid_extensions: List[str]) -> List[str]:
    """
    Format the list of valid extensions to ensure they are all lowercase and include the leading dot.
    :param valid_extensions: list: List of valid extensions
    :return: list: Formatted list of valid extensions
    """
    return ['' if ext == '' else ext.lower() if ext.startswith('.') else '.' + ext.lower() for ext in valid_extensions]


def check_file_extension(file_path: str, valid_extensions: List[str], message: str=None) -> None:
    """
    Check if the file has a valid extension.
    :param file_path: str: File path
    :param valid_extensions: list: List of allowed extension strings. To allow files without an extension, include '' in the list.
    :raise: FileExtensionError: If the file extension is not valid
    :return: bool: True if valid
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    valid_extensions = _format_valid_extensions(valid_extensions)
    
    if ext not in valid_extensions:
        raise FileExtensionError(ext, message)
    
    return True


def choose_driver(file_path: str, message: str=None) -> str:
    """
    Choose the appropriate driver based on the file extension.
    :param file_path: str: File path
    :param message: str: Custom error message
    :raise: FileExtensionError: If the file extension does not match any known driver
    :return: str: Driver name
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if message is None:
        message = f"Could not determine driver for file extension: {ext}"

    match ext:
        case '.shp':
            return 'ESRI Shapefile'
        case '.gpkg':
            return 'GPKG'
        case '.geojson':
            return 'GeoJSON'
        case _:
            raise FileExtensionError(ext, "Could not determine driver for file extension")

