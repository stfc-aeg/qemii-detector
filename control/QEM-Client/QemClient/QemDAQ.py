
import logging
import json

from os import path
from subprocess import Popen, PIPE

from odin.adapters.adapter import ApiAdapterRequest
from odin.adapters.parameter_tree import ParameterTree


class QemDAQ():
    """Encapsulates all the functionaility to initiate the DAQ.

    Configures the Frame Receiver and Frame Processor plugins
    Configures the HDF File Writer Plugin
    Configures the Live View Plugin
    """

    def __init__(self, save_file_dir="", save_file_name="", odin_data_dir=""):
        self.adapters = {}
        # self.data_config_dir = config_dir
        # self.fr_config_file = ""
        # self.fp_config_file = ""
        self.file_dir = save_file_dir
        self.file_name = save_file_name
        self.odin_data_dir = odin_data_dir
        logging.debug("ODIN DATA DIRECTORY: %s", self.odin_data_dir)
        self.process_list = {}
        self.file_writing = False
        self.config_dir = ""
        self.config_files = {
            "fp": "",
            "fr": ""
        }
        self.param_tree = ParameterTree({
            "receiver": {
                "connected": (self.is_fr_connected, None),
                "configured": (self.is_fr_configured, None),
                "config_file": (self.get_fr_config_file, None)
            },
            "processor": {
                "connected": (self.is_fp_connected, None),
                "configured": (self.is_fp_configured, None),
                "config_file": (self.get_fp_config_file, None)
            },
            "file_info": {
                "enabled": (lambda: self.file_writing, self.set_file_writing),
                "file_name": (lambda: self.file_name, self.set_file_name),
                "file_dir": (lambda: self.file_dir, self.set_data_dir)
            }
        })

    def __del__(self):
        self.cleanup()

    def initialize(self, adapters):
        self.adapters["fp"] = adapters['fp']
        self.adapters["fr"] = adapters['fr']
        self.adapters["file_interface"] = adapters['file_interface']
        self.get_fp_config_file()
        self.get_fr_config_file()

    def start_acquisition(self):
        """Ensures the odin data FP and FR are configured, and turn on File Writing
        """

        if self.is_fr_connected() is False:
            self.run_odin_data("fr")
        if self.is_fp_connected() is False:
            self.run_odin_data("fp")
        if self.is_fr_configured() is False:
            # send config message to FR
            logging.debug("Configuring Frame Receiver")
            self.config_odin_data('fr')
        if self.is_fp_configured() is False:
            logging.debug("Configuring Frame Processor")
            self.config_odin_data('fp')

        logging.debug("Starting File Writer")
        self.set_file_writing(True)

    def stop_acquisition(self):
        # disable file writing so other processes can access the saved data (such as the calibration plotting)
        self.set_file_writing(False)

    def is_fr_connected(self):
        status = self.get_od_status("fr")
        return status.get("connected", False)

    def is_fp_connected(self):
        status = self.get_od_status("fp")
        return status.get("connected", False)

    def is_fr_configured(self):
        status = self.get_od_status("fr")
        config_status = status.get("status", {}).get("configuration_complete", False)
        return config_status

    def is_fp_configured(self):
        status = self.get_od_status("fp")
        config_status = status.get("plugins")  # if plugins key exists, it has been configured
        return config_status is not None

    def get_od_status(self, adapter):
        try:
            request = ApiAdapterRequest(None, content_type="application/json")
            response = self.adapters[adapter].get("status", request)
            response = response.data["value"][0]
        except KeyError:
            logging.warning("Odin Data Adapter Not Found")
            response = {"Error": "Adapter {} not found".format(adapter)}

        finally:
            return response

    def get_fr_config_file(self):
        try:
            return_val = None
            request = ApiAdapterRequest(None)
            response = self.adapters["file_interface"].get("", request).data
            self.config_dir = response["config_dir"]
            for config_file in response["fr_config_files"]:
                if "qem" in config_file.lower():
                    return_val = config_file
                    break
            else:
                return_val = response["fr_config_files"][0]

        except KeyError:
            logging.warning("File Interface Adapter Not Found")
            return_val = ""

        finally:
            self.config_files["fr"] = return_val
            return return_val

    def get_fp_config_file(self):
        try:
            return_val = None
            request = ApiAdapterRequest(None)
            response = self.adapters["file_interface"].get("", request).data
            self.config_dir = response["config_dir"]
            for config_file in response["fp_config_files"]:
                if "qem" in config_file.lower():
                    return_val = config_file
                    break
            else:
                return_val = response["fp_config_files"][0]

        except KeyError:
            logging.warning("File Interface Adapter Not Found")

        finally:
            self.config_files["fp"] = return_val
            return return_val

    def set_data_dir(self, directory):
        self.file_dir = directory

    def set_file_name(self, name):
        self.file_name = name

    def set_file_writing(self, writing):
        self.file_writing = writing
        # send command to Odin Data
        command = "config/hdf/file/path"
        request = ApiAdapterRequest(self.file_dir, content_type="application/json")
        self.adapters["fp"].put(command, request)

        command = "config/hdf/file/name"
        request.body = self.file_name
        self.adapters["fp"].put(command, request)

        command = "config/hdf/write"
        request.body = "{}".format(writing)
        self.adapters["fp"].put(command, request)

    def config_odin_data(self, adapter):
        config = path.join(self.config_dir, self.config_files[adapter])
        config = path.expanduser(config)
        if not config.startswith('/'):
            config = '/' + config
        logging.debug(config)
        request = ApiAdapterRequest(config, content_type="application/json")
        command = "config/config_file"
        response = self.adapters[adapter].put(command, request)
        logging.warning(response.data)

    def run_odin_data(self, process_name):
        if process_name == "fr":
            try:
                logging.debug("RUNNING FRAME RECEIVER")
                log_config = path.join(self.config_dir, "fr_log4cxx.xml")
                self.process_list["frame_receiver"] = Popen(["./bin/frameReceiver", "--debug=2", 
                                                             "--logconfig={}".format(log_config)],
                                                            cwd=self.odin_data_dir)
            except OSError as e:
                logging.error("Failed to run Frame Receiver: %s", e)
                return False
        elif process_name == "fp":
            try:
                logging.debug("RUNNING FRAME PROCESSOR")
                log_config = path.join(self.config_dir, "fp_log4cxx.xml")
                self.process_list["frame_processor"] = Popen(["./bin/frameProcessor", "--debug=2",
                                                              "--logconfig={}".format(log_config)],
                                                             cwd=self.odin_data_dir)
            except OSError as e:
                logging.error("Failed to run Frame Processor: %s", e)
                return False
        else:
            logging.warning("None Odin Data process passed: %s", process_name)
            return False
        return True

    def cleanup(self):
        for process in self.process_list:
            self.process_list[process].terminate()
