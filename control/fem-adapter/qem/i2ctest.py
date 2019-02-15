#!/usr/bin/env python2

import smbus
import time as t

#define coarse and fine addresses
coarse = 0x2f
fine = 0x2e
address=coarse

bus=smbus.SMBus(1) # number defines the bus number
bus.write_byte_data(address, 0x1C, 0x02) # enable update of the wiper position



i=0
n=0
UP_DOWNn = 1
while n < 100:
    bus.write_byte_data(address, 0x04^((i&0x300)>>8), i)
    #now read the wiper register
    #bus.write_byte_data(address, 0x08, 0x00)
    #dat= bus.read_word_data(address,0x0)
    #print (hex(((dat&0x3)<< 8) + ((dat&0xFF00) >> 8)))
    #t.sleep(0.05)
    
    if UP_DOWNn == 1:
	i+=1
    else:
	i= i-1

    if i == 1024:
	UP_DOWNn = 0
	n+=1
	#print("DOWN")
    
    if i == 0 :
	UP_DOWNn = 1
	#print("UP")


