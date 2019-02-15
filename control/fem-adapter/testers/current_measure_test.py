import sys, requests
import Tkinter as tk
import tkMessageBox


class mainWindow(object):

  def __init__(self,master):
    self.master=master

  def results(self, name, expected, measured):
    self.resultsOut = resultsWindow(self.master, name, expected, measured)
    if name == 'U45':
      self.center_window(self.resultsOut, 255, 535)
    elif name == 'U39':
      self.center_window(self.resultsOut, 255, 460)
    else:
      self.center_window(self.resultsOut, 255, 85)
    self.master.wait_window(self.resultsOut.top)

  def center_window(self, window, width, height):
    screen_width = window.top.winfo_screenwidth()
    screen_height = window.top.winfo_screenheight()
    x = (screen_width/2) - (width/2)
    y = (screen_height/2) - (height/2)
    window.top.geometry('%dx%d+%d+%d' % (width, height, x, y))


class resultsWindow(object):

  def __init__(self, master, name, expected, measured):
    top = self.top = tk.Toplevel(master)
    top.title('Results')
    if name == 'U45':
      names = ('VDDO', 'VDD_D18', 'VDD_D25', 'VDD_P18', 'VDD_A18_PLL','VDD_D18ADC', 'VDD_D18_PLL') 
      for i in range(7):
        tk.Label(top, text='At {}s register:'.format(names[i])).pack()
        tk.Label(self.top, text='expected {:d}, measured {:d} at 10mA'.format(expected[i][0], measured[i][0])).pack()
        tk.Label(self.top, text='expected {:d}, measured {:d} at 20mA'.format(expected[i][1], measured[i][1])).pack()
        tk.Label(self.top, text=' ').pack()
    elif name == 'U39':
      names = ('VDD_RST', 'VDD_A33', 'VDD_D33', 'VCTRL_NEG', 'VRESET', 'VCTRL_POS')
      for i in range(6):
        tk.Label(top, text='At {}s register:'.format(names[i])).pack()
        tk.Label(self.top, text='expected {:d}, measured {:d} at 10mA'.format(expected[i][0], measured[i][0])).pack()
        tk.Label(self.top, text='expected {:d}, measured {:d} at 20mA'.format(expected[i][1], measured[i][1])).pack()
        tk.Label(self.top, text=' ').pack()
    else:
      tk.Label(top, text='At {}s register:'.format(name)).pack()
      tk.Label(self.top, text='expected {:d}, measured {:d} at 10mA'.format(expected[0], measured[0])).pack()
      tk.Label(self.top, text='expected {:d}, measured {:d} at 20mA'.format(expected[1], measured[1])).pack()
    tk.Button(top,text='OK', command=self.top.destroy).pack()    
    self.top.bind('<Return>', self.cleanup)

  def cleanup(self, event=None):
    self.top.destroy()


class current_test():

  def __init__(self, base_url='http://beagle01.aeg.lan:8888/api/0.1/qem/'):
    self.current_url = base_url + 'current_voltage'
    self.metaheaders = {'Accept': 'application/json;metadata=true'}
    self.expectedCurrent = {'VDDO':(20,41), 'VDD_D18':(8,16), 'VDD_D25':(9,18), 'VDD_P18':(8,16), 'VDD_A18_PLL':(82,164), 'VDD_D18ADC':(8,16), 'VDD_D18_PLL':(82,164), 'VDD_RST':(20,41), 'VDD_A33':(20,41), 'VDD_D33':(20,41), 'VCTRL_NEG':(49,98), 'VRESET':(20,41), 'VCTRL_POS':(82,164)}
    self.neededResistor ={'VDDO':180, 'VDD_D18':180, 'VDD_D25':220, 'VDD_P18':180, 'VDD_A18_PLL':180, 'VDD_D18ADC':180, 'VDD_D18_PLL':180, 'VDD_RST':330, 'VDD_A33':330, 'VDD_D33':330, 'VCTRL_NEG':330, 'VRESET':330, 'VCTRL_POS':330}
    self.plConnector = {'VDDO':75, 'VDD_D18':42, 'VDD_D25':74, 'VDD_P18':41, 'VDD_A18_PLL':76, 'VDD_D18ADC':33, 'VDD_D18_PLL':77, 'VDD_RST':34, 'VDD_A33':36, 'VDD_D33':35, 'VCTRL_NEG':78, 'VRESET':40, 'VCTRL_POS':78}
    self.root = tk.Tk()
    self.windowMain = mainWindow(self.root)
    self.root.withdraw()   


  def checkCurrentName(self,name):
  #returns the current as voltage of 'name' supply
    parsedResponse = requests.get(self.current_url, headers=self.metaheaders).json()
    measured = []
    for cv in parsedResponse['current_voltage']:
      if cv['name'] == name:
        if name in ('VDD_RST', 'VRESET') : changeResistor(name,255)
        elif name == 'VCTRL_POS' : changeResistor('VCTRL',255)
        elif name == 'VCTRL_NEG' : changeResistor('VCTRL',0)
        tkMessageBox.showinfo('Action Required',"Please check PL{} is disconnected".format(self.plConnector[name]))
        measured.append(cv['current_register']['value'])
        tkMessageBox.showinfo('Action Required',"Please connect an additional {}R Resistor at PL{}".format(self.neededResistor[name],self.plConnector[name]))
        measured.append(cv['current_register']['value'])
        return measured
    tkMessageBox.showerror('Name Error',(name + ' is not a valid power supply'))
    sys.exit()

  def changeResistor(resistor,value):
    resist_url = self.base_url + 'resistors'
    parsedResponse = requests.get(resist_url, headers=meta_headers).json()
    for i in range(len(parsedResponse['resistors'])):
      if parsedResponse['resistors'][i]['name'] == resistor:
        resist_url = base_url + 'resistors/' + str(resistor) + '/register_value/value'
        changeResistor = requests.put(resist_url, str(value), headers=headers)
        return 
    print (resistor + ' is not a valid resistor')


  def checkCurrent(self,name):
    measured = self.checkCurrentName(name)
    expected = self.expectedCurrent[name]
    return (expected, measured)

  def currentTest(self, name):
    if name == 'U45':
      expected = []
      measured = []
      for vc in ('VDDO', 'VDD_D18', 'VDD_D25', 'VDD_P18', 'VDD_A18_PLL','VDD_D18ADC', 'VDD_D18_PLL'):
        results = self.checkCurrent(vc)
        expected.append(results[0])
        measured.append(results[1])
    elif name == 'U39':
      expected = []
      measured = []
      for vc in ('VDD_RST', 'VDD_A33', 'VDD_D33', 'VCTRL_NEG', 'VRESET', 'VCTRL_POS'):
        results = self.checkCurrent(vc)
        expected.append(results[0])
        measured.append(results[1])
    else:
      (expected, measured) = self.checkCurrent(name)
    self.windowMain.results(name, expected, measured)


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print 'please input the name of the current voltage device or set (U45 or U39) of devices to be tested'
    sys.exit()
  base_url = None
  for arg in sys.argv[2:]:
    parsedArg = arg.split('=')
    if parsedArg[0] == 'url':
      base_url = parsedArg[1]
      tester = current_test(base_url)
  if not base_url: tester = current_test()
  name = sys.argv[1].replace(' ', '_')
  tester.currentTest(name)
