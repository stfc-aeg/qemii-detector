""" Backplane Adapter

Adapter which exposes the underlying backplane module and access to
it's onboard hardware drivers.

Sophie Kirkham, Application Engineering Group, STFC. 2019
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

from i2c_device import I2CDevice, I2CException
from i2c_container import I2CContainer

from tca9548 import TCA9548
from ad5272 import AD5272
from mcp23008 import MCP23008
from tpl0102 import TPL0102
from si570 import SI570
from ad7998 import AD7998
#from gpio_reset import GPIOReset
from ad5694 import AD5694


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


class Backplane():
    """ Backplane object, representing a single Backplane module.

    Facilitates communication to the underlying hardware resources
    onbaord the Backplane.
    """
    
    def __init__(self):
        #signal.signal(signal.SIGALRM, self.connect_handler)
        #signal.alarm(6)
        try:
            self.voltages = [0.0] * 13
            self.voltages_raw = [0] * 13
            self.power_good = [False] * 8
            self.voltChannelLookup = ((0,2,3,4,5,6,7),(0,2,4,5,6,7))
            self.currents = [0.0] * 15
            self.currents_raw = [0.0] * 15

            """this list defines the resistance of the current-monitoring resistor in the circuit multiplied by 100 (for the amplifier)"""
            self.MONITOR_RESISTANCE = [2.5, 1, 1, 1, 10, 1, 10, 1, 1, 1, 10, 1, 10]

            self.update = True

            #this is the multiplexer, the first device on the bus on the backplane
            self.tca = TCA9548(0x70, busnum=1)

            #this creates a list of tpl0102 devices (potentiometers)
            self.tpl0102 = []
            for i in range(4):
                self.tpl0102.append(self.tca.attach_device(0, TPL0102, 0x50 + i, busnum=1))
            
            #this creates a list of ad7998 devices (Analog to Digital Converters)
            self.ad7998 = []
            for i in range(4):
                self.ad7998.append(self.tca.attach_device(2, AD7998, 0x21 + i, busnum=1))
            
            #this creates a link to the clock
            self.si570 = self.tca.attach_device(1, SI570, 0x5d, 'SI570', busnum=1)
            self.si570.set_frequency(17.5) #Default to 17.5MHz

            #Digital to Analogue Converter 0x2E = fine adjustment (AUXSAMPLE_FILE), 0x2F coarse adjustment (AUXSAMPLE_COARSE)
            self.ad5694 = self.tca.attach_device(5, AD5694, 0x0E, busnum=1)
            #self.ad5694.setup()

            #this creates a list of the GPIO devices
            self.mcp23008 = []
            self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x20, busnum=1))
            self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x21, busnum=1))
            for i in range(8):
                self.mcp23008[0].setup(i, MCP23008.IN)
            self.mcp23008[1].output(0, MCP23008.HIGH)
            self.mcp23008[1].setup(0, MCP23008.OUT)

            #populate the parameter tree
            self.param_tree = ParameterTree({
               
                "VDDO":{    "voltage":(lambda: self.voltages[0], None, {"description": "Sensor main 1.8V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[0], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[0], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D18":{    "voltage":(lambda: self.voltages[1], None, {"description": "Sensor Digital 1.8V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[1], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[1], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D25":{    "voltage":(lambda: self.voltages[2], None, {"description": "Sensor Digital 2.5V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[2], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[2], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_P18":{    "voltage":(lambda: self.voltages[3], None, {"description": "Sensor Programmable Gain Amplifier 1.8V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[3], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[3], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_A18_PLL":{    "voltage":(lambda: self.voltages[4], None, {"description": "Sensor Analogue & Phase Lock Loop 1.8V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[4], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[4], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D18ADC":{    "voltage":(lambda: self.voltages[5], None, {"description": "Sensor Digital Analogue to Digital Converter 1.8V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[5], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[5], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D18_PLL":{    "voltage":(lambda: self.voltages[6], None, {"description": "Sensor Digital Phase Lock Loop 1.8V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[6], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[6], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_RST":{    "voltage":(lambda: self.voltages[7], None, {"description": "Sensor Reset point variable (1.8V - 3.3V) supply", "units": "V"}),
                                "register":(lambda: self.voltages_raw[7], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[7], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_A33":{    "voltage":(lambda: self.voltages[8], None, {"description": "Sensor Analogue 3.3V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[8], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[8], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D33":{    "voltage":(lambda: self.voltages[9], None, {"description": "Sensor Digital 3.3V supply", "units": "V"}),
                                #"v_reg":(lambda: self.voltages_raw[9], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[9], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VCTRL_NEG":{    "voltage":(lambda: self.voltages[10], None, {"description": "Sensor VCTRL variable (-2V - 0V) supply", "units": "V"}),
                                "register":(lambda: self.voltages_raw[10], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[10], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VRESET":{    "voltage":(lambda: self.voltages[11], None, {"description": "Sensor VRESET variable (0V - 3.3V) supply", "units": "V"}),
                                "register":(lambda: self.voltages_raw[11], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[11], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VCTRL_POS":{    "voltage":(lambda: self.voltages[12], None, {"description": "Sensor VCTRL variable (0V - 3.3V) supply", "units": "V"}),
                                "register":(lambda: self.voltages_raw[12], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[12], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "AUXSAMPLE_COARSE":{    "voltage":(self.get_coarse_voltage, self.set_coarse_voltage, {"description": "Sensor AUXSAMPLE COARSE VALUE input", "units": "mV"}),
                                        "register":(self.get_coarse_register, self.set_coarse_register,  {"description": "Register Value"})
                },
                "AUXSAMPLE_FINE":{      "voltage":(self.get_fine_voltage, self.set_fine_voltage, {"description": "Sensor AUXSAMPLE FINE VALUE input", "units": "uV"}),
                                        "register":(self.get_fine_register, self.set_fine_register,  {"description": "Register Value"})
                },        
                "enable":(lambda: self.update, self.set_update, {"description": "Controls I2C activity on the backplane"}),
                "clock(MHz)":(self.get_clock_frequency, self.set_clock_frequency,{"description": "Controls the main clock Reference", "units": "MHz"}), 
                "dacextref":{   "current":(self.get_dacextref, self.set_dacextref, {"description": "Controls the DAC external current reference", "units": "uA"}),
                                "register":(self.get_dacextrefreg, self.set_dacextrefreg, {"description":"register that controls the external reference"})
                },
                "status":{
                    "level1_PG":(lambda: self.power_good[0], None, {"description": "Level 1 of power supply sequence status"}),
                    "level2_PG":(lambda: self.power_good[1], None, {"description": "Level 2 of power supply sequence status"}),
                    "level3_PG":(lambda: self.power_good[2], None, {"description": "Level 3 of power supply sequence status"}),
                    "level4_PG":(lambda: self.power_good[3], None, {"description": "Level 4 of power supply sequence status"}),
                    "level5_PG":(lambda: self.power_good[4], None, {"description": "Level 5 of power supply sequence status"}),
                    "level6_PG":(lambda: self.power_good[5], None, {"description": "Level 6 of power supply sequence status"}),
                    "level7_PG":(lambda: self.power_good[6], None, {"description": "Level 7 of power supply sequence status"}),
                    "level8_PG":(lambda: self.power_good[7], None, {"description": "Level 8 of power supply sequence status"}),
                }

                    
            })





        
        except Exception, exc:
            if exc == 13:
                logging.error("I2C Communications not enabled for user. Try 'su -;chmod 666 /dev/i2c-1'")
            else:
                logging.error(exc)
                # sys.exit(0)    
    
    #method to set the update flag            
    def set_update(self, value):
            self.update = value

    #clock functions
    def get_clock_frequency(self):
        #this will do something amazing one day
        return self.si570.get_frequency()
    
    def set_clock_frequency(self, value):
        #this will do something amazing one day
        logging.debug("got here, value is %d" %value)
        self.si570.set_frequency(value)

    
    #get the power supply status
    def get_status(self):
        return 77

    #functions to control the external chip current DACEXTREF
    def get_dacextref(self):
        return 55
    def set_dacextref(self, value):
        temp=value
        #functions to control the external chip current DACEXTREF
    def get_dacextrefreg(self):
        return 55
    def set_dacextrefreg(self, value):
        temp=value
    
    #definitions to get / set coarse auxsample (1)
    def get_coarse_register(self):
        return self.ad5694.read_dac_value(1, force=True)
    def set_coarse_register(self, value):
        return self.ad5694.set_from_value(1, value) 
    def get_coarse_voltage(self):
        return self.ad5694.read_dac_voltage(1)
    def set_coarse_voltage(self, value):
        return self.ad5694.set_from_voltage(1, value)

    #definitions to get / set fine auxsample (4)
    def get_fine_register(self):
        return self.ad5694.read_dac_value(4, force=True)
    def set_fine_register(self, value):
        return self.ad5694.set_from_value(4, value) 
    def get_fine_voltage(self):
        return self.ad5694.read_dac_voltage(4)
    def set_fine_voltage(self, value):
        return self.ad5694.set_from_voltage(4, value)

    #main get and set methods
    def get(self, path, wants_metadata=False):
        return self.param_tree.get(path, wants_metadata)
    def set(self, path, data):
        return self.param_tree.set(path, data)
    
    #function that updates the vectors
    def poll_all_sensors(self):
        """This will do something amazing one day"""

        if self.update == True:
            self.update_voltages()
            self.update_currents()
            self.power_good = self.mcp23008[0].input_pins([0,1,2,3,4,5,6,7,8])
            
# "VDD_D25", "VDD_P18", "VDD_A18_PLL", "VDD_D18ADC", "VDD_D18_PLL", "VDD_RST", "VDD_A33", "VDD_D33", "VCTRL_NEG", "VRESET", "VCTRL_POS"]

    def update_voltages(self):
        # Voltages
        for i in range(7):
            j = self.voltChannelLookup[0][i]
            self.voltages_raw[i] = int(self.ad7998[1].read_input_raw(j) & 0xfff)
            self.voltages[i] = self.voltages_raw[i] * 3 / 4095.0
        for i in range(6):
            j = self.voltChannelLookup[1][i]
            self.voltages_raw[i + 7] = int(self.ad7998[3].read_input_raw(j) & 0xfff)
            self.voltages[i + 7] = self.voltages_raw[i + 7] * 5 / 4095.0
    
    def update_currents(self):
        # Currents
        for i in range(7):
            j = self.voltChannelLookup[0][i]
            self.currents_raw[i] = int(self.ad7998[0].read_input_raw(j) & 0xfff)
            self.currents[i] = self.currents_raw[i] / self.MONITOR_RESISTANCE[i] * (5000 / 4095.0)

        for i in range(6):
            j = self.voltChannelLookup[1][i]
            self.currents_raw[i + 7] = int(self.ad7998[2].read_input_raw(j) & 0xfff)
            self.currents[i + 7] = self.currents_raw[i + 7] / self.MONITOR_RESISTANCE[i + 7] * 5000 / 4095.0
        




