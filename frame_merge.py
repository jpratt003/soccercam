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

import cv2
import math
import numpy as np
import argparse
import os
import sys

from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Select frame with most YOLO detections from two videos.")
    parser.add_argument(
        "--input1",
        type=str,
        default="left_camera.mp4",
        help="Path to first input video file",
    )
    parser.add_argument(
        "--input2",
        type=str,
        default="right_camera.mp4",
        help="Path to second input video file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="match.mp4",
        help="Output filename for selected video",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="videos",
        help="Directory to save output video",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Draw bounding boxes on output frames for debugging",
    )
    args = parser.parse_args()

    os.makedirs(args.directory, exist_ok=True)
    out_path = os.path.join(args.directory, args.output)
    in1_path = os.path.join(args.directory, args.input1)
    in2_path = os.path.join(args.directory, args.input2)

    cap1 = cv2.VideoCapture(in1_path)
    cap2 = cv2.VideoCapture(in2_path)
    if not cap1.isOpened() or not cap2.isOpened():
        print("Error opening video files")
        sys.exit(1)

    width1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
    height1 = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
    height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if height1 != height2 or width1 != width2:
        print(f"Frame sizes don't match! ({width1}x{height1}) != ({width2}x{height2})")
        sys.exit(1)

    frame_rate1 = math.floor(cap1.get(cv2.CAP_PROP_FPS))
    frame_rate2 = math.floor(cap2.get(cv2.CAP_PROP_FPS))
    if frame_rate1 != frame_rate2:
        print(f"Frame rates don't match! {frame_rate1} != {frame_rate2}")
        sys.exit(1)

    if args.debug:
        width1 = height1 = 640

    # Prepare output video writer
    if args.debug:
        print(f"Output video will be {width1}x{height1} at {frame_rate1} FPS")
    else:
        print(f"Output video will be {width1}x{height1} at {frame_rate1} FPS (debug mode off)")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_cap = cv2.VideoWriter(
        out_path, fourcc, float(frame_rate1), (width1, height1)
    )

    # Load a pre-trained YOLO model (e.g., YOLOv8n)
    # The model will be downloaded if not already present
    model = YOLO("yolov8n.pt")

    frame_count = 0
    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        if not (ret1 and ret2):
            break

        frame1_resized = cv2.resize(frame1, (640, 640))
        frame2_resized = cv2.resize(frame2, (640, 640))

        results1 = model(frame1_resized, verbose=False)
        results2 = model(frame2_resized, verbose=False)

        count1 = len(results1[0].boxes)
        count2 = len(results2[0].boxes)
        if args.debug:
            print(f"Frame {cap1.get(cv2.CAP_PROP_POS_FRAMES)}: Camera 1 detections: {count1}, Camera 2 detections: {count2}")

        frame_count += 1
        if frame_count % int(frame_rate1) == 0:
            print(f"Processed {frame_count / frame_rate1} seconds...")

        if args.debug:
            for result in results1:
                frame1_resized = result.plot()
            for result in results2:
                frame2_resized = result.plot()
            out_frame = frame1_resized.copy() if count1 >= count2 else frame1_resized.copy()
            out_cap.write(out_frame)
        else:
            out_frame = frame1.copy() if count1 >= count2 else frame2.copy()
            out_cap.write(out_frame)

    cap1.release()
    cap2.release()
    out_cap.release()

if __name__ == "__main__":
    main()
