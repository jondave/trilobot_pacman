# Robot scripts

`robot_sender.py` runs on the Trilobot's Raspberry Pi and serves the robot over
WebSocket (port 8765). Install `requirements.txt` first, then run
`python3 robot_sender.py` by hand to test (`--host` and `--port` change the
listen address).

## Fake mode (no robot needed)

`python3 robot_sender.py --fake` runs on a laptop without the `trilobot` or
`picamera2` libraries. It streams synthetic camera frames (moving marker, clock
and session name), a slowly changing fake distance and buttons that are never
pressed, and it logs motor and LED commands instead of running them. The tests
use it via `tests/robot_helpers.py`.

## Sessions

Only one control client drives the robot at a time.

- `hello` includes `session` (a name like `Apple-Pairs`), `resume` (a secret
  token), `robot` (the Pi's hostname) and `resumed`.
- A second client gets `busy` (with `holder` and `since`) and is closed with
  code 4001.
- `?force=1` takes over: the old client gets `taken_over` (`by`, `at`) and is
  closed with code 4002.
- `?resume=<token>` reconnects as the same session, without `force`, if that
  session is still connected or dropped less than 60 s ago. A half-dead old
  socket is closed with code 4003.

Pings every 5 s detect dead connections within about 10 s. Video frames are
dropped, not queued, when the link is slow.

## Run at boot with systemd

1. Edit `trilobot-robot.service`: set `User`, `WorkingDirectory` and
   `ExecStart` (marked `CHANGE`).
2. Install and start it:

   ```bash
   sudo cp trilobot-robot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now trilobot-robot.service
   ```

3. Follow the logs:

   ```bash
   journalctl -u trilobot-robot -f
   ```

   Each connection logs a line such as `Control client connected as <session
   name>`, and rejected clients log `Rejected client; robot is in use by ...`.
   Takeovers log `<new> took over from <old>` and reconnects log
   `<name> resumed`.

Other commands: `sudo systemctl restart trilobot-robot`, `systemctl status
trilobot-robot`.
