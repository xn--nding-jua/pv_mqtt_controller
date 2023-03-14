#! /usr/bin/python3
import sys
import serial, time
import os, stat
from os.path import exists
from os import access, R_OK, W_OK
import paho.mqtt.client as mqtt
import configparser
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='''control dpm86xx devices using mqtt''')
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
SET_TOPIC = config.get("mqtt", "settopic")
# [dpm86xx]
dpm86xx_id = config.get("dpm86xx", "id")
dpm86xx_port = config.get("dpm86xx", "port")
VOLTAGE_MAX = int(config.get("dpm86xx", "v_max"))
CURRENT_MAX = int(config.get("dpm86xx", "i_max"))

APPNAME = "dpm86xx2mqtt"

# supported dpm functions -- see the document "dpm86xx-series-power-supply_simple-communication-protocol.odt/pdf" in this repository
F_MAX_VOLTAGE="00"        # R/-: maximum output voltage
F_MAX_CURRENT="01"        # R/-: maximum output current
F_VOLTAGE_SETTING="10"    # R/W: output voltage target
F_CURRENT_SETTING="11"    # R/W: output current target
F_OUTPUT="12"             # R/W: output on/off
F_VOLTAGE="30"            # R/-: output voltage
F_CURRENT="31"            # R/-: output current
F_CONST="32"              # R/W: constant current or constant voltage status
F_TEMPERATURE="33"        # R/-: temperature

VOLTAGE_MIN=0             #  0 Volt
CURRENT_MIN=0             #  0 Ampere

# create serial-object
dpm86xx_serial = serial.Serial(
    port=dpm86xx_port,
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1, #None
    inter_byte_timeout=None
)

# raw-communication-functions
def dpm86xx_value_read(opcode):
    opcode = str(opcode)

    # sending command
    cmd = ":" + dpm86xx_id + "r" + opcode + "=0" + ",,\n"
    bcmd = cmd.encode()
    written = dpm86xx_serial.write(bcmd)
    if written < len(bcmd): return(-999)

    # reading response
    bresponse = dpm86xx_serial.readline()
    response = bresponse.decode(errors='replace')
    if response == "": return(-999)

    # return corrected response as word
    response = response[7:-3]
    if response.isdigit(): response = int(response)
    return response

def dpm86xx_value_write(opcode, value):
    opcode = str(opcode)
    value = str(value)

    # sending command
    cmd =":" + dpm86xx_id + "w" + opcode + "=" + value + ",,\n"
    bcmd = cmd.encode()
    written = dpm86xx_serial.write(bcmd)
    if written < len(bcmd): return(-999)

    # reading response
    bresponse = dpm86xx_serial.readline()
    response = bresponse.decode(errors='replace')

    # check and return value
    response = response[:-2]
    if response == ":" + dpm86xx_id + "ok": return(1)
    else: return(-999)

# reading values
def dpm86xx_read_temperature():
    return(dpm86xx_value_read(F_TEMPERATURE))

def dpm86xx_read_voltage():
    return(float(dpm86xx_value_read(F_VOLTAGE)) / 100)

def dpm86xx_read_voltage_setting():
    return(float(dpm86xx_value_read(F_VOLTAGE_SETTING)) / 100)

def dpm86xx_read_voltage_max():
    return(float(dpm86xx_value_read(F_MAX_VOLTAGE)) / 100)

def dpm86xx_read_current():
    return(float(dpm86xx_value_read(F_CURRENT)) / 1000)

def dpm86xx_read_current_setting():
    return(float(dpm86xx_value_read(F_CURRENT_SETTING)) / 1000)

def dpm86xx_read_current_max():
    return(float(dpm86xx_value_read(F_MAX_CURRENT)) / 1000)

def dpm86xx_read_power():
    voltage = dpm86xx_read_voltage()
    if voltage<0: return(-999)
    current = dpm86xx_read_current()
    if current<0: return(-999)
    return(voltage * current)

def dpm86xx_read_power_max():
    voltage = dpm86xx_read_voltage()
    if voltage<0: return(-999)
    current_max = dpm86xx_read_current_max()
    if current_max<0: return(-999)
    return(voltage * current_max)

