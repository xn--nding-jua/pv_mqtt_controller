# pv_mqtt_controller
This small piece of software has two parts:
- reading two Victron MPPTs via VE.Direct and send data to a MQTT-Broker
- controlling a DPM86xx via MQTT to control power to a small inverter

Background is to readout a SmartMeter via an infrared-diode and to feed-in only the amount of power you are currently using. In my case I'm using it in combination with a PowerQueen 25,6V battery in my shed which is drawing only around 70W but sometimes more. I'm using NodeRED to control the amount of power the DPM86xx should give to an Envertech-inverter:

Here is my installation:
- 2x Victron SmartSolar MPPT -> Python-Script -> MQTT-Broker
- MQTT-Broker -> NodeRED -> PowerController -> MQTT-Broker
- MQTT-Broker -> Python-Script -> DPM8624 -> Envertech EVT560 -> Grid

On cloudy days (using weather forecast in NodeRED) I'm only feeding-in the amount of power the PV is currently generating to be battery-friendly.  This power is limited to the amount of power the shed is taking - power above the need of the shed is stored in the battery. On sunny days I'm expecting better PV-power so I'm covering the demand of the shed directly if the battery has a SOC above 20%.
All the magic is done using NodeRED, but these two Python-Scripts are the "final fronteer" to the hardware :)

# Files
- dpm86xx2mqtt.py is the MQTT-controller for a connected DPM86xx-DC/DC-supply
- dpm86xx2mqtt.cfg is the configuration-file
- dpm86xx2mqtt.service is the systemd-service-file
- vedirect2mqtt.py is the MQTT-controller for the connected Victron MPPTs
- vedirect2mqtt.cfg is the configuration-file
- vedirect2mqtt.service is the systemd-service-file
- install_daemons.sh is an install-script to download required python-libs and to install and enable the systemd-services

# Installation
Clone this repository to the folder **/opt/pv_mqtt_controller/**, edit the service-files to fit your linux-user and run the install-script as root (**sudo bash install_daemons.sh**). This will install the python-libraries paho-mqtt, pyserial and "karioja/vedirect" from github. Afterwards the two services will be installed and enabled. (If you'd like to change the path, please edit the two service-files.)

Now edit the two configuration-files and setup the MQTT-Broker-Address and the USB-Ports. Then you can start the services and watch the MQTT-Broker to receive the data from the MPPTs. The DPM86xx will not send values by its own. Please use the command **yourtopic/readdata** to request the measurements.

# TODO
- Code is not ready for more than two MPPT. Please feel free to fork and update the code to support individual number of MPPTs