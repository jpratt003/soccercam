#!/usr/bin/env bash
# Uninstall the soccercam web systemd service
# Usage: sudo ./uninstall_service.sh

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run with sudo. Re-run using: sudo ./uninstall_service.sh"
  exit 1
fi

SERVICE_NAME="soccercam-web.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

systemctl disable --now $SERVICE_NAME || true
rm -f $SERVICE_PATH
systemctl daemon-reload

echo "Service removed: $SERVICE_NAME"
