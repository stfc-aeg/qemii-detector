""" Backplane Adapter

Adapter which exposes the underlying backplane module and access to
it's onboard hardware drivers.

Sophie Kirkham, Application Engineering Group, STFC. 2019
Adam Davis, AEG, STFC 2019
"""
import logging
import tornado
import time
import math
from concurrent import futures
import os 

from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from tornado.escape import json_decode

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types, wants_metadata
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin._version import get_versions

from Backplane import Backplane


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

        # Retrieve adapter options from incoming argument list
        self.update_interval = float(1.0)

        # Start the update loop
        self.update_loop()

        print(self.backplane.param_tree)

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.backplane.get(path, wants_metadata(request))
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
        data=0
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

        logging.debug(data)
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
    
    def update_loop(self):
        """Handle background update loop tasks.
        This method polls the sensors in the background and is executed periodically in the tornado
        IOLoop instance.
        """
        # Handle background tasks
        self.backplane.poll_all_sensors()

        # Schedule the update loop to run in the IOLoop instance again after appropriate
        # interval
        IOLoop.instance().call_later(self.update_interval, self.update_loop)


class BackplaneError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass


