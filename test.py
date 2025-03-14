import sys
sys.path.append("/home/embedded/.local/lib/python3.11/site-packages")
from bluepy import btle
import time
from bluepy.btle import Peripheral

btle.Debugging = True
class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
        # ... initialise here

    def handleNotification(self, cHandle, data):
        #print("\n- handleNotification -\n")
        print(data)
        # ... perhaps check cHandle
        # ... process 'data'

# Initialisation  -------
#p = Peripheral("94:b5:55:c8:e9:3e", addrType = "random", iface=0) 
#p = Peripheral("94:b5:55:c8:e9:3e", addrType = "public", iface=0)   #ESP32-DevKitC V4
p = Peripheral("94:b5:55:c8:e9:3e", iface=0) 
p.setSecurityLevel("medium")


# Setup to turn notifications on, e.g.
svc = p.getServiceByUUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
ch_Tx = svc.getCharacteristics("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")[0]
ch_Rx = svc.getCharacteristics("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")[0]

p.setDelegate( MyDelegate())

setup_data = b"\x01\00"
p.writeCharacteristic(ch_Rx.valHandle+1, setup_data)

lasttime = time.localtime()

while True:
    """
    if p.waitForNotifications(1.0):
        pass  #continue

    print("Waiting...")
    """
    try:
        ch_Tx.write(b'keepalive', True)
    except btle.BTLEException:
        print("Connection lost. Reconnecting...")
        p.connect("94:b5:55:c8:e9:3e")
    time.sleep(5)
    nowtime = time.localtime()
    if(nowtime > lasttime):
        lasttime = nowtime
        stringtime = time.strftime("%H:%M:%S", nowtime)
        btime = bytes(stringtime, 'utf-8')
        try:
            ch_Tx.write(btime, True)
        except btle.BTLEException:
            print("btle.BTLEException");
        #print(stringtime)
        #ch_Tx.write(b'wait...', True)
        
    # Perhaps do something else here
