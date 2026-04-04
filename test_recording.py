#!/usr/bin/env python3
"""Simple test to verify recording works properly."""
import time
from record import CameraRecorder

# Test direct recording
print("Starting camera recorders...")
cam1 = CameraRecorder(0)
cam2 = CameraRecorder(1)

print("Configuring cameras...")
cam1.configure()
cam2.configure()

print("Starting recording for 2 seconds...")
cam1.start_recording("videos/test_simple_left.mp4")
cam2.start_recording("videos/test_simple_right.mp4")

time.sleep(2)

print("Stopping recording...")
cam1.stop_recording()
cam2.stop_recording()

print("Stopping cameras...")
cam1.stop()
cam2.stop()

print("Done!")

# Verify files
import os
for fname in ["videos/test_simple_left.mp4", "videos/test_simple_right.mp4"]:
    if os.path.exists(fname):
        size = os.path.getsize(fname)
        print(f"✓ {fname}: {size} bytes")
    else:
        print(f"✗ {fname}: NOT FOUND")
