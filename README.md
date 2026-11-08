<img src="control_scripts/blockly/static/favicon.svg" alt="Trilobot Blockly icon" width="64" height="64" align="right">

# Trilobot Pacman

Content in this repository is built for a workshop in how to make a class with Trilobot robots build a game of Pacman.

Tools for programming and driving a Pimoroni Trilobot robot over the network. There
are two parts:

- **Robot side** (`robot_scripts/`): `robot_sender.py` runs on the robot's
  Raspberry Pi and serves its motors, camera, distance sensor, buttons and LEDs
  over one WebSocket.
- **Control side** (`control_scripts/`): a Blockly/Python web app for students
  (`control_scripts/blockly/`) and a reusable Python client
  (`control_scripts/client.py`) for your own scripts.

## Quick start

1. Run the app on your computer (Docker command in [docs/GET_STARTED.md](docs/GET_STARTED.md)).
2. Start `robot_sender.py` on the robot or install it as a systemd service (same guide).
3. Open <http://localhost:8750>, choose the robot and press **Connect**.

## Repository layout

```text
robot_scripts/            runs on the robot (standalone, no imports from control_scripts)
  robot_sender.py         the WebSocket server
  trilobot-websocket.service  systemd unit
  install_service.sh      installs and starts the unit for this checkout
  ansible/deploy.yml      clones into /opt/trilobot_pacman and installs the unit on many robots
control_scripts/          runs on the control/lab PC
  client.py               RobotClient, imported by students as `from client import RobotClient`
  teleop_example.py       keyboard teleop example
  blockly/                the Blockly web app (app.py, static/, templates/, demos/)
docs/                     guides (below)
scripts/fetch_vendor.sh   downloads Blockly and Monaco for offline use
tests/                    pytest suite
.vscode/                  shared VS Code settings, launch configs and tasks
```

## Documentation

- [Getting started (students)](docs/GET_STARTED.md)
- [Blockly guide](docs/BLOCKLY.md)
- [Python guide](docs/PYTHON.md)
- [Control library: using `client.py` in your own scripts](docs/CONTROL_LIBRARY.md)
- [Robot setup and protocol](robot_scripts/README.md)
- [Developing this repository](docs/DEVELOPING.md)
