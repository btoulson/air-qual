import serial, struct, time

class sds011():
    def __init__(self):
       try:
            self.ser = serial.Serial('/dev/ttyUSB0')
            self.ser.flushInput()
       except:
            print("Error in sds011 init")


    def read(self):
        byte = "\x00"
        readings = None
        while readings == None:
            #try:
            lastbyte = byte
            byte = self.ser.read(size=1)
                #print(byte)
            if lastbyte == b"\xAA" and byte == b"\xC0":
                sentence = self.ser.read(size=8) # Read 8 more bytes
                #print(sentence)
                readings = struct.unpack('<HHxxBB',sentence)
                #print(readings)
                pm_25 = readings[0]/10.0
                pm_10 = readings[1]/10.0
                return pm_25, pm_10
            #except:
            #    print("Error in sds011 read")


if __name__ == '__main__':
    import sys
#    sys.stdout.write(__doc__)
    sys.stdout.write("Testing:\n")
    det = sds011()

    for i in range(10):
        pm25, pm10 = det.read()
        strOut = f"iteration {i}, {pm25}, {pm10}"
        sys.stdout.write(strOut + '\n')
        #print(strOut)
        time.sleep(0.5)
