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
WebSocket address used by teleop, such as `ws://trilo-09:8765`, and press
**Connect**.

The **Robot actions**, **Loops**, **Camera / OpenCV**, **Distance sensor**,
and **Lights & colours** categories contain the beginner blocks. The repeat
block is useful for patterns such as red lights, blue lights, red lights, blue
lights. The named colour actions snap into normal command chains. **Save file**
and **Load file** work with JSON files. The **Demo library** contains starter
traits; load one, change it, and use **Save as demo** to store a named copy in
`control_scripts/blockly/demos`.

The live camera is the stage. Choose camera size, FPS, and JPEG quality below
it. The optional **Teleop reset** panel uses `u i o / j k l / m , .`; enable it
before driving, and release a key to stop.

The OpenCV block takes a snapshot and searches it for a sufficiently large HSV
colour region. The camera panel reports the last detection result.
