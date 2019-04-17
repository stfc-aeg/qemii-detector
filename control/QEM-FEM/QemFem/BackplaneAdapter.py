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
            self.resistor_1 = 5
            self.resistor_2 = 30
            self.voltages = [0.0] * 13
            self.voltages_raw = [0.0] * 13
            self.voltChannelLookup = ((0,2,3,4,5,6,7),(0,2,4,5,6,7))

            self.fixed_vnames = ["VDD_A33", "VDD_D33", "VDD_D25", "VDD0", "VDD_D18", "VDD_P18", "VDD_A18_PLL", "VDD_D18_PLL", "VDD_D18ADC"]
            self.variable_vnames = ["VDD_RST", "VCTRL_NEG", "VRESET", "VCTRL_POS", "AUX_COARSE", "AUX_FINE"]
            #self.names = ["VDD0", "VDD_D18", "VDD_D25", "VDD_P18", "VDD_A18_PLL", "VDD_D18ADC", "VDD_D18_PLL", "VDD_RST", "VDD_A33", "VDD_D33", "VCTRL_NEG", "VRESET", "VCTRL_POS"]
            
            self.currents = [0.0] * 15
            self.currents_raw = [0.0] * 15
            self.cunits = ["mA", "mA", "mA", "mA", "mA", "mA", "mA", "mA", "mA", "mA", "mA", "mA", "mA"]
            self.vunits = ["V", "V", "V", "V", "V", "V", "V", "V", "V", "V", "V", "V", "V"]
            self.cnames = ["VDD_A33", "VDD_D33", "VDD_D25", "VDD0", "VDD_D18", "VDD_P18", "VDD_A18_PLL", "VDD_D18_PLL", "VDD_D18ADC"]

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

            #this creates a list of the GPIO devices
            self.mcp23008 = []
            self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x20, busnum=1))
            self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x21, busnum=1))
            for i in range(8):
                self.mcp23008[0].setup(i, MCP23008.IN)
            self.mcp23008[1].output(0, MCP23008.HIGH)
            self.mcp23008[1].setup(0, MCP23008.OUT)

            #build the resistor parameter tree
            resistor_tree = ParameterTree({
                "name": "Resistors",
                "description": "Resistors on the Backplane.",
                "resistor_1": (self.get_resistor_1, self.set_resistor_1, {
                    "name": "resistor 1",
                    "description": "Fake resistor Value for testing"
                }),
                "resistor_2": (self.resistor_2, {
                    "name": "resistor 2",
                    "description": "Fale Resistor Value for Testing"
                })
            })

            #define templates for the various dictionaries used below to build the parameter tree
            fixed_voltage_dict = {
                "name": "Fixed voltages",
                "description": "Fixed voltages on the backplane."
            }
            variable_voltage_dict = {
                "name": "Variable voltages",
                "description": "Variable voltages on the backplane."
            }
            current_dict = {
                "name": "Currents",
                "description": "Currents on the backplane."
            }

            #build the fixed voltage parameter tree in the system
            for index, name in enumerate(self.fixed_vnames):
                f_voltage = {
                    "voltage": (lambda index=index: self.voltages[index], None, {"name": "Voltage","description": "Actual Voltage from the backplane","units": self.vunits[index]}),
                    "register": (lambda index=index: self.voltages_raw[index], None, {"name": "Register", "description": "Raw register value from the backplane"})
                }
                fixed_voltage_dict[name] = f_voltage
            fixed_voltage_tree = ParameterTree(fixed_voltage_dict)
            
            #build the variable voltage parameter tree in the system
            for index, name in enumerate(self.variable_vnames):
                v_voltage = {
                    "voltage": (lambda index=index: self.voltages[index], None, {"name": "Voltage","description": "Actual Voltage from the backplane","units": self.vunits[index]}),
                    "register": (lambda index=index: self.voltages_raw[index], None, {"name": "Register", "description": "Raw register value from the backplane"})
                }
                variable_voltage_dict[name] = v_voltage
            variable_voltage_tree = ParameterTree(variable_voltage_dict)

            #build the current parameter tree in the system
            for index, name in enumerate(self.cnames):
                current = {
                    "current": (lambda index=index: self.currents[index], None, {"name": "Current","description": "Actual Current from the backplane","units": self.cunits[index]}),
                    "register": (lambda index=index: self.currents_raw[index], None, {"name": "Register","description": "Raw register value from the backplane"})
                }
                current_dict[name] = current
            current_tree = ParameterTree(current_dict)

            
            
            


            
            

            #populate the parameter tree from the above builds
            self.param_tree = ParameterTree({
                "resistors": resistor_tree,
                "currents": current_tree,
                "voltages":{"fixed":fixed_voltage_tree, "variable":variable_voltage_tree},
                "clock(MHz)":(self.get_clock_frequency, self.set_clock_frequency,{"description": "Controls the main clock Reference", "units": "MHz"}), 
                "dacextref":(self.get_dacextref, self.set_dacextref, {"description": "Controls the DAC External Reference"}),
                "status":(self.get_status, None, {"description": "Power supply status"})
            })




        
        except Exception, exc:
            if exc == 13:
                logging.error("I2C Communications not enabled for user. Try 'su -;chmod 666 /dev/i2c-1'")
            else:
                logging.error(exc)
                # sys.exit(0)    
    
    #clock functions
    def get_clock_frequency(self):
        #this will do something amazing one day
        return self.si570.get_frequency()
    
    def set_clock_frequency(self, value):
        #this will do something amazing one day
        logging.debug("got here, value is %d" %value)
        #print(self.si570)
        self.si570.set_frequency(value)
        #print(self.si570)
    
    #get the power supply status
    def get_status(self):
        return 77

    #functions to control the external chip current DACEXTREF
    def get_dacextref(self):
        return 55
    def set_dacextref(self, value):
        temp=value
    
    #definitions to get / set auxsample
    def get_coarse(self):
        return 22        
    def set_coarse(self, value):
        temp=value        
    def get_fine(self):
        return 222        
    def set_fine(self, value):
        temp=value        
    
    

    def get(self, path, wants_metadata=False):
        return self.param_tree.get(path, wants_metadata)

    def set(self, path, data):
        return self.param_tree.set(path, data)

    def get_resistor_1(self):
        return self.resistor_1

    def set_resistor_1(self, value):
        self.resistor_1 = value
    
    

    def poll_all_sensors(self):
        """This will do something amazing one day"""
        
        self.resistor_1 = int(self.resistor_1 + 1)

        if self.update == True:
            self.update_voltages()
            self.update_currents()
            # print("update, now %d" %self.resistor_1)
