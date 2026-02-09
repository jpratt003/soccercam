# Web Control

A simple Flask-based web UI is available to start and stop recordings from a browser.

Installation:

- Install Python dependencies: `pip install -r requirements.txt`
- Start the web server: `python3 web.py`
- Open `http://<raspi-ip>:5000` in a browser. Use the buttons to start/stop recording and set an optional duration.

Notes:

- The web UI talks directly to the same `CameraRecorder` implementation defined in `record.py` and will save files to the `videos/` directory by default.
- `picamera2` and `libcamera` are platform-specific (Raspberry Pi) and should be installed through your Pi package manager or as documented by the Raspberry Pi projects.

## Running as a systemd service (optional)

You can install the web UI as a systemd service so it starts at boot.

Install:

1. Run as root from the project directory:

   sudo ./install_service.sh

This will create `/etc/systemd/system/soccercam-web.service` and start/enable it.

Uninstall:

   sudo ./uninstall_service.sh

Check logs with:

   journalctl -u soccercam-web -f

