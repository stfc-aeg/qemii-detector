#!/bin/bash
#Setup the Odin Server with QEM adapter to run with command qem.sh

#Install site packages
sudo apt-get update
sudo apt-get install python-smbus

 #switch to a virtual environment
sudo pip install virtualenv
virtualenv --system-site-packages venv2.7
source venv2.7/bin/activate

#clone the server with metadata
pip install versioneer
git clone https://github.com/jamesh1999/odin-control

#Install the adapter and server
cd odin-qem
python setup.py install
cd ../odin-control
python setup.py install

#Setup the script to run the server
cd ..
mkdir bin
cp odin-qem/scripts/qem.sh bin
