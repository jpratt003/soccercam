#!/usr/bin/env python3
# MIT License
# 
# Copyright (c) 2025 John Pratt
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import time
import argparse
import os

from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from libcamera import Transform

class CameraRecorder:
    def __init__(self, camera_id, output_file):
        self.camera = Picamera2(camera_id)
        self.output_file = output_file
        self.encoder = H264Encoder(10000000)
        self.output = FfmpegOutput(output_file)

    def configure(self, include_preview=False):
        video_config = self.camera.create_video_configuration()
        
        #main_config.transform = Transform(hflip=True, vflip=True)
        self.camera.configure(video_config)

    def start_recording(self):
        self.camera.start_recording(self.encoder, self.output)

    def stop_recording(self):
        self.camera.stop_recording()

    def start_preview(self, preview_type=Preview.QT):
        self.camera.start_preview(preview_type, hflip=True, vflip=True)

    def stop_preview(self):
        self.camera.stop_preview()

    def stop(self):
        self.camera.stop()

def main():
    parser = argparse.ArgumentParser(description="Record video from two cameras.")
    parser.add_argument('--output1', type=str, default='left_camera.mp4', help='Output filename for camera 1')
    parser.add_argument('--output2', type=str, default='right_camera.mp4', help='Output filename for camera 2')
    parser.add_argument('--duration', type=int, default=90, help='Recording duration in minutes')
    parser.add_argument('--preview', action='store_true', help='Enable camera previews')
    parser.add_argument('--directory', type=str, default='videos', help='Directory to save videos')

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.directory, exist_ok=True)
    output1_path = os.path.join(args.directory, args.output1)
    output2_path = os.path.join(args.directory, args.output2)

    cam1 = CameraRecorder(0, output1_path)
    cam2 = CameraRecorder(1, output2_path)

    if args.preview:
        cam1.start_preview()
        cam2.start_preview()

    cam1.configure()
    cam2.configure()

    cam1.start_recording()
    cam2.start_recording()

    time.sleep(args.duration * 60)

    cam2.stop_recording()
    cam1.stop_recording()

    if args.preview:
        cam1.stop_preview()
        cam2.stop_preview()

    cam2.stop()
    cam1.stop()


if __name__ == "__main__":
    main()