#!~/develop/projects/odin/venv/bin/python

import sys, requests, json

base_url = 'http://beagle01.aeg.lan:8888/api/0.1/qem/'
headers = {'Content-Type': 'application/json'}
meta_headers = {'Accept': 'application/json;metadata=true'}


def baseData():
# returns current state excluding metadata
  theWholeLot = requests.get(base_url, headers={'Accept':'application/json'})

  return theWholeLot.content

def allData():
# returns current state including metadata
  theWholeLot = requests.get(base_url, headers=meta_headers)

  return theWholeLot.content



def checkGood():
# return which inputs are not Power Good
  power_url = base_url + 'power_good'
  response = requests.get(power_url)
  parsed = json.loads(response.text)
  #print response.content
 
  notGood = ''

  for i in range(len(parsed['power_good'])): 
    if not parsed['power_good'][str(i+1)]:
      notGood += (str(i+1) + ', ')
  if notGood != '': return 'Power is not good on pins ' + notGood[:-2]
  else: return 'Power is good'



def checkCurrentVoltageName(name):
#returns the current and voltage of 'name' supply
  voltage_url = base_url + 'current_voltage'
  name = name.replace(' ', '_')
  response = requests.get(voltage_url, headers=meta_headers)
  parsed = json.loads(response.text)
  #print parsed['current_voltage']
  for cv in parsed['current_voltage']:
    if cv['name'] == name:
      return ('{:.' + str(cv['voltage']['dp']) + 'f}V, {:.' + str(cv['current']['dp']) + 'f}mA').format(cv['voltage']['value'], cv['current']['value'])
  for cv in parsed['current_voltage']:
    if cv['name'] == name:
      return ('{:.' + str(cv['voltage']['dp']) + 'f}V, {:.' + str(cv['current']['dp']) + 'f}mA').format(cv['voltage']['value'], cv['current']['value'])
  print (name + ' is not a valid current voltage')



def changeClock(newClock):
#sets the clock frequency to 'newClock' (MHz)
  clock_url = base_url + 'clock'

  response = requests.get(clock_url, headers=meta_headers)
  print response.content

  requests.put(clock_url, str(newClock) ,headers=headers)
  response = requests.get(clock_url)
  print '\n\n' + response.content
  return



def switchPsu():
# enables the psu if disabled and vice versa
  psu_url = base_url + 'psu_enabled'

  response = requests.get(psu_url)
  parsed = json.loads(response.text)
  #print parsed['psu_enabled']

  if parsed['psu_enabled']: disablePsu = requests.put(psu_url, 'false' ,headers=headers)
  else: enablePsu = requests.put(psu_url, 'true' ,headers=headers)

  response = requests.get(psu_url)
  print response.content
  return



def changeResistorName(resistor,value):
  resist_url = base_url + 'resistors'
  response = requests.get(resist_url, headers=meta_headers)
  parsed = json.loads(response.text)
  #print parsed['resistors']
  for i in range(len(parsed['resistors'])):
    if parsed['resistors'][i]['name'] == resistor:
      return changeResistorNum(i,value)     
  print (resistor + ' is not a valid resistor')



def changeResistorNum(resistor,value):
#changes resistor'resistor' to 'value' in V (uA for resistor[2])
  resist_url = base_url + 'resistors/' + str(resistor) + '/resistance'

  #response = requests.get(resist_url)
  #print response.content

  #response = requests.get(resist_url)
  #print response.content

  changeResistor = requests.put(resist_url, str(value), headers=headers)


  print changeResistor.headers
  #response = requests.get(resist_url)
  #response.content
  return



def incrementResistors():
# increase all resistors register by 5
  resist_url = base_url + 'resistors'
  response = requests.get(resist_url)
  parsed = json.loads(response.text)
  resist_url = base_url + 'resistors'
  response = requests.get(resist_url)
  parsed = json.loads(response.text)
  #print response.content

  resist_urls = [] 
  values = []

  for i in range(len(parsed['resistors'])):
    resist_urls.append(resist_url + '/' + str(i) + '/resistance')
    values.append(float(parsed['resistors'][i]['resistance']) + 0.001)
    requests.put(resist_urls[i], str(values[i]), headers=headers)

  #response = requests.get(resist_url)
    requests.put(resist_urls[i], str(values[i]), headers=headers)

  #response = requests.get(resist_url)
  #print response.content
  return



if __name__ == '__main__':

  if len(sys.argv) == 2:
    base_url = sys.argv[1]
  
  #print baseData()
  #print allData()
  #print checkGood()
  #print checkCurrentVoltageName('VDD P18')
  changeClock(25)
  #switchPsu()
  #changeResistorName('VRESET',0)
  #changeResistorNum(0,.90)
  #incrementResistors()


