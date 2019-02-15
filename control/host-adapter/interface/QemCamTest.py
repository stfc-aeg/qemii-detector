#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  8 17:38:08 2018

@author: rha73
"""
import time
from QemCam import *

qemcamera = QemCam()

print qemcamera.server_ctrl_ip_addr

qemcamera.connect()

#increase ifg from minimum
qemcamera.set_ifg()

qemcamera.x10g_stream.check_trailer = True

qemcamera.set_clock()

qemcamera.turn_rdma_debug_0n()

qemcamera.set_10g_mtu('data', 7344)
qemcamera.set_image_size_2(102,288,11,16)

print qemcamera.x10g_stream.num_pkt

#set idelay in 1 of 32 80fs steps  - d1, d0, c1, c0
qemcamera.set_idelay(0,0,0,0)

time.sleep(1)

locked = qemcamera.get_idelay_lock_status()

# set sub cycle shift register delay in 1 of 8 data clock steps - d1, d0, c1, c0
qemcamera.set_scsr(7,7,7,7) #was 3,3,7,7

# set shift register delay in 1 of 16 divide by 8 clock steps - d1, d0, c1, c0
qemcamera.set_ivsr(0,0,27,27) #was 0,0,4,4

qemcamera.turn_rdma_debug_0ff()

#qemcamera.set_test_mode()



#qemcamera.load_vectors_from_file('QEM_D4_198.txt')



#qemcamera.load_vectors_from_file('QEM_D1_1010_Init_Loop_1.txt')
#qemcamera.load_vectors_from_file('QEM_D1_1111_Init_Loop_1.txt')

#qemcamera.start_test_mode()

#qemcamera.load_vectors_from_file('QEM_Init_loop_1.txt')
#qemcamera.load_vectors_from_file('QEM_D4_198_Initialisation_Loop.txt')
#qemcamera.load_vectors_from_file('QEM_D4_198_2_Initialisation_Loop.txt')

#qemcamera.restart_sequencer()

time.sleep(0.1)

qemcamera.get_aligner_status()

locked = qemcamera.get_idelay_lock_status()

print "%-32s %-8X" % ('-> idelay locked:', locked)

#qemcamera.frame_gate_settings(0, 0)
#qemcamera.frame_stats()

#qemcamera.log_image_stream('/u/iu42/images/vreset100',100)
#qemcamera.log_image_stream('/u/iu42/test-spot',10000)
#print "Saving images..."
#qemcamera.log_image_stream('/u/iu42/images/adc-aux1V2',10)
qemcamera.display_image_stream(100)

time.sleep(1)

qemcamera.disconnect()

print "\n-> finished:"

