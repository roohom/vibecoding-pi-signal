#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=${APP_DIR:-$(dirname "$SCRIPT_DIR")}
PORT=${PORT:-8765}
BRIGHTNESS=${BRIGHTNESS:-24}
LED_COUNT=${LED_COUNT:-8}
LED_PIN=${LED_PIN:-18}
PYTHONPATH_EXTRA=${PYTHONPATH_EXTRA:-/home/pi/Desktop/HR-SLPTIME:/home/pi/rpi_ws281x/python}

sudo tee /etc/systemd/system/vibecoding-signal-ring.service >/dev/null <<SERVICE
[Unit]
Description=Vibecoding Signal Ring
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
Environment=PYTHONPATH=${PYTHONPATH_EXTRA}:${APP_DIR}
ExecStart=/usr/bin/python3 -m vibecoding_pi_signal.server --host 0.0.0.0 --port ${PORT} --brightness ${BRIGHTNESS} --count ${LED_COUNT} --pin ${LED_PIN}
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable vibecoding-signal-ring.service
sudo systemctl restart vibecoding-signal-ring.service
sudo systemctl status vibecoding-signal-ring.service --no-pager
