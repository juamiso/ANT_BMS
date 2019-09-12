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
from scipy.interpolate import interp1d
import numpy as np
from binascii import unhexlify

# Import the ADS1x15 module.
from ADS1x15 import ADS1115
adc = ADS1115(address=0x48, busnum=1)
#Open Circuit voltages
#V = (2.50,3.213,3.251,3.290,3.315,3.317,3.319,3.334,3.349,3.356,3.366,3.383,3.445,3.478)
#Pack Level Voltage divided
V = (3.3528,4.3091,4.36,4.4123,4.4458,4.4485,4.4512,4.4713,4.4914,4.5008,4.5142,4.537,4.6202 ,4.6645)
SoC = (0,10,20,30,40,50,60,70,80,90,95,97,99,100)
f_lin = interp1d(V, SoC)
GAIN = 2/3
si_power = 0
si_volt = 0

def get_wh_total():
  url = 'http://localhost:8087/getPlainValue/fritzdect.0.DECT200_116570146230.energy'
  string = req.get(url).text
  wh_total = int(string[1:len(string)-1])
  return(wh_total)

def set_power(grid,PV,SoC_calc,charger,si_power,action):
#Send to iobroker values for diagram purposes
  url = 'http://localhost:8087/set/vis.0.'
  resp = req.get(url+'Grid'+'?value='+str(grid))
  resp = req.get(url+'PV'+'?value='+str(PV))
  resp = req.get(url+'control_status'+'?value='+action)

  resp = req.get(url+'SoC_calc'+'?value='+str(SoC_calc))
  if charger < 0 :
     if si_power != 0:
         req.get(url+'Batt_Charge'+'?value='+str(si_power))
         req.get(url+'Batt_Discharge'+'?value='+str(0))
  elif charger > 0:
     req.get(url+'Batt_Charge'+'?value='+str(0))
     if si_power !=0 :
        req.get(url+'Batt_Discharge'+'?value='+str(si_power))
  else :
    req.get(url+'Batt_Charge'+'?value='+str(0))
    req.get(url+'Batt_Discharge'+'?value='+str(0))
  return()

def get_wh_daily(wh_total,today):
  if int(strftime("%d", time.localtime())) != today : #New Day
    today = int(strftime("%d", time.localtime()))     #Change day
    wh_total = get_wh_total()                 #Reference total counter
  wh_day = get_wh_total()-wh_total            #Calculate current daily
  url = 'http://localhost:8087/set/vis.0.'
  resp = req.get(url+'wh_day'+'?value='+str(wh_day))
  return(wh_total,wh_day,today)

#POSITIVE means discharge battery
def build_data ( pow ) :
  crc16_modbus = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
  if pow >= 0 :
    power = str('%04X' % (pow))
  else:
    pow = -pow
    power = str('8''%03X' % (pow))
  Adr = '0B3F0D'
  #Rest = '01f9021c00960000000000' #50.5V 54V
  Rest = '01f9023500960000000000' #50.5V 56.5V
  #Rest = '01db023000960000000000' #47.5 56V 15CELLS
  #Rest = '01f9023000960000000000' #50.5V 56V
  #Rest = '01f9022100960000000000' #50.5V 54.5V
  #Rest = '01f9022b00960000000000' #50.5V 55.5V
  #Rest = '01f9021900960000000000' #50.5V 53.7V
  data = (Adr+str(power)+Rest)
  crc = (crc16_modbus(data.decode('hex')))
  crch = (crc & 0xff)
  crcl=(((crc>>8) & 0xff))
  crchst=('%02X' % crch)
  crclst= ('%02X' % crcl)
  Send=(data.decode('hex'))+(crchst.decode('hex'))+crclst.decode('hex')
  return Send

def GET_SI():
    Anfr33 = '0b330101325f'
    ser.write (Anfr33.decode('hex'))
    Antw33 = ser.read(42)
    reply_ID = (Antw33.encode('hex') [2:4])
    if reply_ID == '33':
      batp = (Antw33.encode('hex') [20:24])
      batu = (Antw33.encode('hex') [6:10])
      try:
        si_power=struct.unpack('>H',unhexlify(batp))[0]
        si_volt=struct.unpack('>H',unhexlify(batu))[0]*0.108
      except:
        si_volt=0
        si_power=0
        time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
        print ('%s Wrong feedback from Battery Inverter' %(time_s))      
      if si_power > 20000: #negative value comes with twos compl
        si_power = (-32768 + si_power)*0.1
      else:
        si_power = si_power *0.1
    else : #no update possible
        si_power = 12345
        si_volt = 12345
    return (si_power, si_volt)

#Define RS485 serial port
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate = 57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 0)

#Connect to inverter
ip='192.168.0.71' #This is the ip from your fronius inverter
client = ModbusClient(ip,port=502)
client.connect()

load = 0 #(+)
pv = 0 # (+)
grid = int(0)    #Total going to GRID
charger = int(10)
first_run=1
batt_full_flag = 0
SoC_target_int = 90
count = 0
AVM=0
si_power = 0
si_volt = 0
try:
  wh_total=get_wh_total()
