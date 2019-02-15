
import sys, requests, json
import Tkinter as tk
import tkMessageBox

class mainWindow(object):

  def __init__(self,master):
    self.master=master

  def popup(self, location, units):
    self.popupIn = popupWindow(self.master, location, units)
    self.center_window(self.popupIn, 370, 55)
    self.master.wait_window(self.popupIn.top)

  def results(self, name, units, expectedResistance, measuredResistance, I2CResistance):
    self.results = resultsWindow(self.master, name, units, expectedResistance, measuredResistance, I2CResistance)

    self.center_window(self.results, 210, (45 + 18 * len(expectedResistance)))
    self.master.wait_window(self.results.top)

  def entryValue(self):
    return self.popupIn.value

  def center_window(self, window, width, height):
    screen_width = window.top.winfo_screenwidth()
    screen_height = window.top.winfo_screenheight()
    x = (screen_width/2) - (width/2)
    y = (screen_height/2) - (height/2)
    window.top.geometry('%dx%d+%d+%d' % (width, height, x, y))

class popupWindow(object):

  def __init__(self, master, location, units):
    top = self.top = tk.Toplevel(master)
    top.title('Input Needed')
    tk.Label(top, text='Please input the measured voltage between {} in {}: '.format(location, units)).pack()
    tk.Button(top,text='Enter', command=self.cleanup).pack(side=tk.RIGHT, padx=5)
    self.measurement=tk.Entry(top, justify=tk.RIGHT)
    self.measurement.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)
    self.measurement.focus_set()
    self.top.bind('<Return>', self.cleanup)

  def cleanup(self, event=None):
    try:
      self.value = float(self.measurement.get())
      self.top.destroy()
    except ValueError:
      tkMessageBox.showerror('Invalid Input','Please write a number in the entry box')


class resultsWindow(object):

  def __init__(self, master, name, units, expectedResistance, measuredResistance, I2CResistance):
    top = self.top = tk.Toplevel(master)
    top.title('Results')
    tk.Label(top, text='At {}, in {}:'.format(name,units)).pack()
    if name in ('VCTRL', 'VRESET', 'VDD_RST') :
      for i in range(len(expectedResistance)): 
        tk.Label(self.top, text='expected {:.2f}, measured {:.2f}, I2C calculated {:.2f}'.format(expectedResistance[i],  measuredResistance[i], I2CResistance[i])).pack()
    else:
      for i in range(len(expectedResistance)): 
        tk.Label(self.top, text='expected {:.2f}, measured {:.2f}'.format(expectedResistance[i],  measuredResistance[i])).pack()
    tk.Button(top,text='OK', command=self.top.destroy).pack()    
    self.top.bind('<Return>', self.cleanup)

  def cleanup(self, event=None):
    self.top.destroy()


