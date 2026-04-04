#!/usr/bin/env python3
"""Simplified web test with a single camera."""
import subprocess
import time
import json
import requests

# Start web server
print("Starting web.py...")
proc = subprocess.Popen(
    ["python3", "web.py"],
    cwd="/home/jpratt/soccercam",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

time.sleep(3)

# Send start request for a short recording  
print("Sending start recording request...")
try:
    r = requests.post(
        "http://localhost:5000/start",
        json={"duration": 3, "directory": "videos/test_single", "left": "single_cam.mp4", "right": "single_right.mp4"},
        timeout=5
    )
    print(f"Start response: {r.status_code}")
except Exception as e:
    print(f"Start request failed: {e}")
    proc.terminate()
    exit(1)

# Wait
print("Waiting 5 seconds...")
time.sleep(5)

# Send stop request
print("Sending stop recording request...")
try:
    r = requests.post("http://localhost:5000/stop", timeout=5)
    print(f"Stop response: {r.status_code}")
except Exception as e:
    print(f"Stop request failed: {e}")

time.sleep(2)

# Check for files
import os
print("\n=== Checking created files ===")
for fname in ["single_cam.mp4", "single_right.mp4"]:
    fpath = f"/home/jpratt/soccercam/videos/test_single/{fname}"
    if os.path.exists(fpath):
        size =  os.path.getsize(fpath)
        print(f"✓ {fname}: {size} bytes")
    else:
        print(f"✗ {fname}: NOT FOUND")

proc.terminate()
