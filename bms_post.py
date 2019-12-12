import sys
import time
import serial
import struct
from binascii import unhexlify
import requests as req

#Define RS485 serial port
ser = serial.Serial(
    port='/dev/rfcomm0',
    baudrate = 9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 0)
url = 'http://localhost:8087/set/vis.0.'

#104
MOSFET_Discharge_St=["OFF","ON","cell overdischarge","overcurrent","4","pack overdischarge",
"bat overtemp","MOSFET overtemp","Abnormal current","battery is not detected",
"PCB overtemp","charge MOSFET turn on","shortcircuit","Discharge MOSFET abnormality",
"Start exception","Manual off"]
#103
MOSFET_Charge_St=["OFF","ON","overcharge","overcurrent","batt full","pack overvoltage",
"bat overtemp","MOSFET overtemp","abnormal current","bat not detected",
"PCB overtemp","11-undefined","12-undefined","Discharge MOSFET abnormality","14","Manual off"]
#134-135
Bal_St=["OFF","limit trigger exceeds","charging v diff too high","overtemp","ACTIVE",
        "5-udef","6-udef","7-udef","8-udef","9-udef","PCB Overtemp"]
while True :
 test='DBDB00000000'
 try:
   ser.write (test.decode('hex'))
 except: 
   ser.close()
 time.sleep(1)
 if(ser.isOpen() == False):
    ser.open()
 Antw33 = ser.read(140)
# print Antw33
#SoC
 data = (Antw33.encode('hex') [(74*2):(75*2)])
 try:
   resp = req.get(url+'SoC'+'?value='+str(int(data,16)))
 #  print 
 except:
   pass
#Power
 data = (Antw33.encode('hex') [(111*2):(114*2+2)])
 try:
   if int(data,16)>2147483648:
     data=(-(2*2147483648)+int(data,16))
   else:
     data=int(data,16)
   resp = req.get(url+'BMS_pow'+'?value='+str(data))
 except:
    pass
#MOSFET Status
 data = (Antw33.encode('hex') [103*2:103*2+2])
 try:
   resp = req.get(url+'BMS_MOSFET_Ch_St'+'?value='+MOSFET_Charge_St[int(data,16)])
 except:
   pass
 data = (Antw33.encode('hex') [104*2:104*2+2])
 try:
   resp = req.get(url+'BMS_MOSFET_Disch_St'+'?value='+MOSFET_Discharge_St[int(data,16)])
 except:
    pass

#BALANCING STATUS
 data = (Antw33.encode('hex') [105*2:105*2+2])
 try:
   resp = req.get(url+'BMS_Bal_St'+'?value='+Bal_St[int(data,16)])
 except:
    pass

 data = Antw33.encode('hex') [134*2:135*2+2]
 try:
   data=struct.unpack('>H',unhexlify(data))[0]
 except:
   data=0xFFFF
 try:
   resp = req.get(url+'BMS_Bal0'+'?value='+str(data>>0&1))
   resp = req.get(url+'BMS_Bal1'+'?value='+str(data>>1&1))
   resp = req.get(url+'BMS_Bal2'+'?value='+str(data>>2&1))
   resp = req.get(url+'BMS_Bal3'+'?value='+str(data>>3&1))
   resp = req.get(url+'BMS_Bal4'+'?value='+str(data>>4&1))
   resp = req.get(url+'BMS_Bal5'+'?value='+str(data>>5&1))
   resp = req.get(url+'BMS_Bal6'+'?value='+str(data>>6&1))
   resp = req.get(url+'BMS_Bal7'+'?value='+str(data>>7&1))
   resp = req.get(url+'BMS_Bal8'+'?value='+str(data>>8&1))
   resp = req.get(url+'BMS_Bal9'+'?value='+str(data>>9&1))
   resp = req.get(url+'BMS_Bal10'+'?value='+str(data>>10&1))
   resp = req.get(url+'BMS_Bal11'+'?value='+str(data>>11&1))
   resp = req.get(url+'BMS_Bal12'+'?value='+str(data>>12&1))
   resp = req.get(url+'BMS_Bal13'+'?value='+str(data>>13&1))
   resp = req.get(url+'BMS_Bal14'+'?value='+str(data>>14&1))
   resp = req.get(url+'BMS_Bal15'+'?value='+str(data>>15&1))
 except:
  pass

#BMS_Current
 data = (Antw33.encode('hex') [(70*2):(73*2+2)])
 try:
    if int(data,16)>2147483648:
      data=(-(2*2147483648)+int(data,16))*0.1
    else:
      data = int(data,16)*0.1
    resp = req.get(url+'BMS_Current'+'?value='+str(data))
 except:
    pass
#BMS V
 data = (Antw33.encode('hex') [8:12])
 try:
    resp = req.get(url+'BMS_V'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.1))
 except:
    pass

#Cell_avg
 data = (Antw33.encode('hex') [(121*2):(122*2+2)])
 try:
   resp = req.get(url+'cell_avg'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
#Cell_min
 data = (Antw33.encode('hex') [(119*2):(120*2+2)])
 try:
   resp = req.get(url+'cell_min'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_max
 data = (Antw33.encode('hex') [(116*2):(117*2+2)])
 try:
   resp = req.get(url+'cell_max'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_1
 data = (Antw33.encode('hex') [(6*2):(7*2+2)])
 try:
   resp = req.get(url+'cell1'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
#Cell_2
 data = (Antw33.encode('hex') [(8*2):(9*2+2)])
 try:
   resp = req.get(url+'cell2'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_3
 data = (Antw33.encode('hex') [(10*2):(11*2+2)])
 try:
   resp = req.get(url+'cell3'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_4
 data = (Antw33.encode('hex') [(12*2):(13*2+2)])
 try:
   resp = req.get(url+'cell4'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_5
 data = (Antw33.encode('hex') [(14*2):(15*2+2)])
 try:
   resp = req.get(url+'cell5'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_6
 data = (Antw33.encode('hex') [(16*2):(17*2+2)])
 try:
   resp = req.get(url+'cell6'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_7
 data = (Antw33.encode('hex') [(18*2):(19*2+2)])
 try:
   resp = req.get(url+'cell7'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_8
 data = (Antw33.encode('hex') [(20*2):(21*2+2)])
 try:
   resp = req.get(url+'cell8'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_9
 data = (Antw33.encode('hex') [(22*2):(23*2+2)])
 try:
   resp = req.get(url+'cell9'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_10
 data = (Antw33.encode('hex') [(24*2):(25*2+2)])
 try:
   resp = req.get(url+'cell10'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_11
 data = (Antw33.encode('hex') [(26*2):(27*2+2)])
 try:
   resp = req.get(url+'cell11'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_12
 data = (Antw33.encode('hex') [(28*2):(29*2+2)])
 try:
   resp = req.get(url+'cell12'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_13
 data = (Antw33.encode('hex') [(30*2):(31*2+2)])
 try:
   resp = req.get(url+'cell13'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_14
 data = (Antw33.encode('hex') [(32*2):(33*2+2)])
 try:
   resp = req.get(url+'cell14'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_15
 data = (Antw33.encode('hex') [(34*2):(35*2+2)])
 try:
   resp = req.get(url+'cell15'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 #Cell_16
 data = (Antw33.encode('hex') [(36*2):(37*2+2)])
 try:
   resp = req.get(url+'cell16'+'?value='+str((struct.unpack('>H',unhexlify(data))[0])*0.001))
 except:
   pass
 


 time.sleep(10)
ser.close()
