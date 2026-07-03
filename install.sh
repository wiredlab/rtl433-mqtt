#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR=/opt/rtl433-mqtt
CONFIG_SRC=config/rtl433-mqtt.env
CONFIG_DST=/etc/rtl433-mqtt/rtl433-mqtt.env
FORCE_CONFIG=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for arg in "$@"; do
    case "$arg" in
        --force-config)
            FORCE_CONFIG=1
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Usage: sudo ./install.sh [--force-config]" >&2
            exit 2
            ;;
    esac
done

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "This installer must be run as root: sudo ./install.sh" >&2
    exit 1
fi

cd "$SCRIPT_DIR"
mkdir -p "$INSTALL_DIR" /etc/rtl433-mqtt /var/log/rtl433-mqtt

rsync -a \
    --exclude .git \
    --exclude .direnv \
    --exclude .venv \
    --exclude .worktrees \
    --exclude __pycache__ \
    --exclude '*.pyc' \
    ./ "$INSTALL_DIR/"

if [[ -e "$CONFIG_DST" && "$FORCE_CONFIG" != "1" ]]; then
    echo "Keeping existing $CONFIG_DST"
else
    install -m 0640 "$INSTALL_DIR/$CONFIG_SRC" "$CONFIG_DST"
fi

install -m 0644 deploy/rtl433-mqtt.service /etc/systemd/system/rtl433-mqtt.service
install -m 0644 deploy/rtl433-mqtt-logrotate /etc/logrotate.d/rtl433-mqtt

systemctl daemon-reload
systemctl enable --now rtl433-mqtt.service

echo "Installed rtl433-mqtt.service"
echo "Config: $CONFIG_DST"
echo "Logs: /var/log/rtl433-mqtt/rtl433-events.jsonl"
