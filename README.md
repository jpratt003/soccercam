# soccercam
## Open Source Soccer Camera

This project is designed to provide a simple, DIY soccer camera to make it easier for more players to get feedback on their play and improve. It attempts to use lower-cost components and provides plenty of opportunity for improvements within that space. The goal is to capture the moments of the game - good, bad, and learning opportunities - to help players improve.

## Parts & Assembly
The approach is to use a Raspberry Pi 5 with a pair of cameras and a tripod. 
I used these [wide-angle cameras](https://www.amazon.com/dp/B07L2SY756?ref=ppx_yo2ov_dt_b_fed_asin_title).  
A [Raspberry Pi 5](https://www.amazon.com/dp/B0CK2FCG1K?ref=ppx_yo2ov_dt_b_fed_asin_title) with an [SD card](https://www.amazon.com/dp/B07R8GVGN9?ref=ppx_yo2ov_dt_b_fed_asin_title) and [case](https://www.amazon.com/dp/B0CLYHPL5G?ref=ppx_yo2ov_dt_b_fed_asin_title). I used a [bigger power bank](https://www.amazon.com/dp/B0BF54MTCG?ref=ppx_yo2ov_dt_b_fed_asin_title), but it is excessive and doesn't supply enough current to run full speed anyway (don't worry, recording still works).
For the [tripod](https://www.amazon.com/dp/B09DY2652X?ref=ppx_yo2ov_dt_b_fed_asin_title), I used a smaller one. While there are probably reasonably-priced options for taller ones, I wanted to start a little cheaper.

For the initial MVP, I simply mounted them to a sheet of plexiglass with Gorilla tape. I plan to design a 3D printed case for it at some point soon.

Before you mount the cameras, make sure you use the rpicam-hello built into the Raspberry Pi to make sure you place cam0 on the left and cam1 on the right.

To make it easier to align the cameras, the best approach I've come up with is to use small bolts, nuts, & washers to allow them to pivot. **Ensure you focus the cameras**.

## Recording and Processing
The `record.py` script will capture both cameras to cam1/2.mp4 files on the pi. After these are copied over, you can use the crop script to grab any highlights. It's really just a reminder wrapper for ffmpeg commands (at least right now), so that's probably easier if you're familiar with ffmpeg already. 
You can use the `frame_merge.py` to combine the two images. A planned improvement is to select one of the two frames instead of setting them side-by-side. In a future version, the two images will be sitched together into a panorama and then cropped down to a single image based on activity. 

