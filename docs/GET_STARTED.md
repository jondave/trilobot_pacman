# Trilobot Pacman: student get started

You need:

- a computer with Docker installed;
- a Trilobot on the same network as your computer;
- the robot's password printed on the bottom of the robot.

## 1. Start the Blockly app

Open Docker Desktop. Then open a terminal on your computer and run:

```bash
docker run -p 127.0.0.1:8750:8750 -v trilobot_demos:/data/demos uolcs/trilobot_pacman
```

The `127.0.0.1:` prefix keeps the app reachable only from your own computer, because it can control the robot and run code with no password.

Your saved demos are kept in the `trilobot_demos` volume, so they survive restarts. See [the Blockly guide](BLOCKLY.md) and [the Python guide](PYTHON.md) for guides.

Leave this terminal running. Open a web browser and go to:

[http://localhost:8750](http://localhost:8750)

The robot list in the app shows each robot's name and private IP address.
Choose your robot from the list. If it is not listed, choose **Enter address
manually…** and edit the pre-filled WebSocket address, a helper will show you how to find the IP.

## 2. Connect to the robot

In the Blockly app, find your robot's IP address. Open another terminal on
your computer and SSH into the robot, replacing `XX.XX` with the last two
parts of its IP address:

```bash
ssh pi@10.247.XX.XX
```

Enter the password printed on the bottom of the robot. In the robot's terminal,
clone the code and start the robot script:

```bash
git clone https://github.com/jondave/trilobot_pacman
cd trilobot_pacman/robot_scripts
python robot_sender.py
```

If you already cloned the repository on the robot, skip the `git clone` command
and go to its `robot_scripts` folder. Leave this terminal running while you use
Blockly. Return to the browser, select your robot, and press **Connect**.
Robot-side setup is described in [robot_scripts/README.md](../robot_scripts/README.md).

## 3. Run a program

1. Drag blocks into the program workspace.
2. Connect to the robot.
3. Press **Run**.
4. Use **Stop** if the robot needs to halt.

When you are finished, press **Stop** in Blockly, then press `Ctrl+C` in the
robot SSH terminal and in the Docker terminal.
