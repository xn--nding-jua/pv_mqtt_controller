#!/bin/sh

# check if we are superuser
if [ $(whoami) != 'root' ]; then
        echo -e "\nError: Insuffiecent Rights! (You need super-user-rights to execute $0)"
        exit 1;
fi

# check if Python 3 is installed
if [[ ! $(which python3) ]]; then
        echo "Error Python 3 is required!"
        exit 1
fi

# install dependencies (MQTT and Serial)
echo "Installing dependencies..."
/usr/bin/python3 -m pip install paho-mqtt pyserial "git+https://github.com/karioja/vedirect"

# install/update the two services
echo "Stopping services..."
systemctl stop dpm86xx2mqtt.service
systemctl stop vedirect2mqtt.service

echo "Copy files..."
cp dpm86xx2mqtt.service /etc/systemd/system/
cp vedirect2mqtt.service /etc/systemd/system/
chmod a-x /etc/systemd/system/dpm86xx2mqtt.service
chmod a-x /etc/systemd/system/vedirect2mqtt.service

echo "Reload daemon and enabling services..."
systemctl --system daemon-reload
systemctl enable dpm86xx2mqtt.service
systemctl enable vedirect2mqtt.service

echo "Done. Please edit the two config-files and start the services using <sudo systemctl start dpm86xx2mqtt> and <sudo systemctl start vedirect2mqtt>"
