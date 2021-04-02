import requests as req
import sys
import time
from time import strftime
import crcmod
import serial
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.diag_message import *
from pymodbus.file_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
import struct
from binascii import unhexlify
from si_lib import post_to_influx
from si_lib import readbms
import socket

SoC_target = 85
SoC_min_target = 15
BMS_SoC = 0

# Limit inverter power
maxpower = 2200
minpower = 2200 #Charge
# Declare
si_power = 0
si_volt = 0
si_volt_AC = 0
wh_daily = 0
#myToken = 'eyJhbGciOi-JIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InBpIiwiZXhwIjoyMjM4ODgzMjAwfQ.xOwi_jQTLG2T41PF3NT54pKfpTAFfNFl6WldoivzwP8'
#header_string = {'Authorization': 'Bearer {}'.format(myToken)}

# POSITIVE means discharge battery
def build_data(pow):
    crc16_modbus = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
    if pow >= 0:
        power = str('%04X' % (pow))
    else:
        pow = -pow
        power = str('8''%03X' % (pow))
    Adr = '0B3F0D'
    # Rest = '01f9021c00960000000000' #50.5V 54V
    #  Rest = '01f9023500960000000000' #50.5V 56.5V
    Rest = '01e0023500960000000000'  # 48 56.5V
    # Rest = '01f9023000960000000000' #50.5V 56V
    # Rest = '01f9022100960000000000' #50.5V 54.5V
    # Rest = '01f9022b00960000000000' #50.5V 55.5V
    # Rest = '01f9021900960000000000' #50.5V 53.7V
    data = (Adr + str(power) + Rest)
    crc = (crc16_modbus(data.decode('hex')))
    crch = (crc & 0xff)
    crcl = (((crc >> 8) & 0xff))
    crchst = ('%02X' % crch)
    crclst = ('%02X' % crcl)
    Send = (data.decode('hex')) + (crchst.decode('hex')) + crclst.decode('hex')
    return Send


def GET_SI():
    Anfr33 = '0b330101325f'
    ser.write(Anfr33.decode('hex'))
    time.sleep(0.1)
    Antw33 = ser.read(42)
    Antw33h = Antw33.encode('hex')
   # print('Sent %s read %s' % (Anfr33, Antw33h))
    reply_ID = (Antw33.encode('hex')[2:4])
    if (reply_ID) == '3f':
        #Chop off 0b3f0101f25c bytes
        Antw33 = Antw33[6:41]
   #     print('Chopped to %s' % Antw33.encode('hex'))
        reply_ID = (Antw33.encode('hex')[2:4])
    if reply_ID == '33':
        batp = (Antw33.encode('hex')[20:24])
        batu = (Antw33.encode('hex')[6:10])
        batuac = (Antw33.encode('hex')[12:14])
        try:
            si_power = struct.unpack('>H', unhexlify(batp))[0]
            si_volt = struct.unpack('>H', unhexlify(batu))[0] * 0.108
            si_volt_ac = struct.unpack('>B', unhexlify(batuac))[0] + 50
        except:
            si_volt = 0
            si_power = 0
            si_volt_ac = 0
            time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
            print('%s Wrong feedback from Battery Inverter' % (time_s))
        if si_power > 25000:  # negative value comes with twos compl
            si_power = -(-32768 + si_power) * 0.1
        else:
            si_power = si_power * 0.1
    else:  # no update possible
        si_power = 12345
        si_volt = 12345
        si_volt_ac = 12345
        print('SI does not answer to request, setting feedback to 12345')
    return (si_power, si_volt, si_volt_ac)

def GET_SI_WH():
    Anfr3E = '0b3e0101a39c'
    ser.write(Anfr3E.decode('hex'))
    time.sleep(0.1)
    Antw3E = ser.read(38)
    # Antw3Eh = Antw3E.encode('hex')
    # print ('Sent %s read %s'%(Anfr3E,Antw3Eh))
    NRG = (Antw3E.encode('hex')[18:26])
    NRG = int(NRG, 16) / 36000
    # print ('%f kWh total' % NRG)
    return (NRG)

time.sleep(10) #After first boot wait for bluetooth an such to connect
# Define RS485 serial port Solar Inverter
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0)
# Define Serial port (over bluetooth) for BMS
ser_blue = serial.Serial(
    port='/dev/rfcomm0',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 0)

# Connect to solar inverter
try:
  ip=socket.gethostbyname(SolarInvNetName)
except:
  ip = '192.168.0.70'  # Default to this ip if name non resolvable
client = ModbusClient(ip, port=502)
client.connect()

load = 0  # (+)
pv = 0  # (+)
grid = int(0)  # Total going to GRID
charger = int(10)
charger_old = 0
batt_full_flag = 0
batt_empty_flag = 0
#SoC_target_int = 85
count = 0
si_power = 0
si_volt = 0
si_volt_ac = 0
si_volt_new = 0
si_volt_ac_new = 0
si_power_new = 0

wh_total = 0;
today = int(strftime("%M", time.localtime()))
try:
  BMS_SoC = readbms(ser_blue)
except :
  pass
