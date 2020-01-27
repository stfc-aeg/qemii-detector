""" QemFem

Sophie Hall, Detector Systems Software Group, STFC. 2019
Ashley Neaves, Detector Systems Software Group, STFC. 2019
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

        self.mac_addresses = [  # TODO: THIS IS VERY TEMPORARY DONT LEAVE THIS HERE IT SHOULD BE IN THE CONFIG FILE
            {
                "ip": "192.168.1.1",
                "mac": [0x3c, 0xfd, 0xfe, 0x9e, 0x9d, 0xb0],
                "offset": 0x08000000,
                "port": 61661
            },
            {
                "ip": "192.168.2.1",
                "mac": [0x3c, 0xfd, 0xfe, 0x9e, 0x9d, 0xb1],
                "offset": 0x0d000000,
                "port": 61662
            },
            {
                "ip": "192.168.3.1",
                "mac": [0x3c, 0xfd, 0xfe, 0x9e, 0x9d, 0xb2],
                "offset": 0x12000000,
                "port": 61663
            },
            {
                "ip": "192.168.4.1",
                "mac": [0x3c, 0xfd, 0xfe, 0x9e, 0x9d, 0xb3],
                "offset": 0x17000000,
                "port": 61664
            },
            {
                "ip": "192.168.5.1",
                "mac": [0x9c, 0x69, 0xb4, 0x60, 0xb8, 0x4c],
                "offset": 0x1c000000,
                "port": 61665
            },
            {
                "ip": "192.168.6.1",
                "mac": [0x9c, 0x69, 0xb4, 0x60, 0xb8, 0x4d],
                "offset": 0x21000000,
                "port": 61666
            },
            {
                "ip": "192.168.7.1",
                "mac": [0x9c, 0x69, 0xb4, 0x60, 0xb8, 0x4e],
                "offset": 0x26000000,
                "port": 61667
            },
            {
                "ip": "192.168.8.1",
                "mac": [0x9c, 0x69, 0xb4, 0x60, 0xb8, 0x4f],
                "offset": 0x2b000000
            }
        ]
        self.rdma_debug = True  # for comparison with rob code
        self.ip_address = ip_address
        self.port = port
        self.id = int(fem_id)
        self.x10g_rdma = None
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

        self.num_data_streams = 6

        # qem 1 base addresses
        self.rdma_addr = {
            "udp_10G_datas":  [0x08000000, 0x0D000000, 0x12000000, 0x17000000, 0x1C000000, 0x21000000, 0x26000000, 0x2B000000, 0x30000000, 0x35000000],
            "udp_10G_data":    0x08000000,
            "udp_10G_control": 0x00000000,
            "frame_gen_0":     0x00000000,  # unused
            "frm_chk_0":       0x00000000,  # unused
            "frm_gen_1":       0x00000000,  # unused
            "frm_chk_1":       0x00000000,  # unused
            "top_reg":         0x03000000,  # unused
            "mon_data_in":    [0x0B000000, 0x10000000, 0x15000000, 0x1A000000, 0x1F000000, 0x24000000],  # unused
            "mon_data_out":    0x0C000000,  # unused
            "mon_rdma_in":     0xC0000000,  # unused
            "mon_rdma_out":    0xC0000000,  # unused
            "sequencer":       0x00000000,
            "receiver":        0x01000000,
            "receiver_phy":    0x01100000,
            "frm_gates":      [0x3A000000, 0x3B000000, 0x3C000000, 0x3D000000, 0x3E000000],
            "frm_gate":        0x3A000000,
            "Unused_0":        0x00000000,  # unused
            "Unused_1":        0x00000000   # unused
        }

        #
        self.image_size_x    = 4160
        self.image_size_y    = 4096
        self.image_size_p    = 8
        self.image_size_f    = 8

        self.pixel_extract   = [16, 13, 12, 11]
        #
        self.delay = 0
        self.strm_mtu = 8192
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
        self.connect()
        self.x10g_rdma.setDebug(self.rdma_debug)
        self.change_to_register_address_mode()
        
        self.set_ctrl_mac_address()
        self.x10g_rdma.close()  # close to clear ack queue
        self.connect()
        
        self.set_fem_mac_addresses()
        self.set_stripes(6)
        self.set_ifg(128)
        self.set_ivsr(0, 10)    # cycle (8 bits)
        self.set_scsr(0, 4)      # sub-cycle (1 bit)
        self.set_global_idelay(7, 15)
        self.set_lvds_polarity()
        self.set_data_source()
        self.set_10g_mtu('data', 8208)
        self.set_image_size(4224, 4104, 11, 16, 4104*11)
        self.release_sequncer_tristate()
        self.start_seq_clk()
        self.release_if_start_tristates()
        self.release_gpio_tristates()

        # time.sleep(1)
        locked = self.get_idelay_lock_status() != 0
        logging.debug("IDelay Locked: %s", locked)

        self.load_vectors_from_file()  # TODO: added here for testing, probs should remove

        
        
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
        self.x10g_rdma.setDebug(self.rdma_debug) #TODO: set to true FOR NOW to compare rob code. change back when done
        self.x10g_rdma.ack = True

    def disconnect(self):
        # should be called on shutdown to close sockets
        self.x10g_rdma.close()

    def set_ifg(self, ifg_val):
        for address in self.rdma_addr['udp_10G_datas']:
            if ifg_val != 0:
                self.x10g_rdma.write(address + 0xF, 0x11, '10G Ctrl reg rdma ifg en, udpchecksum zero en')
                self.x10g_rdma.write(address + 0xD, ifg_val, '10G Ctrl reg rdma ifg value n x 8B idle')
            else:
                self.x10g_rdma.write(address + 0xF, 0x90, '10G Ctrl reg rdma ifg en, udpchecksum zero en')

    def stop_sequencer(self):
        self.x10g_rdma.write(self.rdma_addr["sequencer"], 0x0, 'qem seq null')
        # time.sleep(self.delay)
        self.x10g_rdma.write(self.rdma_addr["sequencer"], 0x2, 'qem seq stop')
        # time.sleep(self.delay)
        return

    def start_sequencer(self):
        self.x10g_rdma.write(self.rdma_addr["sequencer"], 0x0, 'qem seq null')
        # time.sleep(self.delay)
        self.x10g_rdma.write(self.rdma_addr["sequencer"], 0x1, 'qem seq start')
        # time.sleep(self.delay)
        return

    def start_seq_clk(self):
        """Release sequencer pll reset to allow clock to run on active FEMs"""
        self.x10g_rdma.write(self.rdma_addr['top_reg'] + 0xE, 0x0, 'clear sequencer clock reset')
        self.x10g_rdma.write(self.rdma_addr['receiver'] + 0xF, 0x0, 'clear image pipeline clock reset')

    def get_aligner_status(self):
        address = self.rdma_addr["receiver"] | 0x14
        aligner_status = self.x10g_rdma.read(address, 'aligner status word')
        aligner_status_0 = aligner_status & 0xFFFF
        aligner_status_1 = aligner_status >> 16 & 0xFFFF
        # time.sleep(self.delay)
        return [aligner_status_1, aligner_status_0]

    def set_idelay(self, data_1=0x00, cdn_1=0x00, data_0=0x00, cdn_0=0x00):
        data_cdn_word = data_1 << 24 | cdn_1 << 16 | data_0 << 8 | cdn_0
        address = self.rdma_addr["receiver_phy"] | 0x02
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_idelay word')
        #issue load command
        address = self.rdma_addr["receiver"] | 0x0F
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        self.x10g_rdma.write(address, 0x10, 'set delay load high')
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        address = self.rdma_addr["receiver"] | 0x12
        data_cdn_idelay_word = self.x10g_rdma.read(address, 'data_cdn_idelay word')
        return data_cdn_idelay_word

    def set_global_idelay(self, cdn_dly = 0x00, glbl_dly=0x00):
        delay_word = glbl_dly << 24 | glbl_dly << 16 | glbl_dly << 8 | glbl_dly
        cdn_word_0 = (delay_word & 0x00FFFFFF) | cdn_dly << 24
        cdn_word_1 = (delay_word & 0x00FFFFFF) | cdn_dly << 24

        for i in range(33):
            address = self.rdma_addr['receiver_phy'] + i
            if i == 4:
                # set cdn 0 for fem 1/2- currently with wrong register map at position 19
                self.x10g_rdma.write(address, cdn_word_0, 'global idelay cdn word 0')
            elif i == 16:
                # set cdn 1 for fem 3/4- currently with wrong register map at position 67
                self.x10g_rdma.write(address, cdn_word_1, 'global idelay cdn word 1')
            else:
                self.x10g_rdma.write(address, delay_word, 'global idelay delay word')

        address = self.rdma_addr["receiver"] | 0x0F
        self.x10g_rdma.write(address, 0x00, 'set delay load low')
        self.x10g_rdma.write(address, 0x04, 'set delay load high')
        self.x10g_rdma.write(address, 0x00, 'set delay load low')

    def set_ivsr(self, data_0=0x00, cdn_0=0x00):
        """TODO I Don't know what IVSR is"""
        data_cdn_word = data_0 << 16 | cdn_0
        address = self.rdma_addr["receiver"] | 0x03
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_ivsr word')

    def set_scsr(self, data_0=0x00, cdn_0=0x00):
        """TODO I Don't know what SCSR is"""
        data_cdn_word = data_0 << 16 | cdn_0
        address = self.rdma_addr["receiver"] | 0x05
        self.x10g_rdma.write(address, data_cdn_word, 'data_cdn_scsr word')

    def set_lvds_polarity(self):
        """Set the polarity of the LVDS lines. Apparently they are back to front in hardware"""
        polarity_word = 0xFFFFFFFF

        for reg in range(33, 39):
            address = self.rdma_addr['receiver_phy'] + reg
            self.x10g_rdma.write(address, polarity_word, 'lvds polarity word')

    # Working with descrambling logic in place
    def set_image_size(self, x_size, y_size, p_size, f_size, merge_val):
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
            # data = (pixel_count_max & 0x1FFFF) - 1
            self.x10g_rdma.write(self.rdma_addr["receiver"] + 0x4, p_size - 10, 'pixel bit size')
            self.x10g_rdma.write(self.rdma_addr['receiver'] + 0x1, f_size - 1, 'pixel count max')
            self.x10g_rdma.write(self.rdma_addr['receiver'] + 0x6, merge_val - 1, 'merge val')
            self.x10g_rdma.write(self.rdma_addr['receiver'] + 0x8, 0x8000000F, 'Image Scale - bypass top bit, col sf nibble 1, row sf nibble 0')
            self.x10g_rdma.write(self.rdma_addr['receiver'] + 0xA, y_size - 1, 'Receiver frame gate number of rows per image')

    def get_idelay_lock_status(self):
        if self.x10g_rdma is not None:
            address = self.rdma_addr["receiver"] | 0x13
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
        logging.debug("Loading Vector File")
        # self.x10g_rdma.setDebug(False)  # don'r print thousands of lines of RDMA writes...
        for seq_address, vector_line in enumerate(self.vector_file.vector_data):
            self.x10g_rdma.setDebug(False)  # don'r print thousands of lines of RDMA writes...
            vector_str = "".join(str(x) for x in vector_line)
            vector = int(vector_str, 2)
            # lower_vector_word = vector & 0xFFFFFFFF
            # upper_vector_word = vector >> 32

            lower_vector_word = vector >> 28 & 0x0003FFFF
            upper_vector_word = vector >> 46

            # load fpga block ram
            ram_address = (seq_address * 2) + self.rdma_addr['sequencer'] + 0x00100000
            self.x10g_rdma.write(ram_address, lower_vector_word, 'qem seq ram loop 0')
            # time.sleep(self.delay)
            ram_address = ram_address + 1
            self.x10g_rdma.write(ram_address, upper_vector_word, 'qem seq ram loop 0')
            # time.sleep(self.delay)

        # set loop limit
        self.x10g_rdma.write(self.rdma_addr['sequencer'] + 1, loop_length - 1, 'qem seq loop limit')
        # time.sleep(self.delay)
        # set init limit
        self.x10g_rdma.write(self.rdma_addr['sequencer'] + 2, init_length - 1, 'qem seq init limit')
        # time.sleep(self.delay)
        self.x10g_rdma.write(self.rdma_addr['receiver'] + 0xF, 0x1, 'set image pipe line reset')
        self.x10g_rdma.write(self.rdma_addr['receiver'] + 0xF, 0x0, 'clear image pipe line reset')
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
        self.x10g_rdma.write(self.rdma_addr["receiver"] + 0x9, 0x0, 'frame gate trigger off')
        self.x10g_rdma.write(self.rdma_addr["receiver"] + 0x9, 0x1, 'frame gate trigger on')
        return

    def frame_gate_settings(self, frame_number, frame_gap):
        self.x10g_rdma.write(self.rdma_addr["receiver"] + 0xB, frame_number, 'frame gate frame number')
        # self.x10g_rdma.write(self.rdma_addr["frm_gate"] + 2, frame_gap,    'frame gate frame gap')

    def set_10g_mtu(self, core_num, new_mtu):
        #mtu is set in clock cycles where each clock is 8 bytes -2
        val_mtu = new_mtu // 8 - 2

        if core_num == 'control':
            address = self.rdma_addr["udp_10G_control"]
            self.rdma_mtu = new_mtu
            self.x10g_rdma.UDPMax = new_mtu
        else:
            self.strm_mtu = new_mtu
            for index in range(self.num_data_streams):
                addr = self.rdma_addr['udp_10G_datas'][index]
                self.x10g_rdma.write(addr + 0xC, val_mtu, 'set 10G mtu')

    def cleanup(self):
        self.disconnect()

    # STOLEN FROM ADAM

    def set_stripes(self, num_stripes):
        self.num_data_streams = num_stripes

        data = 0
        for index in range(num_stripes):
            chn_index = index % 6
            data += 2**chn_index

        self.x10g_rdma.write(self.rdma_addr['receiver'] + 0xC, data, 'Receiver 10G Channel enable register bits 0..4')

    def set_data_source(self):
        self.x10g_rdma.write(self.rdma_addr['top_reg'] + 0x1, 0x00, 'set 10G data source to image')
        self.x10g_rdma.write(self.rdma_addr['receiver'],0x00, 'set qem2 source to image source 1')

    def release_sequncer_tristate(self):
        self.x10g_rdma.write(self.rdma_addr['top_reg'] + 0x2, 0x0, 'enable sequencer from tristate')

    def release_if_start_tristates(self):
        self.x10g_rdma.write(self.rdma_addr['top_reg'] + 0xC, 0x0, 'enable if_star tristate')

    def release_gpio_tristates(self):
        """enable gpio monitors"""
        self.x10g_rdma.write(self.rdma_addr['top_reg'] + 0xD, 0xF, 'enable gpio clock monitor')

    def change_to_register_address_mode(self):
        """
        MUST do this after power cycle to change the address mode, dy default the mode
        is in ROM mode which is set up for Rob's system in lab and ignores mac addresses in
        the registers.  This function changes bit 15 to '0' rather than '1' - was 0x90

        cannot do a rmw in this case because the response of a read will not get through
        the software stack because the IP / mac address settings are most likely wrong

        After complete, now change the addresses in the appropriate registers
        """
        self.x10g_rdma.write_noack(0x2B00000F, 0x10,'SRC PORT MAC')

    def change_to_ROM_address_mode(self):
        """
        This changes the mode to ROM mode, so will be the defaults set in the ROM which are currently set to the MAC and
        IP settings for Rob Halsall's system in ESDG lab
        """
        self.x10g_rdma.write_noack(0x2B00000F, 0x90,'SRC PORT MAC')

    def set_ctrl_mac_address(self):
        """
        This sets up the registers that control the src.ip address and src.mac addresses in the camera so they will be sent to the correct place.
        """  
        # #construct the register contents
        # reg1=self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["mac"][1] << 24 | self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["mac"][0] << 16 | 0x800
        # self.x10g_rdma.write_noack(self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["offset"]+self.registers["reg1"], reg1, 'SERVER MAC ADDR')

        # #construct the register contents
        # reg2=self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["mac"][5] << 24 | self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["mac"][4] << 16 | self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["mac"][3] << 8 | self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["mac"][2]
        # self.x10g_rdma.write_noack(self.server_ip_mac_addresses["fem1"]["qspi_u13"]["192.168.8.1"]["offset"]+self.registers["reg2"], reg2,'SERVER MAC ADDR')

        mac = self.mac_addresses[7]['mac']
        offset = self.mac_addresses[7]['offset']
        reg_1 = mac[1] << 24 | mac[0] << 16 | 0x08   << 8 | 0x00
        reg_2 = mac[5] << 24 | mac[4] << 16 | mac[3] << 8 | mac[2]

        self.x10g_rdma.write_noack(offset + 1, reg_1, 'CTRL MAC ADDR REG1')
        self.x10g_rdma.write_noack(offset + 2, reg_2, 'CTRL MAC ADDR REG2')
        time.sleep(1)

    def set_fem_mac_addresses(self):
        """
        This function sets the mac address bits to the correct place in the registers on the FEM-II
        """
        # for qspi, qspi_val in self.server_ip_mac_addresses["fem"+str(fem_number)].items():
        #     for ip, ip_val in qspi_val.items():
        #         x=ip.split(".") #split the ip address
        #         reg1=ip_val["mac"][1] << 24 | ip_val["mac"][0] << 16 | int(x[2]) << 8 | 0x000
        #         self.x10g_rdma.write(ip_val["offset"]+self.registers["reg1"], reg1, 'SERVER MAC ADDR')
        #         reg2=ip_val["mac"][5] << 24 | ip_val["mac"][4] << 16 | ip_val["mac"][3] << 8 | ip_val["mac"][2]
        #         self.x10g_rdma.write(ip_val["offset"]+self.registers["reg2"], reg2,'SERVER MAC ADDR')
        # return

        for index, mac_addr in enumerate(self.mac_addresses):
            # for each ip, mac and offset group
            mac = mac_addr['mac']
            offset = mac_addr['offset']
            port = mac_addr.get('port')

            reg_1 = mac[1] << 24 | mac[0] << 16 | index + 1   << 8 | 0x00
            reg_2 = mac[5] << 24 | mac[4] << 16 | mac[3]      << 8 | mac[2]

            self.x10g_rdma.write(offset + 1, reg_1, 'SERVER MAC ADDR REG1')
            self.x10g_rdma.write(offset + 2, reg_2, 'SERVER MAC ADDR REG2')

            # to set port addr, we need to get this reg, because its combined with the udp_length_base
            if port:
                udp_dest_port_base_reg = self.x10g_rdma.read(offset + 9, "READ PORT ADDR BEFORE")
                udp_dest_port_base_reg = udp_dest_port_base_reg & 0xFFFF0000
                port = ((port << 8) & 0xFF00) | port >> 8
                logging.debug("Port Num: %X", port)
                udp_dest_port_base_reg = udp_dest_port_base_reg | port
                logging.debug("REG WITH NEW PORT: %X", udp_dest_port_base_reg)
                self.x10g_rdma.write(offset + 9, udp_dest_port_base_reg, "WRITE NEW PORT ADDR")
                new_reg = self.x10g_rdma.read(offset + 9, "READ PORT ADDR AFTER")
                logging.debug("NEW PORT ADDR REG: %X", new_reg)
