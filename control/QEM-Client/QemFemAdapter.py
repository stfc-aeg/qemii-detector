""" Qem FEM Adapter for QEM FEM's

Adapter to communicate with a single FEM module, controlling them via UDP.
Sets up each FEM for a DAQ.  

Sophie Kirkham, Application Engineering Group, STFC. 2019
"""
import logging
import tornado
import time
from concurrent import futures
import os 

from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from tornado.escape import json_decode

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin._version import get_versions


class QemFemAdapter(ApiAdapter):
    """
    """

    def __init__(self, **kwargs):
        """Initialize the QemFemAdapter object.

        This constructor initializes the QEMFEM object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(QemFemAdapter, self).__init__(**kwargs)

        self.qemFem = QemFem()
        logging.debug('QemFem Adapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.qemFem.get(path)
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
            self.qemFem.set(path, data)
            response = self.qemFem.get(path)
            status_code = 200
        except QemFemError as e:
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


class QemFemError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass

class QemFem():
    """Qem Fem class. Represents a single FEM-II module.

    Controls and configures each FEM-II module ready for a DAQ via UDP.
    """
