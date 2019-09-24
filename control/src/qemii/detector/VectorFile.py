"""QEM Vector File Adapter for the QEM Detector System.

Opens, Updates, and uploads vector files to the FEM.

Allows a user to change DAC settings, and plot the vector file much like a logic analyser would.

Adam Neaves, Detector Systems Software Group, STFC. 2019
"""

import logging
import os.path
from functools import partial

from odin.adapters.parameter_tree import ParameterTree


class VectorFile():

    BIAS_DEPTH = 6

    # bias names, in the order that they appear in the vector file.
    # DEFAULTS IN COMMENTS
    BIAS_NAMES = ["iBiasCol",        # 001100 - 0x0C - 12
                  "iBiasSF0",        # 000101 - 0x05 - 05
                  "vBiasPGA",        # 000000 - 0x00 - 00
                  "iBiasPGA",        # 001100 - 0x0C - 12
                  "iBiasSF1",        # 001010 - 0x0A - 10
                  "iBiasOutSF",      # 011001 - 0x19 - 25
                  "iBiasLoad",       # 010100 - 0x14 - 20
                  "iBiasADCbuffer",  # 001100 - 0x0C - 12
                  "iBiasCalC",       # 001100 - 0x0C - 12
                  "iBiasRef",        # 001010 - 0x0A - 10
                  "iCbiasP",         # 011010 - 0x1A - 26
                  "vBiasCasc",       # 100000 - 0x20 - 32
                  "iFbiasN",         # 011000 - 0x18 - 24
                  "iBiasCalF",       # 010010 - 0x12 - 18
                  "iBiasADC1",       # 010100 - 0x14 - 20
                  "iBiasADC2",       # 010100 - 0x14 - 20
                  "iBiasAmpLVDS",    # 010000 - 0x10 - 16
                  "iBiasLVDS",       # 101101 - 0x2D - 45
                  "iBiasPLL"]        # 010100 - 0x14 - 20

    def __init__(self, file_name, file_dir):
        self.file_dir = file_dir
        self.file_name = file_name
        self.vector_loop_position = 0
        self.vector_length = 0
        self.vector_names = []
        self.vector_data = []

        self.dac_clock_refs = []
        self.dac_data_vector = []

        self.bias = {}

        self.clock_step = 0

        self.get_vector_information()
        self.extract_clock_references()
        self.convert_raw_dac_data()

        self.bias_tree = ParameterTree(
            # dict comprehension, like a one-line for loop
            # basically, for each bias, create a tuple of partial functions
            # that get/set values from the dictionary
            {
                bias_name: (partial(self.get_bias_val, bias_name),
                            partial(self.set_bias_val, bias_name),
                            # metadata ensures the bias val can't go over its 6 bit max
                            {"min": 0, "max": (2**self.BIAS_DEPTH) - 1})
                for bias_name in self.bias.keys()
            })

        self.param_tree = ParameterTree({
            "bias": self.bias_tree,
            "file_name": (lambda: self.file_name, self.set_file_name),
            "file_dir": (lambda: self.file_dir, None),
            "length": (lambda: self.vector_length, None),
            "loop_pos": (lambda: self.vector_loop_position, None),
            "save": (None, self.write_vector_file),
            "reset": (None, self.reset_vector_file)
        })

    def get_vector_information(self):
        """Extract the information from the vector file, such as loop position,
        vector length, and the vector data.
        """
        path = os.path.join(self.file_dir, self.file_name)
        path = os.path.expanduser(path)
        with open(path, 'r') as f:

            self.vector_loop_position = int(f.readline())
            self.vector_length = int(f.readline())
            self.vector_names = f.readline().split()

            self.dac_clk_in = self.vector_names.index("dacCLKin")
            self.dac_dat_in = self.vector_names.index("dacDin")

            logging.info("Loop Position:      %s", self.vector_loop_position)
            logging.info("Vector File Length: %s", self.vector_length)

            # read the remaining data from the file
            vector_data_string = f.read()

        # convert to 2d array
        self.vector_data = vector_data_string.splitlines()
        self.vector_data = [[int(y) for y in x] for x in self.vector_data]

        logging.info("Vector Data Shape: (%d,%d)", len(self.vector_data), len(self.vector_data[0]))

        # self.extract_clock_references()

    def extract_clock_references(self):
        """Extract the -ve clock positions and list them.
        Also extract the value associated with the -ve clock position and list them.
        """

        latch = 0  # stores previous value of clk_in
        # reset the arrays for clock refs and data vectors
        self.dac_clock_refs = []
        self.dac_data_vector = []

        # get all instances of Falling Edges for the clock ref (self.dac_clk_in) going from 1 -> 0
        for i, row in enumerate(self.vector_data):
            clk_in = row[self.dac_clk_in]
            if latch != clk_in and latch == 1:
                # state has changed from 1 to 0
                self.dac_clock_refs.append(i)
                self.dac_data_vector.append(row[self.dac_dat_in])
            latch = clk_in
        self.clock_step = self.dac_clock_refs[1] - self.dac_clock_refs[0]
        # self.convert_raw_dac_data()

    def convert_raw_dac_data(self):
        """Convert the binary data from the vector files into a dictionary of actual bias values
        and keys
        """

        for i, dac_data_name in enumerate(self.BIAS_NAMES):
            print(dac_data_name)
            # bias values are 6 bit. each value in dac_data_vector is one bit
            data_start = i * self.BIAS_DEPTH
            data_end = (i * self.BIAS_DEPTH) + self.BIAS_DEPTH
            data = self.dac_data_vector[data_start: data_end]
            print(data)
            # using join() + list comprehension
            # converting binary list to integer
            self.bias[dac_data_name] = int("".join(str(x) for x in data), 2)

    def convert_bias_to_raw(self):
        """Convert the data in the bias dictionary into the binary representation required
        in the vector file. Modify the dac_data_vector list to represent this changed data.
        Modify the vector_data list of lists with this new data
        """

        # convert the bias values from the dict into binary values in the dac_data_vector list
        for i, bias_name in enumerate(self.BIAS_NAMES):
            bias = '{:0{depth}b}'.format(self.bias[bias_name], depth=self.BIAS_DEPTH)
            logging.debug("%-16s: %s", bias_name, bias)
            first_start = i * self.BIAS_DEPTH
            second_start = (i + 19) * self.BIAS_DEPTH
            self.dac_data_vector[first_start: first_start + self.BIAS_DEPTH] = list(bias)
            self.dac_data_vector[second_start: second_start + self.BIAS_DEPTH] = list(bias)

        for i, line_num in enumerate(self.dac_clock_refs):  # for each clock edge
            # get slice of vector data, going from half the distance between clock edges above
            for line in self.vector_data[line_num - (self.clock_step / 2): line_num + (self.clock_step / 2)]:
                line[self.dac_dat_in] = self.dac_data_vector[i]

    def write_vector_file(self, file_name):
        logging.debug("Saving Vector File: %s", file_name)
        if file_name.lower() == "none" or file_name == "":
            file_name = self.file_name

        logging.debug("Converting Biases to Binary")
        self.convert_bias_to_raw()

        path = os.path.join(self.file_dir, file_name)
        path = os.path.expanduser(path)
        with open(path, 'w') as f:
            logging.debug("FILE NAME: %s", f.name)
            logging.debug("FILE MODE: %s", f.mode)
            f.write("{}\n".format(self.vector_loop_position))
            f.write("{}\n".format(self.vector_length))
            f.write("\t".join(self.vector_names))
            f.write('\n')

            # write the actual data, line by line
            for line in self.vector_data:
                str_line = "".join([str(x) for x in line])
                f.write("{}\n".format(str_line))
        self.file_name = file_name

    def set_file_name(self, name):
        # TODO: some form of verification
        self.file_name = name
        self.get_vector_information()

    def reset_vector_file(self, data):
        if os.path.isfile(os.path.join(self.file_dir, self.file_name)):
            self.get_vector_information()

    def get_bias_val(self, bias_name):
        return self.bias[bias_name]

    def set_bias_val(self, bias_name, val):
        logging.info("SETTING BIAS %s to %d", bias_name, val)
        if val == self.bias[bias_name]:
            logging.debug("Bias Already %d, ignoring", val)
            return
        self.bias[bias_name] = val

        # get position in list, as its in the same order in the vector_data
        bias_pos = self.BIAS_NAMES.index(bias_name)
        bin_bias = '{:0{depth}b}'.format(self.bias[bias_name], depth=self.BIAS_DEPTH)  # convert to binary
        first_start = bias_pos * self.BIAS_DEPTH
        second_start = (bias_pos + 19) * self.BIAS_DEPTH
        self.dac_data_vector[first_start: first_start + self.BIAS_DEPTH] = list(bin_bias)
        self.dac_data_vector[second_start: second_start + self.BIAS_DEPTH] = list(bin_bias)

        # write all the biases. We only really need to write the one that changed but its easier
        # to write them all.
        for i, line_num in enumerate(self.dac_clock_refs):  # for each clock edge
            # get slice of vector data, full distance of clock edge with current edge in center
            for line in self.vector_data[line_num - (self.clock_step / 2): line_num + (self.clock_step / 2)]:
                line[self.dac_dat_in] = self.dac_data_vector[i]
