import requests
import json

class Backplane_Interface():
    """ This class handles communication with the odin_qem backplane server by passing get and set commands to the appropriate requests"""
    def __init__(self, address="192.168.0.123", port="8888"):
        """
        :param address: The IP address of the odin_qem server on the FEM
        :param address: The port number of the odin_qem server
        """
        self.url = "http://" + address + ":" + port + "/api/0.1/qem/"
        # Headers to handle the data format for api put commnads
        self.put_headers = {'Content-Type': 'application/json'}
        #headers to receive the metadata from the odin-qem server
        self.meta_headers = {'Accept': 'application/json;metadata=true'}

    def get_resistor_value(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return : voltage of resistor as a float
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/resistance")
        parsed_response = float(json.loads(response.text)[u'resistance'])
        return parsed_response

    def set_resistor_value(self, resistor, value):
        """
        :param resistor: the index of the wanted resistor
        :param value: the new value for the resistor as a float
        """
        resistor_url = self.url + "resistors/" + str(resistor)+ "/resistance"
        requests.put(resistor_url, str(value), headers=self.put_headers)

    def get_resistor_name(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return : name of resistor i as a string
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/name", headers=self.meta_headers)
        parsed_response = str(json.loads(response.text)[u'name'])
        return parsed_response

    def get_resistor_units(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return: units of resistor i as a string
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/resistance", headers=self.meta_headers)
        parsed_response = str(json.loads(response.text)[u'resistance'][u'units'])
        return parsed_response

    def get_resistor_min(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return: minimum value of resistor i as a float
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/resistance", headers=self.meta_headers)
        parsed_response = float(json.loads(response.text)[u'resistance'][u'min'])
        return parsed_response

    def get_resistor_max(self, resistor):
        """
        :param resistor: the index of the wanted resistor
        :return: maximum value of resistor i as a float
        """
        response = requests.get(self.url + "resistors/" + str(resistor) + "/resistance", headers=self.meta_headers)
        parsed_response = float(json.loads(response.text)[u'resistance'][u'max'])
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
