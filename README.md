# trilobot_pacman

## Folder layout

The robot code and control-PC code are deliberately separate:

- `robot_scripts/` is copied to and run on the Raspberry Pi.
- `control_scripts/` is copied to the control/lab PC.
- Student teleoperation work is kept completely outside this repository.
  Copy `control_scripts/client.py` beside a student teleop file when it needs
  to use `from client import RobotClient`.

`robot_sender.py` is the only program that runs on the robot. It controls the
motors, camera, distance sensor, physical buttons, and LEDs. It sends binary
JPEG frames and JSON telemetry over one WebSocket connection.

`client.py` is the reusable control-PC client. `teleop_example.py` is only
a basic example; students can write their own teleoperation program separately.

## Install

Run these commands from the `trilobot_pacman` folder.

On the robot:

```bash
python3 -m pip install -r robot_scripts/requirements.txt
```

The robot should already have the Pimoroni `trilobot` package and
`picamera2` installed through the Raspberry Pi/Pimoroni setup.

On the control/lab PC:

```bash
python3 -m pip install -r control_scripts/requirements.txt
```

## Run

Start the sender on the robot:

```bash
python3 robot_scripts/robot_sender.py
```

Then, on the control/lab PC, use the robot hostname or IP address:

```bash
python3 control_scripts/teleop_example.py ws://trilobot.local:8765
```

Video output can be selected from the control PC:

```bash
python3 control_scripts/teleop_example.py ws://trilobot.local:8765 \
  --video-size 640x480 --fps 20 --jpeg-quality 70
```

Supported sizes are `640x480`, `1640x1232`, `1920x1080`, and
`3280x2464`. FPS can be set from 1 to 30, and JPEG quality from 10 to 100.
Lower resolutions and moderate JPEG quality usually give the smoothest Wi-Fi
video.

The client import is intentionally local to `control_scripts`:

```python
from client import RobotClient
```

This works when the student file and the copied `client.py` are in the same
folder.

## Teleoperation controls

The example window is named `Trilobot Teleop` and displays the connection
target, camera settings, telemetry, and controls.

The movement keys are displayed as square buttons in this arrangement:

```text
u  i  o
j  k  l
m  ,  .
```

- `u/i/o`: forward-left, forward, forward-right
- `j/k/l`: turn-left, stop, turn-right
- `m/,/.`: reverse-left, reverse, reverse-right
- `H`/`h`: toggle the centre crosshair
- `q/z`: increase/decrease both speed settings
- `w/x`: increase/decrease linear speed
- `e/c`: increase/decrease turning speed
- `0`-`4`: set underlights
- `B/N/M/Y`: toggle the A/B/X/Y button LEDs
- `R`: request a distance reading
- `ESC`: quit

The sender uses a short exposure to reduce motion blur. The IMX219 is a
rolling-shutter camera, so fast movement can still produce geometric
rolling-shutter distortion.

The sender has a 0.6-second motor watchdog. If the client or Wi-Fi connection
disappears, the motors are stopped automatically.
