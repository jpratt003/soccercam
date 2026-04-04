#!/usr/bin/env python3
"""Test script to run web.py and trace what happens."""
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
print("Web server started, waiting for readiness...")

# Try to hit status endpoint
try:
    r = requests.get("http://localhost:5000/status", timeout=5)
    print(f"Status endpoint: {r.status_code}")
    print(f"Response: {json.dumps(r.json(), indent=2)}")
except Exception as e:
    print(f"Status request failed: {e}")
    proc.terminate()
    exit(1)

# Send start request
print("\nSending start recording request...")
try:
    r = requests.post(
        "http://localhost:5000/start",
        json={"duration": 5, "directory": "videos/test_web", "left": "web_lb.mp4", "right": "web_rb.mp4"},
        timeout=5
    )
    print(f"Start response: {r.status_code}")
    print(f"Response: {json.dumps(r.json(), indent=2)}")
except Exception as e:
    print(f"Start request failed: {e}")
    proc.terminate()
    exit(1)

# Wait MUCH longer for ffmpeg to get data
print("\nWaiting 8 seconds for recording to accumulate...")
for i in range(8):
    time.sleep(1)
    # Check for ffmpeg processes
    import subprocess
    try:
        ps_out = subprocess.check_output("ps aux | grep ffmpeg | grep -v grep", shell=True, text=True)
        if ps_out.strip():
            print(f"  [{i+1}s] ffmpeg process running: {len(ps_out.split(chr(10)))} processes")
        else:
            print(f"  [{i+1}s] No ffmpeg processes found!")
    except:
        print(f"  [{i+1}s] ps command failed")

# Send stop request
print("\nSending stop recording request...")
try:
    r = requests.post("http://localhost:5000/stop", timeout=5)
    print(f"Stop response: {r.status_code}")
    print(f"Response: {json.dumps(r.json(), indent=2)}")
except Exception as e:
    print(f"Stop request failed: {e}")

# Wait for finalization
print("\nWaiting 2 seconds for file finalization...")
time.sleep(2)

# Check for created files
import os
print("\n=== Checking created files ===")
output_dir = "/home/jpratt/soccercam/videos/test_web"
for fname in ["web_lb.mp4", "web_rb.mp4"]:
    fpath = os.path.join(output_dir, fname)
    if os.path.exists(fpath):
        size = os.path.getsize(fpath)
        print(f"✓ {fname}: {size} bytes")
    else:
        print(f"✗ {fname}: NOT FOUND")

# Check stdout from web server
print("\n=== Web Server Output (FULL) ===")  
proc.terminate()
try:
    stdout, _ = proc.communicate(timeout=2)
    # Print last 50 lines
    lines = stdout.split('\n')
    print('\n'.join(lines[-50:]))
except:
    pass
