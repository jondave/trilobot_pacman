# Python programming reference

Every function you can use in the app's **Python** tab, with its arguments,
what it gives back and what to watch out for. For a shorter introduction, see
the [Python guide](PYTHON.md).

Your program is ordinary Python: variables, `if`, `while`, `for`, functions,
lists and `import` all work. The robot functions below are ready to use
without importing anything.

- [Moving](#moving)
- [Waiting](#waiting)
- [Sensors](#sensors)
- [Lights](#lights)
- [Camera and OpenCV](#camera-and-opencv)
- [Helpers](#helpers)
- [Colours and buttons](#colours-and-buttons)
- [How programs run](#how-programs-run)
- [Errors you might see](#errors-you-might-see)

## Moving

The move functions drive for a number of seconds, then stop the motors. Your
program waits until the move has finished before going on to the next line.

| Argument | Meaning | Allowed values |
| --- | --- | --- |
| `seconds` | how long to move | 0 or more (negative counts as 0); default `1` |
| `power` | how fast, as a percentage | 0 to 100 (outside that is clamped); default `60` |

### `forward(seconds=1, power=60)`

Drive straight forwards.

```python
forward()                       # 1 second at power 60
forward(seconds=2, power=40)    # slower, for longer
forward(0.5, 80)                # arguments can be given by position too
```

### `backward(seconds=1, power=60)`

Drive straight backwards.

### `turn_left(seconds=1, power=60)` / `turn_right(seconds=1, power=60)`

Spin on the spot: one wheel forwards, the other backwards. How far the robot
turns depends on `seconds`, `power` and the floor, so test and adjust. For
example, find the `seconds` that gives a quarter turn at power 60.

### `turn_around(seconds=1, power=60)`

Spin right on the spot, like `turn_right`. Choose `seconds` so it turns
half a circle on your floor.

### `drive(direction, seconds=1, power=60)`

Move in a direction chosen by a string, handy when the direction is in a
variable.

| `direction` | Same as |
| --- | --- |
| `"forward"` | `forward(...)` |
| `"backward"` | `backward(...)` |
| `"left"` | `turn_left(...)` |
| `"right"` | `turn_right(...)` |

```python
for direction in ["forward", "left", "forward", "right"]:
    drive(direction, seconds=0.5)
```

Any other direction raises `ValueError`.

### `stop()`

Stop the motors straight away. Moves already stop on their own when they
finish, so you mostly need `stop()` after a loop of short moves.

## Waiting

### `wait(seconds=1)`

Do nothing for `seconds` (0 or more). The motors are not driven while you
wait. The robot stops them by itself about 0.6 s after the last drive command.

### `wait_until(condition)`

Pause until `condition` is true, checking about 20 times a second. Pass a
function (usually a `lambda`) so it is checked again each time:

```python
wait_until(lambda: button_pressed("A"))       # wait for the A button
wait_until(lambda: distance() < 20)           # wait until something is close
```

`wait_until(distance() < 20)` without `lambda` checks only once, so it
either carries straight on or waits until you press Stop.

## Sensors

### `distance()`

The distance sensor reading in centimetres, as a float such as `34.7`.

If there is no reading (for example, nothing in range or the robot did not
answer in time), it returns `nan` ("not a number"). Every comparison with
`nan` is `False`, so both `distance() < 20` and `distance() > 20` are `False`.
Check for it with `math.isnan`:

```python
import math

reading = distance()
if math.isnan(reading):
    print("No distance reading")
elif reading < 20:
    stop()
```

Each call asks the robot for a fresh reading and takes about 0.1 s.

### `button_pressed(button)`

`True` while the button is held down, otherwise `False`. `button` is `"A"`,
`"B"`, `"X"` or `"Y"` (lowercase works too). Anything else raises
`ValueError`.

```python
while not button_pressed("A"):
    set_lights("yellow")
    wait(0.1)
lights_off()
```

## Lights

### `set_lights(colour)`

Turn all the underlights on in one colour. `colour` is a
[colour name](#colours-and-buttons) such as `"red"` or a hex code such as
`"#ff8800"`. An unknown colour raises `ValueError`.

### `lights_off()`

Turn the underlights off.

### `flash_lights(colour, times=3, on_seconds=0.2, off_seconds=0.2)`

Flash the underlights `times` times, then leave them off. `times` is rounded
down to a whole number; `on_seconds` and `off_seconds` are 0 or more.

```python
flash_lights("red", times=5, on_seconds=0.1, off_seconds=0.1)
```

### `set_button_light(button, brightness=1)`

Set the LED next to a button. `brightness` goes from `0` (off) to `1` (full);
values outside that are clamped.

```python
set_button_light("A", 1)      # on
set_button_light("A", 0.3)    # dim
set_button_light("A", 0)      # off
```

## Camera and OpenCV

`cv2` (OpenCV) and `np` / `numpy` (NumPy) are already loaded. Writing
`import cv2` or `import numpy as np` is fine too. Images are NumPy arrays in
OpenCV's usual **BGR** order (blue, green, red), with shape
`(height, width, 3)`. That means the same code works in your own Python
scripts outside the app.

### `take_picture()`

Return the newest camera picture as a NumPy array (a copy, so you can change
it freely). Raises `RuntimeError` if no camera picture has arrived yet, for
example straight after connecting.

```python
image = take_picture()
height, width = image.shape[:2]
print("Picture size:", width, "x", height)
```

### `sees_colour(colour, tolerance=18, min_area=500)`

`True` if a patch of `colour` at least `min_area` pixels in size is in view.

| Argument | Meaning | Allowed values |
| --- | --- | --- |
| `colour` | colour name or `"#rrggbb"` | see [Colours and buttons](#colours-and-buttons) |
| `tolerance` | how far the hue may be from the colour; bigger matches more shades | 1 to 90 (clamped); default `18` |
| `min_area` | smallest patch that counts, in pixels | 1 or more; default `500` |

**Which picture it checks:** the last `take_picture()` from this run if there
is one, otherwise the live camera. So if your program has called
`take_picture()`, call it again each time round a loop before `sees_colour`,
or it keeps checking the old picture:

```python
while True:
    take_picture()
    if sees_colour("red"):
        stop()
        break
    turn_left(seconds=0.2, power=50)
```

Under the hood it is a standard OpenCV recipe you can copy: convert to HSV,
`cv2.inRange` around the colour's hue, clean the mask with a small open/close,
then take the largest contour's area.

### `show_in_live_camera(image)`

Show your own image in the camera panel instead of the live video, for example
to see what your OpenCV processing does. `image` must be a NumPy array, either
greyscale `(height, width)` or colour `(height, width, 3 or 4)` in BGR order.
Values that are not 8-bit are clipped to 0–255. Anything else raises
`TypeError` or `ValueError`. The live video comes back when the next program
starts.

```python
image = take_picture()
edges = cv2.Canny(image, 100, 200)
show_in_live_camera(edges)
```

### `scan_robot_qr()`

Look for a robot's QR code in the live camera picture. Returns the robot's
name in lowercase, such as `"trilo-07"`, or `""` (an empty string) if none
is found. Only the robots' own QR codes count; other QR codes give `""`.

```python
name = scan_robot_qr()
if name:
    print("I can see", name)
```

## Helpers

### `count(start, stop, step=1)`

The numbers from `start` to `stop`, **including both ends**, for `for` loops.
It counts down if `start` is bigger than `stop`. The sign of `step` is
ignored, and a step of `0` raises `ValueError`.

```python
for n in count(1, 5):          # 1, 2, 3, 4, 5
    print(n)
for n in count(10, 0, 2):      # 10, 8, 6, 4, 2, 0
    print(n)
for x in count(0, 1, 0.25):    # 0.0, 0.25, 0.5, 0.75, 1.0
    print(x)
```

Python's own `range()` works too, but it leaves out the end number:
`range(1, 5)` is 1 to 4.

### `print(...)`

Shows text in the program output panel, like normal `print`. `sep` works;
`end` and `file` are ignored, and each call starts a new line. The panel keeps
the last 200 lines.

### `input()`

Not available: there is nowhere to type an answer while a program runs.
Calling it raises `RuntimeError`. Use the robot's buttons instead
(`button_pressed`).

## Colours and buttons

Colour names (any capitals) for `set_lights`, `flash_lights` and
`sees_colour`:

| Name | Hex |
| --- | --- |
| `"red"` | `#ff0000` |
| `"green"` | `#00ff00` |
| `"blue"` | `#0000ff` |
| `"yellow"` | `#ffff00` |
| `"white"` | `#ffffff` |
| `"purple"` | `#ff00ff` |

Any `"#rrggbb"` hex code works as well, for example `"#ff8800"` for orange.

Buttons: `"A"`, `"B"`, `"X"`, `"Y"`.

## How programs run

- **Run** starts your program from the top; pressing Run again stops the old
  one first.
- **Stop** works at any time, even inside `while True:`. Robot functions stop
  immediately; a loop with no robot functions in it is stopped within about
  2 seconds.
- The line that is running is highlighted in the editor.
- When a program ends, finishes with an error or is stopped, the motors stop
  and the underlights and button lights turn off.
- A program can run for at most 15 minutes (your teacher can change this),
  then it is stopped.
- A program also stops if the connection to the robot is lost, someone else
  takes over the robot, or you close the browser tab. The page tells you which.
- Programs can be up to 50,000 characters long.
- **Run** only works while you are connected to a robot.

## Errors you might see

Errors show the line they happened on, for example
`Line 4: ValueError: button must be A, B, X or Y`.

| Message | What it means |
| --- | --- |
| `Line N: invalid syntax` (or similar) | Python could not read that line: check brackets, colons and indentation. Nothing ran. |
| `NameError: name 'fowrard' is not defined` | A misspelt function or a variable used before it was set. |
| `TypeError: seconds must be a number` | An argument needs a number; `"2"` in quotes is text, not a number. |
| `ValueError: Unknown colour 'orange'` | Use a [colour name](#colours-and-buttons) or a `"#rrggbb"` code. |
| `ValueError: direction must be forward, backward, left or right` | Check the `drive()` direction. |
| `RuntimeError: No camera frame is available yet` | `take_picture()` ran before any video arrived. `wait(1)` first. |
| `RuntimeError: input() is not available here` | Use `button_pressed()` instead of `input()`. |
| `Write some Python before running` | The editor is empty. |
| `That Python program is too long` | Over 50,000 characters. |
