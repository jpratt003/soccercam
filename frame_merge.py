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
import torch
import argparse
import numpy as np
import os
import sys
from collections import deque

from ultralytics import YOLO

def letterbox_image(image, target_size=(640, 640), fill_value=(128, 128, 128)):
    """
    Resizes an image while preserving aspect ratio and pads it to the target size.

    Args:
        image (np.array): The input image (OpenCV format).
        target_size (tuple): The desired output size (width, height).
        fill_value (tuple): The color to fill the padded areas (BGR).

    Returns:
        np.array: The letterboxed image.
    """
    h, w = image.shape[:2]
    target_w, target_h = target_size

    scale = min(target_w / w, target_h / h)
    
    new_w = int(w * scale)
    new_h = int(h * scale)

    resized_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Create a new image filled with the fill_value
    letterboxed_image = np.full((target_h, target_w, 3), fill_value, dtype=np.uint8)

    # Calculate padding for centering
    pad_x = (target_w - new_w) // 2
    pad_y = (target_h - new_h) // 2

    # Place the resized image onto the new image
    letterboxed_image[pad_y:pad_y + new_h, pad_x:pad_x + new_w, :] = resized_image

    return letterboxed_image


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
        "--lookahead",
        type=int,
        default=2,
        help="Number of seconds to look ahead for detections",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Run YOLO on GPU (if available), otherwise use CPU",
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
        frame_rate1 = min(frame_rate1, frame_rate2)

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
    device = 'cuda' if torch.cuda.is_available() and args.gpu else 'cpu'
    model = YOLO("yolov8m.pt").to(device)
    lookahead_size = int(frame_rate1 * args.lookahead)
    cam1_detection_lookahead = deque(maxlen=lookahead_size)
    cam2_detection_lookahead = deque(maxlen=lookahead_size)
    cam1_lookahead_frames = deque(maxlen=lookahead_size)
    cam2_lookahead_frames = deque(maxlen=lookahead_size)

    print("Processing frames...")

    frame_count = 0
    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        if not (ret1 and ret2):
            break
        frame1 = cv2.flip(frame1, -1)
        frame2 = cv2.flip(frame2, -1)

        frame1_resized = letterbox_image(frame1)
        frame2_resized = letterbox_image(frame2)

        results1 = model(frame1_resized, verbose=False)
        results2 = model(frame2_resized, verbose=False)

        count1 = len(results1[0].boxes)
        count2 = len(results2[0].boxes)
        cam1_detection_lookahead.append(count1)
        cam2_detection_lookahead.append(count2)
        if args.debug:
            cam1_lookahead_frames.append(results1[0].plot())
            cam2_lookahead_frames.append(results2[0].plot())
        else:
            cam1_lookahead_frames.append(frame1)
            cam2_lookahead_frames.append(frame2)

        if len(cam1_detection_lookahead) < lookahead_size or len(cam2_detection_lookahead) < lookahead_size:
            continue

        cam1_score = sum(cam1_detection_lookahead)
        cam2_score = sum(cam2_detection_lookahead)
        frame1 = cam1_lookahead_frames.popleft()
        frame2 = cam2_lookahead_frames.popleft()
        if args.debug:
            print(f"Frame {frame_count}: Camera 1: {cam1_score}, Camera 2: {cam2_score}")

        frame_count += 1
        if frame_count % int(frame_rate1) == 0:
            print(f"Processed {frame_count / frame_rate1} seconds...")

        out_frame = frame1.copy() if cam1_score >= cam2_score else frame2.copy()
        out_cap.write(out_frame)

    cap1.release()
    cap2.release()
    out_cap.release()

if __name__ == "__main__":
    main()
