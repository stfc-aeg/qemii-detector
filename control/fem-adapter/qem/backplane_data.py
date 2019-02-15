from backplane import Backplane
from odin.adapters.metadata_tree import MetadataTree

class PowerGood(object):
    def __init__(self, backplane, i):
        self.index = i
        self.backplane = backplane

    def get(self):
        return self.backplane.get_power_good(self.index)

class CurrentVoltage(object):
    def __init__(self, backplane, i):
        self.index = i
        self.backplane = backplane

        self.param_tree = MetadataTree({
            "name" : self.backplane.get_adc_name(i),
            "current" : (self.get_current, {"units" : "mA"}),
            "voltage" : (self.get_voltage, {"units" : "V", "dp":3}),
            "voltage_register" : (self.get_voltage_raw,{"dp" : 0}),
            "current_register" : (self.get_current_raw,{"dp" : 0}),
        })

    def get_current(self):
        return self.backplane.get_current(self.index)

    def get_voltage(self):
        return self.backplane.get_voltage(self.index)

    def get_current_raw(self):
        return self.backplane.get_current_raw(self.index)

    def get_voltage_raw(self):
        return self.backplane.get_voltage_raw(self.index)

class Resistor(object):
    def __init__(self, backplane, i):
        self.index = i
        self.backplane = backplane

        self.param_tree = MetadataTree({
            "name" : self.backplane.get_resistor_name(self.index),
            "voltage_current" : (self.get, self.set, {"units" : self.backplane.get_resistor_units(self.index), "min" : self.backplane.get_resistor_min(self.index), "max" : self.backplane.get_resistor_max(self.index)}),
            "register_value" : (self.raw_get,self.raw_set,{"dp" : 0, "min" : 0, "max" : self.backplane.get_register_max(self.index)}),
       })

    def get(self):
        return self.backplane.get_resistor_value(self.index)

    def set(self, value):
        self.backplane.set_resistor_value(self.index, value)

    def raw_get(self):
        return self.backplane.get_resistor_value_raw(self.index)

    def raw_set(self, value):
        self.backplane.set_resistor_value_raw(self.index, value)


class BackplaneData(object):

    def __init__(self):
        self.backplane = Backplane()

        self.power_good = []
        for i in range(8):
            self.power_good.append(PowerGood(self.backplane, i))

        self.current_voltage = []
        for i in range(15):
            self.current_voltage.append(CurrentVoltage(self.backplane, i))

        self.resistors = []
        for i in range(8):
            self.resistors.append(Resistor(self.backplane, i))

        pw_good = {str(i+1) : pg.get for i,pg in enumerate(self.power_good)}
        pw_good.update({"list" : True, "description" : "Power good inputs from the MCP23008"})

        self.param_tree = MetadataTree({
            "name" : "QEM Backplane",
            "description" : "Testing information for the backplane on QEM.",
            "clock" : (self.backplane.get_clock_frequency, self.backplane.set_clock_frequency, {"units" : "MHz", "description" : "Clock frequency for the SI570 oscillator", "min" : 10, "max":945}),
            "sensors_enabled":(self.backplane.get_sensors_enable, self.backplane.set_sensors_enable, {"name" : "sensors updating"}),
            "update_required" : (self.backplane.get_update, self.backplane.set_update,{"name" : "Update Once"}),
            "non_volatile" : (self.backplane.get_resistor_non_volatile, self.backplane.set_resistor_non_volatile, {"name": "Set Defaults", "description":"When setting resistor values setermines if the new value should be set as a temporary value or as the new default"}), 
            "psu_enabled" : (self.backplane.get_psu_enable, self.backplane.set_psu_enable, {"name" : "PSU Enabled"}),
#            "capture_enabled" : (self.backplane.get_capture_enable, self.backplane.set_capture_enable, {"name" : "Capture Data"}),
            "power_good" : pw_good,
            "current_voltage" : [cv.param_tree for cv in self.current_voltage],
            "resistors" : [r.param_tree for r in self.resistors],
            "reset" : (False, self.backplane.set_reset,{"name" : "Reset Server"}),
            "temperature" : (self.backplane.get_temp,{"units": "C", "dp":1}),
            "fpga_reset" : (False, self.backplane.set_reset_fpga,{"name": "Reset FPGA"}),
        })

    def get(self, path, metadata):
        return self.param_tree.get(path, metadata=metadata)

    def set(self, path, value):
	print(path, value)
        self.param_tree.set(path, value)
