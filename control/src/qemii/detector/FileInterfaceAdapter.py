"""Demo adapter for ODIN control FileInterface

This adapter implements methods to connect directories containing the
vector files and such things required for the QEM system

Tim Nicholls, STFC Detector Systems Software Group
Adam Neaves, STFC Detector Systems Software Group
"""
import logging
import tornado
import time
from concurrent import futures
import os

from tornado.escape import json_decode

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin._version import get_versions

DIRECTORY_CONFIG_NAME = "directories"


class FileInterfaceAdapter(ApiAdapter):
    """System info adapter class for the ODIN server.

    This adapter provides ODIN clients with information about the server and the system that it is
    running on.
    """

    def __init__(self, **kwargs):
        """Initialize the WorkshopAdapter object.

        This constructor initializes the WorkshopAdapter object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(FileInterfaceAdapter, self).__init__(**kwargs)
        self.directories = {}
        if DIRECTORY_CONFIG_NAME in self.options:
            for directory_str in self.options[DIRECTORY_CONFIG_NAME].split(','):
                logging.debug(directory_str)
                try:
                    (dir_name, path) = directory_str.split('=')
                    self.directories[dir_name.strip()] = path.strip()
                except ValueError:
                    logging.error("Illegal directory target specified for File Interface: %s",
                                  directory_str.strip())
        self.fileInterface = FileInterface(self.directories)

        logging.debug('FileInterface Adapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.fileInterface.get(path)
            status_code = 200
        except ParameterTreeError as e:
            response = {'error': str(e)}
            status_code = 400

        content_type = 'application/json'

        return ApiAdapterResponse(response, content_type=content_type,
                                  status_code=status_code)

    @request_types('application/json')
    @response_types('application/json', default='application/json')
    def put(self, path, request):
        """Handle an HTTP PUT request.

        This method handles an HTTP PUT request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """

        content_type = 'application/json'

        try:
            data = json_decode(request.body)
            self.fileInterface.set(path, data)
            response = self.fileInterface.get(path)
            status_code = 200
        except FileInterfaceError as e:
            response = {'error': str(e)}
            status_code = 400
        except (TypeError, ValueError) as e:
            response = {'error': 'Failed to decode PUT request body: {}'.format(str(e))}
            status_code = 400

        logging.debug(response)

        return ApiAdapterResponse(response, content_type=content_type,
                                  status_code=status_code)

    def delete(self, path, request):
        """Handle an HTTP DELETE request.

        This method handles an HTTP DELETE request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        response = 'FileInterfaceAdapter: DELETE on path {}'.format(path)
        status_code = 200

        logging.debug(response)

        return ApiAdapterResponse(response, status_code=status_code)


class FileInterfaceError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass


class FileInterface():
    """Workshop - class that extracts and stores information about system-level parameters."""

    # Thread executor used for background tasks
    executor = futures.ThreadPoolExecutor(max_workers=1)

    def __init__(self, directories):
        """Initialise the FileInterface object.

        This constructor initlialises the FileInterface object, building a parameter tree.
        """
        # Save arguments

        self.fp_config_files = []
        self.txt_files = []
        self.fr_config_files = []
        self.vector_files = []
        self.directories = directories

        self.odin_data_config_dir = os.path.expanduser(directories["odin_data"])
        self.vector_file_dir = os.path.expanduser(directories["vector_files"])

        # Store initialisation time
        self.init_time = time.time()

        # Get package version information
        version_info = get_versions()

        # Store all information in a parameter tree
        self.param_tree = ParameterTree({
            'odin_version': version_info['version'],
            'tornado_version': tornado.version,
            'server_uptime': (self.get_server_uptime, None),
            'fr_config_files': (self.get_fr_config_files, None),
            'fp_config_files': (self.get_fp_config_files, None),
            'vector_files': (self.get_vector_files, None),
            'config_dir': (self.odin_data_config_dir, None)
        })

    def get_server_uptime(self):
        """Get the uptime for the ODIN server.

        This method returns the current uptime for the ODIN server.
        """
        return time.time() - self.init_time

    def get(self, path):
        """Get the parameter tree.

        This method returns the parameter tree for use by clients via the FileInterface adapter.

        :param path: path to retrieve from tree
        """
        return self.param_tree.get(path)

    def set(self, path, data):
        """Set parameters in the parameter tree.

        This method simply wraps underlying ParameterTree method so that an exceptions can be
        re-raised with an appropriate FileInterfaceError.

        :param path: path of parameter tree to set values for
        :param data: dictionary of new data values to set in the parameter tree
        """
        try:
            self.param_tree.set(path, data)
        except ParameterTreeError as e:
            raise FileInterfaceError(e)

    def get_config_files(self):
        """ Retrieve all of the txt configuration files in the absolute directory path

        Clears the internal lists first to prevent circular appending at every "GET"
        """
        self.clear_lists()
        logging.debug(self.odin_data_config_dir)
        for file in os.listdir(os.path.expanduser(self.odin_data_config_dir)):
            if file.endswith('.json') and "qemii" in file:
                self.txt_files.append(file)

    def get_fp_config_files(self):
        """ gets the frame processor config files from the list of text files found
        @returns : the fp config files list
        """
        self.get_config_files()
        for file in self.txt_files:
            if "fp" in file:
                self.fp_config_files.append(file)
        return self.fp_config_files

    def get_fr_config_files(self):
        """ gets the frame receiver config files from the list of text files found
        @returns : the fr config files list
        """
        self.get_config_files()
        for file in self.txt_files:
            if "fr" in file:
                self.fr_config_files.append(file)
        return self.fr_config_files
    
    def get_vector_files(self):
        """Gets the vector files for the QEM fem from the declared directory
        @returns: the list of vector files
        """
        self.vector_files = []
        for file in os.listdir(self.vector_file_dir):
            if file.endswith('.txt') and "QEM" in file:
                self.vector_files.append(file)
        return self.vector_files

    def clear_lists(self):
        """ clears the text file, fr and fp config file lists 
        """        
        self.fp_config_files = []
        self.txt_files = []
        self.fr_config_files = []
