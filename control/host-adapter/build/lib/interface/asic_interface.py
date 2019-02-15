import time
import cv2
from QemCam import *

class ASIC_Interface():
    """ This class handles communication with the QEM ASIC through use of the QemCam module"""
    def __init__(self):
        self.imageStore = []
        """ Set up the ASIC as per QemCamTest """
        #Set up QEM sensor/camera
        self.qemcamera = QemCam()
        self.image = "image1"
        self.qemcamera.connect()
        #increase ifg from minimum
        self.qemcamera.set_ifg()
        self.qemcamera.x10g_stream.check_trailer = True
        self.qemcamera.turn_rdma_debug_0n()
        self.qemcamera.set_10g_mtu('data', 7344)
        self.qemcamera.set_image_size_2(102,288,11,16)
        #set idelay in 1 of 32 80fs steps  - d1, d0, c1, c0
        self.qemcamera.set_idelay(0,0,0,0)
        time.sleep(1)
        # set sub cycle shift register delay in 1 of 8 data clock steps - d1, d0, c1, c0
        self.qemcamera.set_scsr(7,7,7,7)
        # set shift register delay in 1 of 16 divide by 8 clock steps - d1, d0, c1, c0
        self.qemcamera.set_ivsr(0,0,27,27)
        self.qemcamera.turn_rdma_debug_0ff()

    def get_image(self):
        if len(self.imageStore) >0:
            img = self.imageStore.pop(0)
            cv2.imwrite('static/img/temp_image.png', img)
        return len(self.imageStore)

    def set_image_capture(self, value):
        self.imageStore = self.qemcamera.display_image_stream_web(value)

    def get_capture_run(self):
        return u'/aeg_sw/work/projects/qem/images/'

    def set_capture_run(self, config):
        fnumber, file_name = config.split(";")
        location = "/aeg_sw/work/projects/qem/images/" + str(file_name)
        self.qemcamera.log_image_stream(location, int(fnumber))

    def get_dac_value(self, dac):
        return u'000000'

    def set_dac_value(self, dac, value):
        pass
