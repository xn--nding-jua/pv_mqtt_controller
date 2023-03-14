#!/usr/bin/python3
from vedirect import Vedirect
import threading
import time
import paho.mqtt.client as mqtt
import configparser
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='''read multiple vedirect mppts using mqtt''')
parser.add_argument('config_file', metavar="<config_file>", help="file with configuration")
args = parser.parse_args()

# read and parse config file
config = configparser.RawConfigParser()
config.read(args.config_file)
# [mqtt]
MQTT_CLIENTNAME = config.get("mqtt", "clientname")
MQTT_HOST = config.get("mqtt", "host")
MQTT_PORT = config.getint("mqtt", "port")
MQTT_LOGIN = config.get("mqtt", "login", fallback=None)
MQTT_PASSWORD = config.get("mqtt", "password", fallback=None)
ROOT_TOPIC = config.get("mqtt", "roottopic")
# [vedirect]
mppt1_port = config.get("vedirect", "mppt1_port")
mppt2_port = config.get("vedirect", "mppt2_port")


# H20 -> 0
# H21 -> 0
# H22 -> 0
# H23 -> 0
# HSDS -> 0
# PID -> 0xA060
# FW -> 161
# SER -> HQ2220WADN7
# V -> 24000
# I -> -10
# VPV -> 10
# PPV -> 0
# CS -> 0
# MPPT -> 0
# OR -> 0x00000001
# ERR -> 0
# LOAD -> ON
# IL -> 0
# H19 -> 0

mppt1_data = {
    "H19": "0",
    "H20": "0",
    "H21": "0",
    "H22": "0",
    "H23": "0",
    "HSDS": "0",
    "PID": "0x0000",
    "FW": "0",
    "SER#": "00000000000",
    "V": "0",
    "I": "0",
    "VPV": "0",
    "PPV": "0",
    "CS": "0",
    "MPPT": "0",
    "OR": "0x00000001",
    "ERR": "0",
    "LOAD": "off",
    "IL": "0"
}

mppt2_data = {
    "H19": "0",
    "H20": "0",
    "H21": "0",
    "H22": "0",
    "H23": "0",
    "HSDS": "0",
    "PID": "0x0000",
    "FW": "0",
    "SER#": "00000000000",
    "V": "0",
    "I": "0",
    "VPV": "0",
    "PPV": "0",
    "CS": "0",
    "MPPT": "0",
    "OR": "0x00000001",
    "ERR": "0",
    "LOAD": "off",
    "IL": "0"
}

mppt1_values = {
    "Ubat": 0.0, # V
    "Ibat": 0.0, # I
    "Upv": 0.0, # VPV
    "Ppv": 0.0, # PPV
    "Iload": 0.0, # IL
    "Etoday": 0.0, # H20
    "Pmaxtoday": 0.0, # H21
    "State": 0 # CS
}

mppt2_values = {
    "Ubat": 0.0, # V
    "Ibat": 0.0, # I
    "Upv": 0.0, # VPV
    "Ppv": 0.0, # PPV
    "Iload": 0.0, # IL
    "Etoday": 0.0, # H20
    "Pmaxtoday": 0.0, # H21
    "State": 0 # CS
}

mppt1_lastdata = 0
mppt2_lastdata = 0

def current_milli_time():
    return round(time.time() * 1000)

def mppt1_callback(packet):
    # put received values into data
    global mppt1_lastdata

    for key, value in packet.items():
        mppt1_data[key] = value
    mppt1_lastdata = current_milli_time()

def mppt2_callback(packet):
    # put received values into data
    global mppt2_lastdata

    for key, value in packet.items():
        mppt2_data[key] = value
    mppt2_lastdata = current_milli_time()

def mppt1_thread_fcn():
    ve1 = Vedirect(mppt1_port, 1)
    ve1.read_data_callback(mppt1_callback)

def mppt2_thread_fcn():
    ve2 = Vedirect(mppt2_port, 1)
    ve2.read_data_callback(mppt2_callback)

