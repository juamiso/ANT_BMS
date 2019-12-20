import time
import sys
import time
import crcmod
import serial

#POSITIVE means discharge battery
def build_data ( pow ) :
  crc16_modbus = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0xFFFF, xorOut=0x0000)
  if pow >= 0 :
    power = str('%04X' % (pow))
  else:
    pow = -pow
    power = str('8''%03X' % (pow))
  Adr = '0B3F0D'
  #Rest = '01f9021c00960000000000' 50.5V 54V
#  Rest = '01f9022b00960000000000'
  Rest = '01db023000960000000000'
  data = (Adr+str(power)+Rest)
  crc = (crc16_modbus(data.decode('hex')))
  crch = (crc & 0xff)
  crcl=(((crc>>8) & 0xff))
  crchst=('%02X' % crch)
  crclst= ('%02X' % crcl)
  Send=(data.decode('hex'))+(crchst.decode('hex'))+crclst.decode('hex')
  return Send

#Define RS485 serial port
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate = 57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 0)
while True:
 value = int(sys.argv[1])
 print 'Setting SI to ', value, 'W'
 data_stream = build_data(value)
 test=data_stream.encode('hex')
 ser.write (test.decode('hex'))
 time.sleep(5)
#Anfr33 = '0b330101325f'
#ser.write (Anfr33.decode('hex'))
#Antw33 = ser.read(42)
#batp = (Antw33.encode('hex') [20:24])
#print (batp)
