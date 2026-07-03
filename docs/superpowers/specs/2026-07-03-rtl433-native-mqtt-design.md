# rtl_433 Native MQTT Modernization Design

## Goal

Modernize this repository so the systemd service uses `rtl_433`'s native MQTT
publisher instead of piping JSON into `mosquitto_pub`, while still writing
local JSONL logs by default.

The deployment target is a modern compiled `rtl_433`, newer than 25.12. The
local reference binary reports:

```text
rtl_433 version 25.12-113-gfed03fac branch master at 202607030840 inputs file rtl_tcp RTL-SDR with TLS
```

This service will also run on the host that runs the S500 logger repository at
`/home/dan/ed/projects/ozone-garden`. That host pattern uses a local MQTT broker
by default, so this repo should default to `localhost:1883` while still allowing
remote and TLS brokers through environment settings. It should also follow the
S500 logger's deployment and local logging conventions: source copied under
`/opt`, configuration preserved under `/etc`, JSONL files under `/var/log`,
daily date-suffixed compressed logrotate, and no `copytruncate`.

## Current Behavior

The current `rtl433-mqtt` launcher:

- builds `rtl_433` options with `-F json`
- sends retained status messages using `mosquitto_pub`
- pipes decoded JSON lines from `rtl_433` into `mosquitto_pub -l`
- exits nonzero so systemd restarts the wrapper

This keeps a fragile shell pipeline in the critical path. The README also
documents known `mosquitto_pub` failure behavior under unreliable network
conditions.

## Target Behavior

The launcher should become a thin wrapper around one supervised `rtl_433`
process. It should build native MQTT output options and then `exec rtl_433 ...`
so systemd supervises the real long-running process.

The wrapper should use:

```text
-F mqtt://HOST:PORT,<options>
```

or, when TLS is enabled:

```text
-F mqtts://HOST:PORT,<options>
```

The native MQTT output should enable:

- `availability`, publishing online/offline availability directly from `rtl_433`
- `events`, publishing decoded JSON events
- `states`, publishing state summaries
- `devices`, publishing device/sensor nested topic data
- `base=<topic>`, with the default base built from `MQTT_TOPIC_PREFIX` and
  `RECEIVER_ID`

The default base topic should remain compatible with the existing service
shape:

```text
${MQTT_TOPIC_PREFIX:-rtl433}/${RECEIVER_ID:-$HOSTNAME}
```

The wrapper should also add a native JSON file output by default:

```text
-F json:${RTL433_EVENT_LOG:-/var/log/rtl433-mqtt/rtl433-events.jsonl}
```

This keeps local logging independent from MQTT transport. `rtl_433` should open
the output file per message or otherwise tolerate logrotate creating a fresh
file after rotation; the implementation should verify this behavior during
testing. If `rtl_433` keeps the file descriptor open across rotations, the
implementation should use a service restart in logrotate's `postrotate` block
rather than `copytruncate`.

## Environment Contract

Keep the current simple environment-file interface and add modern MQTT controls.

Required/defaulted settings:

- `MQTT_HOST`, default `localhost`
- `MQTT_PORT`, default `1883` unless TLS is enabled
- `MQTT_USERNAME`, optional
- `MQTT_PASSWORD`, optional
- `MQTT_USER`, optional backward-compatible alias for `MQTT_USERNAME`
- `MQTT_PASS`, optional backward-compatible alias for `MQTT_PASSWORD`
- `MQTT_TOPIC_PREFIX`, default `rtl433`
- `RECEIVER_ID`, default `$HOSTNAME`
- `RECEIVER_FREQ`, default `433.92M`
- `RTL433_OPTS`, optional extra raw `rtl_433` options
- `RTL433_EVENT_LOG`, default `/var/log/rtl433-mqtt/rtl433-events.jsonl`
- `RTL433_LOG_JSONL`, default `1`; set to `0` to disable local JSONL logging

TLS settings:

- `MQTT_TLS=1` selects `mqtts://`
- `MQTT_TLS_CA_CERT`, optional `tls_ca_cert=<path>`
- `MQTT_TLS_CERT`, optional `tls_cert=<path>`
- `MQTT_TLS_KEY`, optional `tls_key=<path>`