def dpm86xx_read_output():
    return(dpm86xx_value_read(F_OUTPUT))

def dpm86xx_read_mode():
    return(dpm86xx_value_read(F_CONST)) #CV=0 / CC=1

# setting values
def dpm86xx_set_voltage(voltage):
    if voltage < VOLTAGE_MIN or voltage > VOLTAGE_MAX: return(-999)
    return(dpm86xx_value_write(F_VOLTAGE_SETTING, int(voltage * 100)))

def dpm86xx_set_current(current):
    if current < CURRENT_MIN or current > CURRENT_MAX: return(-999)
    return(dpm86xx_value_write(F_CURRENT_SETTING, int(current * 1000)))

def dpm86xx_set_power(power):
    return(dpm86xx_set_current(power / dpm86xx_read_voltage()))

def dpm86xx_set_output(state):
    if state in [0, 1]: return(dpm86xx_value_write(F_OUTPUT, str(state)))
    else: return(-999)

def dpm86xx_set_mode(state): #CV=0 / CC=1
    if state in [0, 1]: return(dpm86xx_value_write(F_CONST, str(state)))
    else: return(-999)


def mqtt_callback(client, userdata, msg):
    #print("got topic: %s" % (str(msg.topic)))
    if (msg.topic == SET_TOPIC + "/voltage"):
        dpm86xx_set_voltage(float(msg.payload.decode("utf-8")))
    elif (msg.topic == SET_TOPIC + "/current"):
        dpm86xx_set_current(float(msg.payload.decode("utf-8")))
    elif (msg.topic == SET_TOPIC + "/power"):
        dpm86xx_set_power(float(msg.payload.decode("utf-8")))
    elif (msg.topic == SET_TOPIC + "/output"):
        dpm86xx_set_output(int(msg.payload.decode("utf-8")))
    elif (msg.topic == SET_TOPIC + "/readdata"):
        mqtt_client.publish(ROOT_TOPIC + "/output", str(dpm86xx_read_output()))
        mqtt_client.publish(ROOT_TOPIC + "/temperature", str(dpm86xx_read_temperature()))
        voltage = dpm86xx_read_voltage()
        mqtt_client.publish(ROOT_TOPIC + "/voltage", str(voltage))
        current = dpm86xx_read_current()
        mqtt_client.publish(ROOT_TOPIC + "/current", str(current))
        mqtt_client.publish(ROOT_TOPIC + "/power", str(voltage * current))


# main-function
if __name__ == '__main__':
    # MQTT-client
    # ================================================================
    mqtt_client = mqtt.Client(MQTT_CLIENTNAME)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)

    mqtt_client.on_message=mqtt_callback
    mqtt_client.subscribe(SET_TOPIC + "/voltage",qos=0)
    mqtt_client.subscribe(SET_TOPIC + "/current", qos=0)
    mqtt_client.subscribe(SET_TOPIC + "/power", qos=0)
    mqtt_client.subscribe(SET_TOPIC + "/output", qos=0)
    mqtt_client.subscribe(SET_TOPIC + "/readdata", qos=0)

    # initialize the device with some desired values
    # set constant-current-mode
    #dpm86xx_set_mode(1)

    # set voltage to 30V, current to 0A and enable output
    #dpm86xx_set_voltage(30)
    #dpm86xx_set_current(0)
    #dpm86xx_set_output(1)

    # wait at least 600ms to let device turnon
    #time.sleep(1.0)

    # set power to 70W
    #dpm86xx_set_power(70)

    # start MQTT-client
    mqtt_client.loop_start()

    # Start Main-Loop
    # ================================================================
    while(True):
        #print("Output-State = " + str(dpm86xx_read_output()))
        #print("Temperature  = " + str(dpm86xx_read_temperature()) + "°C")
        #print("Output-Voltage = " + str(dpm86xx_read_voltage()) + "V")
        #print("Output-Current = " + str(dpm86xx_read_current()) + "A")
        #print("Output-Power = " + str(dpm86xx_read_power()) + "W")

        time.sleep(1)
