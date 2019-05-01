"""QEM Calibrator for the QEM Detector System.

Controls the calibration routines required for the QEM Detector System.

Sophie Kirkham, Application Engineering Group, STFC. 2019
Adam Neaves, Application Engineering Group, STFC. 2019
"""

import time
import logging
import glob
# import os
from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from concurrent import futures
# import cv2
# import sys
# import pprint
# import pickle
import h5py
# import numpy as np
# set logging for MATPLOTLIB separatly to avoid a lot of debug spam
mpl_logger = logging.getLogger('matplotlib')
mpl_logger.setLevel(logging.WARNING)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# from matplotlib.ticker import MaxNLocator

# from concurrent import futures

# from QemCam import *
from odin.adapters.adapter import ApiAdapter, ApiAdapterResponse, ApiAdapterRequest, request_types, response_types
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.adapters.proxy import ProxyAdapter
from odin_data.odin_data_adapter import OdinDataAdapter


class QemCalibrator():
    """Encapsulates the functionality required to initiate ADC calibration of the sensor
    """

    thread_executor = futures.ThreadPoolExecutor(max_workers=1)
    calibration_executor = futures.ThreadPoolExecutor(max_workers=1)

    def __init__(self, coarse_calibration_value, data_dir, fems):
        mpl_logger = logging.getLogger('matplotlib')
        mpl_logger.setLevel(logging.WARNING)
        self.calibration_complete = False
        self.plot_complete = False
        self.coarse_calibration_value = coarse_calibration_value
        self.data_dir = data_dir
        self.qem_fems = fems

        self.dummy = 1

        self.param_tree = ParameterTree({
            "calibration_complete": (self.get_cal_complete, self.set_cal_complete),
            "plot_complete": (self.get_plot_complete, self.set_plot_complete),
            "start_fine_calibrate": (None, self.adc_calibrate_fine),
            "start_coarse_calibrate": (None, self.adc_calibrate_coarse),
            "start_coarse_plot": (None, self.plot_coarse),
            "start_fine_plot": (None, self.plot_fine)
        })

    def set_dummy(self, value):
        self.dummy = value

    def initialize(self, adapters):
        """Receives references to the other adapters needed for calibration
        """

        for _, adapter in adapters.items():
            if isinstance(adapter, ProxyAdapter):
                self.proxy_adapter = adapter
                logging.debug("Proxy Adapter referenced by Calibrator")
            if isinstance(adapter, OdinDataAdapter):
                self.odin_data_adapter = adapter
                logging.debug("Odin Data Adapter referenced by Calibrator")

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

    def generateFineVoltages(self, length):
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

    def getcoarsebitscolumn(self, input):
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

    def Listh5Files(self, adc_type):
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

    def generatecoarsevoltages(self, length):
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

    @run_on_executor(executor='thread_executor')
    def adc_calibrate_coarse(self, calibrate):
        """ perform adc calibration of the coarse values
        @param calibrate: boolean value to trigger calibration
        gets the adc delay value and adc frame value before setting up
        the qemcam. Performs adc calibration sweep from 0-1023 taking images
        and storing them in data_diretory + /coarse
        """
        logging.debug("calibrate: %s", calibrate)
        # config = self.get_adc_config()
        # frames, delay = config.split(":")
        frames = 1  # int(frames)
        delay = 0.01  # int(delay)
        logging.debug("FRAME: %s, delay: %s", frames, delay)

        if calibrate == "true":
            logging.debug("STARTED COARSE CALIBRATION")
            self.set_cal_complete(False)

            for fem in self.qem_fems:
                fem.setup_camera()  # qem fem reference
            time.sleep(0.1)
            for fem in self.qem_fems:
                fem.get_aligner_status()  # qem fem reference
                locked = fem.get_idelay_lock_status()  # qem fem reference
                logging.debug("idelay locked %-8X", locked)
            print("%-32s" % ('-> Calibration started ...'))

            # define number of sweep
            n = 4096  # full range of the register
            # define i and the starting point of the capture
            i = 0
            self.set_backplane_register("AUXSAMPLE_FINE", 4095)  # setting AUXSAMPLE FINE to MAX

            # MAIN loop to capture data
            while i < n:
                # set AUXSAMPLE_COARSE to i
                self.set_backplane_register("AUXSAMPLE_COARSE", i)
                # delay 0 seconds (default) or by number passed to the function
                time.sleep(delay)
                # Save the captured data to here using RAH function
                self.qem_fems[0].log_image_stream(self.data_dir + 'coarse_AN/adc_cal_AUXSAMPLE_COARSE_%04d' % i, frames)  # odin data
                i = i+1

            time.sleep(1)
            # self.plot_coarse()
            self.set_cal_complete(True)

    @run_on_executor(executor='thread_executor')
    def adc_calibrate_fine(self, calibrate):
        """ perform adc calibration of the fine values
        @param calibrate: boolean value to trigger calibration
        gets the adc delay value and adc frame value before setting up
        the qemcam. Performs adc calibration sweep from 0-1023 taking images
        and storing them in /scratch/qem/fine
        calls pltofine and sets calibration fine complete to true when finished.
        """

        config = self.get_adc_config()
        frames, delay = config.split(":")
        frames = int(frames)
        delay = int(delay)

        if calibrate == "true":

            print(delay)
            print(frames)
            self.set_cal_complete(False)
            for fem in self.qem_fems:
                fem.setup_camera()  # qem fem reference

            time.sleep(0.1)

            for fem in self.qem_fems:
                fem.get_aligner_status()  # qem fem reference
                locked = fem.get_idelay_lock_status()  # qem fem reference
                logging.debug("%-32s %-8X" % ('-> idelay locked:', locked))
            print("%-32s" % ('-> Calibration started ...'))

            # define the number of loops for the adc calibration
            n = 4096  # changed from 1024
            # define i and the staring point
            i = 0
            # set the default starting point for the COARSE value
            self.set_backplane_register("AUXSAMPLE_COARSE", 728)  # 435

            # main loop to capture the data
            while i < n:
                # set the the AUXSAMPLE_FINE resistor to i
                self.set_backplane_register("AUXSAMPLE_FINE", i)
                # delay by 0 (default) or by the number passed to the function
                time.sleep(delay)
                # capture the data from the stream using rah function
                self.qem_fems[0].log_image_stream(
                    self.data_dir + 'fine/adc_cal_AUXSAMPLE_FINE_%04d' % i, frames)  # odin data
                i = i+1
            # end of main loop

            # wait for 1 second
            time.sleep(1)
            # self.plot_fine()
            self.set_cal_complete(True)
            print(self.get_cal_complete())

    @run_on_executor(executor='thread_executor')
    def plot_fine(self, plot):
        """ plots the fine bit data from the adc fine calibration onto a graph

        lists all of the h5 files for fine calibration and generates
        voltages and average fine data, plots the results onto a plot, using
        a new set of axes each time to ensure no overwriting.Saves the file to
        /aeg_sw/work/projects/qem/python/03052018/fine.png
        """
        self.set_plot_complete(False)
        filelist = []
        filelist = self.Listh5Files("fine")
        # voltages for the plot
        f_voltages = []
        f_voltages = self.generateFineVoltages(len(filelist))
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
        fig.savefig(self.data_dir + "fine/fine.png", dpi = 100)
        fig.savefig("static/img/fine_graph.png", dpi=100)
        fig.clf()
        self.set_plot_complete(True)
        print(self.get_cal_complete())

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
        filelist = self.Listh5Files("coarse_AN")
        logging.debug(".")
        # populate the voltage array
        voltages = self.generatecoarsevoltages(len(filelist))
        logging.debug(".")
        # process the files in filelist
        for i in filelist:
            f = h5py.File(i, 'r')
            a_group_key = list(f.keys())[0]
            data = list(f[a_group_key])
            column = self.getcoarsebitscolumn(data)
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
        logging.debug("Setting Register %s to %d", register, value)
        data = {register: {"register": value}}
        request = ApiAdapterRequest(data)
        response = self.proxy_adapter.put("backplane", request)
        if response.status_code != 200:
            logging.error("BACKPLANE REGISTER SET FAILED: %s", response.data)
