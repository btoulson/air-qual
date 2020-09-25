#!/usr/bin/env python3
import os, sys
import random
import requests
import time
import logging
import argparse
from threading import Thread

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import sds011
import purple_bt
import atexit

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

logging.info("""particulate_exporter.py - Expose readings from sensor
Press Ctrl+C to exit!
""")

DEBUG = os.getenv('DEBUG', 'false') == 'true'

# object = {script}.{class}()
pmDetector = sds011.sds011()

# Setup InfluxDB
# You can generate an InfluxDB Token from the Tokens Tab in the InfluxDB Cloud UI
INFLUXDB_URL = os.getenv('INFLUXDB_URL', '')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKENAIR', '')
INFLUXDB_ORG_ID = os.getenv('INFLUXDB_ORG_ID', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')
INFLUXDB_SENSOR_LOCATION = os.getenv('INFLUXDB_SENSOR_LOCATION', 'pistachio')
#INFLUXDB_TIME_BETWEEN_POSTS = int(os.getenv('INFLUXDB_TIME_BETWEEN_POSTS', '5'))
INFLUXDB_TIME_BETWEEN_POSTS = int(20)
print(INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG_ID)
influxdb_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG_ID)
influxdb_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

def on_exit():
    """Close clients after terminate a script.

    :param db_client: InfluxDB client
    :param write_api: WriteApi
    :return: nothing
    """
    influxdb_client.__del__()
    influxdb_api.__del__()

def get_particulates():
    """Get the particulate matter readings"""
    try:
        pm25ug, pm10ug = pmDetector.read()
        print(f"pm2.5: {pm25ug}, pm10: {pm10ug} ug/m^3")
    except:
        logging.warning("Failed to read particulate")
        pm25ug, pm10ug = -1, -1
    else:
    #    print("print")
        return pm25ug, pm10ug

def get_purple():
    """Get the PurpleAir readings"""
    try:
        p = purple_bt.Purple()
        pflat = p.as_flat_dict()
        #print(pflat)
    except:
        logging.warning("Failed to read PurpleAir")
    else:
        return pflat

def collect_all_data():
    # need a way of moving global variables around
    """Collects all the data currently set"""
    sensor_data = {}
    #try:
    #    sensor_data = get_purple()
    #except:
    #    sensor_data = {}
    purple = get_purple()
    for key in ['Purple_pm_2.5', 'Purple_pm_10', 'Purple_temp_f', 'Purple_temp_c', 'Purple_humidity', 'Purple_pressure']:
        sensor_data[key] = purple[key]

    pm25ug, pm10ug = get_particulates()
    sensor_data['sds011_pm25'] = pm25ug
    sensor_data['sds011_pm10'] = pm10ug
    print(sensor_data)
    return sensor_data

def post_to_influxdb():
    """Post all sensor data to InfluxDB"""
    #name = 'enviroplus'
    tag = ['location', 'pistachio']
    while True:
        time.sleep(INFLUXDB_TIME_BETWEEN_POSTS)
        data_points = []
        epoch_time_now = round(time.time())
        sensor_data = collect_all_data()
        for field_name in sensor_data:
            data_points.append(Point('aq').tag('location', INFLUXDB_SENSOR_LOCATION).field(field_name, sensor_data[field_name]))
        try:
            influxdb_api.write(bucket=INFLUXDB_BUCKET, record=data_points)
            if DEBUG:
                logging.info('InfluxDB response: OK')
        except Exception as exception:
            logging.warning('Exception sending to InfluxDB: {}'.format(exception))


def get_serial_number():
    """Get Raspberry Pi serial number to use as LUFTDATEN_SENSOR_UID"""
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line[0:6] == 'Serial':
                return str(line.split(":")[1].strip())

def str_to_bool(value):
    if value.lower() in {'false', 'f', '0', 'no', 'n'}:
        return False
    elif value.lower() in {'true', 't', '1', 'yes', 'y'}:
        return True
    raise ValueError('{} is not a valid boolean value'.format(value))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--bind", metavar='ADDRESS', default='0.0.0.0', help="Specify alternate bind address [default: 0.0.0.0]")
    parser.add_argument("-p", "--port", metavar='PORT', default=8000, type=int, help="Specify alternate port [default: 8000]")
    parser.add_argument("-f", "--factor", metavar='FACTOR', type=float, help="The compensation factor to get better temperature results when the Enviro+ pHAT is too close to the Raspberry Pi board")
    parser.add_argument("-i", "--influxdb", metavar='INFLUXDB', type=str_to_bool, default='true', help="Post sensor data to InfluxDB [default: true]")
    args = parser.parse_args()
    cnt = 0
    on_exit()

    if args.factor:
        logging.info("Using compensating algorithm (factor={}) to account for heat leakage from Raspberry Pi board".format(args.factor))

    if args.influxdb:
        p = Point("my_measurement").tag("location", "Prague").field("temperature", 25.3)
        influxdb_api.write(bucket=INFLUXDB_BUCKET, record=p)
        # Post to InfluxDB in another thread
        logging.info("Sensor data will be posted to InfluxDB every {} seconds".format(INFLUXDB_TIME_BETWEEN_POSTS))
        influx_thread = Thread(target=post_to_influxdb)
        influx_thread.start()

    logging.info("Listening on http://{}:{}".format(args.bind, args.port))

    while True:
        #get_temperature(args.factor)
        #get_particulates()
        if DEBUG:
            logging.info('Sensor data: {}'.format(collect_all_data()))


