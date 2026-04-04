#!/usr/bin/env bash
# Install the soccercam web app as a systemd service and enable it at boot.
# Usage: sudo ./install_service.sh

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run with sudo. Re-run using: sudo ./install_service.sh"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$(command -v python3)"
SERVICE_NAME="soccercam-web.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
RUN_USER="${SUDO_USER:-pi}"

cat > /tmp/$SERVICE_NAME <<EOF
[Unit]
Description=SoccerCam Web UI
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON_BIN} ${PROJECT_DIR}/web.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

mv /tmp/$SERVICE_NAME $SERVICE_PATH
chmod 644 $SERVICE_PATH

systemctl daemon-reload
systemctl enable --now $SERVICE_NAME

echo "Service installed and started: $SERVICE_NAME"
systemctl status --no-pager $SERVICE_NAME || true

echo "To see logs: journalctl -u $SERVICE_NAME -f"
