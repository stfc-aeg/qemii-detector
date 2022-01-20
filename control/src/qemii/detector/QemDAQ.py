
import logging

from os import path
from functools import partial

from odin.adapters.adapter import ApiAdapterRequest
from odin.adapters.parameter_tree import ParameterTree
from tornado.ioloop import IOLoop


class QemDAQ():
    """Encapsulates all the functionaility to initiate the DAQ.

    Configures the Frame Receiver and Frame Processor plugins
    Configures the HDF File Writer Plugin
    Configures the Live View Plugin
    """

    def __init__(self, save_file_dir="", save_file_name=""):
        self.adapters = {}
        # self.data_config_dir = config_dir
        # self.fr_config_file = ""
        # self.fp_config_file = ""
        self.file_dir = save_file_dir
        self.file_name = save_file_name
        #self.num_frames = 0

        self.in_progress = False
        self.is_initialized = False  # Flag for initialization

        # these varables used to tell when an acquisiton is completed
        self.frame_start_acquisition = 0  # number of frames received at start of acq
        self.frame_end_acquisition = 0  # number of frames at end of acq (start + acq number)

        self.process_list = {}
        self.file_writing = False
        self.config_dir = ""
        self.config_files = {
            "fp": "",
            "fr": ""
        }
        self.param_tree = ParameterTree({
            "receiver": {
                "connected": (partial(self.is_od_connected, adapter="fr"), None),
                "configured": (self.is_fr_configured, None),
                "config_file": (partial(self.get_config_file, "fr"), None)
            },
            "processor": {
                "connected": (partial(self.is_od_connected, adapter="fp"), None),
                "configured": (self.is_fp_configured, None),
                "config_file": (partial(self.get_config_file, "fp"), None)
            },
            "file_info": {
                "enabled": (lambda: self.file_writing, self.set_file_writing),
                "file_name": (lambda: self.file_name, self.set_file_name),
                "file_dir": (lambda: self.file_dir, self.set_data_dir)
            },
            "in_progress": (lambda: self.in_progress, None),
            "configure_odin": (lambda: None, self.config_odin_data)
        })

    def initialize(self, adapters):
        self.adapters["fp"] = adapters['fp']
        self.adapters["fr"] = adapters['fr']
        self.adapters["file_interface"] = adapters['file_interface']
        self.get_config_file("fp")
        self.get_config_file("fr")
        self.is_initialized = True

    def start_acquisition(self, num_frames):
        """Ensures the odin data FP and FR are configured, and turn on File Writing
        """
        #self.num_frames = int(num_frames)
        logging.debug("Setting up Acquisition")
        fr_status = self.get_od_status("fr")
        fp_status = self.get_od_status("fp")

        if self.is_od_connected(fr_status) is False:
            logging.error("Cannot start Acquisition: Frame Receiver not found")
            return
        elif self.is_fr_configured(fr_status) is False:
            self.config_odin_data("fr")
        else:
            logging.debug("Frame Receiver Already connected/configured")

        if self.is_od_connected(fp_status) is False:
            logging.error("Cannot Start Acquisition: Frame Processor not found")
            return
        elif self.is_fp_configured(fp_status) is False:
            self.config_odin_data("fp")
        else:
            logging.debug("Frame Processor Already connected/configured")

        hdf_status = fp_status.get('hdf', None)
        if hdf_status is None:
            fp_status = self.get_od_status('fp')
            # get current frame written number. if not found, assume FR
            # just started up and it will be 0
            hdf_status = fp_status.get('hdf', {"frames_written": 0})
        self.frame_start_acquisition = hdf_status['frames_written']
        self.frame_end_acquisition = self.frame_start_acquisition + num_frames
        logging.info("FRAME START ACQ: %d END ACQ: %d",
                     self.frame_start_acquisition,
                     self.frame_end_acquisition)

        # self.in_progress = True  # TODO: DISABLED TO ALLOW REPEAT RUNS WITHOUT ODIN DATA WORKING YET - Ashley 22/01/2020
        # IOLoop.instance().add_callback(self.acquisition_check_loop)
        logging.debug("Starting File Writer!!!")
        self.set_file_writing(True, num_frames)
        #self.set_file_writing(True, num_frames)

    def acquisition_check_loop(self):
        hdf_status = self.get_od_status('fp').get('hdf', {"frames_written": 0})
        if hdf_status['frames_written'] == self.frame_end_acquisition:
            self.stop_acquisition()
            logging.debug("Acquisition Complete")
        else:
            IOLoop.instance().call_later(.5, self.acquisition_check_loop)

    def stop_acquisition(self):
        """Disable file writing so other processes can access the saved data"""
        self.in_progress = False
        self.set_file_writing(False)

    def is_od_connected(self, status=None, adapter=""):
        if status is None:
            status = self.get_od_status(adapter)
        return status.get("connected", False)

    def is_fr_configured(self, status={}):
        if status.get('status') is None:
            status = self.get_od_status("fr")
        config_status = status.get("status", {}).get("configuration_complete", False)
        return config_status

    def is_fp_configured(self, status=None):
        status = self.get_od_status("fp")
        config_status = status.get("plugins")  # if plugins key exists, it has been configured
        return config_status is not None

    def get_od_status(self, adapter):
        if not self.is_initialized:
            return {"Error": "Adapter not Initialized with references yet"}
        try:
            request = ApiAdapterRequest(None, content_type="application/json")
            response = self.adapters[adapter].get("status", request)
            response = response.data["value"][0]
        except KeyError:
            logging.warning("%s Adapter Not Found", adapter)
            response = {"Error": "Adapter {} not found".format(adapter)}

        finally:
            return response

    def get_config_file(self, adapter):
        if not self.is_initialized:
            # IAC not setup yet
            return ""
        try:
            return_val = ""
            request = ApiAdapterRequest(None)
            response = self.adapters['file_interface'].get('', request).data
            self.config_dir = response['config_dir']
            for config_file in response["{}_config_files".format(adapter)]:
                if "qem" in config_file.lower():
                    return_val = config_file
                    break
            else:  # else of for loop: calls if finished loop without hitting break
                # just return the first config file found
                return_val = response["{}_config_files".format(adapter)][0]

        except KeyError as key_error:
            logging.warning("KeyError when trying to get config file: %s", key_error)
            return_val = ""

        finally:
            self.config_files[adapter] = return_val
            return return_val

    def set_data_dir(self, directory):
        self.file_dir = directory

    def set_file_name(self, name):
        self.file_name = name

    def set_file_writing(self, writing, num_frames=0):
        self.file_writing = writing
        
        # dissable writing
        request = ApiAdapterRequest(self.file_dir, content_type="application/json")
        # command = "config/hdf/write"
        # request.body = "{}".format(False)
        # self.adapters["fp"].put(command, request)

        #set the path
        command = "config/hdf/file/path"
        request.body = self.file_dir
        self.adapters["fp"].put(command, request)

        #set the filename
        command = "config/hdf/file/name"
        request.body = self.file_name
        self.adapters["fp"].put(command, request)

        #debugging messages
        # logging.info("\n\n\nnum_frames = %d\n\n\\n" %num_frames)
        # logging.info("\n\n\nSETTTING FRAMES to correct value\n\n\n")
        
        #write the number of frames
        command = "config/hdf/frames"
        request.body = "{}".format(num_frames)
        self.adapters["fp"].put(command, request)

        #reset the frame number
        logging.info("SETTTING FRAME NUMBER to 0\n")
        command = "config/qemii/frame_number"
        request.body = "{}".format("0") #this sets the frame number back to 0 ready for the next run
        self.adapters["fp"].put(command, request)

        #re-enable writing
        command = "config/hdf/write"
        request.body = "{}".format(writing)
        self.adapters["fp"].put(command, request)

        # logging.info(request.body)

    def config_odin_data(self, adapter):
        config = path.join(self.config_dir, self.config_files[adapter])
        config = path.expanduser(config)
        logging.debug(config)
        request = ApiAdapterRequest(config, content_type="application/json")
        command = "config/config_file"
        _ = self.adapters[adapter].put(command, request)
