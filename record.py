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
import signal
import sys

from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from libcamera import Transform

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def _safe_directory(user_dir: str) -> str:
    """Return an absolute path inside PROJECT_DIR for a given user-supplied directory."""
    # Treat user_dir as relative to project dir if not absolute
    if os.path.isabs(user_dir):
        candidate = os.path.abspath(user_dir)
    else:
        candidate = os.path.abspath(os.path.join(PROJECT_DIR, user_dir))
    # Prevent directory traversal outside the project
    if not candidate.startswith(PROJECT_DIR):
        raise ValueError('Directory not allowed')
    return candidate

class CameraRecorder:
    def __init__(self, camera_id, hflip=False, vflip=False):
        self.camera = Picamera2(camera_id)
        self.encoder = H264Encoder(10000000)
        self.output_file = None
        self.output = None
        self.hflip = hflip
        self.vflip = vflip
        self.camera_id = camera_id
        self.is_started = False

    def configure(self):
        video_config = self.camera.create_video_configuration(
            transform=Transform(hflip=self.hflip, vflip=self.vflip),
            main={
                "size": (2592, 1944),
                "format": "RGB888",
            },  # Main stream for recording
            lores={
                "size": (640, 480),
                "format": "RGB888",
            },  # Low-res stream for preview
            controls={"FrameRate": 30},  # Set desired frame rate
        )

        self.camera.configure(video_config)
        self.camera.start()
        self.is_started = True

    def start_recording(self, output_file):
        import subprocess
        import logging
        if self.output is not None:
            self.stop_recording()
        
        self.output_file = output_file
        # Set FFREPORT so ffmpeg writes a report file we can inspect if it fails
        prev_ffreport = os.environ.get('FFREPORT')
        report_path = f"{output_file}.ffreport"
        os.environ['FFREPORT'] = f"file={report_path}:level=32"
        try:
            logging.info(f"Creating FfmpegOutput for {output_file} (ffreport={report_path})")
            self.output = FfmpegOutput(output_file)
            logging.info(f"FfmpegOutput created: {self.output}")
        except Exception as exc:
            logging.exception(f"Failed to create FfmpegOutput for {output_file}: {exc}")
            if prev_ffreport is None:
                del os.environ['FFREPORT']
            else:
                os.environ['FFREPORT'] = prev_ffreport
            raise
        try:
            logging.info(f"Calling camera.start_recording with encoder and output...")
            self.camera.start_recording(self.encoder, self.output)
            logging.info(f"Camera.start_recording returned for camera {self.camera_id}")
        except Exception as exc:
            logging.exception(f"Camera.start_recording failed for camera {self.camera_id}: {exc}")
            if prev_ffreport is None:
                del os.environ['FFREPORT']
            else:
                os.environ['FFREPORT'] = prev_ffreport
            raise
        # Restore prev FFREPORT in our process env (ffmpeg child already inherited it)
        if prev_ffreport is None:
            del os.environ['FFREPORT']
        else:
            os.environ['FFREPORT'] = prev_ffreport

        # give ffmpeg a moment to appear in process table
        time.sleep(0.2)
        try:
            ps_out = subprocess.check_output(['ps', '-eo', 'pid,cmd'], text=True, stderr=subprocess.DEVNULL)
            ffprocs = [l for l in ps_out.splitlines() if 'ffmpeg' in l]
            if ffprocs:
                logging.debug(f"ffmpeg processes detected after start: {ffprocs}")
            else:
                logging.warning("No ffmpeg processes detected after start")
        except Exception:
            logging.exception('Failed to inspect process list')

        logging.info(f"Recording started on camera {self.camera_id} to {output_file}")

    def stop_recording(self):
        import logging
        import time
        try:
            self.camera.stop_recording()
        except Exception as exc:
            logging.exception(f"Error stopping camera recording: {exc}")
        
        # Give ffmpeg time to finalize the file and close properly
        time.sleep(0.5)
        
        # Properly close the output to flush buffers and finalize the file
        if self.output is not None:
            try:
                self.output.stop()
            except AttributeError:
                # FfmpegOutput may not have stop(), just close the file
                pass
            except Exception as exc:
                logging.exception(f"Error stopping output: {exc}")
        
        print(f"Recording stopped on camera {self.camera_id}")
        self.output = None
        self.output_file = None

    def start_preview(self, preview_type=Preview.QT):
        self.camera.start_preview(preview_type)

    def stop_preview(self):
        self.camera.stop_preview()

    def stop(self):
        if self.output is not None:
            self.stop_recording()
        print(f"Shutting down camera {self.camera_id}...")
        self.camera.stop()
        self.is_started = False


def cleanup_cameras(cam1, cam2, preview_enabled):
    print("\nStopping recording and shutting down cameras...")
    cam2.stop_recording()
    cam1.stop_recording()

    if preview_enabled:
        cam1.stop_preview()
        cam2.stop_preview()

    cam2.stop()
    cam1.stop()
    print("Cameras stopped successfully")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Record video from two cameras.")
    parser.add_argument(
        "--output1",
        type=str,
        default="left_camera.mp4",
        help="Output filename for camera 1",
    )
    parser.add_argument(
        "--output2",
        type=str,
        default="right_camera.mp4",
        help="Output filename for camera 2",
    )
    parser.add_argument(
        "--duration", type=int, default=90, help="Recording duration in minutes"
    )
    parser.add_argument("--preview", action="store_true", help="Enable camera previews")
    parser.add_argument(
        "--directory", type=str, default="videos", help="Directory to save videos"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.directory, exist_ok=True)
    output1_path = _safe_directory(os.path.join(args.directory, args.output1))
    output2_path =_safe_directory(os.path.join(args.directory, args.output2))

    cam1 = CameraRecorder(0)
    cam2 = CameraRecorder(1)

    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        cleanup_cameras(cam1, cam2, args.preview)

    signal.signal(signal.SIGINT, signal_handler)

    if args.preview:
        cam1.start_preview()
        cam2.start_preview()

    cam1.configure()
    cam2.configure()

    print("Starting recording... Press Ctrl+C to stop")
    cam1.start_recording(output1_path)
    cam2.start_recording(output2_path)

    try:
        time.sleep(args.duration * 60)
        cleanup_cameras(cam1, cam2, args.preview)
    except KeyboardInterrupt:
        # This is a fallback in case the signal handler doesn't catch it
        cleanup_cameras(cam1, cam2, args.preview)


if __name__ == "__main__":
    main()
