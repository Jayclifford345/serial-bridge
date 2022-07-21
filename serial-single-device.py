
import time
import serial
import serial.tools.list_ports
import influxdb_client
import argparse

sensor_names = {"LI":"light", "HU":"humidity", "ST":"soil_temperature",
                "AT":"air_temperature", "SM":"soil_moisture"}
user = "jay"

def get_serial_ports():
        """
        Returns a list of serial ports
        """
        return [port.device for port in serial.tools.list_ports.comports(include_links=False)]

class influxdb_writer():
    def __init__(self, host, token, org, bucket):
            self.client = influxdb_client.InfluxDBClient(
            url = host,
            token = token,
            org = org,
            timeout = 30000)

            self.bucket = bucket

            self.write_api = self.client.write_api()
    
        
    def write_to_influx(self, data):
        p = (influxdb_client.Point("sensor_data")
                            .tag("user",data["user"])
                            .tag("device_id",data["device"])
                            .field(data["sensor_name"], int(data["value"])
                            ))
        self.write_api.write(bucket=self.bucket, record=p)
        print(p, flush=True)
    


class serial_device():
    def __init__(self, influxdb_writer):
        self.port = None
        self.ser = None
        self.baudrate = 9600
        self.timeout = 1
        self.connected = False
        self.influxdb_writer = influxdb_writer
        

    def connect(self):
        """
        Connect to a serial port
        """
       # try: 
        if self.port is None:
                for port in get_serial_ports():
                        self.port = port
                        print("Connecting to " + self.port)
                        break
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self.connected = True
        
       # except:
          #  print("Error - could not connect to serial port")
          #  self.port = None
    
    def disconnect(self):
        """
        Disconnect from a serial port
        """
        self.ser.close()
        self.connected = False
        return True

    
    def formatter(self,sensorData):
        if sensorData[4:].rstrip() != "ERR":
            data = {"device" : sensorData[:2],
                    "sensor_name" : sensor_names.get(sensorData[2:4], "unkown"),
                    "value": int(sensorData[4:].rstrip()) ,
                    "user": user}
        else:
            data = {"device" : sensorData[:2],
                    "sensor_name" : sensor_names.get(sensorData[2:4], "unkown"),
                    "value": int(0) ,
                    "user": user} 
        return data
    
    def read(self):
        # Wait until there is data waiting in the serial buffer
        while (True):
            try: 
                if self.connected == False:
                    self.connect()
                    time.sleep(5)
                    print("Could not connect. Trying again in 5s...")
                else:
                    if(self.ser.in_waiting > 0):
                        print("Reading data...")
                        # Read data out of the buffer until a carraige return / new line is found
                        serialString = self.ser.readline()
                        formatted = self.formatter(serialString.decode('Ascii'))
                        self.influxdb_writer.write_to_influx(formatted)
                    else:
                        time.sleep(5)
            except OSError:
                print("OSError - reconnecting in 5s...")
                self.connected = False
                time.sleep(5)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Personal information')
    parser.add_argument('--host', dest='host', type=str, help='InfluxDB host')  
    parser.add_argument('--org', dest='org', type=str, help='InfluxDB organization')
    parser.add_argument('--token', dest='token', type=str, help='InfluxDB token')
    parser.add_argument('--bucket', dest='bucket', type=str, help='InfluxDB bucket')

    args = parser.parse_args()


    try:
        influxdb_writer = influxdb_writer(args.host, args.token, args.org, args.bucket)
        sd = serial_device(influxdb_writer)
        sd.connect()
        sd.read()
          
    except KeyboardInterrupt:
        print('Interrupted closing Serial Connection')
