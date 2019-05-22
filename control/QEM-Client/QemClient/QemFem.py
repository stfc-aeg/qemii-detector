""" QemFem

Sophie Kirkham, Application Engineering Group, STFC. 2019
"""
import logging
import tornado
import h5py
import time
from concurrent import futures
import os 
from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from tornado.escape import json_decode
from RdmaUDP import RdmaUDP
from ImageStreamUDP import ImageStreamUDP
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError

BUSY = 1
FREE = 0

class QemFemError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass

class QemFem():
    """Qem Fem class. Represents a single FEM-II module.

    Controls and configures each FEM-II module ready for a DAQ via UDP.
    """
    
    def __init__(self, ip_address, port, id,
                 server_ctrl_ip_addr, camera_ctrl_ip_addr,
                 server_data_ip_addr, camera_data_ip_addr, 
                 vector_file_dir="/aeg_sw/work/projects/qem/python/03052018/",
                 vector_file="QEM_D4_198_ADC_10_icbias5_ifbias24.txt"):

        self.ip_address = ip_address
        self.port = port
        self.id = id
        self.state = FREE
        self.x10g_rdma = None
        self.x10g_stream = None
        self.server_ctrl_ip_addr = server_ctrl_ip_addr
        self.camera_ctrl_ip_addr = camera_ctrl_ip_addr

        self.server_data_ip_addr = server_data_ip_addr
        self.camera_data_ip_addr = camera_data_ip_addr

        self.vector_file_dir = vector_file_dir
        self.selected_vector_file = vector_file
        
        # qem 1 base addresses
        self.udp_10G_data    = 0x00000000
        self.udp_10g_control = 0x10000000
        self.frame_gen_0     = 0x20000000
        self.frm_chk_0       = 0x30000000
        self.frm_gen_1       = 0x40000000
        self.frm_chk_1       = 0x50000000
        self.top_reg         = 0x60000000
        self.mon_data_in     = 0x70000000
        self.mon_data_out    = 0x80000000
        self.mon_rdma_in     = 0x90000000
        self.mon_rdma_out    = 0xA0000000
        self.sequencer       = 0xB0000000
        self.receiver        = 0xC0000000
        self.frm_gate        = 0xD0000000
        self.Unused_0        = 0xE0000000
        self.Unused_1        = 0xF0000000
        #
        self.image_size_x    = 0x100
        self.image_size_y    = 0x100
        self.image_size_p    = 0x8
        self.image_size_f    = 0x8

        self.pixel_extract   = [16, 13, 12, 11]
        #
        self.debug_level = -1
        self.delay = 0
        self.strm_mtu = 8000
        self.rdma_mtu = 8000
        #
        self.frame_time = 1

        self.param_tree = ParameterTree({
            "ip_addr": (self.get_address, None),
            "port": (self.get_port, None),
            "vector_file_dir": (self.get_vector_file_dir, None),
            "selected_vector_file": (self.get_selected_vector_file, None),
            "load_vector_file": (None, self.load_vectors_from_file),
            "setup_camera": (None, self.setup_camera)
        })

    def get_vector_file_dir(self):
        return self.vector_file_dir

    def get_selected_vector_file(self):
        return self.selected_vector_file

    def get_address(self):
        return self.ip_address

    def get_id(self):
        return self.id

    def get_port(self):
        return self.port

    def get_state(self):
        return self.state

    def setup_camera(self, put_string="None"):
        logging.debug("SETTING UP CAMERA")
        self.set_ifg()
        #self.set_clock() wasn't implemented in QEM-I
        self.turn_rdma_debug_0ff()
        self.set_10g_mtu('data', 8000)
        self.x10g_rdma.read(0x0000000C, '10G_0 MTU')
        # N.B. for scrambled data 10, 11, 12, 13 bit raw=> column size 360, 396
        self.set_10g_mtu('data', 7344)
        self.set_image_size_2(102,288,11,16)
        #set idelay in 1 of 32 80fs steps  - d1, d0, c1, c0
        self.set_idelay(0,0,0,0)
        time.sleep(1)
        locked = self.get_idelay_lock_status()
        # set sub cycle shift register delay in 1 of 8 data clock steps - d1, d0, c1, c0
        # set shift register delay in 1 of 16 divide by 8 clock steps - d1, d0, c1, c0
        #
        # Shift 72 + 144 bits
        self.set_scsr(7,7,7,7)		# sub-cycle (1 bit)
        self.set_ivsr(0,0,27,27)		# cycle (8 bits)
        
        logging.debug("SETTING UP CAMERA: DONE")
    #Rob Halsall Code#
    
    def log_image_stream(self, file_name, num_images):
        logging.warning("Depreciated method 'log_image_stream'. Use Odin Data for data path")
        # logging.debug("Logging image to file %s", file_name)
        # logging.debug("AHHHHH WHAT IS FRAMES IT IS THIS: %d", num_images)
        # self.frame_gate_settings(num_images-1, 0)
        # self.frame_gate_trigger()
        # image_set = self.x10g_stream.get_image_set(num_images)
        # #write to hdf5 file
        # file_name = file_name + '.h5'
        # h5f = h5py.File(file_name, 'w')
        # h5f.create_dataset('dataset_1', data=image_set)
        # h5f.close()
        return

    def connect(self):
        #must be called as first method after instatiating class.
        self.x10g_rdma = RdmaUDP(
            self.server_ctrl_ip_addr, 61650,  # 10.0.1.2
            self.server_ctrl_ip_addr, 61651,  # 10.0.1.2
            self.camera_ctrl_ip_addr, 61650,  # 10.0.1.102
            self.camera_ctrl_ip_addr, 61651,  # 10.0.1.102
            2000000, 9000, 20)
        self.x10g_rdma.setDebug(False)
        self.x10g_rdma.ack = True

    def disconnect(self):
        # should be called on shutdown to close sockets
        self.x10g_rdma.close()
        # self.x10g_stream.close()

    def set_ifg(self):
        self.x10g_rdma.write(self.udp_10G_data+0xF, 0x0, '10G Ctrl reg rdma ifg en, udpchecksum zero en')
        self.x10g_rdma.write(self.udp_10G_data+0xD, 0x3, '10G Ctrl reg rdma ifg value 3 x 8B idle')
        self.x10g_rdma.write(self.udp_10g_control+0xF, 0x0, '10G Ctrl reg rdma ifg en, udpchecksum zero en')
        self.x10g_rdma.write(self.udp_10g_control+0xD, 0x3, '10G Ctrl reg rdma ifg value 3 x 8B idle')

    def print_ram_depth(self):
        ram_depth = self.x10g_rdma.read(0xB0000010, 'qem sequencer ram depth reg 0')
        logging.debug("sequencer ram depth : %i", ram_depth/8 )
        time.sleep(self.delay)
        return

    def stop_sequencer(self):
        self.x10g_rdma.write(self.sequencer, 0x0, 'qem seq null')
        time.sleep(self.delay)
        self.x10g_rdma.write(self.sequencer, 0x2, 'qem seq stop')
        time.sleep(self.delay)
        return

    def start_sequencer(self):
        self.x10g_rdma.write(self.sequencer, 0x0, 'qem seq null')
        time.sleep(self.delay)
        self.x10g_rdma.write(self.sequencer, 0x1, 'qem seq stop')
        time.sleep(self.delay)
        return

    def set_test_mode(self):
        self.x10g_rdma.write(self.receiver, 0x1, 'select camera test mode')
        return

    def unset_test_mode(self):
        self.x10g_rdma.write(self.receiver, 0x0, 'select camera test mode')
        return

    def start_test_mode(self):
        self.x10g_rdma.write(self.receiver, 0x3, 'select camera test mode')
        return

    def get_aligner_status(self):
        address = self.receiver | 0x14
        aligner_status = self.x10g_rdma.read(address, 'aligner status word')
        aligner_status_0 = aligner_status & 0xFFFF
        aligner_status_1 = aligner_status >> 16 & 0xFFFF
        
        time.sleep(self.delay)
        return [aligner_status_1, aligner_status_0]

    def set_idelay(self, data_1=0x00,cdn_1=0x00, data_0=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | cdn_1 << 16 | data_0 << 8 | cdn_0
        address = self.receiver | 0x02
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_idelay word')
        #issue load command
        address = self.receiver | 0x00
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        self.x10g_rdma.write(address, 0x10, 'set delay load high')
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        address = self.receiver | 0x12
        data_cdn_idelay_word = self.x10g_rdma.read(address, 'data_cdn_idelay word')
        return data_cdn_idelay_word

    def set_ivsr(self, data_1=0x00, data_0=0x00, cdn_1=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | data_0 << 16 | cdn_1 << 8 | cdn_0
        address = self.receiver | 0x03
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_ivsr word')
        return

    def set_scsr(self, data_1=0x00, data_0=0x00, cdn_1=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | data_0 << 16 | cdn_1 << 8 | cdn_0
        address = self.receiver | 0x05
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_ivsr word')
        return

    def set_pixel_count_per_image(self, pixel_count_max):
        number_bytes = pixel_count_max * 2
        number_bytes_r4 = pixel_count_max % 4
        number_bytes_r8 = number_bytes % 8
        first_packets = number_bytes/self.strm_mtu
        last_packet_size = number_bytes % self.strm_mtu
        lp_number_bytes_r8 = last_packet_size % 8
        lp_number_bytes_r32 = last_packet_size % 32
        size_status = number_bytes_r4 + number_bytes_r8 + lp_number_bytes_r8 + lp_number_bytes_r32

        if size_status != 0:
            logging.debug(
                "Size Error %8i %8i %8i %8i %8i %8i",
                number_bytes, number_bytes_r4, number_bytes_r8,
                first_packets, lp_number_bytes_r8, lp_number_bytes_r32)
        else:
            address = self.receiver | 0x01
            data = (pixel_count_max & 0x1FFFF) -1
            self.x10g_rdma.write(address, data, 'pixel count max')
        return

    def set_image_size(self, x_size, y_size, p_size, f_size):
        # set image size globals
        self.image_size_x = x_size
        self.image_size_y = y_size
        self.image_size_p = p_size
        self.image_size_f = f_size
        # check parameters againts ethernet packet and local link frame size compatibility
        pixel_count_max = x_size * y_size
        number_bytes = pixel_count_max * 2
        number_bytes_r4 = pixel_count_max % 4
        number_bytes_r8 = number_bytes % 8
        first_packets = number_bytes/self.strm_mtu
        last_packet_size = number_bytes % self.strm_mtu
        lp_number_bytes_r8 = last_packet_size % 8
        lp_number_bytes_r32 = last_packet_size % 32
        size_status = number_bytes_r4 + number_bytes_r8 + lp_number_bytes_r8 + lp_number_bytes_r32
        # calculate pixel packing settings
        if p_size >= 11 and p_size <= 13 and f_size == 16:
            pixel_extract = self.pixel_extract.index(p_size)
            pixel_count_max = pixel_count_max/2
        elif p_size == 8 and f_size == 8:
            pixel_extract = self.pixel_extract.index(p_size*2)
            pixel_count_max = pixel_count_max/4
        else:
            size_status =size_status + 1

        # set up registers if no size errors
        if size_status != 0:
            # WHO PRINTS TEXT LIKE THIS WHAT WHY?
            logging.debug("Size Error %-8s %-8s %-8s %-8s %-8s %-8s", 'no_bytes', 'no_by_r4', 'no_by_r8', 'no_pkts', 'lp_no_by_r8', 'lp_n0_by_r32')
            logging.debug("Size Error %8i %8i %8i %8i %8i %8i", number_bytes, number_bytes_r4, number_bytes_r8, first_packets, lp_number_bytes_r8, lp_number_bytes_r32)
        else:
            address = self.receiver | 0x01
            data = (pixel_count_max & 0x1FFFF) - 1
            self.x10g_rdma.write(address, data, 'pixel count max')
            self.x10g_rdma.write(self.receiver+4, 0x3, 'pixel bit size => 16 bit')
        return

    # Working with descrambling logic in place
    def set_image_size_2(self, x_size, y_size, p_size, f_size):
        # set image size globals
        self.image_size_x = x_size
        self.image_size_y = y_size
        self.image_size_p = p_size
        self.image_size_f = f_size
        # check parameters againts ethernet packet and local link frame size compatibility
        pixel_count_max = x_size * y_size
        number_bytes = pixel_count_max * 2
        number_bytes_r4 = pixel_count_max % 4
        number_bytes_r8 = number_bytes % 8
        first_packets = number_bytes/self.strm_mtu
        last_packet_size = number_bytes % self.strm_mtu
        lp_number_bytes_r8 = last_packet_size % 8
        lp_number_bytes_r32 = last_packet_size % 32
        size_status = number_bytes_r4 + number_bytes_r8 + lp_number_bytes_r8 + lp_number_bytes_r32
        # calculate pixel packing settings
        if p_size >= 11 and p_size <= 13:
            pixel_extract = self.pixel_extract.index(p_size)
            pixel_count_max = y_size/2
        else:
            size_status =size_status + 1

        # set up registers if no size errors
        if size_status != 0:
            logging.debug("Size Error %-8s %-8s %-8s %-8s %-8s %-8s", 'no_bytes', 'no_by_r4', 'no_by_r8', 'no_pkts', 'lp_no_by_r8', 'lp_n0_by_r32' )
            logging.debug("Size Error %8i %8i %8i %8i %8i %8i", number_bytes, number_bytes_r4, number_bytes_r8, first_packets, lp_number_bytes_r8, lp_number_bytes_r32 )
        else:
            address = self.receiver | 0x01
            data = (pixel_count_max & 0x1FFFF) -1
            self.x10g_rdma.write(address, data, 'pixel count max')
            self.x10g_rdma.write(self.receiver+4, p_size-10, 'Pixel size in bits 10,11,12 or 13')
        return

    def get_idelay_lock_status(self):
        if self.x10g_rdma is not None:
            address = self.receiver | 0x13
            data_locked_word = self.x10g_rdma.read(address, 'data_cdn_idelay word')
            data_locked_flag = data_locked_word & 0x00000001
            return data_locked_flag
        else:
            return 0

    def get_cdn_data_timing_values(self):
        address = self.receiver | 0x16
        cdn_data_timing_word_0 = self.x10g_rdma.read(address, 'cdn-data timing word')
        address = self.receiver | 0x17
        cdn_data_timing_word_1 = self.x10g_rdma.read(address, 'cdn-data timing word')
        address = self.receiver | 0x15
        cdn_data_timing_valid_word = self.x10g_rdma.read(address, 'cdn-data timing word')

        cdn_cdn_gap_0  = cdn_data_timing_word_0 >>  0 & 0xFF
        cdn_sub_pat_0  = cdn_data_timing_word_0 >>  8 & 0xFF
        cdn_dat_gap_0  = cdn_data_timing_word_0 >> 16 & 0xFF
        data_sub_pat_0 = cdn_data_timing_word_0 >> 24 & 0xFF
        cdn_data_timing_bytes_0 = [cdn_cdn_gap_0,cdn_sub_pat_0, cdn_dat_gap_0, data_sub_pat_0]

        cdn_cdn_gap_1  = cdn_data_timing_word_1 >>  0 & 0xFF
        cdn_sub_pat_1  = cdn_data_timing_word_1 >>  8 & 0xFF
        cdn_dat_gap_1  = cdn_data_timing_word_1 >> 16 & 0xFF
        data_sub_pat_1 = cdn_data_timing_word_1 >> 24 & 0xFF
        cdn_data_timing_bytes_1 = [cdn_cdn_gap_1,cdn_sub_pat_1, cdn_dat_gap_1, data_sub_pat_1]

        cdn_data_timing_valid_flag_0 = cdn_data_timing_valid_word & 0x01
        cdn_data_timing_valid_flag_1 = cdn_data_timing_valid_word >> 1 & 0x01
        return [cdn_data_timing_bytes_1, cdn_data_timing_bytes_0, cdn_data_timing_valid_flag_0, cdn_data_timing_valid_flag_1]

    def turn_rdma_debug_0n(self):
        self.x10g_rdma.debug = True
        return

    def turn_rdma_debug_0ff(self):
        self.x10g_rdma.debug = False
        return

    def load_vectors_from_file(self, vector_file_name=None):
        if vector_file_name is None or vector_file_name == "default":
            vector_file_name = os.path.join(self.vector_file_dir, self.selected_vector_file)
        logging.debug("loading vector file: %s", vector_file_name)

        #extract lines into array
        with open(vector_file_name, 'r') as f:
            data = f.readlines()
            init_length  = int(data[0])
            loop_length  = int(data[1])
            number_vectors = len(data)-3
            logging.debug("vectors loaded: %-8i", number_vectors)
            logging.debug("loop position: %-8i", loop_length)
            logging.debug("init position: %-8i", init_length)
            f.close()

        self.stop_sequencer()

        #load sequencer RAM
        logging.debug("Loading Sequncer RAM")
        for seq_address in range(number_vectors):
            words = data[seq_address+3].split()
            format_words = "%64s" % words[0]
            vector = int(words[0],2)
            lower_vector_word = vector & 0xFFFFFFFF
            upper_vector_word = vector >> 32
            if self.debug_level == 0:
                logging.debug("%64s %016X %8X %8X", format_words, vector, upper_vector_word, lower_vector_word)
            #load fpga block ram
            ram_address = seq_address * 2 + 0xB1000000
            self.x10g_rdma.write(ram_address, lower_vector_word, 'qem seq ram loop 0')
            time.sleep(self.delay)
            ram_address = ram_address + 1
            self.x10g_rdma.write(ram_address, upper_vector_word, 'qem seq ram loop 0')
            time.sleep(self.delay)

        #set init  limit
        self.x10g_rdma.write(0xB0000001, init_length - 1, 'qem seq init limit')
        time.sleep(self.delay)
        #set loop limit
        self.x10g_rdma.write(0xB0000002, loop_length - 1, 'qem seq loop limit')
        time.sleep(self.delay)
        self.start_sequencer()
        return

    def restart_sequencer(self):
        self.stop_sequencer()
        self.start_sequencer()
        return

    def frame_gate_trigger(self):
        logging.debug("TRIGGER CAPTURE")
        self.x10g_rdma.write(self.frm_gate+0,0x0,          'frame gate trigger off')
        self.x10g_rdma.write(self.frm_gate+0,0x1,          'frame gate trigger on')
        return

    def frame_gate_settings(self, frame_number, frame_gap):
        self.x10g_rdma.write(self.frm_gate+1,frame_number, 'frame gate frame number')
        self.x10g_rdma.write(self.frm_gate+2,frame_gap,    'frame gate frame gap')

    def frame_stats(self):
        self.x10g_rdma.read(self.mon_data_in+0x10, 'frame last length')
        self.x10g_rdma.read(self.mon_data_in+0x11, 'frame max length')
        self.x10g_rdma.read(self.mon_data_in+0x12, 'frame min length')
        self.x10g_rdma.read(self.mon_data_in+0x13, 'frame number')
        self.x10g_rdma.read(self.mon_data_in+0x14, 'frame last clock cycles')
        self.x10g_rdma.read(self.mon_data_in+0x15, 'frame max clock cycles')
        self.x10g_rdma.read(self.mon_data_in+0x16, 'frame min clock cycles')
        self.x10g_rdma.read(self.mon_data_in+0x17, 'frame data total')
        self.x10g_rdma.read(self.mon_data_in+0x18, 'frame data total clock cycles')
        self.x10g_rdma.read(self.mon_data_in+0x19, 'frame trigger count')
        self.x10g_rdma.read(self.mon_data_in+0x1A, 'frame in progress flag')

        return

    def set_10g_mtu(self,core_num, new_mtu):
        #mtu is set in clock cycles where each clock is 8 bytes -2
        val_mtu = new_mtu/8-2

        if core_num =='control':
            address = self.udp_10g_control
            self.rdma_mtu = new_mtu
            self.x10g_rdma.UDPMax = new_mtu
        else:
            address = self.udp_10G_data
            self.strm_mtu = new_mtu

        self.x10g_rdma.write(address+0xC, val_mtu, 'set 10G mtu')
        

    def i2c_read(self, i2c_addr=0x0):
        logging.warning("Set clock not implemented yet...")
        #setup i2c read command - read + address + data
        address = self.top_reg | 0x08
        i2c_address = i2c_addr & 0x7F
        i2c_cmd_addr_data = 0x8000 | i2c_address << 8
        self.x10g_rdma.write(address, i2c_cmd_addr_data, 'i2c cmd-address-data')
        # i2c trigger command
        address = self.top_reg | 0x09
        self.x10g_rdma.write(address, 0x0, 'i2c trigge low')
        self.x10g_rdma.write(address, 0x1, 'i2c trigger high')
        self.x10g_rdma.write(address, 0x0, 'i2c trigger low')
        #poll until done
        time.sleep(0.01)
        # check error status
        i2c_status = self.x10g_rdma.read(address, 0x0, 'i2c status')
        if i2c_status != 0x0 :
            logging.debug("i2c status: %1X", i2c_status)
        # read i2c data
        address = self.top_reg | 0x18
        i2c_data = self.x10g_rdma.read(address, 'i2c read data') & 0xFF
        return i2c_data

    def disconnect(self):
        self.x10g_rdma.close()
