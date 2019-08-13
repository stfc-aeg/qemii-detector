
import logging

from os import path, devnull
from subprocess import Popen, STDOUT

from odin.adapters.adapter import ApiAdapterRequest
from odin.adapters.parameter_tree import ParameterTree
from tornado.ioloop import IOLoop


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

        self.FNULL = open(devnull)  # file reference to dev/null to hide suprocess output

        self.in_progress = False
        self.initialized = False
        # these varables used to tell when an acquisiton is completed
        self.frame_start_acquisition = 0  # number of frames received at start of acq
        self.frame_end_acquisition = 0  # number of frames at end of acq (start + acq number)
        self.frames = 0

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
            },
            "manual_config": (None, self.manual_config),
            "in_progress": (lambda: self.in_progress, None),
            "acquistion_boundries": {
                "acq_start": (lambda: self.frame_start_acquisition, None),
                "acq_end": (lambda: self.frame_end_acquisition, None)
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
        self.initialized = True

    def start_acquisition(self, num_frames):
        """Ensures the odin data FP and FR are configured, and turn on File Writing
        """
        logging.debug("Setting up Acquisition")
        fr_status = self.get_od_status("fr")
        fp_status = self.get_od_status("fp")

        if self.is_fr_connected(fr_status) is False:
            self.run_odin_data("fr")
            self.config_odin_data("fr")
        elif self.is_fr_configured(fr_status) is False:
            self.config_odin_data("fr")
        else:
            logging.debug("Frame Receiver Already connected/configured")

        if self.is_fp_connected(fp_status) is False:
            self.run_odin_data("fp")
            self.config_odin_data("fp")
        elif self.is_fp_configured(fp_status) is False:
            self.config_odin_data("fp")
        else:
            logging.debug("Frame Processor Already connected/configured")

        # waits till both FP and FR are configured
        IOLoop.instance().add_callback(self.config_wait_loop, num_frames)

    def config_wait_loop(self, num_frames):
        fr_status = self.get_od_status('fr')
        fp_status = self.get_od_status('fp')
        if not self.is_fr_configured(fr_status) or not self.is_fp_configured(fp_status):
            # if both are not yet configured, check again after a small delay
            logging.debug("Not Yet Configured!")
            IOLoop.instance().call_later(.5, self.config_wait_loop, num_frames)
        else:
            hdf_status = fp_status.get('hdf', None)
            if hdf_status is None:
                fp_status = self.get_od_status('fp')
                # get current frame written number. if not found, assume FR
                # just started up and it will be 0
                hdf_status = fp_status.get('hdf', {"frames_processed": 0})
            self.frames = num_frames
            self.frame_start_acquisition = hdf_status['frames_processed']
            self.frame_end_acquisition = self.frame_start_acquisition + num_frames
            logging.info("FRAME START ACQ: %d END ACQ: %d",
                         self.frame_start_acquisition,
                         self.frame_end_acquisition)
            self.set_file_writing(True)
            self.in_progress = True
            IOLoop.instance().add_callback(self.acquisition_check_loop)
            logging.debug("Starting File Writer")

    def acquisition_check_loop(self):
        hdf_status = self.get_od_status('fp').get('hdf', {"frames_processed": 0})
        if hdf_status['frames_processed'] == self.frames:
            self.stop_acquisition()
            logging.debug("Acquisition Complete")
        else:
            IOLoop.instance().call_later(.5, self.acquisition_check_loop)

    def stop_acquisition(self):
        # disable file writing so other processes can access the saved data
        # (such as the calibration plotting)
        self.in_progress = False
        self.set_file_writing(False)

    def is_fr_connected(self, status=None):
        if status is None:
            status = self.get_od_status("fr")
        return status.get("connected", False)

    def is_fp_connected(self, status=None):
        if status is None:
            status = self.get_od_status("fp")
        return status.get("connected", False)

    def is_fr_configured(self, status={}):
        if status.get('status') is None:
            status = self.get_od_status("fr")
        config_status = status.get("status", {}).get("configuration_complete", False)
        return config_status

    def is_fp_configured(self, status=None):
        # if shared memory->configured == true, then it's been configured
        if status is None:
            status = self.get_od_status("fp")
        config_status = status.get("shared_memory", {})
        config_status = config_status.get("configured", False)
        logging.debug("FP Shared Memory Configured: %s", config_status)
        # config_status = None
        return config_status

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

        command = "config/hdf/frames"
        request.body = "{}".format(self.frames)
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
        _ = self.adapters[adapter].put(command, request)

    def run_odin_data(self, process_name):
        if process_name == "fr":
            try:
                logging.debug("RUNNING FRAME RECEIVER")
                log_config = path.join(self.config_dir, "fr_log4cxx.xml")
                self.process_list["frame_receiver"] = Popen(["./bin/frameReceiver", "--debug=2",
                                                             "--logconfig={}".format(log_config)],
                                                            cwd=self.odin_data_dir,
                                                            stdout=self.FNULL,
                                                            stderr=STDOUT)
            except OSError as e:
                logging.error("Failed to run Frame Receiver: %s", e)
                return False
        elif process_name == "fp":
            try:
                logging.debug("RUNNING FRAME PROCESSOR")
                log_config = path.join(self.config_dir, "fp_log4cxx.xml")
                self.process_list["frame_processor"] = Popen(["./bin/frameProcessor", "--debug=2",
                                                              "--logconfig={}".format(log_config)],
                                                             cwd=self.odin_data_dir,
                                                             stdout=self.FNULL,
                                                             stderr=STDOUT)
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
        self.FNULL.close()

    def manual_config(self, override):
        if not self.initialized:
            return
        fr_status = self.get_od_status("fr")
        fp_status = self.get_od_status("fp")

        if self.is_fr_connected(fr_status) is False:
            self.run_odin_data("fr")
            self.config_odin_data("fr")
        elif self.is_fr_configured(fr_status) is False or override is True:
            self.config_odin_data("fr")
        else:
            logging.debug("Frame Receiver Already connected/configured")

        if self.is_fp_connected(fp_status) is False:
            self.run_odin_data("fp")
            self.config_odin_data("fp")
        elif self.is_fp_configured(fp_status) is False:
            self.config_odin_data("fp")
        else:
            logging.debug("Frame Processor Already connected/configured")
