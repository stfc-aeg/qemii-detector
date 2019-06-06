""" Qem Detector Adapter for QEM Detector System.

Main control layer for the entire qem detector system.
Intelligent adapter that can communicate to all other loaded adapters lower down in the heirarchy.
Bridges the gap between generic UI commands and detector specific business logic.

Sophie Kirkham, Application Engineering Group, STFC. 2019
Adam Neaves, Application Engineering Group, STFC. 2019
"""
import logging
import tornado
import time
from concurrent import futures
import os

from tornado.ioloop import IOLoop
from odin.util import decode_request_body, convert_unicode_to_string

from odin.adapters.adapter import ApiAdapter, ApiAdapterRequest, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError

from odin.adapters.proxy import ProxyAdapter
from odin_data.live_view_adapter import LiveViewAdapter
from odin_data.frame_processor_adapter import FrameProcessorAdapter
from odin_data.frame_receiver_adapter import FrameReceiverAdapter

from odin._version import get_versions

from QemCalibrator import QemCalibrator
from QemFem import QemFem


class QemDetectorAdapter(ApiAdapter):
    """Top Level Adapter for the QEM Control system.

    Provides access to all the sub sections that compose a working Qem Dectector System.
    It has access to the other adapters loaded, and thus can sequence required commands.
    """

    def __init__(self, **kwargs):
        """Initialize the QemDetectorAdapter object.

        This constructor initializes the QemDetector object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(QemDetectorAdapter, self).__init__(**kwargs)
        self.qem_detector = QemDetector()
        self.adapters = {}
        logging.debug('QemDetector Adapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.qem_detector.get(path)
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
            data = convert_unicode_to_string(decode_request_body(request))
            self.qem_detector.set(path, data)
            response = self.qem_detector.get(path)
            status_code = 200
        except QemDetectorError as e:
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
        response = 'QemDetectorAdapter: DELETE on path {}'.format(path)
        status_code = 200

        logging.debug(response)

        return ApiAdapterResponse(response, status_code=status_code)

    def initialize(self, adapters):
        self.qem_detector.initialize(adapters)


class QemDetectorError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass


class QemDetector():
    """ QemDetector object representing the entire QEM Detector System.

    Intelligent control plane that can sequence events across the subsystems lower down in the
    hierarchy to perform DAQ, calibration runs and other generic control functions on the entire
    detector system (FEM-II's, Backplane, Data Path Packages etc.)
    """
# server_ctrl_ip = 10.0.1.2
# camera_ctrl_ip = 10.0.1.102

# server_data_ip = 10.0.2.2
# camera_data_ip = 10.0.2.102
    def __init__(self):
        self.daq = QemDAQ()
        # only one FEM for QEM, QEMII will have multiple (up to 4)
        fems = [QemFem(
            ip_address="192.168.0.122",
            port="8070",
            id=0,
            server_ctrl_ip_addr="10.0.1.2",
            camera_ctrl_ip_addr="10.0.1.102",
            server_data_ip_addr="10.0.2.2",
            camera_data_ip_addr="10.0.2.102")]

        fem_tree = {}
        for fem in fems:
            fem.connect()
            fem.setup_camera()

            fem_tree["fem_{}".format(fem.id)] = fem.param_tree

        self.file_dir = "/scratch/qem/QEM_AN_CALIBRATION/"  # TODO: these should be configurable
        self.file_name = "adam_test_4"
        self.file_writing = False
        self.calibrator = QemCalibrator(0, self.file_name, self.file_dir, fems)
        self.param_tree = ParameterTree({
            "file_info": {
                "file_path": (lambda: self.file_dir, self.set_data_dir),
                "file_name": (lambda: self.file_name, self.set_file_name),
                "file_write": (lambda: self.file_writing, self.set_file_writing)
            },
            "calibrator": self.calibrator.param_tree,
            "fems": fem_tree
        })

        self.adapters = {}

    def get(self, path):
        return self.param_tree.get(path)

    def set(self, path, data):
        logging.debug("SET:\n PATH: %s\n DATA: %s", path, data)
        return self.param_tree.set(path, data)

    def set_data_dir(self, directory):
        self.file_dir = directory
        self.calibrator.data_dir = self.file_dir

    def set_file_name(self, name):
        self.file_name = name
        self.calibrator.data_file = self.file_name

    def set_file_writing(self, writing):
        self.file_writing = writing
        # send command to Odin Data
        command = "config/hdf/file/path"
        request = ApiAdapterRequest(self.file_dir, content_type="application/json")
        self.adapters["fp"].put(command, request)

        command = "config/hdf/file/name"
        request.body = self.file_name
        self.adapters["fp"].put(command, request)

        command = "config/hdf/write"
        request.body = "{}".format(writing)
        self.adapters["fp"].put(command, request)

    def initialize(self, adapters):
        """Get references to required adapters and pass those references to the classes that need
            to use them
        """
        for name, adapter in adapters.items():
            if isinstance(adapter, ProxyAdapter):
                logging.debug("%s is Proxy Adapter", name)
                self.adapters["proxy"] = adapter
            elif isinstance(adapter, FrameProcessorAdapter):
                logging.debug("%s is FP Adapter", name)
                self.adapters["fp"] = adapter
            elif isinstance(adapter, FrameReceiverAdapter):
                logging.debug("%s is FR Adapter", name)
                self.adapters["fr"] = adapter
            elif isinstance(adapter, LiveViewAdapter):
                logging.debug("%s is Live View Adapter", name)
                self.adapters["liveview"] = adapter

        self.calibrator.initialize(self.adapters)


class QemDAQ():
    """Encapsulates all the functionaility to initiate the DAQ.

    Configures the Frame Receiver and Frame Processor plugins
    Configures the HDF File Writer Plugin
    Configures the Live View Plugin
    """

    def __init__(self):
        pass