class resistor_test():

  def __init__(self, base_url='http://beagle01.aeg.lan:8888/api/0.1/qem/'):
    self.resistors_url = base_url + 'resistors'
    self.volt_urls = base_url + 'current_voltage/'
    self.headers = {'Content-Type': 'application/json'}
    self.units = {'AUXSAMPLE':'V','AUXRESET':'V','VCM':'V','DACEXTREF':'uV','VRESET':'V','VDD_RST':'V','VCTRL':'V'}
    self.expectedResistance = {}
    self.expectedResistance['AUXSAMPLE'] = [0,.165,.330,.495,.660,.825,.990,1.154,1.319,1.484,1.649,1.814,1.979,2.144,2.309,2.474]
    self.expectedResistance['AUXRESET'] = [0,.165,.330,.495,.660,.825,.990,1.154,1.319,1.484,1.649,1.814,1.979,2.144,2.309,2.474]
    self.expectedResistance['VCM'] = [0,.165,.330,.495,.660,.825,.990,1.154,1.319,1.484,1.649,1.814,1.979,2.144,2.309,2.474]
    self.expectedResistance['DACEXTREF'] = [0,8.60,16.93,24.87,32.48,39.80,46.83,53.58,60.09,66.36,72.39,78.22,83.84,89.27,94.51,99.98]
    self.expectedResistance['VRESET'] = [0,.58,1.04,1.42,1.73,1.99,2.21,2.40,2.57,2.71,2.85,2.96,3.07,3.16,3.25,3.33]
    self.expectedResistance['VDD_RST'] =[1.8,2.26,2.55,2.73,2.86,2.96,3.04,3.10,3.15,3.19,3.23,3.26,3.29,3.32,3.34,3.36]
    self.expectedResistance['VCTRL'] =[-2.02,-1.66,-1.30,-0.94,-0.58,-0.22,.14,.50,.86,1.22,1.57,1.81,2.29,2.65,3.01,3.37]
    self.testLocation = {'AUXSAMPLE':'PL45 Pin 2 and Ground', 'AUXRESET':'PL47 Pin 2 and Ground', 'VCM':'PL 46 Pin 2 and Ground', 'DACEXTREF':'PL43 Pin 1 and Ground', 'VRESET':'PL40 Pins 1 and 2', 'VDD_RST':'PL34 Pins 1 and 2', 'VCTRL':'PL78 Pins 1 and 2'}
    self.i2cVoltageNum = {'VRESET':11, 'VDD_RST':7, 'VCTRL':(12,10)}
    self.root = tk.Tk()
    self.windowMain = mainWindow(self.root)
    self.root.withdraw()

  def measureResistor(self,name):
    self.windowMain.popup(self.testLocation[name],self.units[name])
    return self.windowMain.entryValue()


  def getResistorData(self,name,raw):
    parsedResponse = requests.get(self.resistors_url, headers={'Accept': 'application/json;metadata=true'}).json()
    for i in range(len(parsedResponse['resistors'])):
      if parsedResponse['resistors'][i]['name'] == name:
        if raw: return (i,parsedResponse['resistors'][i]['register']['value'])
        else: return (i,parsedResponse['resistors'][i]['resistance'])
    tkMessageBox.showerror('Name Error',(name + ' is not a valid resistor'))
    sys.exit()

  def expectedFromRaw(self, name, testCases):
    expected = []
    if name == 'VRESET': 
      for test in testCases:
        if test == 0: expected.append(0.0)
        else: expected.append(0.0001 / (1.0/49900 + 1.0/test/390.0))
    elif name == 'VDD_RST':
      for test in testCases:
        if test == 0: expected.append(0.0)
        else: expected.append(0.0001 * (17800 + 1 / (1.0/18200 + 1.0/test/390.0)))
    elif name == 'VCTRL':
      for test in testCases:
        expected.append(test * .021 - 2) 
    elif name == 'DACEXTREF':
      for test in testCases:
        expected.append(test * .029)
    else:
      for test in testCases:
        expected.append(test * .0097)
    return expected


  def checkResistor(self,name,raw,testCases):
    measuredResistance = []
    I2CResistance = []
    voltage_url = ''
    resistorData = self.getResistorData(name,raw)
    if testCases == None: 
      testCases = range(0,256,17)
      expectedResistance = self.expectedResistance[name]
    elif raw == True:
      expectedResistance = self.expectedFromRaw(name, testCases)
    else:
      expectedResistance = testCases
    if raw == True: resistor_url = self.resistors_url + '/' + str(resistorData[0]) + '/register_value'
    else: resistor_url = self.resistors_url + '/' + str(resistorData[0]) + '/value'
    if name == 'DACEXTREF': 
      tkMessageBox.showinfo('Action Required','Please supply 1V at pin 1 of PL43 to restrict current.')
    elif name == 'VRESET' :
      tkMessageBox.showinfo('Action Required',"Please ensure the jumper is on pins 1 and 2 of PL19.")
    if name in self.i2cVoltageNum and name != 'VCTRL':
      voltage_url = self.volt_url + str(self.i2cVoltageNum[name]) + '/voltage'
    elif name == 'VCTRL':
      voltage_urls = []
      voltage_urls[0] = self.volt_url + str(self.i2cVoltageNum[name][0]) + '/voltage'
      voltage_urls[1] = self.volt_url + str(self.i2cVoltageNum[name][1]) + '/voltage'
    for testCase in testCases:
      changeResistor = requests.put(resistor_url, str(testCase), headers=self.headers)
      resistance = self.measureResistor(name)
      measuredResistance.append(resistance)
      if name == 'VCTRL':
        if resistance > 0: voltage_url = voltage_urls[0]
        else: voltage_url = voltage_urls[1]
      if name in self.i2cVoltageNum:
        I2CResistance.append(requests.get(voltage_url,headers={'Accept': 'application/json'}).json()['voltage'])
    requests.put(resistor_url, str(resistorData[1]), headers=self.headers)
    return (expectedResistance, measuredResistance, I2CResistance)
    
  def resistorTest(self,name,raw=True,testCases=None):
    (expectedResistance, measuredResistance, I2CResistance) = self.checkResistor(name,raw,testCases)
    self.windowMain.results(name, self.units[name], expectedResistance, measuredResistance, I2CResistance)


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print 'please input the name of the resistor to be tested'
    sys.exit()
  name = sys.argv[1]
  base_url = None
  testCases = None
  testRaw = True
  for arg in sys.argv[2:]:
    parsedArg = arg.split('=')
    if parsedArg[0] == 'url':
      base_url = parsedArg[1]
      tester = resistor_test(base_url)
    elif parsedArg[0] == 'test':
      testCases = map(float,parsedArg[1].split(','))
    elif parsedArg[0] == 'raw':
      testRaw = parsedArg[1]
    else: 
      print parsedArg[0] + ' is not a valid keyword'
      sys.exit()
  if not base_url: tester = resistor_test()
  tester.resistorTest(name,testRaw,testCases)
