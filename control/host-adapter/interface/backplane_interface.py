import requests
import json
from concurrent import futures

class Backplane_Interface():
    """ This class handles communication with the odin_qem backplane server by passing get and set commands to the appropriate requests"""
    def __init__(self, address="192.168.0.122", port="8888", settings_file=""):
        """
        :param address: The IP address of the odin_qem server on the FEM
        :param address: The port number of the odin_qem server
        """
        self.url = "http://" + address + ":" + port + "/api/0.1/qem/"
        # Headers to handle the data format for api put commnads
        self.put_headers = {'Content-Type': 'application/json'}
        #headers to receive the metadata from the odin-qem server
        self.meta_headers = {'Accept': 'application/json;metadata=true'}
        self.defaults_loaded = False
        self.thread_executor = futures.ThreadPoolExecutor(max_workers=1)
        self.non_volatile = False
        self.settings_file = settings_file
        self.resistor_defaults = [0] * 8
        self.lines = [0] * 8

        file = open(self.settings_file, "r")
        for line in file:
            name, value = line.split("=")
            name = str(name.replace(" ", ""))
           
            if name == "AUXRESET":
                self.resistor_defaults[0] = str(value).replace(" ", "").replace("\n", "")
                self.lines[0] = line
            elif name == "VCM":
                self.resistor_defaults[1] = str(value).replace(" ", "").replace("\n", "")
                self.lines[1] = line
            elif name == "DACEXTREF":
                self.resistor_defaults[2] = str(value).replace(" ", "").replace("\n", "")
                self.lines[2] = line
            elif name == "VDD_RST":
                self.resistor_defaults[3] = str(value).replace(" ", "").replace("\n", "")
                self.lines[3] = line
            elif name == "VRESET":
                self.resistor_defaults[4] = str(value).replace(" ", "").replace("\n", "")
                self.lines[4] = line
            elif name == "VCTRL":
                self.resistor_defaults[5] = str(value).replace(" ", "").replace("\n", "")
                self.lines[5] = line
            elif name == "AUXSAMPLE_FINE":
                self.resistor_defaults[6] = str(value).replace(" ", "").replace("\n", "")
                self.lines[6] = line
            elif name == "AUXSAMPLE_COARSE":
                self.resistor_defaults[7] = str(value).replace(" ", "").replace("\n", "")
                self.lines[7] = line
            else:
                print "resistor name not recognised"
                #TODO Exception

    def set_defaults_loaded(self, true):
        self.defaults_loaded = True

    def get_defaults_loaded(self):
        return self.defaults_loaded

    def load_default_resistors(self, load):
        self.set_defaults_loaded(False)
        i = 0 
        for resistor in self.resistor_defaults:
            url = self.url + "resistors/" + str(i)+ "/voltage_current"
            requests.put(url, str(resistor), headers=self.put_headers)
            #print resistor
            i = i+1
        self.set_defaults_loaded(True)

    def set_resistor_register(self, resistor, value):
        #sets the resistor given name or location 'resistor' to 'value'
        try:
            resistorUrl = self.url + 'resistors/' + str(resistor) + '/register_value'
            requests.put(resistorUrl, str(value), headers=self.put_headers)
        except KeyError:
           logging.error('{} is not a valid resistor name'.format(resistor))

    def get_resistor_value(self, resistor):
        """
        :param resistor: the index of the wanted resistors
        :return : voltage of resistor as a float
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/voltage_current")
        parsed_response = float(json.loads(response.text)[u'voltage_current'])

        return parsed_response

    def set_resistor_value(self, resistor, value):
        """
        :param resistor: the index of the wanted resistor
        :param value: the new value for the resistor as a float
        """
        print value
        resistor_url = self.url + "resistors/" + str(resistor)+ "/voltage_current"
        requests.put(resistor_url, str(value), headers=self.put_headers)
       
        if self.non_volatile is True:
           
            self.resistor_defaults[resistor] = value
            name, number = self.lines[resistor].split("=")
            number = str(value)
            self.lines[resistor] = str(name + "=" + number + "\n")
            open(self.settings_file, "w").writelines(self.lines)


    def get_resistor_name(self, resistor):
        """
        :param resistor: the index of the wanted resistors
        :return : name of resistor i as a string
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/name", headers=self.meta_headers)
        parsed_response = str(json.loads(response.text)[u'name'])
        return parsed_response

    def get_resistor_units(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return: units of resistor i as a strings
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/voltage_current", headers=self.meta_headers)
        parsed_response = str(json.loads(response.text)[u'voltage_current'][u'units'])
        return parsed_response

    def get_resistor_min(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return: minimum value of resistor i as a float
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/voltage_current", headers=self.meta_headers)
        parsed_response = float(json.loads(response.text)[u'voltage_current'][u'min'])
        return parsed_response

    def get_resistor_max(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return: maximum value of resistor i as a float
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/voltage_current", headers=self.meta_headers)
        parsed_response = float(json.loads(response.text)[u'voltage_current'][u'max'])
        return parsed_response

    def get_resistor_non_volatile(self):
        """ Gets whether the set command will change the current and default value of a resistor (non-volatile), or just the current value (volatile)
        :param resistor: the index of the wanted resistor
        :return: non volatility of all resistors as a unicode string "True" or "False"
        (unicode needed for set, get and set datatype must match)
        """
        response = requests.get(self.url + "non_volatile")
        parsed_response = str(json.loads(response.text)[u'non_volatile'])
        return unicode(parsed_response)

    def set_resistor_non_volatile(self, value):
        """
        :param resistor: the index of the wanted resistor
        :param value: non volatility of all resistors as a unicode string "true" or "false"
        (unicode due to js requests generating unicode strings)
        """
      
        if value == "true":
            self.non_volatile = True 
        else:
            self.non_volatile = False
            
        requests.put(self.url + "non_volatile", str(value), headers=self.put_headers)

    def get_clock_frequency(self):
        """
        :return: clock frequency as a float
        """
        response = requests.get(self.url + "clock")
        parsed_response = float(json.loads(response.text)[u'clock'])
        return parsed_response

    def set_clock_frequency(self, freq):
        """
        :param freq: clock frequency as a float
        """
        requests.put(self.url + "clock", str(freq), headers=self.put_headers)

    def get_sensors_enable(self):
        """
        :return: whether the backplane server is continuously updating from the backplane via I2C as u'True' or u'False'
        """
        response = requests.get(self.url + "sensors_enabled")
        parsed_response = str(json.loads(response.text)[u'sensors_enabled'])
        return unicode(parsed_response)

    def set_sensors_enable(self, value):
        """
        :param value: whether to enable server updating as u'true' or u'false'
        """
        requests.put(self.url + "sensors_enabled", str(value), headers=self.put_headers)

    def get_update(self):
        """
        :return:whether the backplane server is set to update from the backplane in the next cycle or not as u'True' or u'False'
        """
        response = requests.get(self.url + "update_required")
        parsed_response = str(json.loads(response.text)[u'update_required'])
        return unicode(parsed_response)

    def set_update(self, value):
        """ Sends u'True' to the backplane server to inform the backplane that an update is needed, otherwise does nothing
        :param value: u'True'
        """
        requests.put(self.url + "update_required", str(value), headers=self.put_headers)

    def set_reset(self, value):
        """
        :param value: expects unicode string, u'True' will reset the sever by checking all resistors are seeing the correct value, setting non_volatile to True, enabling the power supplies and setting the clock back to 20MHz
        """
        requests.put(self.url + "reset", str(value), headers=self.put_headers)

    def set_reset_fpga(self, value):

        requests.put(self.url + "fpga_reset", str(value), headers=self.put_headers)

    def get_current(self, supply):
        """
        :param supply: index of the supply
        :return : current of supply i as float
        """
        response = requests.get(self.url + "current_voltage/" + str(supply) + "/current")
        parsed_response = float(json.loads(response.text)[u'current'])
        return parsed_response

    def get_voltage(self, supply):
        """
        :param supply: index of the supply
        :return : voltage of supply i as float
        """
        response = requests.get(self.url + "current_voltage/" + str(supply) + "/voltage")
        parsed_response = float(json.loads(response.text)[u'voltage'])
        return parsed_response

    def get_adc_name(self, supply):
        """
        :param supply: index of the supply
        :return : name of supply i as string
        """
        response = requests.get(self.url + "current_voltage/" + str(supply) + "/name", headers=self.meta_headers)
        parsed_response = str(json.loads(response.text)[u'name'])
        return parsed_response
