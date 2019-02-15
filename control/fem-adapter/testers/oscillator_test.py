import sys, requests
import Tkinter as tk
import tkMessageBox

class mainWindow(object):

  def __init__(self,master):
    self.master=master

  def popup(self):
    self.popupIn = popupWindow(self.master)
    self.center_window(self.popupIn, 300, 55)
    self.master.wait_window(self.popupIn.top)

  def results(self,testCases,measuredTestCases):
    self.results = resultsWindow(self.master,testCases,measuredTestCases)
    self.center_window(self.results, 240, (50 + 18 * len(testCases)))
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

  def __init__(self,master):
    top = self.top = tk.Toplevel(master)
    top.title('Input Needed')
    tk.Label(top, text='Please input the measured frequency at PL22 in MHz:').pack()
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

  def __init__(self, master, testCases, measuredTestCases):
    top = self.top = tk.Toplevel(master)
    top.title('Results')
    tk.Label(top, text='At Crystal Oscillator, in MHz:').pack()
    for i in range(len(testCases)): 
      tk.Label(self.top, text='expected {:.2f}, measured {:.2f}'.format(testCases[i], measuredTestCases[i])).pack()
    tk.Button(top,text='OK', command=self.top.destroy).pack()    
    self.top.bind('<Return>', self.cleanup)

  def cleanup(self, event=None):
    self.top.destroy()


class oscillator_test():

  def __init__(self, base_url='http://beagle01.aeg.lan:8888/api/0.1/qem/'):
    self.clock_url = base_url + 'clock'
    self.baseTestCases = [10,50,100,20]
    self.headers = {'Content-Type': 'application/json'}
    self.root = tk.Tk()
    self.windowMain = mainWindow(self.root)
    self.root.withdraw()

  def changeClock(self,newClock):
  #sets the clock frequency to 'newClock' (MHz)
    requests.put(self.clock_url, str(newClock) ,headers=self.headers)
    return

  def measureClock(self):
    self.windowMain.popup()
    return self.windowMain.entryValue()

  def checkClock(self,testCases=None):
    currentClock = requests.get(self.clock_url).json()
    measuredTestCases = []
    if testCases is None: testCases = self.baseTestCases
    for testCase in testCases:
      self.changeClock(testCase)
      measuredTestCases.append(self.measureClock())
    self.changeClock(currentClock['clock'])
    return (testCases,measuredTestCases) 

  def clockTest(self,testCases=None):
    if testCases: 
      (testCases, measuredTestCases) = self.checkClock(testCases)
    else: (testCases, measuredTestCases) = self.checkClock()
    self.windowMain.results(testCases,measuredTestCases)


if __name__ == '__main__':
  
  base_url = None
  testCases = None
  for arg in sys.argv[1:]:
    parsedArg = arg.split('=')
    if parsedArg[0] == 'url':
      base_url = parsedArg[1]
      tester = oscillator_test(base_url)
    elif parsedArg[0] == 'test':
      testCases = map(float,parsedArg[1].split(','))
    else: 
      print parsedArg[0] + ' is not a valid keyword'
      sys.exit()
  if not base_url: tester = oscillator_test()
  tester.clockTest(testCases)

