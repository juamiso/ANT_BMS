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

There is a branched influxdb variant, which is simpler
and more robust. It dows not need iobroker to run since
it posts directly from the python script to the influxdb 
server

To be able to automatically connect to the bluetooth of
the BMS this solution uses the following:

This is part of the si_control.py file
```
# Define Serial port (over bluetooth) for BMS
ser_blue = serial.Serial(
    port='/dev/rfcomm0',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 0)
```

And in /etc/bluetooth/rfcomm.conf put 
```
rfcomm0 {
    # Automatically bind the device at startup
    bind yes;

   # Bluetooth address of the device
    device AA:BB:CC:A1:23:45;

    # RFCOMM channel for the connection
    channel 0;

    # Description of the connection
    comment "BMS";
}

```
