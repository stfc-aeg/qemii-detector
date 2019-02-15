import sys
import signal
import logging
import math
	
from i2c_device import I2CDevice, I2CException
from i2c_container import I2CContainer

from tca9548 import TCA9548
from ad5272 import AD5272
from mcp23008 import MCP23008
from tpl0102 import TPL0102
from si570 import SI570
from ad7998 import AD7998
from gpio_reset import GPIOReset
from ad5694 import AD5694

try :
    from logger.qem_logger import qemLogger
except:
    logger_imported = False
else:
    logger_imported = True

class Backplane(I2CContainer):

    # not sure what this is yet, will add comments as I understand it
    CURRENT_RESISTANCE = [2.5, 1, 1, 1, 10, 1, 10, 1, 1, 1, 10, 1, 10]
    FINE = 1
    COARSE = 4

    def __init__(self):
        #Set up I2C devices
        signal.signal(signal.SIGALRM, self.connect_handler)
        signal.alarm(6)
        try:
            self.tca = TCA9548(0x70, busnum=1)
            self.tpl0102 = []
            for i in range(4): # was 5 but removed last one (0x54)
                self.tpl0102.append(self.tca.attach_device(0, TPL0102, 0x50 + i, busnum=1))
		#resistors 0x50=AUXRESET, VCM : 0x51 = DACEXTREF : 0x52 = VDD_RST_SUPPLY, RESET_SUPPLY : 0x53 = VCTRL_SUPPLY : 0x54 = AUXSAMPLE
		#07/06/18 - removed AUXSAMPLE 0x54 from the list for new cal board
            for i in range(4): #was 5 but removed last one
                self.tpl0102[i].set_non_volatile(False)

            # this is the new calibration board resistors 07/06/18 : added by AOD, attached to PL27, mux bus 4
            self.ad5272 = []
            for i in range(2):
                self.ad5272.append(self.tca.attach_device(4, AD5272, 0x2E + i, busnum=1))

            # resistors 0x2E = fine adjustment, 0x2F coarse adjustment
            self.ad5694 = self.tca.attach_device(5, AD5694, 0x0E, busnum=1)
            self.ad5694.set_up()

	    """this is quick testing for the new DAC chip, 1 = FINE 4 = COARSE
            self.ad5694.set_from_value(1, 0x19)
            print(self.ad5694.read_dac_value(1))
	    self.ad5694.set_from_voltage(1, 0.24024)
	    print(self.ad5694.read_dac_value(1))
    	    print(self.ad5694.read_dac_voltage(1))
	    self.ad5694.set_from_voltage(4, 0.9987)
	    print(self.ad5694.read_dac_value(4))
	    print(self.ad5694.read_dac_voltage(4))
	    """

            #set the resistance and number of positions for each ad5272
            #the fine (0x2E) is 256 and 20K
            self.ad5272[0].set_num_wiper_pos(1024)
            self.ad5272[0].set_total_resistance(20) #20K Ohms


            #the course is 1024 and 100K
            self.ad5272[1].set_num_wiper_pos(1024)
            self.ad5272[1].set_total_resistance(20) #100K Ohms

	    # attach the clock and set default frequency
            self.si570 = self.tca.attach_device(1, SI570, 0x5d, 'SI570', busnum=1)
            self.si570.set_frequency(20) #Default to 20MHz

	    # attach the ADC devices
            self.ad7998 = []
            for i in range(4):
                self.ad7998.append(self.tca.attach_device(2, AD7998, 0x21 + i, busnum=1))
        

        
	    # add the GPIO devices
            self.mcp23008 = []
            self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x20, busnum=1))
            self.mcp23008.append(self.tca.attach_device(3, MCP23008, 0x21, busnum=1))
            for i in range(8):
                self.mcp23008[0].setup(i, MCP23008.IN)
            self.mcp23008[1].output(0, MCP23008.HIGH)
            self.mcp23008[1].setup(0, MCP23008.OUT)
