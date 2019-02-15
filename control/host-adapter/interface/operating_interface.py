import os 

class Operating_Interface():
    """ This class handles local operations that need to be completed on the host machine to manipulate vector files and other configuration admin
    """

    def __init__(self, abs_directory="/aeg_sw/work/projects/qem/python/03052018"):
        """
        :param abs_address: The absolute path for the QEM configuration files
        """
        self.abs_directory = abs_directory
        self.txt_files = [] 
        self.adc_vector_files = []
        self.image_vector_files = []

    def get_text_files(self):
        """ Retrieve all of the txt configuration files in the absolute directory path

        Clears the internal lists first to prevent circular appending at every "GET"
        """
        self.clear_lists()
        for file in os.listdir(self.abs_directory):
            if file.endswith('.txt') and "QEM" in file:
                self.txt_files.append(file)

    def get_image_vector_files(self):
        """ gets the image vector files from the list of text files found
        @returns : the image vector files list
        """
        self.get_text_files()
        for file in self.txt_files: 
            if "ADC" not in file:
                self.image_vector_files.append(file)

        return self.image_vector_files

    def get_adc_vector_files(self):
        """ gets the adc vector files from the list of text files found
        @returns : the adc vector files list
        """
        self.get_text_files()
        for file in self.txt_files:
            if "ADC" in file:
                self.adc_vector_files.append(file)
        return self.adc_vector_files
    
    def clear_lists(self):
        """ clears the text file, image and adc vector file lists 
        """        
        self.image_vector_files = []
        self.txt_files = []
        self.adc_vector_files = []
