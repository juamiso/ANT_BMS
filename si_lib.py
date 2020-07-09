import time
import requests as req
import struct
from binascii import unhexlify

url_string = 'http://192.168.0.4:8086/write?db=iobroker'

def post_to_influx(Grid,PV,charger,si_power):
  Batt_Charge=0
  Batt_Discharge=0
  if charger < 0 and si_power < 0:
        Batt_Charge=str(-si_power)
        Batt_Discharge=str(0)
  elif charger > 0:
        Batt_Charge=str(0)
        Batt_Discharge=str(si_power)
  else:
        Batt_Charge=str(0)
        Batt_Discharge=str(0)
  req.post(url_string, data='vis.0.Grid,from=Raspi3B value=' + str(Grid))
  req.post(url_string, data='vis.0.PV,from=Raspi3B value=' + str(PV))
  req.post(url_string, data='vis.0.Batt_Charge,from=Raspi3B value=' + Batt_Charge)
  req.post(url_string, data='vis.0.Batt_Discharge,from=Raspi3B value=' + Batt_Discharge)
  return ()

def readbms(ser_blue):
 test='DBDB00000000'
 SoC=0
 try:
   ser_blue.write (test.decode('hex'))
 except:
   ser_blue.close()
 time.sleep(1)
 if(ser_blue.isOpen() == False):
    ser_blue.open()
 Antw33 = ser_blue.read(140)
# print Antw33
# if True:
 try:
   SoC = int((Antw33.encode('hex') [(74*2):(75*2)]),16)
   data = (Antw33.encode('hex') [(111*2):(114*2+2)])
   if int(data,16)>2147483648:
     BMS_pow=str((-(2*2147483648)+int(data,16)))
   else:
     BMS_pow=str(int(data,16))
   data = (Antw33.encode('hex') [(70*2):(73*2+2)])
   if int(data,16)>2147483648:
      BMS_Current = str((-(2*2147483648)+int(data,16))*0.1)
   else:
      BMS_Current = str(int(data,16)*0.1)
   data = (Antw33.encode('hex') [8:12])
   BMS_V = str((struct.unpack('>H',unhexlify(data))[0])*0.1)
   data = (Antw33.encode('hex') [(121*2):(122*2+2)])
   cell_avg=str((struct.unpack('>H',unhexlify(data))[0])*0.001)
   data = (Antw33.encode('hex') [(119*2):(120*2+2)])
   cell_min=str((struct.unpack('>H',unhexlify(data))[0])*0.001)
   data = (Antw33.encode('hex') [(116*2):(117*2+2)])
   cell_max=str((struct.unpack('>H',unhexlify(data))[0])*0.001)
   for i in range(1,17):
      data = (Antw33.encode('hex') [((4+2*i)*2):((5+2*i)*2+2)])
      resp = str((struct.unpack('>H',unhexlify(data))[0])*0.001)
      data_string = 'vis.0.cell'+str(i)+',from=Raspi3B value=' + resp
      req.post(url_string, data=data_string)
#All to influx
   data_string = 'vis.0.SoC,from=Raspi3B value=' + str(SoC)
   req.post(url_string, data=data_string)
   data_string = 'vis.0.BMS_pow,from=Raspi3B value=' + BMS_pow
   req.post(url_string, data=data_string)
   data_string = 'vis.0.BMS_Current,from=Raspi3B value=' + BMS_Current
   req.post(url_string, data=data_string)
   data_string = 'vis.0.BMS_V,from=Raspi3B value=' + BMS_V
   req.post(url_string, data=data_string)
   data_string = 'vis.0.cell_V_avg,from=Raspi3B value=' + cell_avg
   req.post(url_string, data=data_string)
   data_string = 'vis.0.cell_V_min,from=Raspi3B value=' + cell_min
   req.post(url_string, data=data_string)
   data_string = 'vis.0.cell_V_max,from=Raspi3B value=' + cell_max
   req.post(url_string, data=data_string) 
 except:
   print('BMS_SoC to Influx failed')
 return (SoC)