#            self.mcp23008[1].output(7, MCP23008.LOW)
#            self.mcp23008[1].setup(7, MCP23008.OUT)

            #Resistor readings
            self.resistors_raw = [
                self.tpl0102[0].get_wiper(0),
                self.tpl0102[0].get_wiper(1),
                self.tpl0102[1].get_wiper(0),
                self.tpl0102[2].get_wiper(0),
                self.tpl0102[2].get_wiper(1),
                self.tpl0102[3].get_wiper(0),
                #self.tpl0102[4].get_wiper(0)
                self.ad5694.read_dac_value(4),
		self.ad5694.read_dac_value(1),
	        #self.ad5272[0].get_wiper(),
		#self.ad5272[1].get_wiper()
            ]

	    # not sure where this is used as yet, labelled resisrots, yet calculating voltage
	    # will come back and comment when I know more AD.  The new cal
	    # module uses two resistors for one voltage, will have a think as to what to do when
	    # I know more anout this variables function, for now removed the No.6
            self.resistors = [
                3.3 * (390 * self.resistors_raw[0]) / (390 * self.resistors_raw[0] + 32000),
                3.3 * (390 * self.resistors_raw[1]) / (390 * self.resistors_raw[1] + 32000),
                400.0 * (390 * self.resistors_raw[2]) / (390 * self.resistors_raw[2] + 294000),
                0.0001 * (17800 + (18200 * (390 * self.resistors_raw[3])) / (18200 + (390 * self.resistors_raw[3]))),
                0.0001 * (49900 * (390 * self.resistors_raw[4])) / (49900 + (390 * self.resistors_raw[4])),
                -3.775 + (1.225/22600 + .35*.000001) * (390 * self.resistors_raw[5] + 32400),
                # removed for new cal board 3.3 * (390 * self.resistors_raw[6]) / (390 * self.resistors_raw[6] + 32000),
		20 * self.resistors_raw[6], #this is fine as a microvolts
                0.4 * self.resistors_raw[7], #this is coarse as a millivolts
		#79.10 * self.resistors_raw[6], # this is 79.1 micro-volts / step
		#1.51 * self.resistors_raw[7] # this is 1.42 mili-volts / step

            ]

        except Exception, exc:
            if exc == 13:
                logging.error("I2C Communications not enabled for user. Try 'su -;chmod 666 /dev/i2c-1'")
            else:
                logging.error(exc)
            sys.exit(0)
        finally:
            signal.alarm(0)
            if logger_imported:
                self.logger_state = u"0"
                self.logger = None
            else:
                self.logger_state = u"N/A"

        #Placeholders for sensor readings
        self.voltages = [0.0] * 15
        self.voltages_raw = [0.0] * 15
        self.currents = [0.0] * 15
        self.currents_raw = [0.0] * 15
        self.power_good = [False] * 8
        self.psu_enabled = True
        self.capture_enabled = False
        self.clock_freq = 10.0
        self.resistor_non_volatile = False
        self.temperature = 0

        self.voltChannelLookup = ((0,2,3,4,5,6,7),(0,2,4,5,6,7))
        self.updates_needed = 1
        self.set_sensors_enable(False)

        self.gpio_reset = GPIOReset()

    def connect_handler(self, signum, frame):
        raise Exception("Timeout on I2C connection, Shutting Down")

    def timeout_handler(self, signum, frame):
        raise Exception("Timeout on I2C communication")

    def poll_all_sensors(self):

        if not (self.sensors_enabled or (self.updates_needed > 0)) : return

        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(1)
        try:
            #Currents
            for i in range(7):
                j = self.voltChannelLookup[0][i]
                self.currents_raw[i] = (self.ad7998[0].read_input_raw(j) & 0xfff)
                self.currents[i] = self.currents_raw[i] / self.CURRENT_RESISTANCE[i] * 5000 / 4095.0

            for i in range(6):
                j = self.voltChannelLookup[1][i]
                self.currents_raw[i + 7] = (self.ad7998[2].read_input_raw(j) & 0xfff)
                self.currents[i + 7] = self.currents_raw[i + 7] / self.CURRENT_RESISTANCE[i + 7] * 5000 / 4095.0


            #Voltages
            for i in range(7):
                j = self.voltChannelLookup[0][i]
                self.voltages_raw[i] = self.ad7998[1].read_input_raw(j) & 0xfff
                self.voltages[i] = self.voltages_raw[i] * 3 / 4095.0
            for i in range(6):
                j = self.voltChannelLookup[1][i]
                self.voltages_raw[i + 7] = self.ad7998[3].read_input_raw(j) & 0xfff
                self.voltages[i + 7] = self.voltages_raw[i + 7] * 5 / 4095.0

                
            self.voltages_raw[14] = self.ad7998[1].read_input_raw(1) & 0xfff
            self.voltages[14] = self.voltages_raw[14] * 3 /4095.0

            self.voltages[10] *= -1
            #self.voltages[13]= 0.3428 + (self.resistors[6]*0.000001) + (self.resistors[7]*0.001)
            self.voltages[13] = 0.1987 + (self.resistors[6]*0.000001) +(self.resistors[7]*0.001) #0.1987 is the minimum value of coarse but needs testing 


            #first calculate the voltage from the register
            temp_volt = (self.ad7998[3].read_input_raw(3) & 0xfff) * 5.0 / 4095.0
			#then calculate the natural log of the calculated resistance (5V potential divider with 15K resistor) divided by the resistance at 25 degrees celcius(10K)
            ln_x = math.log(1.5*temp_volt/(5.0-temp_volt))
			#then calulate the temperature using formula from the data sheet of thermistor NTCALUG03A103G and convert from Kelvin
            self.temperature = 1.0/(0.00335402 + ln_x*(0.00025624 + ln_x*(0.00000260597 + ln_x*0.0000000632926)))-273.15

            #Power good monitors
            self.power_good = self.mcp23008[0].input_pins([0,1,2,3,4,5,6,7,8])
        except Exception, exc:
            logging.warning(exc)
        finally:
            signal.alarm(0)
            if self.logger_state == u"2": self.update_log()
            if self.updates_needed > 0: self.updates_needed -= 1

    def set_resistor_value(self, resistor, value):
        if resistor == 0:
            self.resistors_raw[resistor] = int(0.5+(32000/3.3)*value/(390-390*value/3.3))
            self.tpl0102[0].set_wiper(0, self.resistors_raw[resistor])
        elif resistor == 1:
            self.resistors_raw[resistor] = int(0.5+(32000/3.3)*value/(390-390*value/3.3))
            self.tpl0102[0].set_wiper(1, self.resistors_raw[resistor])
        elif resistor == 2:
            self.resistors_raw[resistor] = int(0.5+(294000/400)*value/(390-390*value/400))
            self.tpl0102[1].set_wiper(0, self.resistors_raw[resistor])
        elif resistor == 3:
            self.resistors_raw[resistor] = int(0.5+(18200/0.0001)*(value-1.78)/(390*18200-390*(value-1.78)/0.0001))
            self.tpl0102[2].set_wiper(0, self.resistors_raw[resistor])
        elif resistor == 4:
            self.resistors_raw[resistor] = int(0.5+(49900/0.0001)*value/(390*49900-390*value/0.0001))
            self.tpl0102[2].set_wiper(1, self.resistors_raw[resistor])
        elif resistor == 5:
            self.resistors_raw[resistor] = int(0.5+((value+3.775)/(1.225/22600+.35*.000001)-32400)/390)
            self.tpl0102[3].set_wiper(1, self.resistors_raw[resistor])
        #elif resistor == 6:
        #    self.resistors_raw[resistor] = int(0.5+(32000/3.3)*value/(390-390*value/3.3))
        #    self.tpl0102[4].set_wiper(0, self.resistors_raw[resistor])
        


	elif resistor == 6:
	    self.resistors_raw[resistor] = int(value/20) #store the i2c value
	    self.ad5694.set_from_voltage(4, value*0.000001) #this converts back to volts from uV
            
            #self.resistors_raw[resistor] = int(value/79.10) # this is the fine value 70.058 mico-volts / step 0 - 17997.9 micro-volts (uV) updated to 79.10 11/07/18
            #self.ad5272[0].set_wiper(self.resistors_raw[resistor])
        elif resistor == 7:
	    self.resistors_raw[resistor] = int(value/0.4)#convert to i2c value
	    self.ad5694.set_from_voltage(1, value*0.001)#this is converting back to volts from mV

            #self.resistors_raw[resistor] = int(value/1.51) # this is the coarse value for the 1.42mV / step range 0 - 1454.08 mV updated to 1.51 11/07/18
            #self.ad5272[1].set_wiper(self.resistors_raw[resistor])
            #self.resistors[resistor] = value
        if not self.sensors_enabled: self.updates_needed = 1

    def set_resistor_value_raw(self, resistor, value):
        if resistor == 0:
            self.tpl0102[0].set_wiper(0, value)
            self.resistors[resistor] = 3.3 * (390 * value) / (390 * value + 32000)
        elif resistor == 1:
            self.tpl0102[0].set_wiper(1, value)
            self.resistors[resistor] = 3.3 * (390 * value) / (390 * value + 32000)
        elif resistor == 2:
            self.tpl0102[1].set_wiper(0, value)
            self.resistors[resistor] = 400 * (390 * value) / (390 * value + 294000)
        elif resistor == 3:
            self.tpl0102[2].set_wiper(0, value)
            self.resistors[resistor] = 0.0001 * (17800 + (18200 * (390 * value)) / (18200 + (390 * value)))
        elif resistor == 4:
            self.tpl0102[2].set_wiper(1, value)
            self.resistors[resistor] = 0.0001 * (49900 * (390 * value)) / (49900 + (390 * value))
        elif resistor == 5:
            self.tpl0102[3].set_wiper(0, value)
            self.resistors[resistor] = -3.775 + (1.225/22600 + .35*.000001) * (390 * value + 32400)
