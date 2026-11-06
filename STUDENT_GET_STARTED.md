# Trilobot Pacman: student get started

You need:

- a computer with Docker installed;
- a Trilobot on the same network as your computer;
- the robot's password printed on the bottom of the robot.

## 1. Start the Blockly app

On your computer, run:

```bash
docker run -p 127.0.0.1:8750:8750 -v trilobot_demos:/data/demos uolcs/trilobot_pacman
```

The `127.0.0.1:` prefix keeps the app reachable only from your own computer, because it can control the robot and run code with no password.

Your saved demos are kept in the `trilobot_demos` volume, so they survive restarts. See [docs/BLOCKLY.md](docs/BLOCKLY.md) and [docs/PYTHON.md](docs/PYTHON.md) for guides.

Leave this terminal running. Open the Blockly app in a browser:

[http://localhost:8750](http://localhost:8750)

The robot list in the app shows each robot's name and private IP address.
Choose your robot from the list. If it is not listed, choose **Enter address
manually…** and edit the pre-filled WebSocket address, a helper will show you how to find the IP.

## 2. Start the robot script

SSH into the robot using the same IP address:

```bash
ssh pi@ROBOT_IP
```

Enter the password printed on the bottom of the robot. Then run:

```bash
python3 ~/code/trilobot_pacman/robot_scripts/robot_sender.py
```

Don't worry: If `robot_sender.py` is not already on the robot, a helper will help you get it on the robot.

Leave this SSH terminal running while you use Blockly. Return to the browser,
select the robot, and press **Connect**.

## 3. Run a program

1. Drag blocks into the program workspace.
2. Connect to the robot.
3. Press **Run**.
4. Use **Stop** if the robot needs to halt.

When you are finished, press **Stop** in Blockly, then press `Ctrl+C` in the
robot SSH terminal and in the Docker terminal.
