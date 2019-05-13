#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  9 16:53:18 2018

@author: rha73
"""

import socket
import struct
import time
import numpy as np
import logging

class ImageStreamUDP(object):

    def __init__(self, MasterTxUDPIPAddress='192.168.0.1', MasterTxUDPIPPort=65535, MasterRxUDPIPAddress='192.168.0.1', MasterRxUDPIPPort=65536,TargetTxUDPIPAddress='192.168.0.2', TargetTxUDPIPPort=65535, TargetRxUDPIPAddress='192.168.0.2', TargetRxUDPIPPort=65536, RxUDPBuf=1024, UDPMTU=9000, UDPTimeout=10):

        self.txsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rxsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.rxsocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, RxUDPBuf)

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
        self.check_trailer = False
        

        self.ack = False
        
        self.image_size_p = 2
        self.image_size_x = 256  # 256
        self.image_size_y = 256  # 256
        self.image_mtu    = 8000
        self.num_pkt      = (self.image_size_x * self.image_size_y * self.image_size_p ) // self.image_mtu
        
        self.num_pkt = 8  # OVERWRITE FOR DEBUGGING NEW SYSTEM
        self.sensor_image = np.uint8(np.random.rand(self.image_size_x,self.image_size_y)*256)
        self.sensor_image_1d = np.uint8(np.random.rand(self.image_size_x*self.image_size_y)*256)
        
    def __del__(self):
        self.txsocket.close()
        self.rxsocket.close()
        
    def close(self):
        self.txsocket.close()
        self.rxsocket.close()
        
    def set_image_size_8b(self, x_size, y_size, f_size):
        self.image_size_x = x_size
        self.image_size_y = y_size
        self.sensor_image = np.uint8(np.random.rand(x_size,y_size)*256)
        self.sensor_image_1d = np.uint8(np.random.rand(x_size*y_size)*256)
        data_size = x_size * y_size * f_size//8
        self.num_pkt = data_size // self.image_mtu
        data_rem  = data_size % self.image_mtu
        if data_rem != 0: self.num_pkt = self.num_pkt + 1
        
        print x_size, y_size, f_size, self.num_pkt
        
        return
        
    def get_image_8b(self):
        pkt_num = 0
        frm_num = 0
        insert_point = 0
        while pkt_num < self.num_pkt-1:
            #receive packet up to 8K Bytes
            pkt = self.rxsocket.recv(9000)
            #extract trailer
            pkt_len = len(pkt)
            if self.check_trailer == True:
                pkt_top = pkt_len - 8
                frame_number = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                packet_number = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                #pkt_top = 8
                #data2 = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                #data3 = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                # print trailer
                # pkt_str = "%08X  %08X %08X %08X %08X %08X" % (pkt_num, pkt_len, frame_number, packet_number)
                # print pkt_str
            pld_len = pkt_len-8
            #build image
            pkt_array_1d=np.fromstring(pkt, dtype=np.uint8, count=pld_len)
            self.sensor_image_1d[insert_point:insert_point + pld_len] = pkt_array_1d
            insert_point = insert_point + pld_len
            pkt_num = pkt_num + 1
        self.sensor_image = self.sensor_image_1d.reshape(self.image_size_x,self.image_size_y)
        return self.sensor_image
    
    def set_image_size(self, x_size, y_size, f_size):
        self.image_size_x = x_size
        self.image_size_y = y_size
        self.sensor_image = np.uint16(np.random.rand(x_size,y_size)*256)
        self.sensor_image_1d = np.uint16(np.random.rand(x_size*y_size)*256)
        data_size = x_size * y_size * f_size//8
        self.num_pkt = data_size // self.image_mtu
        data_rem  = data_size % self.image_mtu
        if data_rem != 0: self.num_pkt = self.num_pkt + 1
        
        print x_size, y_size, f_size, self.num_pkt
        
        return
    
    def get_image(self):
        pkt_num = 0
        frm_num = 0
        insert_point = 0
        while pkt_num <= self.num_pkt-1:
            #receive packet up to 8K Bytes
            pkt = self.rxsocket.recv(9000)
            #extract trailer
            pkt_len = len(pkt)
            pkt_top = pkt_len - 8
            sof_marker = ord(pkt[pkt_top+7]) & 0x40
            if sof_marker == sof_marker:
                if self.check_trailer == True:
                    frame_number = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                    packet_number = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                    #pkt_top = 8
                    #data2 = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                    #data3 = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                    # print trailer
                    pkt_str = "%08X  %08X %08X %08X" % (pkt_num, pkt_len, frame_number, packet_number)
                    print pkt_str
                pld_len = (pkt_len-8)//2
                #build image
                pkt_array_1d=np.fromstring(pkt, dtype=np.uint16, count=pld_len)
                self.sensor_image_1d[insert_point:insert_point + pld_len] = pkt_array_1d
                insert_point = insert_point + pld_len
                pkt_num = pkt_num + 1
        self.sensor_image = self.sensor_image_1d.reshape(self.image_size_x,self.image_size_y)
        return self.sensor_image
    
    def get_image_set_8b(self, num_images):
        image_array =np.zeros((num_images,self.image_size_x,self.image_size_y), dtype=np.uint8)
        self.sensor_image_1d = np.uint8(np.random.rand(self.image_size_x*self.image_size_y)*256)
        img_num = 0
        while img_num <= num_images-1:
            pkt_num = 1
            insert_point = 0
            while pkt_num <= self.num_pkt-1:
                #receive packet up to 8K Bytes
                pkt = self.rxsocket.recv(9000)
                #extract trailer
                pkt_len = len(pkt)
                if self.debug == True:
                    pkt_top = pkt_len - 8
                    data0 = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                    data1 = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                    pkt_top = 8
                    data2 = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                    data3 = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                    # print trailer
                    pkt_str = "%08X  %08X %08X %08X %08X %08X" % (pkt_num, pkt_len, data0, data1, data2, data3)
                    print pkt_str
                pld_len = pkt_len-8
                #build image
                pkt_array_1d=np.fromstring(pkt, dtype=np.uint8, count=pld_len)
                self.sensor_image_1d[insert_point:insert_point + pld_len] = pkt_array_1d
                insert_point = insert_point + pld_len
                pkt_num = pkt_num + 1
            image_array[img_num] = self.sensor_image_1d.reshape(self.image_size_x,self.image_size_y)
            img_num = img_num + 1
        return image_array

    def get_image_set(self, num_images):
        image_array =np.zeros((num_images,self.image_size_x,self.image_size_y), dtype=np.uint16)
        
        self.sensor_image_1d = np.uint16(np.random.rand(self.image_size_x*self.image_size_y)*256)
        
        img_num = 0
        while img_num <= num_images-1:
            pkt_num = 0
            insert_point = 0
            logging.debug("NUM PKT: %d", self.num_pkt)
            while pkt_num <= self.num_pkt-1:
                
                
                #receive packet up to 8K Bytes
                pkt = self.rxsocket.recv(9000)
                logging.debug("PACKETS RECEIVED. HUZZAH")
                
                #extract trailer
                pkt_len = len(pkt)
                
                if self.check_trailer == True:
                    pkt_top = pkt_len - 8
                    data0 = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                    data1 = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                    pkt_top = 8
                    data2 = (ord(pkt[pkt_top+3]) << 24) + (ord(pkt[pkt_top+2]) << 16) + (ord(pkt[pkt_top+1]) << 8) + ord(pkt[pkt_top+0])
                    data3 = (ord(pkt[pkt_top+7]) << 24) + (ord(pkt[pkt_top+6]) << 16) + (ord(pkt[pkt_top+5]) << 8) + ord(pkt[pkt_top+4])
                    # print trailer
                    pkt_str = "%08X  %08X %08X %08X %08X %08X" % (pkt_num, pkt_len, data0, data1, data2, data3)
                    
                
                pld_len = (pkt_len-8)/2
                #build image
                pkt_array_1d=np.fromstring(pkt, dtype=np.uint16, count=pld_len)
                
                #print img_num, pkt_num, insert_point, pld_len, self.image_size_x, self.image_size_y
                self.sensor_image_1d[insert_point:insert_point + pld_len] = pkt_array_1d
                
                insert_point = insert_point + pld_len
                pkt_num = pkt_num + 1
            image_array[img_num] = self.sensor_image_1d.reshape(self.image_size_x,self.image_size_y)
            img_num = img_num + 1
        
        return image_array