except:
  print("WH_TOTAL funtion call error")
today = int(strftime("%M", time.localtime()))
while 1:
    value=adc.read_adc(0, gain=GAIN,data_rate=8)
    voltage = float(value)*6.144/32768.0 - 0.04 #0.3 V offset at pack level calibrated
    voltage_lim=voltage
    if voltage < 3.35 :
      voltage_lim = 3.35
    if voltage > 4.66 :
      voltage_lim = 4.66
    SoC_calc = f_lin(voltage_lim) #Deprecated, using now BMS SoC instead of read Voltage
    try: 
      BMS_SoC = int(req.get('http://localhost:8087/getPlainValue/vis.0.SoC').text)
    except:
      BMS_SoC = SoC_calc #Default to meas. Voltage based SoC if BMS_SoC not available
    cell = voltage/1.34113 #right
    pack = cell * 16
   
    #GET GRID VALUE from SMARTMETER
    try:
      value= client.read_holding_registers(40098-1,2,unit=240)
      smACPower = BinaryPayloadDecoder.fromRegisters(value.registers, byteorder=Endian.Big, 
            wordorder=Endian.Big)
      grid = int(smACPower.decode_32bit_float())
    except:
      time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
      print ('%s WARNING Modbus smartmeter not answering' %(time_s))
    try:
      value= client.read_holding_registers(40092-1,2,unit=1)
      sf = BinaryPayloadDecoder.fromRegisters(value.registers, byteorder=Endian.Big, 
           wordorder=Endian.Big)
      pv = int(sf.decode_32bit_float())
    except:
      time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
      print ('%s WARNING Modbus Inverter not answering' %(time_s))
    try:
      SoC_target=int(req.get('http://localhost:8087/getPlainValue/vis.0.SoC_target').text)
      if SoC_target > 10 and SoC_target <=100 and SoC_target != SoC_target_int:
         SoC_target_int = SoC_target
         batt_full_flag = 0
         time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
         print ('%s updating SoC Target' %(time_s))
    except:
      pass

    #control loop start here
    if grid < -10 and batt_full_flag == 0 :
        charger -= 2      #slowly increment charger
        if grid < -80 :
          charger += grid      #setpoint charger
        if grid < -20 :
          charger -= 10
        if charger < 0 :
           action = "Inc.Charg"
        else :
           action = "Dec.Supply"
        if charger <= -1600 :      #Upper limit
            charger = -1600
            action = "Charg.Max"
        if BMS_SoC >= SoC_target_int:  #Batt. full
            charger = 0
            action = "Max.SoC"
            batt_full_flag=1
            time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
            print ('%s Batt Full' %(time_s))


    elif grid > 10:
        if charger == 0:      #Sudden increase of demand while inverter was off
           first_run = 1      #leave some time to react before looping again
        charger += grid      #setpoint charger
        action = "Inc.Supply"
        if charger > 1600 :        #Lower limit
            charger = 1600
            action = "Suppl.Max"
        if BMS_SoC < (SoC_target -2) and batt_full_flag == 1:
           batt_full_flag = 0


    elif batt_full_flag==1 and grid < 0: #and pv > 150: #Batt Full and PV available
        if charger > 0 :   #Grid injection is not coming from PV but from Supply
          charger += grid #Supply less
          action ="Decr.Supply"
        else:
          charger = 0 #Supply was off, Turn SI OFF
        action = "Batt_Full"
    else :
        action = ("Opt._Ctrl")
    (si_power_new,si_volt_new) = GET_SI()
    if si_power_new != 12345: #Updated values available
      si_power = si_power_new
      si_volt = si_volt_new
    #Avoid toggling after big load turns off and system changes from supply to charge
    #even though PV is not enough (or even 0)
    if (pv+charger)<0 : #if charger bigger than photovoltaik
      time_s = strftime("%y/%m/%d %H:%M:%S", time.localtime())
      print ('%s Avoid toggle charger %d pv %d' %(time_s,charger,pv))
      charger = -pv
      if pv == 0 :
        charger = - 100  #keep supplying something, avoid turning SI off
    set_power(grid,pv,SoC_calc,charger,si_power,action)
    if count == 5 :
      try:
         (wh_total,wh_daily,today) = get_wh_daily(wh_total, today)
         count = 0
      except:
         AVM=-9999
    else :
      count+=1
    if charger > 0 :
      modus = "Supply"
    else :
      modus = "Charge"
    # VERBOSE MODE for logging to file
    #time_s = strftime("%y/%m/%d %H:%M:%S ", time.localtime())
    #print ('%s%s %04d act %04.0f %04.0f PV %04d GRID %04d CELL %.3f PACK %2.2f %05.2f SoC %2.1f %s' 
    #        %(time_s, modus, charger, AVM ,si_power, pv, grid, cell ,pack,si_volt, SoC_calc, action))
    data_stream = build_data(charger)
    test=data_stream.encode('hex')
    ser.write (test.decode('hex'))
    if first_run :
      first_run = 0    
      time.sleep(15)
    else:
      time.sleep(2)
client.close()

