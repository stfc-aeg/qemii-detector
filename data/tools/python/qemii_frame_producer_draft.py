import dpkt
import struct
import socket
import os
from dpkt.compat import compat_ord
import logging
import time

QEM_SOF = 128 << 24
QEM_EOF = (64 << 24) + 7


class QEMFrame():

    QEM_SOF = 128 << 24
    QEM_EOF = (64 << 24) + 7
    QEM_SUB_FRAMES = 8

    def __init__(self, frame_num):

        
        self.frame_number = frame_num
        self.packets = []   
    
    def get_packets(self):
        return self.packets[]
    
    def append_packet(self, packet):
        self.packets.append(packet)

    def get_num_packets(self):
        return len(self.packets)

class QEMFrameProducer():


    def __init__(self):

        self.frames = []
        self.ip_address = 'localhost'
        self.port = 51501
        self.pcap_file = "/scratch/qem/data.pcap"
        self.tx_interval = 0
        self.log_level = 'info'

        logging.basicConfig(
            level=self.log_level, format='%(levelname)1.1s %(message)s',
            datefmt='%y%m%d %H:%M:%S'
        )

    def run(self):

        self.load_pcap()
        self.send_packets()

    def load_pcap(self):

        f = open(self.pcap_file)

        logging.info(
            "Extracting QEM frame packets from PCAP file %s",
            self.pcap_file
        )

        # Initialise the packet capture file reader
        pcap = dpkt.pcap.Reader(f)
        total_packets = 0
        total_bytes = 0
        frame_number = -1
        
        # Initialise current frame
        current_frame = None

        for timestamp, buffer in pcap:
            
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
            

            if packet_number == QEMFrame.QEM_SOF

                if current_frame is not None: 
                    if current_frame.get_num_packets() != QEM_SUB_FRAMES:
                        #we didn't get a correct number of packets in the last frame before receiving a new SOF.

                        logging.debug(
                            "Received an incorrect number of packets in frame %s",
                            frame_number
                        )

                current_frame = QEMFrame(frame_number)
                frame_number +=1
                #current_frame.append_packet(udp_packet)

            if packet_number == QEMFrame.QEM_EOF:
                #current_frame.append_packet(udp_packet)
                self.frames.append(current_frame)
         
            current_frame.append_packet(udp_packet)

            # Increment total packet and byte count
            total_packets += 1
            total_bytes += data_length

    def send_packets(self):
        # Create the UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if udp_socket is None:
            logging.error("Failed to open UDP socket")
            return

        #get the length of frames

        frames_to_send = len(self.frames)

        for frame in range(frames_to_send):

            current_frame = self.frames[frame]
            
            start_time = time.time()

            for packet in current_frame.packet:


                # Send the packet over the UDP socket
                try:
                    udp_socket.sendto(packet, (self.ip_address, self.port))
                    #frame_packets_sent += 1
                
                except socket.error as exc:
                    logging.error("Got error sending frame packet: %s", exc)
                    break

if __name__ == "__main__":
    QEMFrameProducer().run()