MQTT output settings:

- `MQTT_RETAIN`, default `0`
- `MQTT_BASE_TOPIC`, optional full override for the computed base topic
- `MQTT_ENABLE_AVAILABILITY`, default `1`
- `MQTT_ENABLE_EVENTS`, default `1`
- `MQTT_ENABLE_STATES`, default `1`
- `MQTT_ENABLE_DEVICES`, default `1`

Credentials should be exported as `MQTT_USERNAME` and `MQTT_PASSWORD` for
`rtl_433` to read. Existing `MQTT_USER` and `MQTT_PASS` env files should keep
working by mapping those aliases to the modern names when the modern names are
unset. Credentials should not be interpolated into the logged MQTT URL.

## Version Differences To Document

The old local `rtl_433 23.11` supported native MQTT events, states, and devices,
but did not advertise availability, base topic support, or TLS certificate
options in `rtl_433 -F help`.

The target newer-than-25.12 build advertises:

- `availability`
- default event/state/device topics under `<base>`
- `base=<topic>`
- env-based MQTT auth
- `mqtts://` with `tls_cert`, `tls_key`, and `tls_ca_cert`
- TLS support compiled into the binary

The README should state that this repo now targets a current compiled
`rtl_433`, not distro-era `23.11`.

## Systemd Behavior

Use the same installed-service shape as `s500-logger` where it fits this
shell-based service:

- `Type=simple`
- `Restart=always`
- `RestartSec=5`
- `After=local-fs.target`
- `RequiresMountsFor=/var/log/rtl433-mqtt`
- `EnvironmentFile=/etc/rtl433-mqtt/rtl433-mqtt.env`
- `WorkingDirectory=/opt/rtl433-mqtt`
- `ExecStart=/opt/rtl433-mqtt/rtl433-mqtt`

Because `rtl_433` owns the MQTT connection, the wrapper should not synthesize
its own retained status messages. Native `availability` replaces those messages.

The unit should not require `network-online.target`. Local JSONL logging should
start whenever the SDR and local filesystem are available; `rtl_433`'s native
MQTT reconnect behavior should handle MQTT broker availability.

## Installation Layout

Replace the current Makefile-centered install flow with an S500-shaped
installer:

```text
install.sh
config/rtl433-mqtt.env
deploy/rtl433-mqtt.service
deploy/rtl433-mqtt-logrotate
docs/rtl433-mqtt-service-deployment.md
```

The installer should:

- require root and print `sudo ./install.sh` guidance when not root
- accept `--force-config`
- create `/opt/rtl433-mqtt`, `/etc/rtl433-mqtt`, and `/var/log/rtl433-mqtt`
- copy the repository contents into `/opt/rtl433-mqtt` with development
  artifacts excluded, following the S500 `rsync -a --exclude ...` pattern
- install `config/rtl433-mqtt.env` to
  `/etc/rtl433-mqtt/rtl433-mqtt.env` only when missing, unless
  `--force-config` is supplied
- install the systemd unit to `/etc/systemd/system/rtl433-mqtt.service`
- install the logrotate config to `/etc/logrotate.d/rtl433-mqtt`
- run `systemctl daemon-reload`
- run `systemctl enable --now rtl433-mqtt.service`
- print installed service, config path, and log path

Existing local MQTT settings must be protected by default. Running
`sudo ./install.sh` after a `git pull --ff-only` should update the deployed
application files and service/logrotate definitions without overwriting
`/etc/rtl433-mqtt/rtl433-mqtt.env`.

The old Makefile may remain as a compatibility shim only if it delegates to the
new installer or is clearly documented as deprecated. The main documented path
should be `sudo ./install.sh`.

## Local JSONL Logging

Do not reintroduce the MQTT pipe for logging. Local JSONL logging should be
enabled by default as a separate `rtl_433` output:

```text
/var/log/rtl433-mqtt/rtl433-events.jsonl
```

The installer should create `/var/log/rtl433-mqtt` and install a logrotate
config at:

```text
/etc/logrotate.d/rtl433-mqtt
```

Use the same rotation policy as `s500-logger`:

```text
/var/log/rtl433-mqtt/*.jsonl {
    daily
    rotate 30
    dateext
    dateformat _%Y-%m-%d
    compress
    missingok
    notifempty
    create 0640 root root
}
```

The S500 logger avoids `copytruncate` because its Python logger opens JSONL
files per write. This repo should preserve that same no-`copytruncate` policy.
If `rtl_433 -F json:<file>` does not reopen the log file after rotation, the
logrotate config should restart `rtl433-mqtt.service` after rotation instead of
using `copytruncate`. The implementation should test this behavior and document
the selected path.

## Error Handling

The wrapper should fail before starting `rtl_433` if:

- TLS is enabled but the selected `rtl_433` binary does not advertise TLS
- no MQTT output category is enabled
- a TLS client cert or key is supplied without its pair
- local JSONL logging is enabled but the target log directory cannot be created
  or written

The wrapper should avoid printing passwords in logs. It may print the MQTT
scheme, host, port, base topic, enabled output categories, and `rtl_433` version.

## Testing

This shell-based repo does not currently have tests. Add focused verification
that does not require SDR hardware:

- shell syntax check with `bash -n rtl433-mqtt`
- a dry-run mode such as `RTL433_MQTT_PRINT_COMMAND=1` that prints the generated
  `rtl_433` command without executing it
- command-generation checks for default MQTT, TLS MQTT, topic override, disabled
  categories, password redaction, default JSONL logging, and JSONL logging
  disabled
- logrotate config checks for the S500-style daily, 30-rotation,
  date-suffixed, compressed, no-`copytruncate` policy
- installer checks for root enforcement, `--force-config`, existing-config
  preservation, `/opt` copy behavior, systemd unit install path, logrotate
  install path, and user-facing output
- documentation checks that README and deployment docs cover fresh install,
  configuration changes, application updates, config replacement, service
  operations, logs, MQTT topics, and `rtl_433` version expectations

Manual deployment verification on the target host:

1. Compile and install current `rtl_433` with TLS support.
2. Run `rtl_433 -V` and `rtl_433 -F help` to confirm the expected MQTT feature
   surface.
3. Install the updated service and env file.
4. Subscribe to `${base}/#` and confirm `availability`, `events`, `states`, and
   `devices` messages appear.
5. Confirm JSONL events are written to `/var/log/rtl433-mqtt/rtl433-events.jsonl`.
6. Force logrotate and confirm rotated logs receive `_YYYY-MM-DD` suffixes,
   compression is applied, and new events continue landing in the active JSONL
   file.
7. Restart the service and verify availability transitions.

## Out Of Scope

- Rewriting this repo as Python or another long-running supervisor.
- Adding Home Assistant discovery generation.
- Changing the S500 logger repository.
- Preserving compatibility with old `rtl_433` versions that lack native MQTT
  availability and TLS features.

## User Documentation

The README should match the S500 repo's high-level shape:

- short description of what the service does
- requirements, including a current compiled `rtl_433` newer than 25.12 with TLS
  support when TLS is needed
- quick install on Raspberry Pi:
  `git clone`, `cd rtl433-mqtt`, edit `config/rtl433-mqtt.env`, run
  `sudo ./install.sh`
- pointer to detailed deployment docs
- MQTT topic shape under the configured base topic
- test or verification commands that do not require SDR hardware where possible

Add detailed deployment documentation at
`docs/rtl433-mqtt-service-deployment.md`, modeled after
`docs/s500-service-deployment.md`. It should cover:

- fresh install flow
- the expected clone path on `stippler`, if known
- application update flow:
  `git pull --ff-only` followed by `sudo ./install.sh`
- config edit flow:
  edit `/etc/rtl433-mqtt/rtl433-mqtt.env` and restart the service
- config replacement flow:
  edit repo `config/rtl433-mqtt.env` and run
  `sudo ./install.sh --force-config`
- existing config protection
- service operations:
  `systemctl status`, `journalctl -u ... -f`, restart, stop
- local JSONL log paths and logrotate behavior
- MQTT boot/network behavior and native reconnect expectations
- MQTT payload and topic shape:
  `${base}/availability`, `${base}/events`, `${base}/states`, and
  `${base}/devices/...`
- target `rtl_433 -V` and `rtl_433 -F help` checks