# "VDD_D25", "VDD_P18", "VDD_A18_PLL", "VDD_D18ADC", "VDD_D18_PLL", "VDD_RST", "VDD_A33", "VDD_D33", "VCTRL_NEG", "VRESET", "VCTRL_POS"]
    
    def get_voltages(self):
        return dict(zip(self.names, self.voltages))

    def get_vraw(self):
        return dict(zip(self.names, self.voltages_raw))
    
    def get_vunits(self):
        return dict(zip(self.names, self.vunits))

    def get_currents(self):
        return dict(zip(self.names, self.currents))

    def get_craw(self):
        return dict(zip(self.names, self.currents_raw))
    
    def get_cunits(self):
        return dict(zip(self.names, self.cunits))

    def update_voltages(self):
        # Voltages
        for i in range(7):
            j = self.voltChannelLookup[0][i]
            self.voltages_raw[i] = self.ad7998[1].read_input_raw(j) & 0xfff
            self.voltages[i] = self.voltages_raw[i] * 3 / 4095.0
        for i in range(6):
            j = self.voltChannelLookup[1][i]
            self.voltages_raw[i + 7] = self.ad7998[3].read_input_raw(j) & 0xfff
            self.voltages[i + 7] = self.voltages_raw[i + 7] * 5 / 4095.0
    
    def update_currents(self):
        # Currents
        for i in range(7):
            j = self.voltChannelLookup[0][i]
            self.currents_raw[i] = (self.ad7998[0].read_input_raw(j) & 0xfff)
            self.currents[i] = self.currents_raw[i] / self.MONITOR_RESISTANCE[i] * (5000 / 4095.0)

        for i in range(6):
            j = self.voltChannelLookup[1][i]
            self.currents_raw[i + 7] = (self.ad7998[2].read_input_raw(j) & 0xfff)
            self.currents[i + 7] = self.currents_raw[i + 7] / self.MONITOR_RESISTANCE[i + 7] * 5000 / 4095.0
        