#       elif resistor == 6: # was the old AUXSAMPLE, modified for the new module
#            self.tpl0102[4].set_wiper(0, value)
#            self.resistors[resistor] = 3.3 * (390 * value) / (390 * value + 32000)
        elif resistor == 6:
            self.ad5694.set_from_value(4, value)
	    print(value)
            self.resistors[resistor] = (value * 20) #setting the voltage
            
	    #self.ad5272[0].set_wiper(value)
            #self.resistors[resistor] = (value * 79.10) # updated to 79.10 from 70.58 11/07/18
        elif resistor == 7:
            self.ad5694.set_from_value(1, value)
            self.resistors[resistor] = (value * 0.4)

	    #self.ad5272[1].set_wiper(value)
            #self.resistors[resistor] = (value * 1.51) # updated to 1.51 from 1.42 11/07/18
            #self.resistors_raw[resistor] = value
        if not self.sensors_enabled: self.updates_needed = 1

    # this gets the resistor value from the loacal variable list and does not need
    # access the device 
    def get_resistor_value(self, resistor):
        return self.resistors[resistor]

    # this function returns the raw resistor value from the local stored variable list
    # so it does not have to access the device
    def get_resistor_value_raw(self, resistor):
        return self.resistors_raw[resistor]

    # this returns the names for the various voltages / currents that can be changed
    def get_resistor_name(self, resistor):
        return ["AUXRESET", "VCM", "DACEXTREF", "VDD_RST", "VRESET", "VCTRL", "AUXSAMPLE_FINE", "AUXSAMPLE_COARSE"][resistor]

    # returns the units for the values returned
    def get_resistor_units(self, resistor):
        return ["V", "V", "uA", "V", "V", "V", "uV", "mV"][resistor] #changed 6/7 from uV and mV to V

    # returns the minimum voltage that can be set
    def get_resistor_min(self, resistor):
       return [0, 0, 0, 1.78, 0, -2, 0, 0][resistor]

    # returns the maximum voltage that can be set for a given resistor
    def get_resistor_max(self, resistor):
        return [2.497, 2.497, 101.1, 3.318, 3.322, 3.41, 81900, 1638][resistor]#changed from 80919.3uV and 1544.73mV 

    # returns the maximum register value that can be set for a given resistor
    def get_register_max(self, resistor):
        return [255, 255, 255, 255, 255, 255, 4095, 4095][resistor] #changed from 1023, 1023.

    # returns the status of the non-volatile local variable
    def get_resistor_non_volatile(self):
        return self.resistor_non_volatile

    # sets the value of the non-volatile bit in each resistor that supports this function
    def set_resistor_non_volatile(self, value):
        for i in range(4):
            self.tpl0102[i].set_non_volatile(value)
        self.resistor_non_volatile = value

    # allows the current value to be stored to the resistors that support this fuction - only 50 memory spaces!!!
    def enable_value_storage(self, value):
	    self.ad5272[value].enable_50TP("TRUE")

    # store the value function for the adc_cal resistors
    def store_value(self, value):
	    self.ad5272[value].store_50TP("TRUE")

    def get_power_good(self, i):
        return self.power_good[i]

    def get_clock_frequency(self):
        return self.clock_freq

    def set_clock_frequency(self, freq):
        freq = max(10, min(945, freq))
        self.clock_freq = freq + 0.0
        self.si570.set_frequency(freq)

    def get_psu_enable(self):
        return self.psu_enabled

    def set_psu_enable(self, value):
        self.psu_enabled = value
        self.mcp23008[1].output(0, MCP23008.HIGH if value else MCP23008.LOW)
        if not self.sensors_enabled: self.updates_needed = 3

    def get_capture_enable(self):
        return self.capture_enabled

    def set_capture_enable(self, value):
        self.capture_enabled = value
        self.mcp23008[1].output(0, MCP23008.HIGH if value else MCP23008.LOW)

    def get_sensors_enable(self):
        return self.sensors_enabled

    def set_sensors_enable(self, value):
        self.sensors_enabled = value

    def get_update(self):
        return (self.sensors_enabled or self.updates_needed > 0)

    def set_update(self, value):
        if value and not self.sensors_enabled: self.updates_needed = 1

    def set_reset(self, value):
	   
        self.mcp23008[1].setup(0, MCP23008.OUT)
