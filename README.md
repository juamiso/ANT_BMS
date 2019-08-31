#Description
This is a set of python scripts used for controlling a
DIY battery storage for a Photovoltaic based system.
Two python scripts plus a iobroker installation on a
raspberry pi.

bms_post.py is used to parse the information coming 
via bluetooth from a china made Battery Monitoring System
which is taking care of a 16s LIFEPO 100Ah bank.
The type of BMS is ANT (can be found on aliexpress)
The script reads info from the serial port and sends it
via simple_api to iobroker signals

si_control.py is the main control script: It reads some
information directly from the pI (ADC converter reading
battery pack voltage) as well as grid and photovoltaic
powers (using TCP Modbus from a Fronius Inverter). Some
signals are read from iobroker via simple_api.

Work in progress. 
