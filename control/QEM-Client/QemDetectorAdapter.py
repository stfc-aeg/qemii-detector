""" Qem Detector Adapter for QEM Detector System.

Main control layer for the entire qem detector system.
Intelligent adapter that can communicate to all other loaded adapters lower down in the heirarchy.
Bridges the gap between generic UI commands and detector specific business logic.

Sophie Kirkham, Application Engineering Group, STFC. 2019
"""
import logging
import tornado
import time
from concurrent import futures
import os

from tornado.ioloop import IOLoop
from tornado.escape import json_decode

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin._version import get_versions

from QemCalibrator import QemCalibrator


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
            data = json_decode(request.body)
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
        # get references to required adapters
        # pass those references to the classes that need to use em
        pass


class QemDetectorError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass


class QemDetector():
    """ QemDetector object representing the entire QEM Detector System.

    Intelligent control plane that can sequence events across the subsystems lower down in the
    hierarchy to perform DAQ, calibration runs and other generic control functions on the entire
    detector system (FEM-II's, Backplane, Data Path Packages etc.)
    """

    def __init__(self):
        self.daq = QemDAQ()
        self.vector_file = None
        self.calibrator = QemCalibrator(0, "")

    def get(self, path):
        pass

    def set(self, path, data):
        pass


class QemDAQ():
    """Encapsulates all the functionaility to initiate the DAQ.

    Configures the Frame Receiver and Frame Processor plugins
    Configures the HDF File Writer Plugin
    Configures the Live View Plugin
    """

    def __init__(self):
        pass
