import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

class vectorfile:
    """This class initialises variables and methods to allow the manipulation of the 
    QEM Vector file format.  It allows the user to change DAC settings and plot the
    vector file much like a logic analyser would
    """

    def __init__(self, filename):
        #variables used for basic vector file manipulation
        self.FileName = filename
        self.VectorLength = int(83000)
        self.VectorLoopPosition = int(82000)
        self.VectorNames = []
        self.VectorData=()
        #variables below are used for DAC value manipulation
        self.DacClockReference = []
        self.DacDataVector = []
        self.DacNewDataVector = []
        #the folliowng two may not be necessary, these are used for DAC manipulation
        self.VectorFileTxt = []
        self.NewFile = ""

        #Signals below used for plotting the file as a graph (ie: logic analyser)
        self.NumberOfSignalsToPlot = 20
        self.StartPlottingSignalsFromHere = 30
        self.LengthOfPlot = 1000
        self.StartPlotFromHere = 0
        self.EnableDisplayPlot = "True"
        self.PlotFileName = "./MY_PLOT.png"
        self.vectorfile = vectorfile

        #might run this automatically to extract data from file - yep it appears I am
        self.CheckItIsAFilename(self.FileName)
        self.GetVectorInformation()

        self.bias_dict = {}
        self.bias_names = ["iBiasPLL",# 010100
                            "iBiasLVDS",# 101101
                            "iBiasAmpLVDS",# 010000
                            "iBiasADC2",# 010100
                            "iBiasADC1",# 010100
                            "iBiasCalF",#  010010
                            "iFbiasN",#  011000
                            "vBiasCasc",#  100000
                            "iCbiasP",#  011010
                            "iBiasRef",#  001010
                            "iBiasCalC",#  001100
                            "iBiasADCbuffer",#  001100
                            "iBiasLoad",#  010100
                            "iBiasOutSF",#  011001
                            "iBiasSF1",#  001010
                            "iBiasPGA",#  001100
                            "vBiasPGA",#  000000
                            "iBiasSF0",#  000101
                            "iBiasCol"]#  001100

        self.init_bias_dict()

    def init_bias_dict(self):
        """ initialises the bias_dict holding the bias settings 
            for each 19 dac's along with their index and name.
        """

        for i in range(19):
            self.bias_dict[self.bias_names[18-i]] = [i+1, '000000']   


    def CheckItIsAFilename(self, filename):
        """This method cheks to see if the filename
        being used exists, if not it exits cleanly from
        the code
        """

        try:
            f=open(filename, "r")
            f.close()
            return filename
        except FileNotFoundError:
            print("CheckItsAFilename: File does not exist")
            sys.exit()
        

    ## these function definitions are for basic file fucntions
    def ChangeFileName(self, filename):
        """Changes: self.Filename
        Calls:GetVectorInformation()
        This method allows the user to change the referenced
        vector file name, then it extracts the vector file
        information from the new file by calling the function GetVectorInformation()
        """

        self.FileName = self.CheckItIsAFilename(filename)
        self.GetVectorInformation()

    def GetVectorInformation(self):
        """Changes: self.VectorLoopPositon, self.vectorLength, self.vectorFileNames
        Calls:DacExtractClockReferences()
        Dependances:ChangeFileName(), __init__()
        This method extracts the information from the vector file, information such
        as loop position, vector length and vector data, it also called the function
        to extract DAC clock references and value at these clock edges
        """

        f = open(self.FileName, "r")
        #extract the first three lines
        self.VectorLoopPosition=f.readline()
        self.VectorLength=f.readline()
        self.VectorNames=f.readline().split()

        #print the data extracted
        #print("loop position = %s" %loopposition)
        #print("Vector file length = %s" %vectorfilelength)
        #print("Signal names = %s" %vectorsignalnames)

        #read the rest of the file into the list variable
        self.VectorFileTxt=f.read()
        #print(listDATA[0:222])
        f.close()
        #split the list to make first dimention
        listDATA_s=self.VectorFileTxt.split()
        #print(listDATA_s[0:2])

        #try the following
        #for i in range(len(listDATA_s)):
        #    lst[i] = [x for x in listDATA_s[i]]

        lst=[]
        for i in range(len(listDATA_s)):
            line = list(listDATA_s[i])
            lst.append(line)

        #convet this list of lists into an array - this works!!!
        self.VectorData = np.asarray(lst, dtype=np.uint8)
        #print(npa.shape)
        #print(npa[0:5,2])

        #data = np.loadtxt("QEM_D4_396_images_aSpectBias_AUXRSTsampled_A_DCbuf_05_iCbias_13.txt",skiprows=3,dtype='bool')
        #data.shape

        #print(data[0])

        f.close()
        self.DacExtractClockReferences()

    #this function updates the vector file with the new settings
    def DacUpdateVectorFile(self, filename="NULL"):
        """Changes: output filename (if provided)
        Dependancies: GetVectorInformation(), Vector file input, DacNewDataVector[]
        This method saves the updated vector file.  If no variable has been passed, it will
        save it as the same name with _mod.txt appended on the end of the filename
        """
        
        if str(filename) == "NULL":
            f=open("%s_mod.txt" %self.FileName, 'w') 
        else: 
            f=open("%s" %filename, 'w')
        
        

        #write the first three lines, don't change!!
        f.write(self.VectorLoopPosition)
        f.write(self.VectorLength) #
        f.write("\t".join(self.VectorNames))
        f.write("\r\n")# add a carridge return, line feed

        k=len(self.DacNewDataVector) # assign k to the length of the new data array
        j=0   		# number used to increment through the new_data array
        m=0   		# number that increments by o after changing the lines
        n=5  		# change number of lines before -ve clock edge
        p=3  		# number of lines to change from to new value after the -ve clock edge
        o=n+1+p  	# total number of lines to change from 'n' to new value, default is 1 extra + p

        for i in range((int(self.VectorLength))-(k*(o-1))):
            if (j < k) : 			# if array increment value of new data is less than k (length of new data) do this, else just write the line to file
                if((i+m+n) == self.DacClockReference[j]):  # looking forward by n, if the line number is equal to the first elemnt of array do this, else just write data to the file
                    for l in range(o):	        # do this for the next 'o' number of lines
                        line = self.VectorFileTxt[(i+m+l)*65:65+((i+m+l)*65)]  # extract line from origional file
                        f.write(line[0:43]) 	# write up to the reference point
                        f.write(str(self.DacNewDataVector[j])) # add new data from the file
                        f.write(line[44:]) 	# add the rest of the origional line
                    j=j+1
                    m=m+(o-1)
                else:	
                    f.write(self.VectorFileTxt[(i+m)*65:65+((i+m)*65)])
            else:	
                f.write(self.VectorFileTxt[(i+m)*65:65+((i+m)*65)])
        f.close()
        print("\nNew file has been created, check folder")


    #this function updates a value in the DacNewDataVector variable
    def DacNewDacSetting(self, register, value):
        """Changes: self.DacNewDataVector
        Dependancies: GetVectorInformation(), Vector file input, DacNewDataVector[]
        This method allows the user to mofify a specific DAC register.  This assumes the user knows what register number referrs
        to what DAC name
        """
        
        for i in range(6):
            self.DacNewDataVector[((register-1)*6)+i]=np.uint8(value[i])
            self.DacNewDataVector[(((register-1)+19)*6)+i]=np.uint8(value[i])
    
    
    #this function prints the current NEW DAC settings
    def DacPrintDacNewDataVector(self):
        """Dependancies: GetVectorInformation(), Vector file input, DacNewDataVector[]
        This prints the new DAC information that has been changed so that you can see what is going to change.  Run DacUpdateVectorFile
        once you are happy with the new settings
        """

        for i in range(19):
            print("%s%-10i %s%s%s%s%s%-4s %s%s%s%s%s%s" % ("register" ,i+1 ,self.DacNewDataVector[i*6 + 0],self.DacNewDataVector[i*6 + 1],self.DacNewDataVector[i*6 + 2],self.DacNewDataVector[i*6 + 3],self.DacNewDataVector[i*6 + 4],self.DacNewDataVector[i*6 + 5],self.DacNewDataVector[i*6 + 114],self.DacNewDataVector[i*6 +115],self.DacNewDataVector[i*6 + 116],self.DacNewDataVector[i*6 + 117],self.DacNewDataVector[i*6 + 118],self.DacNewDataVector[(i*6) + 119]))


    def DacPrintDacDataVector(self):
        """Dependancies: GetVectorInformation(), Vector file input
        This function prints the current DAC settings in the loaded file
        """

        for i in range(19):
            print("%s%-10i %s%s%s%s%s%-4s %s%s%s%s%s%s" % ("register" ,i+1 ,self.DacDataVector[i*6 + 0],self.DacDataVector[i*6 + 1],self.DacDataVector[i*6 + 2],self.DacDataVector[i*6 + 3],self.DacDataVector[i*6 + 4],self.DacDataVector[i*6 + 5],self.DacDataVector[i*6 + 114],self.DacDataVector[i*6 +115],self.DacDataVector[i*6 + 116],self.DacDataVector[i*6 + 117],self.DacDataVector[i*6 + 118],self.DacDataVector[(i*6) + 119]))

    
    def DacExtractClockReferences(self):
        """Changes:self.DacClockReference, self.DacDataVector
        Dependances:GetVectorInformation(), Vectorfile input
        This functinn extracts the -ve clock positions and makes a list of them (DacClockReference).
        This also extracts the value associated with the -ve clock positon and makes a list of them (DacDataVector)
        """

        latch = '1'

        #find how many -ve clock edges and create a list of references
        for i in range(len(self.VectorData)):
            y = self.VectorData[i,41] #this is 41 (dacCLKin)
            if y == 0:
                if latch == '0':
                    self.DacClockReference.append(i)
                    self.DacDataVector.append(self.VectorData[i,43]) # this is 43 (dacDin)
                    latch = '1'
            else :
                latch = '0'
        
        self.DacNewDataVector = self.DacDataVector


