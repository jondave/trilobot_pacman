# Python guide

The **Python** tab runs real Python with the same robot functions the blocks use.
`cv2` and `numpy` (`np`) are available. Press F1 in the editor and choose
**Format document (Black)** to tidy your code.

| Function | What it does |
| --- | --- |
| `forward(seconds=2, power=60)` / `backward(...)` | drive straight, power 0–100 |
| `turn_left(seconds=1, power=60)` / `turn_right(...)` / `turn_around(...)` | spin on the spot |
| `drive(left, right)` | set both motors directly |
| `wait(seconds)` | pause |
| `stop()` | stop the motors |
| `distance()` | distance in cm |
| `button_pressed("A")` | `True` while a button is held |
| `wait_until(lambda: distance() < 20)` | pause until a condition is true |
| `set_lights("red")`, `lights_off()`, `flash_lights(...)` | underlights |
| `set_button_light("A", 1)` | button LED |
| `take_picture()` | camera image (BGR array) |
| `sees_colour("red")` | `True` if the colour is in view |
| `show_in_live_camera(image)` | show an image in the camera panel |
| `scan_robot_qr()` | read a robot QR code |
| `count(1, 10)` | numbers 1 to 10, for `for` loops |

Example:

```python
while distance() > 20:
    forward(seconds=0.3, power=50)
stop()
```

Saved demos are kept in the folder set by `TRILOBOT_USER_DEMOS_DIR`
(`/data/demos` in Docker; run with `-v trilobot_demos:/data/demos`).
