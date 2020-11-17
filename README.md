# rtl433-mqtt
This script and service uses an RTL2832U-based dongle with `rtl_433` to decode packets in ISM bands and publish the information to an MQTT broker.


## Requirements

* `mosquitto` >= 1.5
* `rtl_433`

`sudo apt update && sudo apt install rtl_433 mosquitto-clients`


`mosquitto_pub` will currently turn into a zombie process, accepting input from `rtl_433` but not publishing the data, under certain conditions.

NOTE:  This branch https://github.com/wiredlab/mosquitto/tree/pub-disconnect contains a fix on top of version 1.6.12, but is not yet merged into the upstream repository.
Build and install `mosquitto` and friends from our `pub-disconnect` branch for more robust behavior under unreliable network connections.


## Install

* Clone this repository somewhere convenient.

* Copy `rtl433-mqtt.env.example` to `rtl433-mqtt.env` and change the variables
  as appropriate.  NOTE: systemd does not do variable substitution in this
  file!

* Edit variable `PREFIX` in `Makefile` if desired.

* `sudo make`


## Uninstall

This will stop and disable the systemd service and remove the installed files (including the customized configuration file).

* `sudo make uninstall`


## Local logging
The `rtl433-mqtt` script includes commented-out items that log the information
to a local file.
You will need to edit the script to enable this feature.

Also included is `rtl433-mqtt.logrotate`, a configuration file for using
`logrotate` for easily rotating the log files.