#did put below in a seperate class but not now

##################################################################################
##################################################################################
##################################################################################
##################################################################################

    
    def CheckItIsANumber(self, number):
        """Checks to see if what has been passed is a number and exits cleanly if not
        """

        try:
            val = int(number)
            return val
        except ValueError:
            print("CheckItIsANumber: Number passed is not of type int")
            sys.exit()
    
    def CheckItIsABool(self, enable):
        """This checks to see if what is passed is in fact a bool and exists cleanly if not.
        This is not currently used
        """

        return enable
    

##################################################################################
##################################################################################
##################################################################################
##################################################################################


    #these functions for used for plotting
    def PlotChangeFileName(self, filename):
        """Changes: self.PlotFileName
        This changes the output file name if this is enabled
        """

        self.PlotFileName = filename

    def PlotEnableShowPlot(self):
        """Changes: self.EnableDisplayPlot
        This changes the status of the variable that is used to either display the plot or save it
        """

        self.EnableDisplayPlot = "True"
    
    def PlotDisableShowPlot(self):
        """Changes: self.EnableDisplayPlot
        This changes the status of the variable that is used to either display the plot or save it
        """

        self.EnableDisplayPlot = "False"

    def PlotChangeStartPlotFromHere(self, number):
        """Changes: self.StartPlotFromHere
        This method changes the plot position in terms of time.  This 'should' be constrained
        to the total length -1000 so that it doesn't get in a tiz but it isn't at the moment
        """

        self.StartPlotFromHere = self.CheckItIsANumber(number)

    def PlotChangeLengthOfPlot(self, number):
        """Changes: self.LengthOfPlot
        This changes the total length of the plot (time x axis).  The greater the number here
        the more information is plotted and less detail
        """

        self.LengthOfPlot = self.CheckItIsANumber(number)

    def PlotChangeStartPlottingSignalPosition(self, number):
        """Changes: self.StartPlottingSignalsFromHere
        This changes which signal the plots start from
        """

        self.StartPlottingSignalsFromHere = self.CheckItIsANumber(number)


    def PlotChangeNumberOfSignals(self, number):
        """Changes: self.NumberOfSignalsToPlot
        This changes the number of signals that are plotted on the graph
        """

        self.NumberOfSignalsToPlot = self.CheckItIsANumber(number)

    def PlotVectorFile(self):
        """Changes: generates a graph / plots it or saves a file
        Based on the settings, this will plot a graph.  depending on self.EnableDisplayPlot variable
        it will either display or save a file
        """

        signals = self.NumberOfSignalsToPlot
        start= self.StartPlottingSignalsFromHere
        length = self.LengthOfPlot
        tstart= self.StartPlotFromHere
        fig, ax = plt.subplots(nrows=signals, ncols=2, figsize=(15,3), gridspec_kw = {'width_ratios':[1, 30]})
        #removed sharex='col'
        #gs = gridspec.GridSpec(signals, 2, width_ratios=[1, 3])
        #fig.patch.set_visible(False)

        #create a vector of x-values
        xvector=list(range(tstart,tstart+length))
        majorLocator = MultipleLocator(100)

        #print(xvector)
        #print(len(xvector))
        for i in range(len(ax)):
                
            #left column configuration
            #add the signal names
            ax[i][0].text(0,0, "(%d)%s" %(start+i,self.VectorNames[start+i]))
            #remove axis
            ax[i][0].axis("off")
                
            #Right column configuration
            #plot data
            ax[i][1].plot(xvector,self.VectorData[tstart:tstart+length,start+i])
                
            #configure appearance
            if i < len(ax)-1:
                ax[i][1].axis("off")
            else:
                ax[i][1].axis(ymin=0, ymax=1)
                ax[i][1].tick_params(top=0, bottom=0, left=0, right=0, labelleft=0, labelbottom=1, labelrotation=90)
                #remove frame
                #ax.[i][1].
                #ax[i][1].frame(show='False')
                #ax[i][1].spines.cla()
                #ax[i][1].spines["top"].set_visible('False')
                ax[i][1].set_frame_on(0)
                ax[i][1].xaxis.set_major_locator(majorLocator)
                #ax[i][1].spines["right"].set_visible('False')
                #ax[i][1].spines["bottom"].set_visible('False')

        #plt.subplots_adjust(hspace=1.5)
        #fig.subplots_adjust(top = 0.99, bottom=0.01, hspace=1.5, wspace=0.4)
        #seaborn.despine(left=True, bottom=True, right=True)
        fig.suptitle('Vector file plots between %d(%s) and %d(%s)' %(start, self.VectorNames[start], start+signals, self.VectorNames[start+signals]))
        #this needs to be changed to save the file as a png for when it is used in the final system

        if self.EnableDisplayPlot == "True":
            plt.show()
        else:
            plt.savefig(self.PlotFileName)
            
        #except TypeError:
        #print("PlotVectorFile: There is a problem, seems you need to look at the above error")
        #sys.exit()
        

