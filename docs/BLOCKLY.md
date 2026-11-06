# Blockly guide

Open the app (<http://localhost:8750>), choose your robot and press **Connect**.
If someone else is already using that robot you are asked whether to kick them
off; this ends all of that robot's active sessions. Each session has a random
two-word name such as `Apple-Grape`, shown next to **Connected**.

1. Open a category in the toolbox. The drawer stays open, so you can drag out
   several blocks in a row. Click the workspace to close it.
2. Snap blocks into **one** stack from top to bottom.
3. Press **Run**. Press **Stop** at any time.
4. **Save as demo** stores a named copy in the demo library (marked *(mine)*).
   An existing name is never overwritten; `(1)`, `(2)`… is added instead.
   **Save file** downloads a `.json` file and asks for a file name.
5. Teleop (`u i o / j k l / m , .`): the diagonal keys drive in an arc.

Start with the demo **Example task - Stop at the wall**.

| Category | What it does |
| --- | --- |
| Robot actions | forward, backward, turn, wait, stop |
| Loops / Logic | repeat, if, while, count |
| Distance sensor | read the distance in cm |
| Lights & colours | underlights and button lights |
| Camera / OpenCV | take a picture, find a colour, scan a QR code |

Use the Python tab to see the Python your blocks make.
