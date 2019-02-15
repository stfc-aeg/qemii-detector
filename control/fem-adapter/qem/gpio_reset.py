""" GPIOReset class, access to the gpio reset register on the zynq

The GPIOReset class provides functionality to issue commands to the
reset register to reset various componments on the FEM-II e.g. the FPGA

"""

import subprocess

class GPIOReset(object): 

    FPGA_RESET = "0x20"

    def __init__(self, base_address="0x41220000", width="32"):
        self.base_address = base_address
        self.width = width
    
    def reset(self, command):
        """ Sends a command to reset the FPGA on board the FEM
        """
        command = "devmem " + self.base_address + " " + self.width + " " + str(command)        
        reset = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        output, error = reset.communicate()
        

        check = "devmem 0x41210000"
        check_cmd = subprocess.Popen(check, shell=True, stdout=subprocess.PIPE)
        output, error =  check_cmd.communicate()
        fpga_done = int(output.decode("utf8"), 0)
	
        print("trying..")
        while ((fpga_done & 0x00000800) < 1):
            check = "devmem 0x41210000"
            check_cmd = subprocess.Popen(check, shell=True, stdout=subprocess.PIPE)
            output, error =  check_cmd.communicate()
            fpga_done = int(output.decode("utf8"), 0)
            fpga_done = (fpga_done & 0x00000800) 
        print("DONE")
