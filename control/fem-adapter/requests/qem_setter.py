import requests, logging

class QemSetter:

    def __init__(self, url='http://localhost', port=8888):
        self.headers = {'Content-Type': 'application/json'}
        self.url = '{}:{}/api/0.1/qem/'.format(url, str(port))

    def setClock(self, frequency):
    #sets the clock frequency to 'frequency' (MHz)
        requests.put(self.url + 'clock', str(frequency) ,headers=self.headers)

    def findResistor(self, resistor):
    #returns the base Url for the named 'resistor'
        resistorLookup = {'AUXRESET':'0', 'VCM':'1', 'DACEXTREF':'2', 'VDD_RST':'3', 'VRESET':'4', 'VCTRL':'5', 'AUXSAMPLE_FINE':'6', 'AUXSAMPLE_COARSE':'7'}
        resistorLocation = resistorLookup[resistor.strip().upper().replace(' ', '_')]
        resistorUrl = self.url + 'resistors/{}/'.format(resistorLocation)
        return resistorUrl

    def setResistorValue(self, resistor, value):
    #sets the resistor given name or location 'resistor' to 'value' in V (uA for DACEXTREF)
        try:
            resistorUrl = self.findResistor(resistor) + 'resistance'
            requests.put(resistorUrl, str(value), headers=self.headers)
        except KeyError:
            logging.error('{} is not a valid resistor name'.format(resistor))

    def setResistorRegister(self, resistor, value):
    #sets the resistor given name or location 'resistor' to 'value'
        try:
            resistorUrl = self.findResistor(resistor) + 'register'
            requests.put(resistorUrl, str(value), headers=self.headers)
        except KeyError:
           logging.error('{} is not a valid resistor name'.format(resistor))

    def enablePSU(self):
    #sets the psu to enabled
        requests.put(self.url + 'psu_enabled', 'true', headers=self.headers)

    def changeDefaults(self, default):
        if default:
            requests.put(self.url + 'non_volatile', 'true', headers=self.headers)
        else:
            requests.put(self.url + 'non_volatile', 'false', headers=self.headers)


if __name__ == '__main__':
    setter = QemSetter()
    setter.setClock(25)
    setter.enablePSU()
    setter.setResistorRegister('auxsample_coarse', 50)
    setter.setResistorValue(' VDD RST ', 1)
    setter.setResistorRegister('VCM', 300)
    setter.setResistorValue('test', 2)
