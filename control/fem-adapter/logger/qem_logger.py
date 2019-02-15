import sys
import logging
import json
import datetime
import time
import signal

try:
    import requests
except ImportError:
    logging.warning("requests module not found, logger unavailable");
    sys.exit(0)
try:
    from influxdb import InfluxDBClient
except ImportError:
    logging.warning("influxdb module not found, logger unavailable");
    sys.exit(0)

db_name='qem_test'
pscu_host='beagle01.aeg.lan'
pscu_port=8888

update_interval = 5.0

def shutdown_handler():
    qemLogger.shutdown()

class qemLogger(object):

    do_update = True

    @classmethod
    def shutdown(cls):
        cls.do_update = False
    
    def __init__(self, db_host, db_port):

        self.pscu_host = pscu_host

        logging.basicConfig(level=logging.INFO, format='%(levelname)1.1s %(asctime)s %(message)s', datefmt='%y%m%d %H:%M:%S')

        logging.info("Opening connection to influxDB at {:s}:{:d}".format(db_host, db_port))
        self.db_exists = False
        try:
            self.influx_client = InfluxDBClient(host=db_host, port=db_port)
            existing_dbs =  self.influx_client.get_list_database()
        except:
            logging.info("Failed to open connection to influxDB at {:s}:{:d}".format(db_host, db_port))          
        else:
            for db in existing_dbs:
                if db['name'] == db_name:
                    self.db_exists = True
                    break
            if self.db_exists:
                logging.info("OK, {} database exists already".format(db_name))
            else:
                logging.info("Creating {} database".format(db_name))
                self.influx_client.create_database(db_name)

            self.influx_client.switch_database(db_name)

            self.pscu_request_url = 'http://{}:{}/api/0.1/qem/'.format(pscu_host, pscu_port)
            self.pscu_request_headers = {'Content-Type': 'application/json'}

            signal.signal(signal.SIGINT, lambda signum, frame: shutdown_handler())

    def get_pscu_data(self):

        pscu_data = None
        
        try:
            response = requests.get(self.pscu_request_url, headers=self.pscu_request_headers)
            pscu_data = response.json()
        except Exception as e:
            logging.error('Request of data from PSCU failed: {}'.format(e))

        return pscu_data

    def create_point(self, measurement, data, fields, tags={}, extra_fields={}):
        
        point_fields = {}
        for field in fields:
            point_fields[field] = float(data[field])

        point_fields.update(extra_fields)
        point = {
            'measurement': measurement,
            'time': self.now,
            'fields': point_fields,
            'tags': tags,
        }
        return point


    def create_global_point(self, pscu_data):
        
        global_fields = ['sensors_enabled', 'psu_enabled', 'clock']
        
        return self.create_point('global', pscu_data, global_fields)

    def create_psu_point(self, pscu_data):

        name = 'power_good'
        psu_fields = map(lambda x: str(x),range(1,9))

        return self.create_point(name, pscu_data[name], psu_fields)

    def create_supply_points(self, pscu_data):

        supply_fields = ['current', 'current_register', 'voltage', 'voltage_register']
        supply_group_data = pscu_data['current_voltage']

        supply_points = []
        for supply in range(len(supply_group_data)):
            supply_tags = {
                'name': str(supply),
            }
            supply_points.append(self.create_point('supply', supply_group_data[supply], supply_fields,
                                                             tags=supply_tags))
        return supply_points

    def create_resistor_points(self, pscu_data):

        name = 'resistors'
        resistor_fields = ['resistance', 'register']
        resistor_group_data = pscu_data[name]

        resistor_points = []
        for resistor in range(len(resistor_group_data)):
            resistor_tags = {
                'name': str(resistor),
            }
            resistor_points.append(self.create_point(name, resistor_group_data[resistor], resistor_fields,
                                                             tags=resistor_tags))
        return resistor_points


    def do_pscu_update(self):

        pscu_data = self.get_pscu_data()

        points = []

        points.append(self.create_global_point(pscu_data))
        points.append(self.create_psu_point(pscu_data))
        points.extend(self.create_supply_points(pscu_data))
        points.extend(self.create_resistor_points(pscu_data))

        shared_tags = {
            'pscu_host': self.pscu_host,
        }
        write_ok = self.influx_client.write_points(points, tags=shared_tags)
        
        if not write_ok:
            logging.error("Failed to write PSCU update to DB")

    def run(self):

        while qemLogger.do_update and self.db_exists:
            self.now = datetime.datetime.today()

            self.do_pscu_update()
            
            logging.info("DB update completed")
            time.sleep(update_interval)

        logging.info("qemLogger shutting down")

if __name__ == '__main__':
    
    logger = qemLogger('localbranch',8086)
    logger.run()
