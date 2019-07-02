"""QEM Calibrator for the QEM Detector System.

Controls the calibration routines required for the QEM Detector System.

Sophie Kirkham, Detector Systems Software Group, STFC. 2019
Adam Neaves, Detector Systems Software Group, STFC. 2019
"""

import logging
import glob
import h5py

# set logging for MATPLOTLIB separatly to avoid a lot of debug spam
mpl_logger = logging.getLogger('matplotlib')
mpl_logger.setLevel(logging.WARNING)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from concurrent import futures

from odin.adapters.adapter import ApiAdapterRequest
from odin.adapters.parameter_tree import ParameterTree
from odin.adapters.proxy import ProxyAdapter
# from odin_data.frame_processor_adapter import FrameProcessorAdapter
# from odin_data.frame_receiver_adapter import FrameReceiverAdapter

COARSE_BIT_MASK = 0x7C0
FINE_BIT_MASK = 0x3F

# defined from previous version of software
VOLT_OFFSET_BASE = 0.19862
VOLT_MULTIPLY_COARSE = 0.000375
VOLT_MULTIPLY_FINE = 0.00002


class QemCalibrator():
    """Encapsulates the functionality required to initiate ADC calibration of the sensor
    """

    thread_executor = futures.ThreadPoolExecutor(max_workers=1)

    def __init__(self, coarse_calibration_value, fems, daq):
        self.busy = False
        self.coarse_calibration_value = coarse_calibration_value
        self.qem_fems = fems
        self.qem_daq = daq

        self.max_calibration = 4096
        self.min_calibration = 0
        self.calibration_step = 1

        self.calibration_value = 0

        self.param_tree = ParameterTree({
            "is_busy": (lambda: self.busy, None),
            "start_calibrate": (None, self.adc_calibrate),
            "start_plot": (None, self.adc_plot),
            "calibration_vals": {
                "max": (lambda: self.max_calibration, self.set_max_calib),
                "min": (lambda: self.min_calibration, self.set_min_calib),
                "step": (lambda: self.calibration_step, self.set_calib_step),
                "current": (lambda: self.calibration_value, None)
            }
        })

    def set_max_calib(self, value):
        self.max_calibration = value if value < 4096 else 4096

    def set_min_calib(self, value):
        self.min_calibration = value if value > 0 else 0

    def set_calib_step(self, value):
        self.calibration_step = value

    def initialize(self, adapters):
        """Receives references to the other adapters needed for calibration
        """

        for _, adapter in adapters.items():
            if isinstance(adapter, ProxyAdapter):
                self.proxy_adapter = adapter
                logging.debug("Proxy Adapter referenced by Calibrator")

    def get_fine_bits_column(self, input, column):
        """ extracts the fine data bits from the given H5 file.
        @param input: the h5 file to extract the fine bits from.
        @returns fine_data: an array storing the fine bits.
        """
        fine_data = []
        for i in input:
            fine_data.append((i[column] & FINE_BIT_MASK))  # extract the fine bits
        return fine_data

    def get_coarse_bits_column(self, input, column):
        """ extracts the coarse bits for a single adc from a frame
        @param input: the frame to extract bits from
        @param column: The column number to extract bits from
        @returns : a list of the coarse bits.
        """

        coarse_data = []
        for i in input:
            coarse_data.append((i[column] & COARSE_BIT_MASK) >> 6)  # extract the coarse bits
        return coarse_data

    def generate_fine_voltages(self, length):
        """ generates the voltages for a given length
        @param length: the length to use to generate voltages.
        @returns : an array of voltages
        """
        voltages = []
        offset = VOLT_OFFSET_BASE + (VOLT_MULTIPLY_COARSE * self.coarse_calibration_value)
        for i in range(length):
            voltages.append(float(offset + (i * VOLT_MULTIPLY_FINE)))
        return voltages

    def generate_coarse_voltages(self, length):
        """ generates the coarse voltages for a given length
        @param length: the length to use for generating the voltages
        @returns: the list of coarse voltages
        """
        voltages = []
        for i in range(length):
            voltages.append(float(VOLT_OFFSET_BASE + (i * VOLT_MULTIPLY_COARSE)))
        return voltages

    def get_h5_file(self):
        files = glob.glob(self.qem_daq.file_dir + "/*h5")
        for filename in files:
            if self.qem_daq.file_name in filename:
                return filename
        return "not_found"

    def adc_calibrate(self, calibrate_type):
        if self.busy:
            logging.warning("Cannot Start Calibration: Calibrator is Busy")
            return
        calibrate_type = calibrate_type.upper().strip()
        if calibrate_type != "COARSE" and calibrate_type != "FINE":
            logging.warning("Cannot Start Calibration: Calibration type %s not recognised", calibrate_type)
            return
        self.busy = True
        register_name = "AUXSAMPLE_{}".format(calibrate_type)
        logging.debug(register_name)
        self.qem_daq.start_acquisition()
        for fem in self.qem_fems:
            fem.setup_camera()
            fem.get_aligner_status() # TODO: is this required?
            locked = fem.get_idelay_lock_status()
            if not locked:
                fem.load_vectors_from_file()
        # Set other register to default value for calibration
        if calibrate_type == "COARSE":
            logging.debug("Setting fine auxsample to max")
            self.set_backplane_register("AUXSAMPLE_FINE", self.max_calibration - 1)
        else:
            self.set_backplane_register("AUXSAMPLE_COARSE", 2000)
        
        self.calibration_value = self.min_calibration

        IOLoop.instance().add_callback(self.calibration_loop, register=register_name)

    def calibration_loop(self, register):
        self.set_backplane_register(register, self.calibration_value)
        self.qem_fems[0].frame_gate_settings(0, 0)  # set fem to take a single frame
        self.qem_fems[0].frame_gate_trigger()
        self.calibration_value += self.calibration_step
        if self.calibration_value < self.max_calibration:
            IOLoop.instance().call_later(0, self.calibration_loop, register)
        else:
            logging.debug("Calibration Complete")
            self.busy = False
            self.qem_daq.stop_acquisition()

    @run_on_executor(executor='thread_executor')
    def adc_plot(self, plot_type):
        if self.busy:
            logging.warning("Cannot Start Plot: Calibrator is Busy")
            return
        plot_type = plot_type.lower().strip()
        if plot_type != "coarse" and plot_type != "fine":
            logging.warning("Cannot Start Plot: Plot type %s not recognised", plot_type)
            return
        logging.debug("Start Plot %s", plot_type)
        self.busy = True
        averages = []
        file_name = self.get_h5_file()
        f = h5py.File(file_name, 'r')
        dataset_key = f.keys()[0]
        dataset = f[dataset_key]
        data_size = self.max_calibration - self.min_calibration
        dataset = dataset[-data_size:]
        logging.debug("GOT %d FRAMES", len(dataset))
        if plot_type == "fine":
            voltages = self.generate_fine_voltages(data_size)
            # assign function used repeatedly to a variable so we don't have to keep checking
            # plot_type in the for loop below
            get_bits_column = self.get_fine_bits_column
        else:
            voltages = self.generate_coarse_voltages(data_size)
            get_bits_column = self.get_coarse_bits_column
        f.close()
        logging.debug("Closed file")
        for frame in dataset:
            column = get_bits_column(list(frame), 33)
            average = sum(column) / len(column)
            averages.append(average)
        logging.debug("Got Averages")

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(voltages, averages, '-')
        ax.grid(True)
        ax.set_xlabel('Voltage')
        ax.set_ylabel("{} value".format(plot_type))

        fig.savefig("static/img/{}_graph.png".format(plot_type), dpi=100)
        fig.clf()
        self.busy = False
        logging.debug("Plot Complete")

    def set_backplane_register(self, register, value):
        """Sets the value of a resistor on the backplane
        """
        data = {register: {"register": value}}
        request = ApiAdapterRequest(data)
        response = self.proxy_adapter.put("backplane", request)
        if response.status_code != 200:
            logging.error("BACKPLANE REGISTER SET FAILED: %s", response.data)
