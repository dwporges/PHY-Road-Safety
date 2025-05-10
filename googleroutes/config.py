import googlemaps as gm


class Config:
    """
    Configuration class for the library.
    This class is a singleton and should be accessed through the provided functions.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.crs = 'epsg:4326'
            cls._instance.client = None
        return cls._instance
    
    def set_crs(self, crs: str) -> None:
        self.crs = crs

    def get_crs(self) -> str:
        return self.crs
    
    def set_client(self, client) -> None:
        self.client = client
        
    def get_client(self):
        return self.client
    
    def __repr__(self):
        return f"Config(crs={self.crs}, client={self.client})"

# Create a singleton instance
config = Config()

def set_crs(crs: str) -> None:
    """
    Set the CRS for the library.
    :param crs: str: CRS
    """
    config.set_crs(crs)

def get_crs() -> str:
    """
    Get the CRS for the library.
    :return: str: CRS
    """
    return config.get_crs()

def get_client():
    """
    Get the Google Maps client instance.
    :return: googlemaps.Client: The Google Maps client
    :raises: RuntimeError if client hasn't been initialized
    """
    client = config.get_client()
    if client is None:
        raise RuntimeError("Google Maps client not initialized. Call start_client() first.")
    return client

def start_client(api_key: str, crs: str='epsg:4326') -> None:
    """
    Start a Google Maps client
    :param api_key: str: API key
    :param crs: str: Default CRS to use
    :return: None
    :raises: ValueError if api_key is not provided
    """
    if not api_key:
        raise ValueError('API key is required')
        
    # Start Google Maps client
    client = gm.Client(key=api_key)
    
    # Set client and CRS in config
    config.set_client(client)
    print("Google Maps client started.")
    config.set_crs(crs)

def stop_client() -> None:
    """
    Stop the Google Maps client
    :return: None
    """
    del config.client
    config.set_client(None)
    print("Google Maps client stopped.")