while 1:
      # GET GRID VALUE from SMARTMETER
    try:
        value = client.read_holding_registers(40098 - 1, 2, unit=240)
        smACPower = BinaryPayloadDecoder.fromRegisters(value.registers, byteorder=Endian.Big,
                                                       wordorder=Endian.Big)
        grid = int(smACPower.decode_32bit_float())
    except:
        time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
        print('%s WARNING Modbus smartmeter not answering' % (time_s))
    try:
        value = client.read_holding_registers(40092 - 1, 2, unit=1)
        sf = BinaryPayloadDecoder.fromRegisters(value.registers, byteorder=Endian.Big,
                                                wordorder=Endian.Big)
        pv = int(sf.decode_32bit_float())
    except:
        time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
        print('%s WARNING Modbus Inverter not answering' % (time_s))
#    try:  # Read from iobroker the user whised max SoC
#        SoC_target = int(req.get('http://localhost:8087/getPlainValue/vis.0.SoC_target').text)
#        if SoC_target > 10 and SoC_target <= 100 and SoC_target != SoC_target_int:
#            SoC_target_int = SoC_target
#            batt_full_flag = 0
#            time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
#            print('%s updating SoC Target' % (time_s))
#    except:
#    SoC_target = 100
#    try:  # Read from Iobroker the user wished min SoC
#        SoC_min_target = int(req.get('http://localhost:8087/getPlainValue/vis.0.SoC_min_target').text)
#        if SoC_min_target >= 0 and SoC_min_target <= 100 and SoC_min_target != SoC__min_target_int:
#            SoC_min_target_int = SoC_min_target
#    except:
#    SoC_min_target = 15

    # control loop start here
    if grid < -10 and batt_full_flag == 0:
        charger -= 2  # slowly increment charger
        if grid < -80:
            charger += grid  # setpoint charger
        if grid < -20:
            charger -= 10
        if charger < 0:
            action = "Inc.Charg"
        else:
            action = "Dec.Supply"
        if charger <= -minpower:  # Upper limit
            charger = -minpower
            action = "Charg.Max"
        if BMS_SoC >= SoC_target:  # Batt. full
            charger = 0
            action = "Max.SoC"
            batt_full_flag = 1
            time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
            print('%s Batt Full' % (time_s))

    elif grid > 10:
        charger += grid  # setpoint charger
        action = "Inc.Supply"
        if charger > maxpower:  # Lower limit
            charger = maxpower
            action = "Suppl.Max"
        if BMS_SoC < (SoC_target - 2) and batt_full_flag == 1:
            batt_full_flag = 0

    elif batt_full_flag == 1 and grid < 0:  # and pv > 150: #Batt Full and PV available
        if charger > 0:  # Grid injection is not coming from PV but from Supply
            charger += grid  # Supply less
            action = "Decr.Supply"
        else:
            charger = 0  # Supply was off, Turn SI OFF
        action = "Batt_Full"
    else:
        action = "Opt._Ctrl"

    # Avoid toggling after big load turns off and system changes from supply to charge
    # even though PV is not enough (or even 0)
    if (pv + charger) < 0:  # if charger bigger than photovoltaik
        time_s = strftime("%y/%m/%d %H:%M:%S", time.localtime())
        # print ('%s Avoid toggle charger %d pv %d' %(time_s,charger,pv))
        charger = -pv
        if pv == 0:
            charger = - 100  # keep supplying something, avoid turning SI off

    # Battery lower limit
    if BMS_SoC <= SoC_min_target:
        batt_empty_flag = 1
    if BMS_SoC > (SoC_min_target + 2):
        batt_empty_flag = 0
    if (charger > 0) and (batt_empty_flag == 1):
        charger = 0  # Stop discharging the battery
        action = "Empty"

    (si_power_new, si_volt_new_,si_volt_ac_new) = GET_SI()
    if si_power_new != 12345:  # Updated values available
        si_power = si_power_new
        si_volt = si_volt_new
        si_volt_ac = si_volt_ac_new
    elif charger == 0:  # Looks like no updates due to inverter turned off
        print ('Setting SI Power to zero since it does not update feedback')
        si_power = 0  # so setting the value to zero for nice plots
    if count == 5:
        try:
          BMS_SoC_temp = readbms(ser_blue)
        except:
          pass
        if BMS_SoC_temp != 0: #Only update SoC if non zero
           BMS_SoC = BMS_SoC_temp
        post_to_influx(grid,pv,charger,si_power,si_volt,si_volt_ac)
        count = 0
    else:
        count += 1
    if charger > 0:
        modus = "Supply"
    else:
        modus = "Charge"
    # VERBOSE MODE for logging to file
    time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
    print ('%s%s %04d act %04.0f PV %04d GRID %04d PACK %05.2f SoC %2d AC %3dV  %s'
            %(time_s, modus, charger, si_power, pv, grid, si_volt, BMS_SoC , si_volt_ac, action))
    data_stream = build_data(charger)
    test = data_stream.encode('hex')
    ser.write(test.decode('hex'))
    if (charger_old >= 0 and charger < 0) or (charger_old <= 0 and charger > 0):
        time.sleep(15)
        print("MOde switch, wait 15s")
    else:
        time.sleep(2)
    charger_old = charger  # Remember last cycle mode
client.close()
