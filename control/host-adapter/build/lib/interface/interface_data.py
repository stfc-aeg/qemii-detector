from backplane_interface import Backplane_Interface
from asic_interface import ASIC_Interface
from odin.adapters.metadata_tree import MetadataTree

class CurrentVoltage(object):
    """This class handles the API commands for an individual power supply on the backplane"""
    def __init__(self, backplane_interface, i):
        """Initialises the CurrentVoltage instance
        This creates a parameter tree for the supply which contains the current and voltage, with name and units stored as metadata, linking in the methods to access the data
        :param backplane_interface: the instance of the backplane_interface that handles communication with the odin_qem server
        :param i: The unique number to associate with this supply"""
        self.index = i
        self.backplane_interface = backplane_interface

        self.param_tree = MetadataTree({
            #"identity" : (apiGET handler, {metadata})
            "name" : self.backplane_interface.get_adc_name(i),
            "current" : (self.get_current, {"units" : "mA"}),
            "voltage" : (self.get_voltage, {"units" : "V", "dp":3}),
        })

    def get_current(self):
        """Handles HTTP GET command for the current of supply i
        :return: the current of the supply from the backplane_interface as a float
        """
        return self.backplane_interface.get_current(self.index)

    def get_voltage(self):
        """Handles HTTP GET command for the voltage of supply i
        :return: the voltage of the supply from the backplane_interface as a float
        """

        return self.backplane_interface.get_voltage(self.index)

class Resistor(object):
    """This class handles the API commands for an individual programmable resistor on the backplane"""
    def __init__(self, backplane_interface, i):
        """Initialises the CurrentVoltage instance
        This creates a parameter tree for the resistor which contains the voltage read for the resistance as it stands, with name, units, minimum and maximum resistance stored as metadata, linking in the methods to access the data
        :param backplane_interface: the instance of the backplane_interface that handles communication with the odin_qem server
        :param i: The unique number to associate with this supply
        """
        self.index = i
        self.backplane_interface = backplane_interface

        self.param_tree = MetadataTree({
            #"identity":(HTTP Get handler, HTTP PUT handler, {metadata "name": HTTP GET handler})
            "name" : self.backplane_interface.get_resistor_name(self.index),
            "resistance" : (self.get, self.set, {"units" : self.backplane_interface.get_resistor_units(self.index), "min" : self.backplane_interface.get_resistor_min(self.index), "max" : self.backplane_interface.get_resistor_max(self.index)}),
       })

    def get(self):
        """Handles HTTP GET command for the resistance of resistor i
        :return: the Voltage of the resistor from the backplane_interface as a float
        """
        return self.backplane_interface.get_resistor_value(self.index)

    def set(self, value):
        """"Handles HTTP GET command for the resistance of resistor i
        Passes the new resistor voltage to the interface which handles communicatrion with the backplane server
        :param value: the new Voltage to set the resistor to as a float
        """
        self.backplane_interface.set_resistor_value(self.index, value)


class DAC(object):
    """This class handles the API commands for an individual DAC register resistor on the ASIC"""
    def __init__(self, asic_interface, i):
        """Initialises the DAC instance
        This creates a parameter tree for the resistor which contains the voltage read for the resistance as it stands, with name, units, minimum and maximum resistance stored as metadata, linking in the methods to access the data
        :param asic_interface: the instance of the asic_interface that handles communication with the ASIC
        :param i: The unique number to associate with this supply
        """
        self.index = i
        self.asic_interface = asic_interface

        self.param_tree = MetadataTree({
            "value" : (self.get, self.set),
       })

    def get(self):
        """ :returns: DAC value as a 6 digit string (since may include leading zeros)
        """
        return self.asic_interface.get_dac_value(self.index)

    def set(self, value):
        """ :param value: the new 6 digit value as a string """
        self.asic_interface.set_dac_value(self.index, value)

class InterfaceData(object):
    """This class handles the API commands for the interface by constructing a tree structure for the data and passing the commands down to each leaf"""
    def __init__(self):
        """Initialises the InterfaceData Data structure
        creates instances of the backplane_interface and asic_interface,
        then creates a tree structure containing all data needed by the interace, and passes the API commands to the relevant interface so they can be sent on to the asic or the backplane server
        """
        self.backplane_interface = Backplane_Interface()
        self.asic_interface = ASIC_Interface()

        #Initialise all backplane power supplies
        self.current_voltage = []
        for i in range(13):
            self.current_voltage.append(CurrentVoltage(self.backplane_interface, i))

        self.resistors = []
        for i in range(7):
            self.resistors.append(Resistor(self.backplane_interface, i))

        self.dacs = []
        for i in range(19):
            self.dacs.append(DAC(self.asic_interface, i))

        #create the tree structure
        self.param_tree = MetadataTree({
            "name" : "QEM Interface",

            #Backplane subtree
            "clock" : (self.backplane_interface.get_clock_frequency, self.backplane_interface.set_clock_frequency, {"units" : "MHz", "description" : "Clock frequency for the SI570 oscillator", "min" : 10, "max":945}),
            "sensors_enabled":(self.backplane_interface.get_sensors_enable, self.backplane_interface.set_sensors_enable, {"name" : "sensors updating"}),
            "update_required" : (self.backplane_interface.get_update, self.backplane_interface.set_update,{"name" : "Update Once"}),
            "non_volatile" : (self.backplane_interface.get_resistor_non_volatile, self.backplane_interface.set_resistor_non_volatile, {"name": "Set Defaults", "description":"When setting resistor values determines if the new value should be set as a temporary value or as the new default"}),
                #reset always returns false
            "reset" : (u'False', self.backplane_interface.set_reset,{"name" : "Reset Backplane"}),
            # Attach subtrees for each supply and resistor
            "current_voltage" : [cv.param_tree for cv in self.current_voltage],
            "resistors" : [r.param_tree for r in self.resistors],

            #ASIC subtree
            "image" : (self.asic_interface.get_image, self.asic_interface.set_image_capture),
            "capture_run": (self.asic_interface.get_capture_run, self.asic_interface.set_capture_run, {"name": "Capture Run"}),
            "dacs" : [d.param_tree for d in self.dacs],

        })

    def get(self, path, metadata):
        """ Construct a dict by running the get command for the given path on the tree
        :param path: URI path of request
        :param metadata: Boole representing whether to include the metadata
        :return: a dict containing the data in a tree structure
        """
        return self.param_tree.get(path, metadata=metadata)

    def set(self, path, value):
        self.param_tree.set(path, value)
