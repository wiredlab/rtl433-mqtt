.PHONY: default install restart stop status

default: install

install:
	./install.sh

restart:
	systemctl restart rtl433-mqtt.service

stop:
	systemctl stop rtl433-mqtt.service

status:
	systemctl status rtl433-mqtt.service