def main():
    #the following show how to use the various methods for the class in here.  just specify the following two variables for this
    #to work properly
    #this is an input vector file of the correct format (existing file)
    test_vector_file = "QemNoiseAnalysis/QEM_D4_396_images_aSpectBias_AUXRSTsampled_A_DCbuf_05_iCbias_13.txt"
    
    #this is a file that does not exist yet (or it does as it will overwrite).  If not specified, will use same filename with _mod.txt at the end
    new_vector_file = "QemNoiseAnalysis/QEM_D4_396_images_aSpectBias_AUXRSTsampled_A_DCbuf_05_iCbias_13_MOD.txt"
    
    #begin with creating a new variable of type QemVectorFileAnalysis, passing the filename as specified above
    a = vectorfile(test_vector_file)

    # *********************************************************************

    #when the above is defined, it will trigger the extraction of information from the file so we can print this straight away
    print(a.VectorNames)
    print(a.VectorLength)
    print(a.VectorLoopPosition)
    print(a.VectorData.shape)

    # *********************************************************************
    
    #you can plot the Vectors straight away, default is 10 signals, window size is 1000, starting from 30
    a.PlotVectorFile()
    
    #Change the number of signals to plot and re-plot
    a.PlotChangeNumberOfSignals(7)
    a.PlotVectorFile()

    #change the plot signal position and re-plot
    a.PlotChangeStartPlottingSignalPosition(40)
    a.PlotVectorFile()

    #change the position from were the plot starts from
    a.PlotChangeStartPlotFromHere(1000)
    a.PlotVectorFile()

    #change the window width to plot and re-plot
    a.PlotChangeLengthOfPlot(2000) 
    a.PlotVectorFile()

    #change that you are not going to plot but save instead
    a.PlotDisableShowPlot()
    a.PlotVectorFile()
    #look in directory to see a file called MY_PLOT.png

    #change the filename of the plot
    a.PlotChangeFileName("image.png")
    a.PlotVectorFile()

    a.PlotChangeNumberOfSignals(63)
    a.PlotChangeStartPlottingSignalPosition(0)
    a.PlotChangeStartPlotFromHere(0)
    a.PlotChangeLengthOfPlot(83000)
    a.PlotEnableShowPlot()
    a.PlotVectorFile()

    

    # ********************************************************************* 

    #the following show the usage of the DAC value manipulation
    #you can print the DAC reference if you so wish, no method for this because why unless debug
    print(a.DacClockReference)

    #you can print the current data at each of these clock references if you so wish
    print(a.DacDataVector)

    #there is a method to print the same data in a sensible format
    a.DacPrintDacDataVector()

    #method to change a DAC setting
    a.DacNewDacSetting(19, "111111")

    #Print out the new settings
    a.DacPrintDacNewDataVector()

    #print out New DAC Data vector directly without method
    print(a.DacNewDataVector)

    #Print out the length of the new data vector
    print(len(a.DacNewDataVector))

    #write the Vector File (will default to vector file name with _mod.txt on the end if no name specified)
    a.DacUpdateVectorFile(new_vector_file)

    #change the vector file to the new file just created
    a.ChangeFileName(new_vector_file)
    #a.ChangeFileName("IsThisAFile")

    #print out the new DAC data extracted from the file to show it has been changed
    a.DacPrintDacDataVector()

    # *********************************************************************



if __name__ == "__main__":
    main()