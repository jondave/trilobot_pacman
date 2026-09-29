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

Then open [http://127.0.0.1:6767](http://127.0.0.1:6767). Enter the same robot
WebSocket address used by teleop, such as `ws://trilo-09:8765`, and press
**Connect**.

The **Robot actions**, **Camera / OpenCV**, **Distance sensor**, and **Lights**
categories contain the beginner blocks. Number and colour inputs are blocks,
so students can replace the example values. **Save file** downloads a JSON
trait file, and **Load file** restores one.

The live camera is the stage. Choose camera size, FPS, and JPEG quality below
it. The optional **Teleop reset** panel uses `u i o / j k l / m , .`; enable it
before driving, and release a key to stop.

The OpenCV block takes a snapshot and searches it for a sufficiently large HSV
colour region. The camera panel reports the last detection result.
