#!/bin/bash
#Setup the Odin Server with QEM adapter to run as a service

#Install site packages then switch to a virtual environment
sudo apt-get update
sudo apt-get install python-smbus
sudo pip install virtualenv
virtualenv --system-site-packages venv2.7
source venv2.7/bin/activate

#Install the adapter and server
pip install versioneer
git clone https://github.com/jamesh1999/odin-control
cd odin-qem
sed -i 's/exit(0)/exit(1)/g' qem/backplane.py
python setup.py install
cd ../odin-control
python setup.py install

#Setup the server as a service
cd ..
sudo apt-get install supervisor
sudo cp odin-qem/config/qem.conf /etc/supervisor/conf.d
