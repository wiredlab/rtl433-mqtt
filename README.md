# rtl433-mqtt

`rtl433-mqtt` runs `rtl_433` as a boot-starting systemd service. It decodes
ISM-band sensor packets with an RTL-SDR receiver, publishes them through
`rtl_433`'s native MQTT output, and writes local JSONL event logs.

The service is intentionally small:

- publish `rtl_433` availability, events, states, and devices to MQTT
- write decoded events to `/var/log/rtl433-mqtt/rtl433-events.jsonl`
- run unattended as a systemd service
- use `rtl_433`'s native MQTT reconnect behavior instead of `mosquitto_pub`
- preserve deployed configuration across application updates

## Requirements

- A current compiled `rtl_433`, newer than 25.12
- TLS-enabled `rtl_433` if `MQTT_TLS=1` is used
- `rsync`, `systemd`, and `logrotate` on the target host

Verify the expected `rtl_433` feature surface:

```bash
rtl_433 -V
rtl_433 -F help
```

The MQTT help should list `availability`, `events`, `states`, `devices`,
`base=<topic>`, env-based MQTT credentials, and `mqtts://` options when TLS is
available.

## Quick Install On Raspberry Pi

Clone the repository, edit the configuration, and run the installer:

```bash
git clone <repository-url> rtl433-mqtt
cd rtl433-mqtt
nano config/rtl433-mqtt.env
sudo ./install.sh
```

The installer copies the application to `/opt/rtl433-mqtt`, copies the initial
config to `/etc/rtl433-mqtt/rtl433-mqtt.env`, installs the systemd unit and
logrotate config, then enables and starts `rtl433-mqtt.service`.

After installation, edit the live config here:

```text
/etc/rtl433-mqtt/rtl433-mqtt.env
```

Detailed installation, update, config, service, and log operations are in
[docs/rtl433-mqtt-service-deployment.md](docs/rtl433-mqtt-service-deployment.md).

## MQTT Topics

By default, the base topic is:

```text
rtl433/<hostname>
```

The native `rtl_433` MQTT output publishes under that base:

```text
rtl433/<hostname>/availability
rtl433/<hostname>/events
rtl433/<hostname>/states
rtl433/<hostname>/devices/...
```

Change the base with `MQTT_TOPIC_PREFIX`, `RECEIVER_ID`, or
`MQTT_BASE_TOPIC`.

## Local Logs

Decoded events are written as JSONL:

```text
/var/log/rtl433-mqtt/rtl433-events.jsonl
```

Logrotate keeps 30 daily, date-suffixed, compressed rotations using the same
policy shape as `s500-logger`.

## Tests

Run the hardware-free checks:

```bash
bash -n rtl433-mqtt install.sh
python3 -m unittest discover -v
RTL433_MQTT_PRINT_COMMAND=1 ./rtl433-mqtt
```
