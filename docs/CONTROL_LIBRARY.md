# Control library

`control_scripts/client.py` is a small asyncio client for the robot's WebSocket.
Use it from your own scripts, outside the Blockly app. Students import it as:

```python
from client import RobotClient
```

so copy `client.py` into the same folder as your script (or put
`control_scripts/` on `PYTHONPATH`).

## Install

```bash
python3 -m pip install -r control_scripts/requirements.txt
```

This installs `websockets`, `opencv-python` and `numpy`. The robot itself is
set up as described in [robot_scripts/README.md](../robot_scripts/README.md).

## Connecting

```python
import asyncio
from client import RobotClient

async def main():
    async with RobotClient("ws://trilobot.local:8765") as robot:
        await robot.hello_event.wait()
        print("session", robot.session_name, "on", robot.robot_name)
        await robot.drive(0.5, 0.5)
        await asyncio.sleep(1)
        await robot.stop()

asyncio.run(main())
```

`RobotClient(url, *, max_size, on_message, open_timeout=5, ping_interval=5,
ping_timeout=5)`. Use it as an async context manager, or call `await open()` and
`await close()`. `open()` raises if the connection cannot be made. `close()`
sends a stop first. `abort()` drops the link immediately.

The robot sends a `hello` message on connect. Wait on `hello_event` and then
read `session_name`, `resume_token`, `robot_name` and `resumed` (also the raw
message in `hello`). Every JSON message is also passed to your `on_message`
callback if you supply one.

## Commands

All are coroutines returning `True` if sent, `False` if not connected.

| Method | Effect |
| --- | --- |
| `drive(left, right)` | wheel speeds, each -1.0 to 1.0 |
| `stop()` | stop the motors |
| `set_underlights(color)` | `(r, g, b)` with 0-255 values |
| `set_button_led(button, value)` | button `"A"`, `"B"`, `"X"` or `"Y"`, value 0.0-1.0 |
| `request_distance()` | ask for a distance reading |
| `configure_video(width, height, fps, jpeg_quality)` | camera settings |
| `send(message)` | send any JSON-serialisable dict |

The robot stops its motors if it hears nothing for 0.6 s, so keep re-sending
`drive` (the example does so every 0.1 s).

Supported video sizes are `640x480`, `1640x1232`, `1920x1080` and `3280x2464`;
FPS 1 to 30; JPEG quality 10 to 100. Smaller sizes and moderate quality
usually give the smoothest Wi-Fi video.

## Frames and telemetry

- `take_frame()` returns the newest frame as a BGR OpenCV array, or `None`
  if none arrived since the last call.
- `take_frame_bytes()` is the same but returns the raw JPEG bytes.
- `await next_frame_bytes()` waits for a newer JPEG; it returns `None` once
  the connection closes. `RobotClient.decode_frame(data)` decodes JPEG bytes.
- Only the newest frame is kept, so a slow loop never builds up delay.
- `telemetry` is the latest telemetry dict, for example `distance_cm` and
  `buttons` (`{"A": bool, ...}`).

## Sessions and close codes

Only one client drives a robot at a time. Each connection gets a random
two-word session name such as `Apple-Grape`. Connection state:
`connected`, `error`, `closed_event`, `close_code`, `close_reason`.

<a id="close-codes"></a>

| Code | Constant | Meaning |
| --- | --- | --- |
| 4001 | `CLOSE_BUSY` | The robot is in use. `busy_holder`, `busy_session` and `busy_since` say by whom. |
| 4002 | `CLOSE_TAKEN_OVER` | Someone else connected with `?force=1`. `kicked` is `True`; `taken_over_by` and `taken_over_at` say who and when. |
| 4003 | `CLOSE_REPLACED` | You reconnected with `?resume=<token>` and the robot closed your half-dead old socket. |

To take over a busy robot, connect to `ws://host:8765/?force=1`. To reconnect
as the same session after a brief drop (under 60 s), use
`ws://host:8765/?resume=<resume_token>`. The robot's side of this is in
[robot_scripts/README.md](../robot_scripts/README.md#sessions).

## Teleop example

`control_scripts/teleop_example.py` is a complete worked example: it connects,
configures video, sends `drive` every 0.1 s from key presses, shows
`take_frame()` frames with telemetry in an OpenCV window and calls `stop()` on
exit.

```bash
python3 control_scripts/teleop_example.py ws://trilobot.local:8765
python3 control_scripts/teleop_example.py ws://trilobot.local:8765 \
  --video-size 640x480 --fps 20 --jpeg-quality 70
```

### Teleop example keys

The movement keys form a grid:

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
- `Space`: stop; `ESC`: quit
