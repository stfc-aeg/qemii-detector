from backplane_interface import Backplane_Interface
from asic_interface import ASIC_Interface
from operating_interface import Operating_Interface
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
    def __init__(self, **kwargs):
        """Initialises the InterfaceData Data structure
        creates instances of the backplane_interface and asic_interface,
        then creates a tree structure containing all data needed by the interace, and passes the API commands to the relevant interface so they can be sent on to the asic or the backplane server
        """

        self.backplane_interface = Backplane_Interface(kwargs['fem_ip'], kwargs['fem_port'], kwargs['resistor_defaults'])
        self.asic_interface = ASIC_Interface(
                            self.backplane_interface, 
                            kwargs['working_dir'], 
                            kwargs['data_dir'], 
                            kwargs['server_ctrl_ip'], 
                            kwargs['server_data_ip'], 
                            kwargs['camera_ctrl_ip'],
                            kwargs['camera_data_ip']
                        )
        self.operating_interface = Operating_Interface(kwargs['working_dir'])

        #Initialise all backplane power supplies
        self.current_voltage = []
        for i in range(13):
            self.current_voltage.append(CurrentVoltage(self.backplane_interface, i))

        self.resistors = []
        for i in range(8):#add another row for coarse..
            self.resistors.append(Resistor(self.backplane_interface, i))

        self.dacs = []
        for i in range(19):
            self.dacs.append(DAC(self.asic_interface, i+1))

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
            "fpga_reset" : (u'False', self.backplane_interface.set_reset_fpga),
            "load_defaults" : (u'False', self.backplane_interface.load_default_resistors),
            "defaults_loaded" : (self.backplane_interface.get_defaults_loaded, self.backplane_interface.set_defaults_loaded),

            #ASIC subtree
            "image" : (1, self.asic_interface.set_image_capture),
            "capture_run": (self.asic_interface.get_capture_run, self.asic_interface.set_capture_run, {"name": "Capture Run"}),
            "image_ready" :(self.asic_interface.get_image_ready, self.asic_interface.set_image_ready),


            "dacs" : [d.param_tree for d in self.dacs],
            "vector_file": (self.asic_interface.get_vector_file, self.asic_interface.set_vector_file),
            "update_bias" :(u'true', self.asic_interface.set_update_bias),
            "upload_vector_file" : (u'False', self.asic_interface.upload_vector_file),
            "bias_parsed" : (self.asic_interface.get_bias_data_parsed, self.asic_interface.set_bias_data_parsed),
            "vector_file_written" :(self.asic_interface.get_vector_file_written, self.asic_interface.set_vector_file_written),
            "upload_vector_complete" : (self.asic_interface.get_upload_vector_complete, self.asic_interface.set_upload_vector_complete),
            "log_complete" :(self.asic_interface.get_log_image_complete, self.asic_interface.set_log_image_complete),
            "adc_config" : (self.asic_interface.get_adc_config, self.asic_interface.set_adc_config),
            "adc_calibrate_fine" : (u'False', self.asic_interface.adc_calibrate_fine),
            "adc_calibrate_coarse" : (u'False', self.asic_interface.adc_calibrate_coarse),
            "coarse_cal_complete":(self.asic_interface.get_coarse_cal_complete, self.asic_interface.set_coarse_cal_complete),
            "fine_cal_complete":(self.asic_interface.get_fine_cal_complete, self.asic_interface.set_fine_cal_complete),
            "plot_fine" : (u'False', self.asic_interface.plot_fine),
            "plot_coarse" :(u'False', self.asic_interface.plot_coarse),
            "coarse_plot_complete":(self.asic_interface.get_coarse_plot_complete, self.asic_interface.set_coarse_plot_complete),
            "fine_plot_complete":(self.asic_interface.get_fine_plot_complete, self.asic_interface.set_fine_plot_complete),


            #operating subtree to parse configuration files
            "image_vector_files" : (self.operating_interface.get_image_vector_files),
            "adc_vector_files" : (self.operating_interface.get_adc_vector_files),


        })

    def get(self, path, metadata):
        """ Construct a dict by running the get command for the given path on the tree
        :param path: URI path of request
        :param metadata: Boole representing whether to include the metadata
        :return: a dict containing the data in a tree structure
        """
        
        return self.param_tree.get(path, metadata=metadata)

    def set(self, path, value):
        """ Runs the set command on the given path on the tree, settings
            the value to the value provided.
            
        @param path: uri path of request
        @param value: the value to set 
        """
        if "dacs" in path: 
            value = value.encode('ascii','ignore')
  
        self.param_tree.set(path, value)
