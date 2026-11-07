# Blockly guide

Open the app (<http://localhost:8750>), choose your robot and press **Connect**.
If someone else is already using that robot you are asked whether to kick them
off; this ends all of that robot's active sessions. Each session has a random
two-word name such as `Apple-Grape`, shown next to **Connected**.

1. Open a category in the toolbox. The drawer stays open, so you can drag out
   several blocks in a row. Click the workspace to close it.
2. Snap blocks into **one** stack from top to bottom.
3. Press **Run**. Press **Stop** at any time.
4. **Save as demo** stores a named copy in the demo library (marked *(mine)*) in `control_scripts/blockly/demos/saved`, or in `$TRILOBOT_USER_DEMOS_DIR` if set (see [DEVELOPING.md](DEVELOPING.md#environment-variables); with Docker it is the `trilobot_demos` volume from [GET_STARTED.md](GET_STARTED.md)). Block demos are `.json`; Python demos are `.py` files that open in the Python tab (**Save as demo** there saves a `.py`).
   An existing name is never overwritten; `(1)`, `(2)`… is added instead.
   **Save file** downloads a `.json` file and asks for a file name.
5. Teleop: enable the **Teleop reset** panel under the camera before driving and release a key to stop. It uses the same key layout as the [teleop example](CONTROL_LIBRARY.md#teleop-example-keys).

Start with the demo **Example task - Stop at the wall**.

| Category | What it does |
| --- | --- |
| Robot actions | forward, backward, turn, wait, stop |
| Loops / Logic | repeat, if, while, count |
| Distance sensor | read the distance in cm |
| Lights & colours | underlights and button lights |
| Camera / OpenCV | take a picture, find a colour, scan a QR code |

Use the Python tab to see the Python your blocks make.

## Camera and OpenCV

The live camera is the stage; choose camera size, FPS and JPEG quality below
it. The Camera / OpenCV blocks follow the usual workflow: take an image, blur
it, convert BGR to HSV, make an HSV mask, count its white pixels and show an
image variable in the live camera. The **scan robot QR code** block reads codes
of the form `https://lcastor.lincoln.ac.uk/#trilo-XX` and returns `trilo-XX`.

## Demos and help

The demo library marks each demo with `✓ blocks` when it converts to blocks.
A quick start guide opens the first time the page is loaded; the **? Help**
button shows it again. Blocks produce real Python, so see the
[Python guide](PYTHON.md) for the functions and the editor.
