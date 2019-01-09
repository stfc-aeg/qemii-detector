import dpkt
import struct
import socket
import random
import os
from dpkt.compat import compat_ord
import logging
import time
import argparse

QEM_SOF = 128 << 24
QEM_EOF = (64 << 24) + 7

class QEMFrame():
    """ Class to represent one QEM Frame, holding 8 packets of UDP data.
    """
    QEM_SOF = 128 << 24  #start of frame marker
    QEM_EOF = (64 << 24) + 7 #end of frame marker
    QEM_SUB_FRAMES = 8 #number of packets in one frame

    def __init__(self, frame_num):

        self.frame_number = frame_num
        self.packets = []   
    
    def get_packets(self):
        #returns the packets inside the frame
        return self.packets
    
    def append_packet(self, packet):
        """ Appends the given packet to the list of packets
        @param packet: The UDP packet to append.
        """
        self.packets.append(packet)

    def get_num_packets(self):
        """ Returns the number of packets in the given frame
        @returns : the length of the packets list.
        """
        return len(self.packets)


class QEMFrameProducerDefaults():
    """ Class to hold default values for the QEM-II
    Frame Producer parameters.
    """

    def __init__(self):

        self.ip_address = 'localhost'
        self.port = '51501'
        self.num_frames = 0
        self.tx_interval = 0
        self.drop_list = None
        self.drop_frac = 0
        self.log_level = logging.INFO
        self.pcap_file = "/scratch/qem/data.pcap"


def min_max(value):
    """ Checks whether value is between 0.0 - 1.0 (inclusive)
    @throws ArgumentTypeError: if the value is outside the given range.
    @param value: Cmd line value passed to the QEM-II Frame producer tool.
    @returns fvalue: Floating point cast version of value.
    """

    fvalue = float(value)
    if (0.0 <= fvalue <= 1.0):
        pass
    else:
        raise argparse.ArgumentTypeError("%s is an invalid value, values can be 0.0 - 1.0" % value)
    return fvalue
    
