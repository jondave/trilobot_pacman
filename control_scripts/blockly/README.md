# Blockly Lab

This is a separate, beginner-friendly web app for making simple Trilobot
behaviours with Blockly blocks. It does not change the existing teleoperation
program or the reusable WebSocket client.

## Start it on the control/lab PC

From the repository root:

```bash
cd /home/cheddar/code/trilobot_pacman
python3 -m venv .venv
.venv/bin/python -m pip install -r control_scripts/blockly/requirements.txt
.venv/bin/python control_scripts/blockly/app.py
```

If `python3 -m venv .venv` says that `venv` is missing on Debian/Raspberry Pi
OS, install it once with `sudo apt install python3-venv`, then repeat the
commands above. Do not install these packages into the system Python.

Then open [http://127.0.0.1:8750](http://127.0.0.1:8750). Enter the same robot
WebSocket address used by teleop, such as `ws://trilo-xx:8765`, and press
**Connect**.

The **Robot actions**, **Loops**, **Camera / OpenCV**, **Distance sensor**,
and **Lights & colours** categories contain the beginner blocks. The repeat
block is useful for patterns such as red lights, blue lights, red lights, blue
lights. The named colour actions snap into normal command chains. **Save file**
and **Load file** work with JSON files. The **Demo library** contains starter
traits; load one, change it, and use **Save as demo** to store a named copy in
`control_scripts/blockly/demos`. Block demos are `.json` files; Python demos
are plain `.py` files that open in the **Python** tab (they use `print()`,
functions and lists that blocks cannot show). **Save as demo** from the Python
tab saves a `.py` file.

A quick start guide opens the first time the page is loaded in a browser (it
remembers this in `localStorage`). The **? Help** button at the top right shows
it again.

Blocks run through the same Python API as the Python tab, so generated code is
real Python rather than a second robot language. The shared terminal is
available in both tabs. Python exposes the real `cv2`, `numpy`/`np`, and BGR
image values returned by `take_picture()`; `show_in_live_camera(image)` can
display a grayscale mask or colour image. The Camera / OpenCV blocks follow
the usual workflow: take a camera image, blur it, convert BGR to HSV, make an
HSV mask, count its white pixels, and show an image variable in the live
camera. `import cv2` and `import numpy as np` are setup-only imports when
switching Python back to blocks, so they do not need import blocks.
The **scan robot QR code** block/function reads codes in the form
`https://lcastor.lincoln.ac.uk/#trilo-XX` and returns `trilo-XX`.
The demo library marks each demo with `✓ blocks` after checking its Python or
workspace form through the same converter used by the editor. The OpenCV
step-by-step demo continuously captures, blurs, converts to HSV, converts the
HSV values back into a camera-friendly preview, and keeps that processed view
on screen until another image is shown or a new program starts.
In the Python editor, press F1 and choose **Format document (Black)**.

The live camera is the stage. Choose camera size, FPS, and JPEG quality below
it. The optional **Teleop reset** panel uses `u i o / j k l / m , .`; enable it
before driving, and release a key to stop.

The OpenCV block takes a snapshot and searches it for a sufficiently large HSV
colour region. The camera panel reports the last detection result.
