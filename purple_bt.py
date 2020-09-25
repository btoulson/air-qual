import json
import requests, logging
from datetime import timedelta
from datetime import datetime
API_ROOT = 'https://www.purpleair.com/json'

class Purple():
    '''Class for a single PurpleAir sensor; set initialize=True to fetch data from the API'''
    def __init__(self, id=40059, json=None):
        self.id = id
        self.json = json
        self.data = self.get_data()
        self.setup()


    def get_data(self) -> dict:
        '''Get new data if no data is provided'''
        # Fetch the JSON and exclude the child sensors
        if not self.json:
            response = requests.get(f'{API_ROOT}?show={self.id}')
            data = json.loads(response.content)
            return data['results'][0]
        else:
            return self.json


    def setup(self) -> None:
        '''Initiailze metadata and real data for a sensor; for detailed info see docs'''
        # Meta
        self.lat = self.data.get('Lat', None)
        self.lon = self.data.get('Lon', None)
        self.id = self.data.get('ID', None)
        self.name = self.data.get('Label', None)
        self.location_type = self.data['DEVICE_LOCATIONTYPE'] if 'DEVICE_LOCATIONTYPE' in self.data else ''

        # Data, same value in 'PM2_5Value' identical to  'pm2_5_cf_1' field
        if 'PM2_5Value' in self.data:
            if self.data['PM2_5Value'] != None:
                self.current_pm2_5 = float(self.data['PM2_5Value'])
            else: 
                self.current_pm2_5 = self.data['PM2_5Value']
        else:
            self.current_pm2_5 = ''

        try:
            self.current_pm10 = float(self.data['pm10_0_cf_1'])
        except TypeError:
            self.current_humidity = None
        except ValueError:
            self.current_humidity = None
        except KeyError:
            self.current_humidity = None

        try:
            f_temp = float(self.data['temp_f'])
            if f_temp > 150 or f_temp < -100:
                self.current_temp_f = None
                self.current_temp_c = None
            else:
                self.current_temp_f = float(self.data['temp_f'])
                self.current_temp_c = round((self.current_temp_f - 32) * (5 / 9),2)
        except TypeError:
            self.current_temp_f = None
            self.current_temp_c = None
        except ValueError:
            self.current_temp_f = None
            self.current_temp_c = None
        except KeyError:
            self.current_temp_f = None
            self.current_temp_c = None

        try: 
            self.current_humidity = int(self.data['humidity']) / 100
        except TypeError:
            self.current_humidity = None
        except ValueError:
            self.current_humidity = None
        except KeyError:
            self.current_humidity = None

        try:
            self.current_pressure = float(self.data['pressure'])
        except TypeError:
            self.current_pressure = None
        except ValueError:
            self.current_pressure = None
        except KeyError:
            self.current_pressure = None

        # Statistics
        stats = self.data.get('Stats', None)
        if stats:
            self.pm2_5stats = json.loads(self.data['Stats'])
            self.m10avg = self.pm2_5stats['v1']
            self.m30avg = self.pm2_5stats['v2']
            self.h1ravg = self.pm2_5stats['v3']
            self.h6ravg = self.pm2_5stats['v4']
            self.d1avg = self.pm2_5stats['v5']
            self.w1avg = self.pm2_5stats['v6']
            try:
                self.last_modified_stats = datetime.utcfromtimestamp(int(self.pm2_5stats['lastModified']) / 1000)
            except TypeError:
                self.last_modified_stats = None
            except ValueError:
                self.last_modified_stats = None
            except KeyError:
                self.last_modified_stats = None

            try:
                self.last2_modified = self.pm2_5stats['timeSinceModified'] # MS since last update to stats
            except KeyError:
                self.last2_modified = None


        # Diagnostic
        self.last_seen = datetime.utcfromtimestamp(self.data['LastSeen'])
        self.model = self.data['Type'] if 'Type' in self.data else ''
        self.hidden = False if self.data['Hidden'] == 'false' else True
        self.flagged = True if 'Flag' in self.data and self.data['Flag'] == 1 else False
        self.downgraded = True if 'A_H' in self.data and self.data['A_H'] == 'true' else False
        self.age = int(self.data['AGE']) # Number of minutes old the data is

    def as_dict(self) -> dict:
        '''Returns a dictionary representation of the sensor data'''
        d = {
            'meta': {
                'Purple_id': self.id,
                'Purple_lat': self.lat,
                'Purple_lon': self.lon,
                'Purple_id': self.id,
                'Purple_name': self.name,
                'Purple_locaction_type': self.location_type
            },
            'data': {
                'Purple_pm_2.5': self.current_pm2_5,
                'Purple_pm_10': self.current_pm10,
                'Purple_temp_f': self.current_temp_f,
                'Purple_temp_c': self.current_temp_c,
                'Purple_humidity': self.current_humidity,
                'Purple_pressure': self.current_pressure
            },
            'diagnostic': {
                'Purple_last_seen': self.last_seen,
                'Purple_model': self.model,
                'Purple_hidden': self.hidden,
                'Purple_flagged': self.flagged,
                'Purple_downgraded': self.downgraded,
                'Purple_age': self.age
            }
        }

        if self.data['Stats']:
            d['statistics']: {
                '10min_avg': self.m10avg,
                '30min_avg': self.m30avg,
                '1hour_avg': self.h1ravg,
                '6hour_avg': self.h6ravg,
                '1week_avg': self.w1avg
            }
        else:
            d['statistics']: {
                '10min_avg': None,
                '30min_avg': None,
                '1hour_avg': None,
                '6hour_avg': None,
                '1week_avg': None
            }

        return d


    def as_flat_dict(self) -> dict:
        '''Returns a flat dictionart representation of the Sensor data'''
        d = {}
        src = self.as_dict()
        for data_category in src:
            for data in src[data_category]:
                d[data] = src[data_category][data]
        return d

    def __repr__(self):
        '''String representation of the class'''
        return f"Sensor {self.id}"


if __name__ == '__main__':
    logging.basicConfig(filename=__file__+'.log', level=logging.INFO)
    logging.info(str(datetime.now())+" : Script was started")

    try:
        p = Purple()
        pflat = p.as_flat_dict()
        logging.info("PurpleAir_flat_dict: ")
        logging.info(pflat)
        #logging.info("Stats: ", p.as_dict())
    #for i in range(10):
    #    pm25, pm10 = det.read()
    #    strOut = f"iteration {i}, {pm25}, {pm10}"
    #    sys.stdout.write(strOut + '\n')
        #print(strOut)
    #    time.sleep(0.5)
    
    except Exception as e:
         logging.error('Caught exception: ' + str(e))
    
    exit()
