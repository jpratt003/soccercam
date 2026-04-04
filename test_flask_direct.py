#!/usr/bin/env python3
"""Minimal Flask app to test if issue is Flask-specific."""
from flask import Flask
from record import CameraRecorder
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

def record_in_thread():
    """Run recording in a thread."""
    print("Starting recording from Flask thread...")
    cam = CameraRecorder(0)
    cam.configure()
    cam.start_recording('videos/test_flask_thread.mp4')
    time.sleep(3)
    cam.stop_recording()
    cam.stop()
    print("Recording completed")

@app.route('/record', methods=['POST'])
def record():
    """Start recording in a background thread."""
    t = threading.Thread(target=record_in_thread, daemon=False)
    t.start()
    t.join()  # Wait for it to complete
    return {'ok': True}

@app.route('/ping', methods=['GET'])
def ping():
    return {'ping': 'pong'}

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(host='localhost', port=5555, debug=False)
