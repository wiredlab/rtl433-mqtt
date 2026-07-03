# rtl_433 Native MQTT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `mosquitto_pub` pipeline with native `rtl_433` MQTT publishing, default JSONL logging, and S500-shaped deployment/docs.

**Architecture:** Keep `rtl433-mqtt` as a focused Bash wrapper that validates environment, builds `rtl_433` output arguments, supports dry-run command inspection, and `exec`s `rtl_433`. Move deployment assets into `config/` and `deploy/`, add an `install.sh` that mirrors `s500-logger`, and cover behavior with shell-based tests.

**Tech Stack:** Bash, systemd unit files, logrotate, `rtl_433` newer than 25.12 with TLS support for TLS deployments, Python standard library `unittest` for repository tests.

## Global Constraints

- Target a modern compiled `rtl_433`, newer than 25.12.
- Use native `rtl_433` MQTT output; do not pipe JSON into `mosquitto_pub`.
- Default MQTT broker is `localhost:1883`.
- Use `availability`, `events`, `states`, `devices`, and `base=<topic>`.
- Write JSONL logs by default to `/var/log/rtl433-mqtt/rtl433-events.jsonl`.
- Install application files under `/opt/rtl433-mqtt`.
- Preserve configuration under `/etc/rtl433-mqtt/rtl433-mqtt.env` by default.
- Install logrotate at `/etc/logrotate.d/rtl433-mqtt`.
- Use daily, 30-rotation, date-suffixed, compressed logrotate without `copytruncate`.
- Do not print MQTT passwords in logs or dry-run output.

---

### Task 1: Test Harness And Expected Behavior

**Files:**
- Create: `tests/test_rtl433_mqtt.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: executable `rtl433-mqtt`
- Produces: command-generation and file-content tests for later tasks

- [ ] **Step 1: Write failing tests**

Create Python `unittest` tests that run `rtl433-mqtt` with `RTL433_MQTT_PRINT_COMMAND=1` and inspect generated output. Include tests for default MQTT/logging, TLS options, password redaction, disabled JSONL logging, all MQTT categories disabled error, deployment files, installer config preservation text, and docs coverage.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest discover -v`

Expected: failures because the current wrapper has no dry-run mode, no new deployment files, and docs do not cover the new install shape.

### Task 2: Native MQTT Wrapper

**Files:**
- Modify: `rtl433-mqtt`

**Interfaces:**
- Consumes: env vars from `config/rtl433-mqtt.env`
- Produces: `RTL433_MQTT_PRINT_COMMAND=1` dry-run and real `exec rtl_433 ...`

- [ ] **Step 1: Implement command generation**

Replace the pipe with Bash array-based command construction. Build `-F mqtt://...` or `-F mqtts://...`, export `MQTT_USERNAME` and `MQTT_PASSWORD`, map legacy `MQTT_USER`/`MQTT_PASS`, add enabled category options, add default JSONL output, keep metadata options, validate TLS and enabled categories, and avoid password logging.

- [ ] **Step 2: Run tests**

Run: `python3 -m unittest tests.test_rtl433_mqtt -v`

Expected: wrapper behavior tests pass; deployment/docs tests may still fail until later tasks.

### Task 3: Deployment Assets And Installer

**Files:**
- Create: `config/rtl433-mqtt.env`
- Create: `deploy/rtl433-mqtt.service`
- Create: `deploy/rtl433-mqtt-logrotate`
- Create: `install.sh`
- Modify: `Makefile`
- Modify: `rtl433-mqtt.env.example`
- Modify: `rtl433-mqtt.service.in`
- Modify: `rtl433-mqtt.logrotate`

**Interfaces:**
- Consumes: wrapper path `/opt/rtl433-mqtt/rtl433-mqtt`
- Produces: S500-shaped install flow

- [ ] **Step 1: Add deployment files**

Create config, service, logrotate, and installer files following the design. Keep legacy root files as compatibility pointers where useful.

- [ ] **Step 2: Run tests**

Run: `python3 -m unittest tests.test_rtl433_mqtt -v`

Expected: deployment tests pass; docs tests may still fail.

### Task 4: User Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/rtl433-mqtt-service-deployment.md`

**Interfaces:**
- Consumes: env names and paths from implementation
- Produces: user-facing install, update, config, service, logs, and MQTT docs

- [ ] **Step 1: Update docs**

Rewrite README into the S500 style and add detailed deployment docs covering fresh install, app update, config edit, force config replacement, service operations, logs, MQTT topics, and version checks.

- [ ] **Step 2: Run tests**

Run: `python3 -m unittest discover -v`

Expected: all tests pass.

### Task 5: Final Verification

**Files:**
- All changed files

**Interfaces:**
- Consumes: completed implementation
- Produces: verified working tree

- [ ] **Step 1: Run full verification**

Run:

```bash
bash -n rtl433-mqtt install.sh
python3 -m unittest discover -v
RTL433_MQTT_PRINT_COMMAND=1 ./rtl433-mqtt
```

Expected: shell syntax checks pass, unit tests pass, dry-run prints a redacted `rtl_433` command with native MQTT and JSONL outputs.
