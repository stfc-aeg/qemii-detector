"""Packet Reordering Proxy

Reorders the packet structure for QEM, moving the trailer of QEM to a header
to simulate the stucture of QEMII packets.

Adam Neaves, Application Engineering Group, STFC. 2019
"""

import socket
import argparse
import logging


class PacketReorderer():

    def __init__(self):
        self.defaults = PacketReordererDefaults()  # get default values

        parser = argparse.ArgumentParser(description="QEM Packet Reorder Proxy")

        parser.add_argument(
            '--saddr', type=str, dest='source_addr',
            default=self.defaults.source_addr,
            help="Address of the packet Source"
        )
        parser.add_argument(
            '--sport', type=int, dest='source_port',
            default=self.defaults.source_port,
            help="Port of the packet Source"
        )
        parser.add_argument(
            '--daddr', type=str, dest='dest_addr',
            default=self.defaults.dest_addr,
            help="Address of the packet destination"
        )
        parser.add_argument(
            '--dport', type=int, dest='dest_port',
            default=self.defaults.dest_port,
            help="Address of the packet destination"
        )
        parser.add_argument(
            '--logging', type=str, dest='logging',
            default=self.defaults.logging,
            help="Level of Logging required"
        )
        self.args = parser.parse_args()
        
        logging.basicConfig(
            level=logging._levelNames[self.args.logging], format='%(levelname)1.1s %(message)s',
            datefmt='%y%m%d %H:%M:%S'
        )
        self.source_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dest_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.debug("Connecting socket to %s:%d", self.args.source_addr, self.args.source_port)
        self.source_socket.bind((self.args.source_addr, self.args.source_port))
        logging.debug("Running loop:")
        
        self.process_loop()

        self.source_socket.close()
        self.dest_socket.close()

    def process_loop(self):
        
        while True:
            data, addr = self.source_socket.recvfrom(10000)  # buffer size needs to be bigger than packet size
            data_array = bytearray(data)
            logging.debug("Data Size: %d", len(data_array))
            logging.debug("Data Source: %s", addr)
            header = data_array[-8:]  # get last 8 bytes of data
            logging.debug("HEADER: %s", ''.join('{:02X}'.format(x) for x in header))
            header.extend(data_array[:-8])
            logging.debug("New Data Size: %d", len(header))
            self.dest_socket.sendto(header, (self.args.dest_addr, self.args.dest_port))


class PacketReordererDefaults():

    def __init__(self):

        self.source_addr = "10.0.2.2"
        self.source_port = 61651

        self.dest_addr = "127.0.0.1"
        self.dest_port = 61660

        self.logging = "WARNING"

        self.logging_levels = logging._levelNames
        

if __name__ == "__main__":
    order = PacketReorderer()
