""" Backplane Adapter

Adapter which exposes the underlying backplane module and access to
it's onboard hardware drivers.

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


class BackplaneAdapter(ApiAdapter):
    """
    """

    def __init__(self, **kwargs):
        """Initialize the BackplaneAdapter object.

        This constructor initializes the BackplaneAdapter object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(BackplaneAdapter, self).__init__(**kwargs)
        self.backplane = Backplane()
        logging.debug('Backplane Adapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.backplane.get(path)
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
            self.backplane.set(path, data)
            response = self.backplane.get(path)
            status_code = 200
        except BackplaneError as e:
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
        response = 'BackplaneAdapter: DELETE on path {}'.format(path)
        status_code = 200

        logging.debug(response)

        return ApiAdapterResponse(response, status_code=status_code)


class BackplaneError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass


class Backplane():
    """ Backplane object, representing a single Backplane module.

    Facilitates communication to the underlying hardware resources 
    onbaord the Backplane.
    """
    pass