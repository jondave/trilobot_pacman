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

The client import is intentionally local to `control_scripts`:

```python
from client import RobotClient
```

This works when the student file and the copied `client.py` are in the same
folder.

Controls in the example use the ROS 2 keyboard layout:

```text
u i o
j k l
m , .
```

These keys move the robot. `k` or space stops. `q/z` change both speed
settings, `w/x` change linear speed, `e/c` change turning speed, and
`ESC` quits. `1`-`4` and `0` set the underlights. `B`, `N`, `M`,
and `Y` toggle the A, B, X, and Y button LEDs. `R` requests a distance
reading.

The sender has a 0.6-second motor watchdog. If the client or Wi-Fi connection
disappears, the motors are stopped automatically.