def mppt1_process_data():
    # process data for MPPTs
    if ((mppt1_lastdata>0) and ((current_milli_time()-mppt1_lastdata)<5000)):
        mppt1_values["Ubat"] = int(mppt1_data["V"]) / 1000
        mppt1_values["Ibat"] = int(mppt1_data["I"]) / 1000
        mppt1_values["Pbat"] = mppt1_values["Ubat"] * mppt1_values["Ibat"]
        mppt1_values["Upv"] = int(mppt1_data["VPV"]) / 1000
        mppt1_values["Ppv"] = int(mppt1_data["PPV"])
        mppt1_values["Iload"] = int(mppt1_data["IL"]) / 1000
        mppt1_values["Pload"] = mppt1_values["Ubat"] * mppt1_values["Iload"]
        mppt1_values["Etoday"] = int(mppt1_data["H20"]) / 100
        mppt1_values["Pmaxtoday"] = int(mppt1_data["H21"]) / 100

        if int(mppt1_data["CS"]) == 0:
            mppt1_values["State"] = "Off"
        elif int(mppt1_data["CS"]) == 2:
            mppt1_values["State"] = "Fault"
        elif int(mppt1_data["CS"]) == 3:
            mppt1_values["State"] = "Bulk"
        elif int(mppt1_data["CS"]) == 4:
            mppt1_values["State"] = "Absorption"
        elif int(mppt1_data["CS"]) == 5:
            mppt1_values["State"] = "Float"
        elif int(mppt1_data["CS"]) == 7:
            mppt1_values["State"] = "Equalize"
        elif int(mppt1_data["CS"]) == 245:
            mppt1_values["State"] = "Starting-Up"
        elif int(mppt1_data["CS"]) == 247:
            mppt1_values["State"] = "Recondition"
        elif int(mppt1_data["CS"]) == 252:
            mppt1_values["State"] = "External Ctrl"
        else:
            mppt1_values["State"] = "State " + mppt1_data["CS"]
    else:
        mppt1_values["Ubat"] = 0
        mppt1_values["Ibat"] = 0
        mppt1_values["Pbat"] = 0
        mppt1_values["Upv"] = 0
        mppt1_values["Ppv"] = 0
        mppt1_values["Iload"] = 0
        mppt1_values["Pload"] = 0
        mppt1_values["Etoday"] = 0
        mppt1_values["Pmaxtoday"] = 0
        mppt1_values["State"] = "Timeout"

def mppt2_process_data():
    # process data for MPPTs
    if ((mppt2_lastdata>0) and ((current_milli_time()-mppt2_lastdata)<5000)):
        mppt2_values["Ubat"] = int(mppt2_data["V"]) / 1000
        mppt2_values["Ibat"] = int(mppt2_data["I"]) / 1000
        mppt2_values["Pbat"] = mppt2_values["Ubat"] * mppt2_values["Ibat"]
        mppt2_values["Upv"] = int(mppt2_data["VPV"]) / 1000
        mppt2_values["Ppv"] = int(mppt2_data["PPV"])
        mppt2_values["Iload"] = int(mppt2_data["IL"]) / 1000
        mppt2_values["Pload"] = mppt2_values["Ubat"] * mppt2_values["Iload"]
        mppt2_values["Etoday"] = int(mppt2_data["H20"]) / 100
        mppt2_values["Pmaxtoday"] = int(mppt2_data["H21"]) / 100

        if int(mppt2_data["CS"]) == 0:
            mppt2_values["State"] = "Off"
        elif int(mppt2_data["CS"]) == 2:
            mppt2_values["State"] = "Fault"
        elif int(mppt2_data["CS"]) == 3:
            mppt2_values["State"] = "Bulk"
        elif int(mppt2_data["CS"]) == 4:
            mppt2_values["State"] = "Absorption"
        elif int(mppt2_data["CS"]) == 5:
            mppt2_values["State"] = "Float"
        elif int(mppt2_data["CS"]) == 7:
            mppt2_values["State"] = "Equalize"
        elif int(mppt2_data["CS"]) == 245:
            mppt2_values["State"] = "Starting-Up"
        elif int(mppt2_data["CS"]) == 247:
            mppt2_values["State"] = "Recondition"
        elif int(mppt2_data["CS"]) == 252:
            mppt2_values["State"] = "External Ctrl"
        else:
            mppt2_values["State"] = "State " + mppt2_data["CS"]
    else:
        mppt2_values["Ubat"] = 0
        mppt2_values["Ibat"] = 0
        mppt2_values["Pbat"] = 0
        mppt2_values["Upv"] = 0
        mppt2_values["Ppv"] = 0
        mppt2_values["Iload"] = 0
        mppt2_values["Pload"] = 0
        mppt2_values["Etoday"] = 0
        mppt2_values["Pmaxtoday"] = 0
        mppt2_values["State"] = "Timeout"

