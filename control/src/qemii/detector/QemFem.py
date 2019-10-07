""" QemFem

Sophie Kirkham, Detector Systems Software Group, STFC. 2019
Adam Neaves, Detector Systems Software Group, STFC. 2019
"""
import logging
import tornado
import h5py
import time
from concurrent import futures
from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
from tornado.escape import json_decode
from socket import error as socket_error
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError

from qemii.detector.VectorFile import VectorFile
from qemii.detector.RdmaUDP import RdmaUDP


class QemFemError(Exception):
    """Simple exception class for PSCUData to wrap lower-level exceptions."""

    pass


class QemFem():
    """Qem Fem class. Represents a single FEM-II module.

    Controls and configures each FEM-II module ready for a DAQ via UDP.
    """
    thread_executor = futures.ThreadPoolExecutor(max_workers=1)

    def __init__(self, ip_address, port, fem_id,
                 server_ctrl_ip_addr, camera_ctrl_ip_addr,
                 server_data_ip_addr, camera_data_ip_addr,
                 vector_file_dir="/aeg_sw/work/projects/qem/python/03052018/",
                 vector_file="QEM_D4_198_ADC_10_icbias30_ifbias24.txt"):

        self.ip_address = ip_address
        self.port = port
        self.id = int(fem_id)
        self.x10g_rdma = None
        self.x10g_stream = None
        self.server_ctrl_ip_addr = server_ctrl_ip_addr
        self.camera_ctrl_ip_addr = camera_ctrl_ip_addr

        self.server_data_ip_addr = server_data_ip_addr
        self.camera_data_ip_addr = camera_data_ip_addr
        if self.id == 0:
            self.vector_file_dir = vector_file_dir
            self.vector_file = VectorFile(vector_file, vector_file_dir)
        else:
            self.vector_file = None
            self.vector_file_dir = None

        # qem 1 base addresses
        self.rmda_addr = {
            "udp_10G_data":    0x00000000,
            "udp_10G_control": 0x10000000,
            "frame_gen_0":     0x20000000,  # unused
            "frm_chk_0":       0x30000000,  # unused
            "frm_gen_1":       0x40000000,  # unused
            "frm_chk_1":       0x50000000,  # unused
            "top_reg":         0x60000000,  # unused
            "mon_data_in":     0x70000000,  # unused
            "mon_data_out":    0x80000000,  # unused
            "mon_rdma_in":     0x90000000,  # unused
            "mon_rdma_out":    0xA0000000,  # unused
            "sequencer":       0xB0000000,
            "receiver":        0xC0000000,
            "frm_gate":        0xD0000000,
            "Unused_0":        0xE0000000,  # unused
            "Unused_1":        0xF0000000   # unused
        }

        #
        self.image_size_x    = 0x100
        self.image_size_y    = 0x100
        self.image_size_p    = 0x8
        self.image_size_f    = 0x8

        self.pixel_extract   = [16, 13, 12, 11]
        #
        self.delay = 0
        self.strm_mtu = 8000
        self.rdma_mtu = 8000
        #
        self.frame_time = 1

        param_tree_dict = {
            "ip_addr": (self.ip_address, None),
            "port": (self.port, None),
            "setup_camera": (None, self.setup_camera),
            "id": (self.id, None)
        }
        if self.id == 0:
            param_tree_dict["vector_file"] = self.vector_file.param_tree
            param_tree_dict["load_vector_file"] = (None, self.load_vectors_from_file)

        self.param_tree = ParameterTree(param_tree_dict)

    def __del__(self):
        if self.x10g_rdma is not None:
            self.x10g_rdma.close()

    def setup_camera(self, put_string="None"):
        logging.debug("SETTING UP CAMERA")
        self.set_ifg()
        self.x10g_rdma.debug = False
        # self.set_10g_mtu('data', 8000)
        # self.x10g_rdma.read(0x0000000C, '10G_0 MTU')
        # N.B. for scrambled data 10, 11, 12, 13 bit raw=> column size 360, 396
        self.set_10g_mtu('data', 7344)
        self.set_image_size(102, 288, 11, 16)
        #set idelay in 1 of 32 80fs steps  - d1, d0, c1, c0
        self.set_idelay(0,0,0,0)
        # time.sleep(1)
        locked = self.get_idelay_lock_status() != 0
        logging.debug("IDelay Locked: %s", locked)
        # set sub cycle shift register delay in 1 of 8 data clock steps - d1, d0, c1, c0
        # set shift register delay in 1 of 16 divide by 8 clock steps - d1, d0, c1, c0
        #
        # Shift 72 + 144 bits
        self.set_scsr(7,7,7,7)		# sub-cycle (1 bit)
        self.set_ivsr(0,0,27,27)		# cycle (8 bits)
        
        logging.debug("SETTING UP CAMERA: DONE")
    #Rob Halsall Code#
    
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
        self.x10g_rdma.write(self.rmda_addr["udp_10G_data"]+0xF, 0x0, '10G Ctrl reg rdma ifg en, udpchecksum zero en')
        self.x10g_rdma.write(self.rmda_addr["udp_10G_data"]+0xD, 0x3, '10G Ctrl reg rdma ifg value 3 x 8B idle')
        self.x10g_rdma.write(self.rmda_addr["udp_10G_control"]+0xF, 0x0, '10G Ctrl reg rdma ifg en, udpchecksum zero en')
        self.x10g_rdma.write(self.rmda_addr["udp_10G_control"]+0xD, 0x3, '10G Ctrl reg rdma ifg value 3 x 8B idle')

    def stop_sequencer(self):
        self.x10g_rdma.write(self.rmda_addr["sequencer"], 0x0, 'qem seq null')
        # time.sleep(self.delay)
        self.x10g_rdma.write(self.rmda_addr["sequencer"], 0x2, 'qem seq stop')
        # time.sleep(self.delay)
        return

    def start_sequencer(self):
        self.x10g_rdma.write(self.rmda_addr["sequencer"], 0x0, 'qem seq null')
        # time.sleep(self.delay)
        self.x10g_rdma.write(self.rmda_addr["sequencer"], 0x1, 'qem seq stop')
        # time.sleep(self.delay)
        return

    def get_aligner_status(self):
        address = self.rmda_addr["receiver"] | 0x14
        aligner_status = self.x10g_rdma.read(address, 'aligner status word')
        aligner_status_0 = aligner_status & 0xFFFF
        aligner_status_1 = aligner_status >> 16 & 0xFFFF
        
        # time.sleep(self.delay)
        return [aligner_status_1, aligner_status_0]

    def set_idelay(self, data_1=0x00, cdn_1=0x00, data_0=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | cdn_1 << 16 | data_0 << 8 | cdn_0
        address = self.rmda_addr["receiver"] | 0x02
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_idelay word')
        #issue load command
        address = self.rmda_addr["receiver"] | 0x00
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        self.x10g_rdma.write(address, 0x10, 'set delay load high')
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        address = self.rmda_addr["receiver"] | 0x12
        data_cdn_idelay_word = self.x10g_rdma.read(address, 'data_cdn_idelay word')
        return data_cdn_idelay_word

    def set_ivsr(self, data_1=0x00, data_0=0x00, cdn_1=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | data_0 << 16 | cdn_1 << 8 | cdn_0
        address = self.rmda_addr["receiver"] | 0x03
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_ivsr word')
        return

    def set_scsr(self, data_1=0x00, data_0=0x00, cdn_1=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | data_0 << 16 | cdn_1 << 8 | cdn_0
        address = self.rmda_addr["receiver"] | 0x05
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_ivsr word')
        return

    # Working with descrambling logic in place
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
        first_packets = number_bytes // self.strm_mtu
        last_packet_size = number_bytes % self.strm_mtu
        lp_number_bytes_r8 = last_packet_size % 8
        lp_number_bytes_r32 = last_packet_size % 32
        size_status = number_bytes_r4 + number_bytes_r8 + lp_number_bytes_r8 + lp_number_bytes_r32
        # calculate pixel packing settings
        if p_size >= 11 and p_size <= 13:
            pixel_extract = self.pixel_extract.index(p_size)
            pixel_count_max = y_size // 2
        else:
            size_status = size_status + 1

        # set up registers if no size errors
        if size_status != 0:
            logging.debug("Size Error %-8s %-8s %-8s %-8s %-8s %-8s", 'no_bytes', 'no_by_r4', 'no_by_r8', 'no_pkts', 'lp_no_by_r8', 'lp_n0_by_r32' )
            logging.debug("Size Error %8i %8i %8i %8i %8i %8i", number_bytes, number_bytes_r4, number_bytes_r8, first_packets, lp_number_bytes_r8, lp_number_bytes_r32 )
        else:
            address = self.rmda_addr["receiver"] | 0x01
            data = (pixel_count_max & 0x1FFFF) - 1
            self.x10g_rdma.write(address, data, 'pixel count max')
            self.x10g_rdma.write(self.rmda_addr["receiver"] + 4, p_size - 10, 'Pixel size in bits 10,11,12 or 13')
        return

    def get_idelay_lock_status(self):
        if self.x10g_rdma is not None:
            address = self.rmda_addr["receiver"] | 0x13
            data_locked_word = self.x10g_rdma.read(address, 'data_cdn_idelay word')
            data_locked_flag = data_locked_word & 0x00000001
            return data_locked_flag
        else:
            return 0

    # @run_on_executor(executor='thread_executor')
    def load_vectors_from_file(self, vector_file_name=None):

        init_length  = self.vector_file.vector_length
        loop_length  = self.vector_file.vector_loop_position

        self.stop_sequencer()

        # load sequencer RAM
        logging.debug("Loading Sequncer RAM")

        for seq_address, vector_line in enumerate(self.vector_file.vector_data):
            vector_str = "".join(str(x) for x in vector_line)
            vector = int(vector_str, 2)
            lower_vector_word = vector & 0xFFFFFFFF
            upper_vector_word = vector >> 32
            # load fpga block ram
            ram_address = (seq_address * 2) + self.rmda_addr['sequencer'] + 0x01000000
            self.x10g_rdma.write(ram_address, lower_vector_word, 'qem seq ram loop 0')
            # time.sleep(self.delay)
            ram_address = ram_address + 1
            self.x10g_rdma.write(ram_address, upper_vector_word, 'qem seq ram loop 0')
            # time.sleep(self.delay)

        # set loop limit
        self.x10g_rdma.write(self.rmda_addr['sequencer'] + 1, loop_length - 1, 'qem seq loop limit')
        # time.sleep(self.delay)
        # set init limit
        self.x10g_rdma.write(self.rmda_addr['sequencer'] + 2, init_length - 1, 'qem seq init limit')
        # time.sleep(self.delay)
        self.start_sequencer()
        time.sleep(0.1)  # this sleep might have been the missing thing allowing this whole bloody thing to work?
        self.get_aligner_status()
        lock = self.get_idelay_lock_status() != 0
        logging.debug("Idelay Lock status after vector upload: %s", lock)
        return

    def restart_sequencer(self):
        self.stop_sequencer()
        self.start_sequencer()
        return

    def frame_gate_trigger(self):
        self.x10g_rdma.write(self.rmda_addr["frm_gate"], 0x0, 'frame gate trigger off')
        self.x10g_rdma.write(self.rmda_addr["frm_gate"], 0x1, 'frame gate trigger on')
        return

    def frame_gate_settings(self, frame_number, frame_gap):
        self.x10g_rdma.write(self.rmda_addr["frm_gate"] + 1, frame_number, 'frame gate frame number')
        self.x10g_rdma.write(self.rmda_addr["frm_gate"] + 2, frame_gap,    'frame gate frame gap')

    def set_10g_mtu(self, core_num, new_mtu):
        #mtu is set in clock cycles where each clock is 8 bytes -2
        val_mtu = new_mtu // 8 - 2

        if core_num == 'control':
            address = self.rmda_addr["udp_10G_control"]
            self.rdma_mtu = new_mtu
            self.x10g_rdma.UDPMax = new_mtu
        else:
            address = self.rmda_addr["udp_10G_data"]
            self.strm_mtu = new_mtu

        self.x10g_rdma.write(address+0xC, val_mtu, 'set 10G mtu')

    def cleanup(self):
        self.disconnect()
