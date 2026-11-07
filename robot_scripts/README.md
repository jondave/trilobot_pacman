# Robot scripts

`robot_sender.py` runs on the Trilobot's Raspberry Pi and serves the robot over
WebSocket (port 8765). Install `requirements.txt` first (`python3 -m pip install -r requirements.txt`; the Pimoroni `trilobot` and `picamera2` packages must already be present), then run
`python3 robot_sender.py` by hand to test (`--host` and `--port` change the
listen address).

## Fake mode (no robot needed)

`python3 robot_sender.py --fake` runs on a laptop without the `trilobot` or
`picamera2` libraries. It streams synthetic camera frames (moving marker, clock
and session name), a slowly changing fake distance and buttons that are never
pressed, and it logs motor and LED commands instead of running them. See [docs/DEVELOPING.md](../docs/DEVELOPING.md) for running it with the app and tests.

The frames also show a simulated robot: a circle labelled `robot` with a line
pointing the way it faces. It starts near the bottom middle facing up and
drives with the motor commands (full speed is 0.35 of the frame width per
second, spinning on the spot is half a turn per second), stays inside the
frame, and stops with the 0.6 s motor watchdog. It is grey (150, 150, 150)
when the underlights are off, otherwise the average colour of the lit
underlights. The fake distance sensor reports how far its front is from the
frame edge it is facing, with the frame 200 cm wide (at most 400 cm), and fake
telemetry has an extra `sim` field (position, heading, wheel speeds and
colour) for debugging.

## Sessions

Only one control client drives the robot at a time.

- `?name=Grapes-Escape` sets the session name. The Blockly app picks one name
  per student and sends it to every robot, so a student has the same name on
  all of them. Names are two or three letter-only words joined by hyphens;
  a missing or invalid name gets a `LEARNER-ABCD` name.
- `hello` includes `session` (that name), `resume` (a secret token), `robot`
  (the Pi's hostname) and `resumed`.
- A second client gets `busy` (with `holder` and `since`) and is closed with
  code 4001.
- `?force=1` takes over: the old client gets `taken_over` (`by`, `at`) and is
  closed with code 4002. What clients should do with these codes is in
  [docs/CONTROL_LIBRARY.md](../docs/CONTROL_LIBRARY.md#close-codes).
- `?resume=<token>` reconnects as the same session, without `force`, if that
  session is still connected or dropped less than 60 s ago. A half-dead old
  socket is closed with code 4003.

Pings every 5 s detect dead connections within about 10 s. Video frames are
dropped, not queued, when the link is slow.

## Run at boot with systemd

From the `robot_scripts` folder on the robot:

```bash
sudo ./install_service.sh
```

This installs `trilobot-websocket.service` for wherever the checkout lives. It
fills in this folder's path, the user who ran `sudo`, and `python3` (from a
`.venv` in the repo or `robot_scripts/` if there is one; set `PYTHON=...` or
`SERVICE_USER=...` to choose). It also removes the old `trilobot-robot.service`
if it was installed. Run it again after moving the checkout.

Follow the logs:

```bash
journalctl -u trilobot-websocket -f
```

Each connection logs a line such as `Control client connected as <session
name>`, and rejected clients log `Rejected client; robot is in use by ...`.
Takeovers log `<new> took over from <old>` and reconnects log `<name> resumed`.

Other commands: `sudo systemctl restart trilobot-websocket`, `systemctl status
trilobot-websocket`.

To install by hand instead, copy `trilobot-websocket.service` to
`/etc/systemd/system/`, replace the `@USER@`, `@ROBOT_SCRIPTS@` and `@PYTHON@`
placeholders with absolute values, then run `sudo systemctl daemon-reload` and
`sudo systemctl enable --now trilobot-websocket`.

### Deploy to many robots with Ansible

`ansible/deploy.yml` clones the repo over HTTPS into `/opt/trilobot_pacman`
(owned by `pi`), installs `trilobot-websocket.service` for that folder, removes
the old `trilobot-robot.service` and starts the service. Re-running it pulls
the latest `main` and restarts the service only if something changed.

```bash
cd robot_scripts/ansible
cp inventory.example.ini inventory.ini   # robots' IP addresses and passwords
ansible-playbook -i inventory.ini deploy.yml
```

`inventory.ini` holds the SSH and sudo passwords (`ansible_password`,
`ansible_become_password`) and is git-ignored; never commit it. Password logins
need `sshpass` on the machine running Ansible (`sudo apt install sshpass`).

Override `repo_version`, `install_dir`, `service_user` or `python` with `-e`,
for example `-e repo_version=my-branch`. The robot's Python packages must
already be installed. Stop any `python3 robot_sender.py` you started by hand
first: only one copy can listen on port 8765.

## Control PC

Using the robot from your own scripts or the example teleop is covered in
[docs/CONTROL_LIBRARY.md](../docs/CONTROL_LIBRARY.md). The motor watchdog
stops the motors 0.6 s after the client or Wi-Fi connection disappears. The
camera uses a short exposure to reduce motion blur, but the IMX219 is a
rolling-shutter camera, so fast movement can still distort the image.
