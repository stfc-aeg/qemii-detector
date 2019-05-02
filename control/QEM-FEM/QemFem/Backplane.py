import logging

from i2c_device import I2CDevice, I2CException
from i2c_container import I2CContainer

from tca9548 import TCA9548
from ad5272 import AD5272
from mcp23008 import MCP23008
from tpl0102 import TPL0102
from si570 import SI570
from ad7998 import ad7998
from ad5694 import ad5694
import math

from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError


class Backplane():
    """ Backplane object, representing a single Backplane module.

    Facilitates communication to the underlying hardware resources
    onbaord the Backplane.
    """
    
    def __init__(self):
        #signal.signal(signal.SIGALRM, self.connect_handler)
        #signal.alarm(6)
        try:
            self.voltages = [0.0] * 16
            self.voltages_raw = [0] * 15
            """
            above: voltage names are =
            vddo, vdd_d18, vdd_d25, vdd_p18, vdd_a18_pll, vdd_a18adc, vdd_d18_pll, vdd_rst, vdd_a33, vdd_d33, vctrl_neg, vreset, vctrl_pos, aux_coarse, aux_fine,        aux_total
            | 0      1        2        3         4            5           6      | |   7       8         9        10       11       12    | |      13      14   |      |     15     |
            |-------------------------- U46, 0x34 -------------------------------| |------------------- U40, 0x36 ------------------------| |----- U? 0x0E -----|      | CALCULATED |
                                                                                                                                            |QEM-I backplane    |
                                                                                                                                            |this is an extra   |
                                                                                                                                            |module retro-fitted|
                                                                                                                                            |QEM-II backplane   |
                                                                                                                                            |this has been put  |
                                                                                                                                            |in and is U102     |
            """
            self.currents = [0.0] * 14
            self.currents_raw = [0.0] * 14
            """
            above: current names are =
            vddo, vdd_d18, vdd_d25, vdd_p18, vdd_a18_pll, vdd_a18adc, vdd_d18_pll, vdd_rst, vdd_a33, vdd_d33, vctrl_neg, vreset, vctrl_pos, dacextref
            | 0      1        2        3         4            5           6      | |   7       8         9        10       11       12          13   |
            |-------------------------- U45, 0x33 -------------------------------| |------------------- U39, 0x35 -----------------------------------|
            """


            self.adjust_resistor_raw = [0] * 8
            self.adjust_voltage = [0.0] * 8


            """BELOW: I2C devices instances"""
            self.tca = TCA9548(0x70, busnum=1) #this is the multiplexer, the first device on the bus on the backplane
            self.ad5694 = self.tca.attach_device(5, ad5694, 0x0E, busnum=1) #Digital to Analogue Converter 0x2E = fine adjustment (AUXSAMPLE_FILE), 0x2F coarse adjustment (AUXSAMPLE_COARSE)
            self.si570 = self.tca.attach_device(1, SI570, 0x5d, 'SI570', busnum=1) #this creates a link to the clock
            self.tpl0102 = [] #this creates a list of tpl0102 devices (potentiometers)
            self.ad7998 = []#this creates a list of ad7998 devices (Analog to Digital Converters)
            self.mcp23008 = [] #this creates a list of the GPIO devices
            self.i2c_init() # initialise i2c devices to the list variables above & initialise defaults

            """"BELOW: local variables for control & initialise defaults"""
            self.update = True #This is used to enable or dissable to I2C access to the hardware
            self.MONITOR_RESISTANCE = [2.5, 1, 1, 1, 10, 1, 10, 1, 1, 1, 10, 1, 10] #this list defines the resistance of the current-monitoring resistor in the circuit multiplied by 100 (for the amplifier)
            self.power_good = [False] * 8 #Power goor array to indicate the status of the power suppy power-good indicators
            self.voltChannelLookup = ((0,2,3,4,5,6,7),(0,2,4,5,6,7)) #this is used to lookup the chip and channel for the voltage and current measurements
            self.si570.set_frequency(17.5)
            self.clock_frequency = 17.5 # local variable used to read pre-set clock frequency rather than reading i2c each time

        #exception error handling needs further improvement
        except ValueError:
            print('Non-numeric input detected.')

        except ImportError:
            print('Unable to locate the module.')

        try:    

            #populate the parameter tree
            self.param_tree = ParameterTree({
               
                "VDDO":{        "voltage":(lambda: self.voltages[0], None, {"description": "Sensor main 1.8V supply", "units": "V"}),
                                "current":(lambda: self.currents[0], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D18":{     "voltage":(lambda: self.voltages[1], None, {"description": "Sensor Digital 1.8V supply", "units": "V"}),
                                "current":(lambda: self.currents[1], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D25":{     "voltage":(lambda: self.voltages[2], None, {"description": "Sensor Digital 2.5V supply", "units": "V"}),
                                "current":(lambda: self.currents[2], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_P18":{     "voltage":(lambda: self.voltages[3], None, {"description": "Sensor Programmable Gain Amplifier 1.8V supply", "units": "V"}),
                                "current":(lambda: self.currents[3], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_A18_PLL":{ "voltage":(lambda: self.voltages[4], None, {"description": "Sensor Analogue & Phase Lock Loop 1.8V supply", "units": "V"}),
                                "current":(lambda: self.currents[4], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D18ADC":{  "voltage":(lambda: self.voltages[5], None, {"description": "Sensor Digital Analogue to Digital Converter 1.8V supply", "units": "V"}),
                                "current":(lambda: self.currents[5], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D18_PLL":{ "voltage":(lambda: self.voltages[6], None, {"description": "Sensor Digital Phase Lock Loop 1.8V supply", "units": "V"}),
                                "current":(lambda: self.currents[6], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_A33":{     "voltage":(lambda: self.voltages[8], None, {"description": "Sensor Analogue 3.3V supply", "units": "V"}),
                                "current":(lambda: self.currents[8], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VDD_D33":{     "voltage":(lambda: self.voltages[9], None, {"description": "Sensor Digital 3.3V supply", "units": "V"}),
                                "current":(lambda: self.currents[9], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "AUXSAMPLE_COARSE":{    "voltage":(lambda: self.voltages[13], self.set_coarse_voltage, {"description": "Sensor AUXSAMPLE COARSE VALUE input", "units": "mV"}),
                                        "register":(lambda: self.voltages_raw[13], self.set_coarse_register,  {"description": "Register Value"})
                },
                "AUXSAMPLE_FINE":{      "voltage":(lambda: self.voltages[14], self.set_fine_voltage, {"description": "Sensor AUXSAMPLE FINE VALUE input", "units": "uV"}),
                                        "register":(lambda: self.voltages_raw[14], self.set_fine_register,  {"description": "Register Value"})
                },
                "AUXSAMPLE":{   "voltage":(lambda: self.voltages[15], None,{"description":"Sum of coarse and fine settings"})
                },
                #BELOW:need to add the set methods into the parameter tree
                "VDD_RST":{     "voltage":(lambda: self.voltages[7], self.set_vdd_rst_voltage, {"description": "Sensor Reset point variable (1.8V - 3.3V) supply", "units": "V"}),
                                "register":(lambda: self.adjust_resistor_raw[4] , self.set_vdd_rst_register_value,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[7], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VCTRL_NEG":{   "voltage":(lambda: self.voltages[10], None, {"description": "Sensor VCTRL variable (-2V - 0V) supply", "units": "V"}),
                                "register":(lambda: self.voltages_raw[10], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[10], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VRESET":{      "voltage":(lambda: self.voltages[11], self.set_vreset_voltage, {"description": "Sensor VRESET variable (0V - 3.3V) supply", "units": "V"}),
                                "register":(lambda: self.adjust_resistor_raw[5], self.set_vreset_register_value,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[11], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },
                "VCTRL_POS":{   "voltage":(lambda: self.voltages[12], None, {"description": "Sensor VCTRL variable (0V - 3.3V) supply", "units": "V"}),
                                "register":(lambda: self.voltages_raw[12], None,  {"description": "Register Value"}),
                                "current":(lambda: self.currents[12], None,  {"description": "Current being drawn by this supply", "units": "mA"})
                },   
                "VCTRL":{       "voltage":(lambda: self.adjust_voltage[6], self.set_vctrl_voltage, {"description":"calculated voltage of vctrl and vctrl set method"}),
                                "register":(lambda: self.adjust_resistor_raw[6], self.set_vctrl_register_value,  {"description": "Register Value"})
                },
                "AUXREST":{     "voltage":(lambda: self.adjust_voltage[0], self.set_auxreset_voltage, {"description": "Sensor AUXRESET variable (0V - 3.3V) supply", "units": "V"}),  
                                "register":(lambda: self.adjust_resistor_raw[0], self.set_auxrest_register_value,  {"description": "Register Value"})
                },
                "VCM":{         "voltage":(lambda: self.adjust_voltage[1], self.set_vcm_voltage, {"description": "Sensor AUXRESET variable (0V - 3.3V) supply", "units": "V"}),  
                                "register":(lambda: self.adjust_resistor_raw[1], self.set_vcm_register_value,  {"description": "Register Value"})
                },

                #ABOVE: need to add set methods in the parameter tree
                "enable":(lambda: self.update, self.set_update, {"description": "Controls I2C activity on the backplane"}),
                "clock(MHz)":(lambda : self.clock_frequency, self.set_clock_frequency,{"description": "Controls the main clock Reference", "units": "MHz"}), 
                "dacextref":{   "current":(self.get_dacextref, self.set_dacextref_current
        , {"description": "Controls the DAC external current reference", "units": "uA"}),
                                "register":(lambda: self.adjust_resistor_raw[2], self.set_dacextref_register_value, {"description":"register that controls the external reference"})
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

        #excepts need revision to be meaningful
        except ValueError:
            print('Non-numeric input detected.')

        except ImportError:
            print('Unable to locate the module.')

    def i2c_init(self):
        """Initialises the I2C devices and some default values asociated with them"""
        #init below
        for i in range(4):
            self.tpl0102.append(self.tca.attach_device(0, TPL0102, 0x50 + i, busnum=1)) 
            self.ad7998.append(self.tca.attach_device(2, ad7998, 0x21 + i, busnum=1))
            self.tpl0102[i].set_non_volatile(False)  


        #below: AUXSAMPLE: read the current value in the DAC registers
        self.voltages_raw[13] = self.ad5694.read_dac_value(1)
        self.voltages_raw[14] = self.ad5694.read_dac_value(4)
        #below: AUXSAMPLE : calculate the voltages based on the hardware constants set by the feeback resistors in the schematics
        self.voltages[13] = format(self.voltages_raw[13] * 0.0003734, '.3f') #constant required as the multiplier for the hardware (see schematics)
        self.voltages[14] = format(self.voltages_raw[14] * 0.00002, '.3f') #constant required as the multiplier for the hardware (see schematics)
        self.voltages[15] = format(float(float(self.voltages[13]) + float(self.voltages[14]) + float(0.197)), '.3f') #constant is the voltage o/p from the op-amp when both i/p are zero

        self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x20, busnum=1))
        self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x21, busnum=1))
        for i in range(8):
            self.mcp23008[0].setup(i, MCP23008.IN)
        self.mcp23008[1].output(0, MCP23008.HIGH)
        self.mcp23008[1].setup(0, MCP23008.OUT)

        #voltage 
        self.adjust_resistor_raw = [
            self.tpl0102[0].get_wiper(0,force=True),
            self.tpl0102[0].get_wiper(1,force=True),
            self.tpl0102[1].get_wiper(0,force=True),
            self.tpl0102[1].get_wiper(1,force=True),
            self.tpl0102[2].get_wiper(0,force=True),
            self.tpl0102[2].get_wiper(1,force=True),
            self.tpl0102[3].get_wiper(0,force=True),
            self.tpl0102[3].get_wiper(1,force=True)
        ]
        print(self.adjust_resistor_raw)

        #self.adjust_voltage[0] = 3.3 * (390 * self.adjust_resistor_raw[0]) / (390 * self.adjust_resistor_raw[0] + 32000)
        #self.adjust_voltage[1] = 3.3 * (390 * self.adjust_resistor_raw[1]) / (390 * self.adjust_resistor_raw[1] + 32000)
        #self.adjust_voltage[6]=-3.775 + (1.225/22600 + .35*.000001) * (390 * self.adjust_resistor_raw[6] + 32400)

        self.load_defaults()
    



    #Functions below are used to modify the register value on the variable supplies
    def set_vdd_rst_register_value(self, value):
        self.tpl0102[2].set_wiper(0, value)
        self.adjust_resistor_raw[4] = self.tpl0102[2].get_wiper(0)
    def set_vdd_rst_voltage(self, value):
        self.tpl0102[2].set_wiper(0, int(1+(18200/0.0001)*(value-1.78)/(390*18200-390*(value-1.78)/0.0001)))
        self.adjust_resistor_raw[4] = self.tpl0102[2].get_wiper(0)

    def set_vreset_register_value(self, value):
        self.tpl0102[2].set_wiper(1, value)
        self.adjust_resistor_raw[5] = self.tpl0102[2].get_wiper(1)
    def set_vreset_voltage(self, value):
        self.tpl0102[2].set_wiper(1, int(1+(49900/0.0001)*value/(390*49900-390*value/0.0001)))
        self.adjust_resistor_raw[5] = self.tpl0102[2].get_wiper(1)
    
    def calc_vctrl_voltage(self, value):
        return format(-3.775 + (1.225/22600 + .35*.000001) * (390 * self.adjust_resistor_raw[6] + 32400), '.3f')
    def set_vctrl_register_value(self, value):
        self.tpl0102[3].set_wiper(0, value)
        self.adjust_resistor_raw[6] = self.tpl0102[3].get_wiper(0)
        self.adjust_voltage[6]= self.calc_vctrl_voltage(6)
    def set_vctrl_voltage(self, value):
        self.tpl0102[3].set_wiper(0, int(1+((value+3.775)/(1.225/22600+.35*.000001)-32400)/390))
        self.adjust_resistor_raw[6] = self.tpl0102[3].get_wiper(0)
        self.adjust_voltage[6]=self.calc_vctrl_voltage(6)


    def calc_aux_vcm_voltage(self, value):
        return format(3.3 * (390 * self.adjust_resistor_raw[value]) / (390 * self.adjust_resistor_raw[value] + 32000), '.3f')
    def calc_aux_vcm_register(self, value):
        return int(0.5+(32000/3.3)*value/(390-390*value/3.3))
    def set_register_value(self, TPL, wiper, vector, value):
        self.tpl0102[TPL].set_wiper(wiper, value)
        self.adjust_resistor_raw[vector] = self.tpl0102[0].get_wiper(wiper)
        self.adjust_voltage[vector] = self.calc_aux_vcm_voltage(resistor_num)

    def set_auxrest_register_value(self, value):
        resistor_num=0
        self.set_register_value(0, 0, 0, value)
        # self.tpl0102[0].set_wiper(0, value)
        # self.adjust_resistor_raw[0] = self.tpl0102[0].get_wiper(0)
        # self.adjust_voltage[0] = self.calc_aux_vcm_voltage(resistor_num)
    def set_auxreset_voltage(self, value):
        resistor_num=0
        self.tpl0102[0].set_wiper(0, self.calc_aux_vcm_register(value))
        self.adjust_resistor_raw[0] = self.tpl0102[0].get_wiper(0)
        self.adjust_voltage[0] = self.calc_aux_vcm_voltage(resistor_num)

    
    def set_vcm_register_value(self, value):
        resistor_num=1
        self.tpl0102[0].set_wiper(1, value)
        self.adjust_resistor_raw[1] = self.tpl0102[0].get_wiper(1)
        self.adjust_voltage[1] = self.calc_aux_vcm_voltage(resistor_num)
    def set_vcm_voltage(self, value):
        resistor_num=1
        self.tpl0102[0].set_wiper(1, self.calc_aux_vcm_register(value))
        self.adjust_resistor_raw[resistor_num] = self.tpl0102[0].get_wiper(1)
        self.adjust_voltage[resistor_num] = self.calc_aux_vcm_voltage(resistor_num)

    

    def load_defaults(self):
        """
        AUXRESET=1.9V
        VCM=1.39V
        DACEXTREF=11uA
        VDD_RST=3.3V
        VRESET=1.3V
        VCTRL=0V
        """
        self.set_vdd_rst_voltage(3.28)
        self.set_vcm_voltage(1.39)
        self.set_auxreset_voltage(1.9)
        self.set_vctrl_voltage(0)
        self.set_vreset_voltage(1.3)
        self.set_dacextref_current(11)




    #clock functions
    def get_clock_frequency(self):
        """This returns the clock frequency in MHz"""
        return self.clock_frequency
        
    def set_clock_frequency(self, value):
        """This sets the clock frequency in MHz"""
        self.clock_frequency = value
        
    
    def get(self, path, wants_metadata=False):
        """Main get method for the parameter tree"""
        return self.param_tree.get(path, wants_metadata)
    def set(self, path, data):
        """Main set method for the parameter tree"""
        return self.param_tree.set(path, data)

    
    #method to set the update flag            
    def set_update(self, value):
        """This enables / disables I2C communication on the backplane"""
        self.update = value

    #functions to control the external chip current DACEXTREF - START
    def set_dacextref_register_value(self, value):
        self.tpl0102[1].set_wiper(0, value)
        self.adjust_resistor_raw[2] = self.tpl0102[1].get_wiper(0)
    def get_dacextref(self):
        """This returns the DAC External current reference, this is not measured, just calculated
        constants are: 400 (400mV voltage reference), 390 (390 Ohms per step on programmable resistor), 294000 (R108 Resistor 294K)
        see pc3611m1 pg.6
        """
        return (400 * (390 * self.adjust_resistor_raw[2]) / (390 * self.adjust_resistor_raw[2] + 294000))
    def set_dacextref_current(self, value):
        """This sets the DAC external current reference with a specific current value"""
        self.adjust_resistor_raw[2] = int(1+(294000/400)*value/(390-390*value/400))
        self.set_dacextref_register_value(self.adjust_resistor_raw[2])
        #functions to control the external chip current DACEXTREF - END

    
    #definitions to set coarse auxsample (1)
    def set_coarse_register(self, value):
        """This function sets the coarse register value"""
        self.voltages_raw[13] = value
        self.voltages[13] = self.voltages_raw[13] * 0.0003734
        self.voltages[15] = self.voltages[13] + self.voltages[14] + 0.197
        self.ad5694.set_from_value(1, value)
    def set_coarse_voltage(self, value):
        """This function sets the coarse voltage value"""
        self.voltages_raw[13] = int(value / 0.0003734)
        self.voltages[13] = self.voltages_raw[13] * 0.0003734
        self.voltages[15] = self.voltages[13] + self.voltages[14] + 0.197
        self.ad5694.set_from_voltage(1, value)

    #definitions to set fine auxsample (4)
    def set_fine_register(self, value):
        """This sets the fine register value"""
        self.voltages_raw[14] = value
        self.voltages[14] = self.voltages_raw[14] * 0.00002
        self.voltages[15] = self.voltages[13] + self.voltages[14] + 0.197
        self.ad5694.set_from_value(4, value) 
    def set_fine_voltage(self, value):
        """This sets the fine voltage value"""
        self.voltages_raw[14] = int(value / 0.00002)
        self.voltages[14] = self.voltages_raw[14] * 0.00002
        self.voltages[15] = self.voltages[13] + self.voltages[14] + 0.197
        self.ad5694.set_from_voltage(4, value)

    
    
    def poll_all_sensors(self):
        """This function calls all the update functions that are executed every 1 second(s) if update = true"""
        if self.update == True:
            self.update_voltages()
            self.update_currents()
            self.power_good = self.mcp23008[0].input_pins([0,1,2,3,4,5,6,7,8])


    def update_voltages(self):
        """Method to update the voltage vectors"""
        for i in range(7):
            j = self.voltChannelLookup[0][i]
            self.voltages_raw[i] = int(self.ad7998[1].read_input_raw(j) & 0xfff)
            self.voltages[i] = format(self.voltages_raw[i] * 3 / 4095.0, '.3f')
        for i in range(6):
            j = self.voltChannelLookup[1][i]
            self.voltages_raw[i + 7] = int(self.ad7998[3].read_input_raw(j) & 0xfff)
            self.voltages[i + 7] = format(self.voltages_raw[i + 7] * 5 / 4095.0, '.3f')
    
    def update_currents(self):
        """Method to update the current vectors"""
        for i in range(7):
            j = self.voltChannelLookup[0][i]
            self.currents_raw[i] = int(self.ad7998[0].read_input_raw(j) & 0xfff)
            self.currents[i] = format(self.currents_raw[i] / self.MONITOR_RESISTANCE[i] * (5000 / 4095.0), '.3f')

        for i in range(6):
            j = self.voltChannelLookup[1][i]
            self.currents_raw[i + 7] = int(self.ad7998[2].read_input_raw(j) & 0xfff)
            self.currents[i + 7] = format(self.currents_raw[i + 7] / self.MONITOR_RESISTANCE[i + 7] * 5000 / 4095.0, '.3f')
        

