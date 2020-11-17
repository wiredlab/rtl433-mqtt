
# directory tree where to install the script
PREFIX=/usr/local


# action when calling with no argument
default: enable start


# set the location of the installed script
rtl433-mqtt.service: rtl433-mqtt.service.in
	sed 's,PREFIX,$(PREFIX),' $< > $@

install: rtl433-mqtt.service rtl433-mqtt.env
	install --mode=755 rtl433-mqtt $(PREFIX)/bin/
	install --mode=600 rtl433-mqtt.env /etc/default/
	install --mode=644 rtl433-mqtt.service /usr/lib/systemd/system/

uninstall: disable
	rm $(PREFIX)/bin/rtl433-mqtt
	rm /etc/default/rtl433-mqtt.env
	rm /usr/lib/systemd/system/rtl433-mqtt.service

enable: install
	systemctl enable rtl433-mqtt.service

start: install reload
	systemctl start rtl433-mqtt.service

restart: install reload
	systemctl restart rtl433-mqtt.service

reload:
	systemctl daemon-reload

disable: stop
	systemctl disable rtl433-mqtt.service

stop:
	systemctl stop rtl433-mqtt.service

