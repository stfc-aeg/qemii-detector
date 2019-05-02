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
from tornado.escape import json_decode

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
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
        self.qem_detector.calibrator.initialize(adapters)


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
        #BACKUP VECTOR FILE REFERENCE: "/aeg_sw/work/projects/qem/python/03052018/QEM_D4_396_ADC_aSpectBias_AUXRSTsampled_ADCbuf_05_iCbias_11_iFbias_20.txt"
        self.vector_file = "/aeg_sw/work/projects/qem/python/03052018/QEM_D4_198_ADC_10_icbias21_ifbias14.txt"
        fems = [QemFem(
            ip_address="192.168.0.122",
            port="8070",
            id=0,
            server_ctrl_ip_addr="10.0.1.2",
            camera_ctrl_ip_addr="10.0.1.102",
            server_data_ip_addr="10.0.2.2",
            camera_data_ip_addr="10.0.2.102")]
        for fem in fems:
            fem.connect()
            fem.load_vectors_from_file(self.vector_file)
        self.calibrator = QemCalibrator(0, "/scratch/qem/QEM_AN_CALIBRATION/", fems)  # TODO: replace hardcoded directory

        self.param_tree = ParameterTree({
            "calibrator": self.calibrator.param_tree
        })

    def get(self, path):
        return self.param_tree.get(path)

    def set(self, path, data):
        return self.param_tree.set(path, data)


class QemDAQ():
    """Encapsulates all the functionaility to initiate the DAQ.

    Configures the Frame Receiver and Frame Processor plugins
    Configures the HDF File Writer Plugin
    Configures the Live View Plugin
    """

    def __init__(self):
        pass
