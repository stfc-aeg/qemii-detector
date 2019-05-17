"""QEM Calibrator for the QEM Detector System.

Controls the calibration routines required for the QEM Detector System.

Sophie Kirkham, Application Engineering Group, STFC. 2019
Adam Neaves, Application Engineering Group, STFC. 2019
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
from odin_data.frame_processor_adapter import FrameProcessorAdapter
from odin_data.frame_receiver_adapter import FrameReceiverAdapter


class QemCalibrator():
    """Encapsulates the functionality required to initiate ADC calibration of the sensor
    """

    thread_executor = futures.ThreadPoolExecutor(max_workers=1)

    def __init__(self, coarse_calibration_value, data_dir, fems):
        self.calibration_complete = True
        self.plot_complete = True
        self.coarse_calibration_value = coarse_calibration_value
        self.data_dir = data_dir
        self.qem_fems = fems

        self.max_calibration = 10
        self.min_calibration = 0
        self.calibration_step = 1

        self.calibration_value = 0

        self.param_tree = ParameterTree({
            "calibration_complete": (self.get_cal_complete, None),
            "plot_complete": (self.get_plot_complete, None),
            "start_fine_calibrate": (None, self.adc_calibrate_fine),
            "start_coarse_calibrate": (None, self.adc_calibrate_coarse),
            "start_coarse_plot": (None, self.plot_coarse),
            "start_fine_plot": (None, self.plot_fine),
            "calibration_vals": {
                "max": (lambda: self.max_calibration, self.set_max_calib),
                "min": (lambda: self.min_calibration, self.set_min_calib),
                "step": (lambda: self.calibration_step),
                "current": (lambda: self.calibration_value, None)
            }
        })

    def set_max_calib(self, value):
        self.max_calibration = value
    
    def set_min_calib(self, value):
        self.min_calibration = value if value > -1 else 0

    def set_calib_step(self, value):
        self.calibration_step = value

    def initialize(self, adapters):
        """Receives references to the other adapters needed for calibration
        """

        for _, adapter in adapters.items():
            if isinstance(adapter, ProxyAdapter):
                self.proxy_adapter = adapter
                logging.debug("Proxy Adapter referenced by Calibrator")

    def get_cal_complete(self):
        """ getter method for the calibration completed flag
        @Returns : boolean value to indicate whether the coarse calibration has completed.
        """
        return self.calibration_complete

    def set_cal_complete(self, complete):
        """ sets the calibration complete flag
        @param complete: boolean value to indicate whether the coarse calibration is complete.
        """
        self.calibration_complete = complete

    def get_plot_complete(self):
        """ getter method for the plot completed flag
        @Returns : boolean value to indicate whether the coarse plot has completed.
        """
        return self.plot_complete

    def set_plot_complete(self, complete):
        """ sets the plot complete flag
        @param complete: boolean value to indicate whether the coarse plot is complete.
        """
        self.plot_complete = complete

    def getfinebitscolumn(self, input):
        """ extracts the fine data bits from the given H5 file.
        @param input: the h5 file to extract the fine bits from.
        @returns fine_data: an array storing the fine bits.
        """
        fine_data = []
        for i in input:
            for j in i:
                fine_data.append((j[33] & 63))  # extract the fine bits
        return fine_data

    def generate_fine_voltages(self, length):
        """ generates the voltages for a given length
        @param length: the length to use to generate voltages.
        @returns : an array of voltages
        """
        voltages = []
        # Where did these numbers come from?
        offset = 0.19862 + (0.000375 * self.coarse_calibration_value)
        for i in range(length):
            # voltages.append(float(1.544 + (i * 0.00008)))
            voltages.append(float(offset + (i * 0.00002)))
        return voltages

    def get_coarse_bits_column(self, input):
        """ extracts the coarse bits for a column for a single adc
        @param input : the h5 file to extract the data from
        @returns : a list of the coarse bits.
        """
        new_list = []
        for i in input:
            for j in i:
                # the heck are these numbers?
                new_list.append((j[33] & 1984) >> 6)  # extract the coarse bits
        return new_list

    def list_h5_files(self, adc_type):
        """ lists all of the H5 files for a given adc cal type in /scratch/qem
        sorts the found files to numerical ascending order.
        @param adc_type : string value - fine/coarse
        @returns : the list of filenames found
        """
        filenames = []
        for file in glob.glob(self.data_dir + adc_type + "/*.h5"):
            filenames.append(file)
        filenames.sort()
        return filenames

    def generate_coarse_voltages(self, length):
        """ generates the coarse voltages for a given length
        @param length: the length to use for generating the voltages
        @returns: the list of coarse voltages
        """
        voltages = []
        for i in range(length):
            voltages.append(float(0.19862 + (i * 0.000375)))
        return voltages

    def set_adc_config(self, config):
        """ sets the adc config (frames/delay) to use during adc calibration
        @param config : the string value of number or frames and delay for adc calibration
        """
        self.adc_config = config

    def get_adc_config(self):
        """ gets the adc config (frames/delay) to use during adc calibration
        @returns : the string value of number or frames and delay for adc calibration
        """
        return self.adc_config

    def adc_calibrate_coarse(self, calibrate):
        """ Begin adc calibration of the coarse values
        @param calibrate: boolean value to trigger calibration
        gets the adc delay value and adc frame value before setting up
        the qemcam. Performs adc calibration sweep from 0-4095 taking images
        and storing them in data_diretory + /coarse
        """

        # config = self.get_adc_config()
        # frames, delay = config.split(":")
        frames = 1  # int(frames)
        delay = 0  # int(delay)

        if calibrate == "true":
            logging.debug("Started Coarse Calibration")
            self.set_cal_complete(False)

            for fem in self.qem_fems:
                fem.setup_camera()  # qem fem reference
                fem.get_aligner_status()  # qem fem reference
                locked = fem.get_idelay_lock_status()  # qem fem reference
                logging.debug("idelay locked %-8X", locked)

            self.set_backplane_register("AUXSAMPLE_FINE", self.max_calibration - 1)  # setting AUXSAMPLE FINE to MAX
            self.calibration_value = self.min_calibration
            # MAIN loop to capture data
            IOLoop.instance().add_callback(self.coarse_calibration_loop, delay, frames)  # runs loop on main IO loop to avoid multi-threaded issues
            return

    def adc_calibrate_fine(self, calibrate):
        """ perform adc calibration of the fine values
        @param calibrate: boolean value to trigger calibration
        gets the adc delay value and adc frame value before setting up
        the qemcam. Performs adc calibration sweep from 0-1023 taking images
        and storing them in /scratch/qem/fine
        """

        # config = self.get_adc_config()
        # frames, delay = config.split(":")
        frames = 1
        delay = 0

        if calibrate == "true":
            logging.debug("Started Fine Calibration")
            self.set_cal_complete(False)
            for fem in self.qem_fems:
                fem.setup_camera()  # qem fem reference
                fem.get_aligner_status()  # qem fem reference
                locked = fem.get_idelay_lock_status()  # qem fem reference
                logging.debug("'-> idelay locked:' %-8X", locked)

            # set the default starting point for the COARSE value
            self.set_backplane_register("AUXSAMPLE_COARSE", 728)  # 435
            self.calibration_value = self.min_calibration
            # main loop to capture the data
            IOLoop.instance().add_callback(self.fine_calibration_loop, delay, frames) # run on IOLoop
            return

    def coarse_calibration_loop(self, delay, frames):
        self.set_backplane_register("AUXSAMPLE_COARSE", self.calibration_value)
        self.qem_fems[0].frame_gate_settings(frames-1, 0)
        self.qem_fems[0].frame_gate_trigger()
        # self.qem_fems[0].log_image_stream(self.data_dir + 'coarse_AN/adc_cal_AUXSAMPLE_COARSE_%04d' % self.calibration_value, frames)  # odin data
        self.calibration_value += self.calibration_step
        if self.calibration_value < self.max_calibration:
            IOLoop.instance().call_later(delay, self.coarse_calibration_loop, delay, frames)
        else:
            logging.debug("Calibration Complete")
            self.set_cal_complete(True)
        return

    def fine_calibration_loop(self, delay, frames):
        self.set_backplane_register("AUXSAMPLE_FINE", self.calibration_value)
        self.qem_fems[0].frame_gate_settings(frames-1, 0)
        self.qem_fems[0].frame_gate_trigger()
        # self.qem_fems[0].log_image_stream(self.data_dir + "fine_AN/adc_cal_AUXSAMPLE_FINE_%04d" % self.calibration_value, frames)
        self.calibration_value += self.calibration_step
        if self.calibration_value < self.max_calibration:
            IOLoop.instance().call_later(delay, self.fine_calibration_loop, delay, frames)
        else:
            logging.debug("Calibration Complete")
            self.set_cal_complete(True)
        return

    @run_on_executor(executor='thread_executor')
    def plot_fine(self, plot):
        """ plots the fine bit data from the adc fine calibration onto a graph

        lists all of the h5 files for fine calibration and generates
        voltages and average fine data, plots the results onto a plot, using
        a new set of axes each time to ensure no overwriting.Saves the file to
        /aeg_sw/work/projects/qem/python/03052018/fine.png
        """
        logging.debug("START PLOT FINE")
        self.set_plot_complete(False)
        filelist = []
        filelist = self.list_h5_files("fine_AN")
        # voltages for the plot
        f_voltages = []
        f_voltages = self.generate_fine_voltages(len(filelist))
        # averaged data for the plot
        f_averages = []

        # extract the data from each file in the folder
        for i in filelist:
            # open the file in the filelist array
            f = h5py.File(i, 'r')
            # extract the data key from the file
            a_group_key = list(f.keys())[0]
            # get the data
            data = list(f[a_group_key])
            # get data for column
            column = self.getfinebitscolumn(data)
            # average the column data
            average = sum(column) / len(column)
            # add the averaged data to the averages[] array
            f_averages.append(average)
            # close the file
            f.close()

        # generate the x / y plot of the data collected
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(f_voltages, f_averages, '-')
        ax.grid(True)
        ax.set_xlabel('Voltage')
        ax.set_ylabel('fine value')
        # fig.savefig(self.data_dir + "fine/fine.png", dpi = 100)
        fig.savefig("static/img/fine_graph.png", dpi=100)
        fig.clf()
        self.set_plot_complete(True)
        logging.debug("END PLOT FINE")

    @run_on_executor(executor='thread_executor')
    def plot_coarse(self, plot=None):
        """ plots the coarse bit data from the adc coarse calibration onto a graph

        lists all of the h5 files for coarse calibration and generates
        voltages and average coarse data, plots the results onto a plot, using
        a new set of axes each time to ensure no overwriting.Saves the file to
        /aeg_sw/work/projects/qem/python/03052018/coarse.png
        """
        logging.debug("START PLOT COARSE")
        self.set_plot_complete(False)
        logging.debug(".")
        filelist = []
        # array of voltages for the plot
        voltages = []
        # array of column averages for the plot
        averages = []
        # generate a list of files to process
        filelist = self.list_h5_files("coarse_AN")
        logging.debug(".")
        # populate the voltage array
        voltages = self.generate_coarse_voltages(len(filelist))
        logging.debug(".")
        # process the files in filelist
        for i in filelist:
            f = h5py.File(i, 'r')
            a_group_key = list(f.keys())[0]
            data = list(f[a_group_key])
            column = self.get_coarse_bits_column(data)
            # average the data
            average = sum(column) / len(column)
            averages.append(average)
            f.close()
        logging.debug(".")
        # generate and plot the graph
        fig = plt.figure()
        logging.debug(".")
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(voltages, averages, '-')
        ax.grid(True)
        ax.set_xlabel('Voltage')
        ax.set_ylabel('coarse value')
        # fig.savefig(self.data_dir + "coarse/coarse.png", dpi = 100)
        fig.savefig("static/img/coarse_graph.png", dpi=100)
        fig.clf()
        self.set_plot_complete(True)
        logging.debug("END PLOT COARSE")

    def set_backplane_register(self, register, value):
        """Sets the value of a resistor on the backplane
        """
        # logging.debug("Setting Register %s to %d", register, value)
        data = {register: {"register": value}}
        request = ApiAdapterRequest(data)
        response = self.proxy_adapter.put("backplane", request)
        if response.status_code != 200:
            logging.error("BACKPLANE REGISTER SET FAILED: %s", response.data)
