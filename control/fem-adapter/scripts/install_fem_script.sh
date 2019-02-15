#!/bin/bash
#Setup the Odin Server with QEM adapter to run with a script

#Gain root privelige
su -

#Allow access to I2C
chmod 666 /dev/i2c-1

#Install the adapter and server
git config --global http.sslVerify false
git clone https://github.com/BenCEdwards/odin-control
git config --global http.sslVerify true
cd odin-qem
python fem_setup.py install
cd ../odin-control
python setup.py install

#Setup the script to run the server
cd ..
mkdir bin
cp odin-qem/scripts/QEM.sh bin