def mppt_mqtt_publish():
    # process data for MPPTs
    mppt1_process_data()
    mppt2_process_data()

    # send MPPT1
    mqtt_client.publish(ROOT_TOPIC + "/1/Ubat", mppt1_values["Ubat"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Ibat", mppt1_values["Ibat"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Pbat", mppt1_values["Pbat"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Upv", mppt1_values["Upv"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Ppv", mppt1_values["Ppv"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Iload", mppt1_values["Iload"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Pload", mppt1_values["Pload"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Etoday", mppt1_values["Etoday"])
    mqtt_client.publish(ROOT_TOPIC + "/1/Pmaxtoday", mppt1_values["Pmaxtoday"])
    mqtt_client.publish(ROOT_TOPIC + "/1/State", mppt1_values["State"])

    # send MPPT2
    mqtt_client.publish(ROOT_TOPIC + "/2/Ubat", mppt2_values["Ubat"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Ibat", mppt2_values["Ibat"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Pbat", mppt2_values["Pbat"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Upv", mppt2_values["Upv"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Ppv", mppt2_values["Ppv"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Iload", mppt2_values["Iload"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Pload", mppt2_values["Pload"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Etoday", mppt2_values["Etoday"])
    mqtt_client.publish(ROOT_TOPIC + "/2/Pmaxtoday", mppt2_values["Pmaxtoday"])
    mqtt_client.publish(ROOT_TOPIC + "/2/State", mppt2_values["State"])

    # send commulated values
    mqtt_client.publish(ROOT_TOPIC + "/sum/Ibat", mppt1_values["Ibat"] + mppt2_values["Ibat"])
    mqtt_client.publish(ROOT_TOPIC + "/sum/Pbat", mppt1_values["Pbat"] + mppt2_values["Pbat"])
    mqtt_client.publish(ROOT_TOPIC + "/sum/Ppv", mppt1_values["Ppv"] + mppt2_values["Ppv"])
    mqtt_client.publish(ROOT_TOPIC + "/sum/Iload", mppt1_values["Iload"] + mppt2_values["Iload"])
    mqtt_client.publish(ROOT_TOPIC + "/sum/Pload", mppt1_values["Pload"] + mppt2_values["Pload"])
    mqtt_client.publish(ROOT_TOPIC + "/sum/Etoday", mppt1_values["Etoday"] + mppt2_values["Etoday"])
    mqtt_client.publish(ROOT_TOPIC + "/sum/Pmaxtoday", mppt1_values["Pmaxtoday"] + mppt2_values["Pmaxtoday"])

if __name__ == '__main__':
    # MQTT-client
    # ================================================================
    mqtt_client = mqtt.Client(MQTT_CLIENTNAME)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)

    # Connect to MPPT
    # ================================================================
    mppt1_thread = threading.Thread(target=mppt1_thread_fcn)
    mppt1_thread.start()
    mppt2_thread = threading.Thread(target=mppt2_thread_fcn)
    mppt2_thread.start()

    # Start Main-Loop
    # ================================================================
    while(True):
        mppt_mqtt_publish()

        time.sleep(1)

