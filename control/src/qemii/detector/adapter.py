""" Qem Detector Adapter for QEM Detector System.

Main control layer for the entire qem detector system.
Intelligent adapter that can communicate to all other loaded adapters lower down in the heirarchy.
Bridges the gap between generic UI commands and detector specific business logic.

Sophie Kirkham, Application Engineering Group, STFC. 2019
Adam Neaves, Detector Systems Software Group, STFC. 2019
"""
import logging
import os

from odin.util import decode_request_body, convert_unicode_to_string

from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError

from odin.adapters.proxy import ProxyAdapter
from qemii.detector.FileInterfaceAdapter import FileInterfaceAdapter
from odin_data.frame_processor_adapter import FrameProcessorAdapter
from odin_data.frame_receiver_adapter import FrameReceiverAdapter

from qemii.detector.QemCalibrator import QemCalibrator
from qemii.detector.QemFem import QemFem
from qemii.detector.QemDAQ import QemDAQ


class QemDetectorAdapter(ApiAdapter):
    """Top Level Adapter for the QEM Control system.

    Provides access to all the sub sections that compose a working Qem Dectector System.
    It has access to the other adapters loaded, and thus can sequence required commands.
    """

    def __init__(self, **kwargs):
        """Initialize the QemDetectorAdapter object.

        This constructor initializes the QemDetector object.

        :param kwargs: keyword arguments specifying options
        """
        # Intialise superclass
        super(QemDetectorAdapter, self).__init__(**kwargs)
        self.qem_detector = QemDetector(self.options)
        self.adapters = {}
        logging.debug('QemDetector Adapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        try:
            response = self.qem_detector.get(path)
            status_code = 200
        except ParameterTreeError as e:
            response = {'error': str(e)}
            status_code = 400

        content_type = 'application/json'

        return ApiAdapterResponse(response, content_type=content_type,
                                  status_code=status_code)

    @request_types('application/json')
    @response_types('application/json', default='application/json')
    def put(self, path, request):
        """Handle an HTTP PUT request.

        This method handles an HTTP PUT request, returning a JSON response.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """

        content_type = 'application/json'

        try:
            data = convert_unicode_to_string(decode_request_body(request))
            self.qem_detector.set(path, data)
            response = self.qem_detector.get(path)
            status_code = 200
        except (TypeError, ValueError, ParameterTreeError) as e:
            response = {'error': 'Failed to decode PUT request body: {}'.format(str(e))}
            status_code = 400

        logging.debug(response)

        return ApiAdapterResponse(response, content_type=content_type,
                                  status_code=status_code)

    def initialize(self, adapters):
        self.qem_detector.initialize(adapters)

    def cleanup(self):
        self.qem_detector.cleanup()


class QemDetector():
    """ QemDetector object representing the entire QEM Detector System.

    Intelligent control plane that can sequence events across the subsystems lower down in the
    hierarchy to perform DAQ, calibration runs and other generic control functions on the entire
    detector system (FEM-II's, Backplane, Data Path Packages etc.)
    """

    def __init__(self, options):

        defaults = QemDetectorDefaults()
        self.file_dir = options.get("save_dir", defaults.save_dir)
        self.file_name = options.get("save_file", defaults.save_file)
        self.vector_file_dir = options.get("vector_file_dir", defaults.vector_file_dir)
        self.vector_file = options.get("vector_file_name", defaults.vector_file)
        self.acq_num = options.get("acquisition_num_frames", defaults.acq_num)
        self.acq_gap = options.get("acquisition_frame_gap", defaults.acq_gap)
        odin_data_dir = options.get("odin_data_dir", defaults.odin_data_dir)
        odin_data_dir = os.path.expanduser(odin_data_dir)

        self.daq = QemDAQ(self.file_dir, self.file_name, odin_data_dir=odin_data_dir)

        self.fems = []
        for key, value in options.items():
            logging.debug("%s: %s", key, value)
            if "fem" in key:
                fem_info = value.split(',')
                fem_info = [(i.split('=')[0], i.split('=')[1]) for i in fem_info]
                fem_dict = {fem_key.strip(): fem_value.strip() for (fem_key, fem_value) in fem_info}
                logging.debug(fem_dict)

                self.fems.append(QemFem(
                    fem_dict.get("ip_addr", defaults.fem["ip_addr"]),
                    fem_dict.get("port", defaults.fem["port"]),
                    fem_dict.get("id", defaults.fem["id"]),
                    fem_dict.get("server_ctrl_ip_addr", defaults.fem["server_ctrl_ip"]),
                    fem_dict.get("camera_ctrl_ip_addr", defaults.fem["camera_ctrl_ip"]),
                    fem_dict.get("server_data_ip_addr", defaults.fem["server_data_ip"]),
                    fem_dict.get("camera_data_ip_addr", defaults.fem["camera_data_ip"]),
                    # vector file only required for the "main" FEM, fem_0
                    self.vector_file_dir,
                    self.vector_file
                ))

        if not self.fems:  # if self.fems is empty
            self.fems.append(QemFem(
                ip_address=defaults.fem["ip_addr"],
                port=defaults.fem["port"],
                fem_id=defaults.fem["id"],
                server_ctrl_ip_addr=defaults.fem["server_ctrl_ip"],
                camera_ctrl_ip_addr=defaults.fem["camera_ctrl_ip"],
                server_data_ip_addr=defaults.fem["server_data_ip"],
                camera_data_ip_addr=defaults.fem["camera_data_ip"],
                vector_file_dir=self.vector_file_dir,
                vector_file=self.vector_file
            ))

        fem_tree = {}
        for fem in self.fems:
            fem.connect()
            fem.setup_camera()

            fem_tree["fem_{}".format(fem.id)] = fem.param_tree

        self.file_writing = False
        self.calibrator = QemCalibrator(2000, self.fems, self.daq)
        self.param_tree = ParameterTree({
            "calibrator": self.calibrator.param_tree,
            "fems": fem_tree,
            "daq": self.daq.param_tree,
            "acquisition": {
                "num_frames": (lambda: self.acq_num, self.set_acq_num),
                "frame_gap": (lambda: self.acq_gap, self.set_acq_gap),
                "start_acq": (None, self.acquisition)
            }
        })

        self.adapters = {}

    def get(self, path):
        return self.param_tree.get(path)

    def set(self, path, data):
        # perhaps hijack the message here and run the acquisition prep
        # before passing the message on to the param_tree?
        logging.debug("SET:\n PATH: %s\n DATA: %s", path, data)
        return self.param_tree.set(path, data)

    def set_acq_num(self, num):
        logging.debug("Number Frames: %d", num)
        self.acq_num = num

    def set_acq_gap(self, gap):
        logging.debug("Frame Gap: %d", gap)
        self.acq_gap = gap

    def initialize(self, adapters):
        """Get references to required adapters and pass those references to the classes that need
            to use them
        """
        for name, adapter in adapters.items():
            if isinstance(adapter, ProxyAdapter):
                logging.debug("%s is Proxy Adapter", name)
                self.adapters["proxy"] = adapter
            elif isinstance(adapter, FrameProcessorAdapter):
                logging.debug("%s is FP Adapter", name)
                self.adapters["fp"] = adapter
            elif isinstance(adapter, FrameReceiverAdapter):
                logging.debug("%s is FR Adapter", name)
                self.adapters["fr"] = adapter
            elif isinstance(adapter, FileInterfaceAdapter):
                logging.debug("%s is File Interface Adapter", name)
                self.adapters["file_interface"] = adapter

        self.calibrator.initialize(self.adapters)
        self.daq.initialize(self.adapters)

    def cleanup(self):
        self.daq.cleanup()
        for fem in self.fems:
            fem.cleanup()

    def acquisition(self, put_data):
        if self.daq.in_progress:
            logging.warning("Cannot Start Acquistion: Already in progress")
            return
        self.daq.start_acquisition(self.acq_num)
        for fem in self.fems:
            fem.setup_camera()
            fem.get_aligner_status()  # TODO: is this required?
            locked = fem.get_idelay_lock_status()
            if not locked:
                fem.load_vectors_from_file()
        self.fems[0].frame_gate_settings(self.acq_num - 1, self.acq_gap)
        self.fems[0].frame_gate_trigger()


class QemDetectorDefaults():

    def __init__(self):
        self.save_dir = "/scratch/qem/QEM_AN_CALIBRATION/"
        self.save_file = "default_file"
        self.vector_file_dir = "/aeg_sw/work/projects/qem/python/03052018/"
        self.vector_file = "QEM_D4_198_ADC_10_icbias30_ifbias24.txt"
        self.odin_data_dir = "~/develop/projects/qemii/install/"
        self.acq_num = 4096
        self.acq_gap = 1
        self.fem = {
            "ip_addr": "192.168.0.122",
            "port": "8070",
            "id": 0,
            "server_ctrl_ip": "10.0.1.2",
            "camera_ctrl_ip": "10.0.1.102",
            "server_data_ip": "10.0.2.2",
            "camera_data_ip": "10.0.2.102"
        }
