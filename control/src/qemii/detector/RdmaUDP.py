""" RdmaUDP 

Read/Write control access to FEM-II via UDP.

Rob Halsall 2018, Sophie Kirkham, Application Engineering Group, STFC, 2019.
"""

import socket
import struct
import time
import logging


class RdmaUDP(object):
    def __init__(self, MasterTxUDPIPAddress='192.168.0.1', MasterTxUDPIPPort=65535, 
                 MasterRxUDPIPAddress='192.168.0.1', MasterRxUDPIPPort=65536,
                 TargetTxUDPIPAddress='192.168.0.2', TargetTxUDPIPPort=65535,
                 TargetRxUDPIPAddress='192.168.0.2', TargetRxUDPIPPort=65536, 
                 RxUDPBuf=1024, UDPMTU=9000, UDPTimeout=10):

        self.txsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rxsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rxsocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, RxUDPBuf)
        # set sockets to be reusable to avoid the error when tornado reloads an edited server
        self.rxsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.txsocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.rxsocket.bind((MasterRxUDPIPAddress, MasterRxUDPIPPort))
        self.txsocket.bind((MasterTxUDPIPAddress, MasterTxUDPIPPort))

        #self.rxsocket.settimeout(None)
        #self.txsocket.settimeout(None)

        self.rxsocket.setblocking(1)
        #self.txsocket.setblocking(1)

        self.TgtRxUDPIPAddr = TargetRxUDPIPAddress
        self.TgtRxUDPIPPrt  = TargetRxUDPIPPort
        self.UDPMaxRx = UDPMTU
        self.debug = False
        self.ack = False

    def __del__(self):
        self.close()

    def read(self, address, comment=''):
        """ Read 64 bits from the address.

        Sends a read commend to the target rx UDP address/port and returns the result.
        @param address: the address to read from
        @param comment: comment to print out 
        """
        command = struct.pack('=BBBBIQBBBBIQQQQQ', 1,0,0,3, address, 0, 9,0,0,255, 0, 0,0,0,0,0)
        self.txsocket.sendto(command,(self.TgtRxUDPIPAddr,self.TgtRxUDPIPPrt))

        if self.ack:
            response = self.rxsocket.recv(self.UDPMaxRx)
            data = 0x00000000
            if len(response) == 56:
                decoded = struct.unpack('=IIIIQQQQQ', response)
                data = decoded[3]
                #print decoded

        if self.debug:
            logging.debug('R %08X : %08X %s', address, data, comment)
        print("Data: {}".format(data))
        return data

    def write(self, address, data, comment=''):

        if self.debug:
            logging.debug('W %08X : %08X %s', address, data, comment)

        #create single write command + 5 data cycle nop command for paddings
        command = struct.pack('=BBBBIQBBBBIQQQQQ', 1,0,0,2, address, data, 9,0,0,255,0, 0,0,0,0,0)

        #Send the single write command packet
        self.txsocket.sendto(command,(self.TgtRxUDPIPAddr,self.TgtRxUDPIPPrt))

        # TODO: this bit doesn't seem to do anything so I commented it out - Adam 30/09/19
        # if self.ack:
        #     #receive acknowledge packet
        #     response = self.rxsocket.recv(self.UDPMaxRx)
        #     #time.sleep(10)
        #     if len(response) == 48:
        #         decoded = struct.unpack('=IIIIQQQQ', response)
        #         #print decoded

        # return

    def close(self):
        self.txsocket.close()
        self.rxsocket.close()

        return

    def setDebug(self, enabled=True):
        self.debug = enabled

        return