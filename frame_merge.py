import cv2
import math
import numpy as np

# Create a VideoCapture object
cam1_path= '/home/jpratt/code/soccercam/stenger1cam1.mp4'
cam2_path= '/home/jpratt/code/soccercam/stenger1cam2.mp4'
cap1 = cv2.VideoCapture(cam1_path)
cap2 = cv2.VideoCapture(cam2_path)

width1 = cap1.get(cv2.CAP_PROP_FRAME_WIDTH)
width2 = cap2.get(cv2.CAP_PROP_FRAME_WIDTH)
height1 = cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)
height2 = cap2.get(cv2.CAP_PROP_FRAME_HEIGHT)
if height1 != height2:
    print(f"Heights don't match! {height1} != {height2}")
    exit(1)

bar_width=20
frame_rate1=math.floor(cap1.get(cv2.CAP_PROP_FPS))
frame_rate2=math.floor(cap2.get(cv2.CAP_PROP_FPS))
if frame_rate1 != frame_rate2:
    print(f"Frame rates don't match! {frame_rate1} != {frame_rate2}")
    exit(1)

out_path= '/home/jpratt/code/soccercam/stenger1combined.mp4'
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out_cap = cv2.VideoWriter(out_path, fourcc, float(frame_rate1), (int(width1+width2),int(height1)))
# out_cap = cv2.VideoWriter(out_path, fourcc, 32.0, (2560, 720))

# Check if the video file was opened successfully
if not cap1.isOpened() or not cap2.isOpened():
    print("Error opening video files")
    exit(1)

# Read, combine, and write frames. 
while cap1.isOpened() and cap2.isOpened():
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()
    if ret1 and ret2:
        # Combine the frames into a pair.
        out_frame = np.concatenate((frame1, frame2), axis=1)
        out_cap.write(out_frame)

    else:
        break

# Release the VideoCapture object and close all windows
cap1.release()
cap2.release()
out_cap.release()
