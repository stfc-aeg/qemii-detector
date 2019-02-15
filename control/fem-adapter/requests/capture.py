import sys
import requests

def userContinue(prompt="Continue(Y/n)?"):
    while True:
        response = raw_input(prompt)
        if response.upper() == "N":
            sys.exit()
        elif response.upper() == "Y" :
             return


def userReplace(type, name = None):
    while True:
        response = raw_input("Input replacement value or continue(Y/n)?")
        if response.upper() == "N":
            sys.exit()
        elif response.upper() == "Y":
             return -1
        elif type == "Clock":
            return checkClock(response)
        elif type == "Resistor":
            return checkResistor(name, response)

def checkClock(frequencyRaw):
    try:
       frequency = int(frequencyRaw)
    except ValueError:
        print  "Clock: " + frequencyRaw.strip() + " is not a valid frequency - not an integer"
        return userReplace("Clock")
    if frequency < 10 or frequency > 945:
        print  "Clock: " + str(frequency) + " is not a valid frequency - not in range 10-945"
        return userReplace("Clock")
    else:
        return frequency

def checkResistor(name, registerRaw):
    try:
        register = int(registerRaw)
    except ValueError:
        print name + ":  " + registerRaw.strip() + " is not a valid register - not an integer"
        return userReplace("Resistor", name)
        return -1
    if register < 0 or register > 255:
        print name + ":  " + str(register) + " is not a valid register - not in range 0-255"
        return userReplace("Resistor", name)
    else:
       return register


def parseConfig(cfgFile):
    resistLookup = {"AUXRESET":0, "VCM":1, "DACEXTREF":2, "VDD_RST":3, "VRESET":4, "VCTRL":5, "AUXSAMPLE":6}

    config = {'resistor':[]}
    with open(cfgFile, 'r') as configFile:
        for line in configFile:
            if line.strip() == "":
                continue
            line = line.split(":")
            if line[0] == "clock" :
                frequency = checkClock(line[1])
                if frequency >= 0:
                    config["clock"] = frequency
            else:
                name = line[0].upper().strip().replace(" ", "_")
                if not name in resistLookup:
                    print line[0] + " is not a valid resistor name or clock"
                    userContinue()
                else:
                    location = resistLookup[name]
                    register = checkResistor(name, line[1])
                    if register >= 0:
                        config["resistor"].append([location, register])
    return config


def runCapture(config):
    baseUrl = "http://localhost:8888/api/0.1/qem/"
    putHeaders = {'Content-Type': 'application/json'}

    requests.put(baseUrl + "non_volatile", "false", headers=putHeaders)
    if "clock" in config:
        requests.put(baseUrl + "clock", str(config["clock"]), headers=putHeaders)
    for resistor in config["resistor"]:
        requests.put(baseUrl + "resistors/" +  str(resistor[0]) + "/register", str(resistor[1]), headers=putHeaders)
    requests.put(baseUrl + "psu_enabled", "true", headers=putHeaders)
#    requests.put(baseUrl + "capture_enabled", "true", headers=putHeaders)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'please include a configuration file (.cfg) as an argument'
        sys.exit()
    config = parseConfig(sys.argv[1])
    if "clock" not in config and config["resistor"] == []:
        userContinue("Configuration is empty. Run test anyway(Y/n)?")
    runCapture(config)
