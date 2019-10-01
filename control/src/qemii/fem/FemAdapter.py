""" Fem Adapter

Adapter which exposes the underlying FEM-II module and access to
it's onboard hardware including GPIO access, the QSPI driver and internal monitoring devices.

Sophie Kirkham, Application Engineering Group, STFC. 2019
"""
import logging
import tornado
import time
import os
import gpio

from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from tornado.escape import json_decode

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin._version import get_versions


class FemAdapter(ApiAdapter):
    """
    This is a comment
    """

    def __init__(self, **kwargs):
        """Initialize the FemAdapter object.

        This constructor initializes the FemAdapter object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(FemAdapter, self).__init__(**kwargs)
        self.fem = Fem()
        logging.debug('Fem Adapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.fem.get(path)
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
            self.fem.set(path, data)
            response = self.fem.get(path)
            status_code = 200
        except FemError as e:
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
        """
        #:return: an ApiAdapterResponse object containing the appropriate response
        

        response = 'FemAdapter: DELETE on path {}'.format(path)
        status_code = 200

        logging.debug(response)

        return ApiAdapterResponse(response, status_code=status_code)

    


class FemError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""
    print("an error happened")

    pass


class Fem():
    """
    FEM object, representing a single FEM-II module.

    Facilitates communication to the underlying hardware resources 
    onbaord the FEM-II.

    GPIO    0x00    
    """
    def __init__(self):
        try:
            #BELOW: list of status register names and the corresponding GPIO port address
            self.status_register={"DONE":1006,"P1V0_MGT_PGOOD":1005,"QDR_TERM_PGOOD":1004,"DDR3_TERM_PGOOD":1003,"P1V8_MGT_PGOOD":1002,"P1V2_PGOOD":1001,"P1V5_PGOOD":1000,"P1V8_PGOOD":999,"P2V0_PGOOD":998,"P1V0_PGOOD":997,"P5V0_PGOOD":996,"P3V3_PGOOD":995, "QSFP_MODULE_PRESENT_U20":994, "QSFP_MODULE_PRESENT_U13":993}
            self.status_names = self.status_register.keys()
            
            #BELOW: list of reset register names and the corresponding GPIO port address
            self.reset_register={"ZYNC_F_RST":1010,"ZYNC_FW_RST_N":1011,"RESETL0":1012,"RESETL1":1013,"V7_INIT_B":1014,"V7_PRG_ZY":1015}
            self.reset_names = self.reset_register.keys()
            """
            from firmware
            ZYNC_F_RST           <= reset_gpio_wo(0);
            ZYNC_FW_RST_N        <= reset_gpio_wo(1); -- active HIGH!!! signal
            RESETL0              <= NOT reset_gpio_wo(2); -- active low signal
            RESETL1              <= NOT reset_gpio_wo(3); -- active low signal
            V7_INIT_B            <= NOT reset_gpio_wo(4); -- active low signal
            V7_PRG_ZY            <= reset_gpio_wo(5);
            """
            
            #BELOW: list of control register names and the corresponding GPIO port address
            self.control_register={"FSEL_1_DE": 986, "FSEL_0_DE": 987, "F_CLK_SEL": 988, "QSFP_I2C_SEL0": 989, "LPMODE0": 990, "LPMODE1": 991, "P1V0_EN_ZYNC": 992}
            self.control_names = self.control_register.keys()
            self.control_register_local = {"FSEL_1_DE": 0, "FSEL_0_DE": 0, "F_CLK_SEL": 0, "QSFP_I2C_SEL0": 0, "LPMODE0": 0, "LPMODE1": 0, "P1V0_EN_ZYNC": 1}

            """
             -- *** Control Register bis assignments for register control ***
            FSEL_1_DE <= control_reg(0);
            FSEL_0_DE <= control_reg(1);  
            F_CLK_SEL <= control_reg(2);
            QSFP_I2C_SEL0 <= control_reg(3);
            LPMODE0 <= control_reg(4);
            MODPRSL0 <= control_reg(5);
            LPMODE1 <= control_reg(6);
            MODPRSL1 <= control_reg(7);
            P1V0_EN_ZYNC <= control_reg(8);
            
            """
            self.selected_flash = 1 # device 1,2,3 or 4
        #exception error handling needs further improvement
        except ValueError:
            print('Non-numeric input detected.')

        print("I got here")
        self.gpio_root = '/sys/class/gpio/'
        self.gpiopath = lambda pin: os.path.join(gpio_root, 'gpio{0}'.format(pin))
        self.RoMODE = 'r'
        self.RWMODE = 'r+'
        self.WMODE = 'w'

        # try: #setup the gpio registers
        #     self.gpio_setup()
        # except BaseException as e:
        #     print("Failed to do something: ", e)
        # finally:
        #     print("Closing all gpio instances")
        #     gpio.cleanup()
        try:
            for key,val in self.control_register.items():
                ppath = str(self.gpio_root + 'gpio' + str(val))
                value = open(str(ppath + '/value'), self.RWMODE)
                direction = open(str(ppath + '/direction'), self.RoMODE)
                gpio._open[val] = gpio.PinState(value=value, direction=direction)
            
            for key,val in self.status_register.items():
                ppath = str(self.gpio_root + 'gpio' + str(val))
                value = open(str(ppath + '/value'), self.RoMODE)
                direction = open(str(ppath + '/direction'), self.RoMODE)
                gpio._open[val] = gpio.PinState(value=value, direction=direction)
            
            for key,val in self.reset_register.items():
                ppath = str(self.gpio_root + 'gpio' + str(val))
                value = open(str(ppath + '/value'), self.RWMODE)
                direction = open(str(ppath + '/direction'), self.RoMODE)
                gpio._open[val] = gpio.PinState(value=value, direction=direction)
            
            print(gpio._open)
            print(gpio._open[990].value)

        except (BaseException) as e:
            response = {'error': 'Something happened: {}'.format(str(e))}

            
        
        print(gpio._open)


        try: #populate the parameter tree
            self.param_tree = ParameterTree({
                "status":{
                    "DONE":(lambda: gpio.read(self.status_register.get("DONE")), None),
                    "P1V0_MGT_PGOOD":(lambda: gpio.read(self.status_register.get("P1V0_MGT_PGOOD")), None),
                    "QDR_TERM_PGOOD":(lambda: gpio.read(self.status_register.get("QDR_TERM_PGOOD")), None),
                    "DDR3_TERM_PGOOD":(lambda: gpio.read(self.status_register.get("DDR3_TERM_PGOOD")), None),
                    "P1V8_MGT_PGOOD":(lambda: gpio.read(self.status_register.get("P1V8_MGT_PGOOD")), None),
                    "P1V2_PGOOD":(lambda: gpio.read(self.status_register.get("P1V2_PGOOD")), None),
                    "P1V5_PGOOD":(lambda: gpio.read(self.status_register.get("P1V5_PGOOD")), None),
                    "P1V8_PGOOD":(lambda: gpio.read(self.status_register.get("P1V8_PGOOD")), None),
                    "P2V0_PGOOD":(lambda: gpio.read(self.status_register.get("P2V0_PGOOD")), None),
                    "P1V0_PGOOD":(lambda: gpio.read(self.status_register.get("P1V0_PGOOD")), None),
                    "P5V0_PGOOD":(lambda: gpio.read(self.status_register.get("P5V0_PGOOD")), None),
                    "P3V3_PGOOD":(lambda: gpio.read(self.status_register.get("P3V3_PGOOD")), None),
                    "QSFP_MODULE_PRESENT_U20_BOTn":(lambda: gpio.read(self.status_register.get("QSFP_MODULE_PRESENT_U20")), None),
                    "QSFP_MODULE_PRESENT_U13_TOPn":(lambda: gpio.read(self.status_register.get("QSFP_MODULE_PRESENT_U13")), None),
                    
                },
                "reset":{
                    "ZYNC_F_RST": (None, self.ZYNC_F_RST_set),
                    "ZYNC_FW_RST_N": (None, self.ZYNC_FW_RST_N_set),
                    "RESETL0": (None, self.RESETL0_set),
                    "RESETL1": (None, self.RESETL1_set),
                    "V7_INIT_B": (None, self.V7_INIT_B_set),
                    "RE-PROGRAM_FPGA": (None, self.V7_PRG_ZY_set)
                },
                "control":{
                    "FIRMWARE_SELECT":(lambda: self.selected_flash, self.set_flash, {"description":"flash 1 = default firmware, flash 2 = test firmware, flash 3 = test firmware, flash 4 = FLASH PROGRAMMING FIRMWARE"}),
                    "FLASH_CLOCK_SELECT":(lambda: self.read_control_reg("F_CLK_SEL"), self.F_CLK_SEL_set, {"description":"FPGA (DEFAULT/NORMAL) = 0, QSPI (PROGRAMMING FIRMWARE) = 1"}),
                    "QSFP_I2C_SELECT":(lambda: self.read_control_reg("QSFP_I2C_SEL0"),self.QSFP_I2C_SEL0_set, {"description":"changes which I2C interface is ACTIVE, 0 = U20 BOTT, 1 = U13 TOP"}),
                    "QSFP_LOW_POWER_MODE_U20_BOT":(lambda: self.read_control_reg("LPMODE0"), self.LPMODE0_set, {"description":"puts the bottom QSFP device into low power mode"}),
                    "QSFP_LOW_POWER_MODE_U13_TOP":(lambda: self.read_control_reg("LPMODE1"), self.LPMODE1_set, {"description":"puts the top QSFP device into low power mode"}),
                    "P1V0_EN_ZYNC":(lambda: self.read_control_reg("P1V0_EN_ZYNC"), self.P1V0_EN_ZYNC_set)
                    
                }         
            })



        except ValueError: #excepts need revision to be meaningful
            print('Non-numeric input detected.')


    def read_control_reg(self, value):
        return self.control_register_local.get(value)
    
    #parameter tree wrapper functions for control registers
    def F_CLK_SEL_set(self, value):
        self.control_register_local["F_CLK_SEL"]=value
        gpio.set(self.control_register.get("F_CLK_SEL"), value)
    def QSFP_I2C_SEL0_set(self, value):
        self.control_register_local["QSFP_I2C_SEL0"]=value
        gpio.set(self.control_register.get("QSFP_I2C_SEL0"), value)
    def LPMODE0_set(self, value):
        self.control_register_local["LPMODE0"]=value
        gpio.set(self.control_register.get("LPMODE0"), value)
    def MODPRSL0_set(self, value):
        self.control_register_local["MODPRSL0"]=value
        gpio.set(self.control_register.get("MODPRSL0"), value)
    def LPMODE1_set(self, value):
        self.control_register_local["LPMODE1"]=value
        gpio.set(self.control_register.get("LPMODE1"), value)
    def MODPRSL1_set(self, value):
        self.control_register_local["MODPRSL1"]=value
        gpio.set(self.control_register.get("MODPRSL1"), value)
    def P1V0_EN_ZYNC_set(self, value):
        self.control_register_local["P1V0_EN_ZYNC"]=value
        gpio.set(self.control_register.get("P1V0_EN_ZYNC"), value)
    def set_flash(self, value):
        
        if value == 1:
            gpio.set(self.control_register.get("FSEL_1_DE"), 0)
            self.control_register_local["FSEL_1_DE"] = 0
            gpio.set(self.control_register.get("FSEL_0_DE"), 0)
            self.control_register_local["FSEL_0_DE"] = 0
            self.selected_flash = value

        if value == 2:
            gpio.set(self.control_register.get("FSEL_1_DE"), 0)
            self.control_register_local["FSEL_1_DE"] = 0
            gpio.set(self.control_register.get("FSEL_0_DE"), 1)
            self.control_register_local["FSEL_0_DE"] = 1
            self.selected_flash = value
            
        if value == 3:
            gpio.set(self.control_register.get("FSEL_1_DE"), 1)
            self.control_register_local["FSEL_1_DE"] = 1
            gpio.set(self.control_register.get("FSEL_0_DE"), 0)
            self.control_register_local["FSEL_0_DE"] = 0
            self.selected_flash = value

        if value == 4:
            gpio.set(self.control_register.get("FSEL_1_DE"), 1)
            self.control_register_local["FSEL_1_DE"] = 1
            gpio.set(self.control_register.get("FSEL_0_DE"), 1)
            self.control_register_local["FSEL_0_DE"] = 1
            self.selected_flash = value
        else:
            print("Not a valid number, no change!")
        
        
    
    
    #parameter tree wrapper functions for gpio.set
    def ZYNC_F_RST_set(self, value):
        gpio.set(self.reset_register.get("ZYNC_F_RST"), value)
    def ZYNC_FW_RST_N_set(self, value):
        gpio.set(self.reset_register.get("ZYNC_FW_RST_N"), value)
    def RESETL0_set(self, value):
        gpio.set(self.reset_register.get("RESETL0"), value)
    def RESETL1_set(self, value):
        gpio.set(self.reset_register.get("RESETL1"), value)
    def V7_INIT_B_set(self, value):
        gpio.set(self.reset_register.get("V7_INIT_B"), value)
    def V7_PRG_ZY_set(self, value):
        gpio.set(self.reset_register.get("V7_PRG_ZY"), value)


    def gpio_setup(self):
        """This sets the GPIO registers up"""
        for key, val in  self.status_register.items():
            gpio.setup(val, "in")
        for key, val in  self.reset_register.items():
            gpio.setup(val, "out")
        for key, val in  self.control_register.items():
            gpio.setup(val, "out")
            gpio.set(val, self.control_register_local[key])

    def get(self, path, wants_metadata=False):
        """Main get method for the parameter tree"""
        return self.param_tree.get(path, wants_metadata)
    def set(self, path, data):
        """Main set method for the parameter tree"""
        return self.param_tree.set(path, data)