#        self.mcp23008[1].setup(7, MCP23008.OUT)
        for i in range(4): # was 5, now 4 with the addition of adc cal module
            self.tpl0102[i].set_non_volatile(False)
        self.resistor_non_volatile = False
        self.set_clock_frequency(17.5)#used to be 10
        self.resistors_raw = [
            self.tpl0102[0].get_wiper(0,True),
            self.tpl0102[0].get_wiper(1,True),
            self.tpl0102[1].get_wiper(0,True),
            self.tpl0102[2].get_wiper(0,True),
            self.tpl0102[2].get_wiper(1,True),
            self.tpl0102[3].get_wiper(0,True),
            #self.tpl0102[4].get_wiper(0,True)
	    self.ad5694.read_dac_value(4, True),
	    self.ad5694.read_dac_value(1, True),
	    #self.ad5272[0].get_wiper(True),
	    #self.ad5272[1].get_wiper(True)
]

	# not sure where this is used as yet, labelled resistors, yet calculating voltage
	# will come back and comment when I know more AD.  The new cal
	# module uses two resistors for one voltage, will have a think as to what to do when
	# I know more anout this variables function, for now removed the No.6
        self.resistors = [
            3.3 * (390 * self.resistors_raw[0]) / (390 * self.resistors_raw[0] + 32000),
            3.3 * (390 * self.resistors_raw[1]) / (390 * self.resistors_raw[1] + 32000),
            400 * (390 * self.resistors_raw[2]) / (390 * self.resistors_raw[2] + 294000),
            0.0001 * (17800 + (18200 * (390 * self.resistors_raw[3])) / (18200 + (390 * self.resistors_raw[3]))),
            0.0001 * (49900 * (390 * self.resistors_raw[4])) / (49900 + (390 * self.resistors_raw[4])),
            -3.775 + (1.225/22600 + .35*.000001) * (390 * self.resistors_raw[5] + 32400),
            #3.3 * (390 * self.resistors_raw[6]) / (390 * self.resistors_raw[6] + 32000),
	    (20 * self.resistors_raw[6]),
	    (0.4 * self.resistors_raw[7]),
	    #79.1 * self.resistors_raw[6], # this is 70.58 micro-volts / step changed to 79.1 11/07/18
	    #1.51 * self.resistors_raw[7] # this is 1.42 mili-volts / step changed to 1.51 11/07/18

]
        self.set_psu_enable(True)
#        self.set_capture_enable(False)

    def get_temp(self):
        return self.temperature

    def get_current(self, i):
        return self.currents[i]

    def get_current_raw(self, i):
        return self.currents_raw[i]

    def get_voltage(self, i):
        return self.voltages[i]

    def get_voltage_raw(self, i):
        return self.voltages_raw[i]

    def get_adc_name(self, i):
        return ["VDDO", "VDD_D18", "VDD_D25", "VDD_P18",  "VDD_A18_PLL",  "VDD_D18ADC",
               "VDD_D18_PLL", "VDD_RST", "VDD_A33", "VDD_D33", "VCTRL_NEG", "VRESET",
               "VCTRL_POS", "AUXSAMPLE_SUM", "AUXSAMPLE_MEASURED"][i]

    def set_reset_fpga(self, reset):
	print("set reset called") 
        self.gpio_reset.reset("0x20")