class QEMFrameProducer():


    def __init__(self):

        self.frames = []
        self.defaults = QEMFrameProducerDefaults() #initialise default values

        parser = argparse.ArgumentParser(description="QEM-II Frame Producer")

        parser.add_argument(
            'pcap_file', type=argparse.FileType('rb'),
            default= self.defaults.pcap_file, 
            help="Packet capture file to load."
        )
        parser.add_argument(
            '--address', '-a', type=str, dest='ip_address',
            default=self.defaults.ip_address,
            help='IP address to send the UDP packets to'
        )
        parser.add_argument(
            '--port', '-p', type=int, dest='port',
            default=self.defaults.port,
            help='Port number to send the UDP packets to'
        )
        parser.add_argument(
            '--frames', '-n', type=int, dest='num_frames',
            default=self.defaults.num_frames, metavar='FRAMES',
            help='Number of frames to transmit (0 = send all frames found in packet capture file'
        )
        parser.add_argument(
            '--interval', '-i', type=float, dest='tx_interval',
            default=self.defaults.tx_interval, metavar='INTERVAL',
            help='Interval in seconds between transmission of frames'
        )
     
        parser.add_argument(
            '--drop_frac', type=min_max, dest='drop_frac',
            default=self.defaults.drop_frac, metavar='FRACTION',
            help='Fraction of packets to drop'
        )
      
        parser.add_argument(
            '--drop_list', type=int, nargs='+', dest='drop_list',
            default=self.defaults.drop_list,
            help='Packet number(s) to drop from each frame',
        )
        parser.add_argument(
            '--logging', type=str, dest='log_level',
            default=self.defaults.log_level,
            help='Set logging output level'
        )

        self.args = parser.parse_args()

        #configure logging 
        logging.basicConfig(
            level=self.defaults.log_level, format='%(levelname)1.1s %(message)s',
            datefmt='%y%m%d %H:%M:%S'
        )

        #parse the pcap file.
        self.pcap = dpkt.pcap.Reader(self.args.pcap_file)

    def run(self):
        """ Run the QEM Frame Producer, calls load_pcap and send_packets
        """
        self.load_pcap()
        self.send_packets()

    def load_pcap(self):
        """ Extracts the UDP packet data from the PCAP file.
        Moves the trailer to a header, reforming the UDP packets. 
        Packages each 8 packets in QEM-II Frames and stores in 
        self.frames.
        """

        logging.info(
            "Extracting QEM frame packets from PCAP file %s",
            self.args.pcap_file
        )

        total_packets = 0
        total_bytes = 0
        frame_number = -1
        
        # Initialise current frame
        current_frame = None

        for timestamp, buffer in self.pcap:
            
            ethernet_layer = dpkt.ethernet.Ethernet(buffer)
            ip_layer = ethernet_layer.data
            udp_layer = ip_layer.data
            data_length = len(udp_layer.data)
            raw_trailer = udp_layer.data[data_length-8:]

            frame_number, packet_number = struct.unpack("<II", udp_layer.data[data_length-8:])
            trailer = struct.unpack("<II", udp_layer.data[data_length-8:])
            
            stripped_udp_packet = udp_layer.data[:data_length-8]
            header  = struct.pack("<II", frame_number, packet_number)
            udp_packet = header + stripped_udp_packet
            
            # if we have a SOF maker, create a new QEM Frame
            if packet_number == QEMFrame.QEM_SOF:

                if current_frame is not None: 
                    if current_frame.get_num_packets() != QEMFrame.QEM_SUB_FRAMES:
                        #we didn't get a correct number of packets in the last frame before receiving a new SOF.

                        logging.debug(
                            "Received an incorrect number of packets in frame %s",
                            frame_number
                        )
                # create a new QEM Frame
                current_frame = QEMFrame(frame_number)
                frame_number +=1
          
            # check whether we got an EOF marker, if so add the frame to the list
            if packet_number == QEMFrame.QEM_EOF:
                self.frames.append(current_frame)

            #append the packe to the current frame
            current_frame.append_packet(udp_packet)

            # Increment total packet and byte count
            total_packets += 1
            total_bytes += data_length

        #print len(self.frames)

    def send_packets(self):
        """ Send the QEM Frames over UDP
        """
        # Create the UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if udp_socket is None:
            logging.error("Failed to open UDP socket")
            return

        #get the length of frames to send
        if self.args.num_frames == 0:
            frames_to_send = len(self.frames)
        else:
            frames_to_send = self.args.num_frames

        total_bytes_sent = 0
        total_frames_sent = 0
        total_packets_sent = 0
        total_packets_dropped = 0

        logging.info(
            "Sending %d frames to destination %s:%d", frames_to_send, self.args.ip_address, self.args.port
        )

        # iterate over every frame
        for frame in range(frames_to_send):

            current_frame = self.frames[frame]
            start_time = time.time()
            frame_pkts_dropped = 0

            # iterate over the packets in the given frame
            for packet_id, packet in enumerate(current_frame.packets):
                
                # If a drop fraction option was specified, decide if the packet should be dropped
                if self.args.drop_frac > 0.0:
                    if random.uniform(0.0, 1.0) < self.args.drop_frac:
                        frame_pkts_dropped += 1
                        continue

                # if there is a drop list and pkt is in it - drop the pkt.
                if self.args.drop_list is not None: 
                    if packet_id in self.args.drop_list:
                        frame_pkts_dropped += 1
                        continue

                # Send the packet over the UDP socket
                try:
                    total_bytes_sent += udp_socket.sendto(packet, (self.args.ip_address, self.args.port))
                    total_packets_sent += 1
                    #PACKET GAP GOES HERE
                
                except socket.error as exc:
                    logging.error("Got error sending frame packet: %s", exc)
                    break

            total_frames_sent += 1
            total_packets_dropped += frame_pkts_dropped

            # add a pause if a tx interval has been provided.
            end_time = time.time()
            wait_time = (start_time + self.args.tx_interval) - end_time
            if wait_time > 0:
                time.sleep(wait_time)


        udp_socket.close()
        logging.info(
            "sent %d bytes, %d frames and %d packets. Dropped %d packets", 
            total_bytes_sent, total_frames_sent, total_packets_sent, total_packets_dropped
        )

if __name__ == "__main__":
    QEMFrameProducer().run()