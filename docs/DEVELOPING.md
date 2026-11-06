# Developing

For using the app, see [GET_STARTED.md](GET_STARTED.md). This page is for
changing this repository.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r control_scripts/blockly/requirements.txt pytest ruff
bash scripts/fetch_vendor.sh   # optional: Blockly/Monaco for offline use
```

`control_scripts/blockly/requirements.txt` pulls in `control_scripts/requirements.txt`
(the client library's dependencies) and adds the app-only packages (Flask, black).
On Debian/Raspberry Pi OS you may need `sudo apt install python3-venv` first.
Without `fetch_vendor.sh` the page falls back to CDNs.

## Running the app

```bash
.venv/bin/python control_scripts/blockly/app.py
```

then open <http://127.0.0.1:8750>.

## Running a fake robot

```bash
.venv/bin/python robot_scripts/robot_sender.py --fake --host 127.0.0.1 --port 8765
```

Fake mode needs no `trilobot` or `picamera2`; it streams synthetic frames and
logs motor and LED commands. Connect the app to `ws://127.0.0.1:8765`. The
tests use it through `tests/robot_helpers.py`.

## Tests and linting

```bash
.venv/bin/pytest
.venv/bin/ruff check
```

CI (`.github/workflows/test.yaml`) runs both. `tests/test_consistency.py`
checks that blocks, toolbox, generator, config and the robot/client close codes
agree.

## Docker

```bash
docker build -t trilobot-pacman .
```

The image installs `control_scripts/blockly/requirements.txt`, fetches the
vendor libraries and runs as a non-root user. To run it, see
[GET_STARTED.md](GET_STARTED.md).
`.github/workflows/build-container.yaml` builds and publishes the image.

## Repository layout

See the tree in the [README](../README.md#repository-layout). Constraints:
`robot_scripts/robot_sender.py` must stay standalone (it runs on the Pis and must
not import from `control_scripts`), and `control_scripts/client.py` keeps its
path, name and public API because students import it.

## Environment variables

| Variable | Default | Effect |
| --- | --- | --- |
| `HOST` | `127.0.0.1` (`0.0.0.0` in Docker) | address the app listens on |
| `PORT` | `8750` | port the app listens on |
| `PROGRAM_MAX_SECONDS` | `900` | longest a program may run |
| `PAGE_CLOSE_GRACE_SECONDS` | `5` | wait after the tab closes before stopping the program |
| `PAGE_HEARTBEAT_TIMEOUT_SECONDS` | `150` | stop the program if the page goes silent this long |
| `PAGE_RELEASE_AFTER_SECONDS` | `60` | release the robot this long after the page is gone |
| `TRILOBOT_USER_DEMOS_DIR` | `control_scripts/blockly/demos/saved` | where **Save as demo** writes (`/data/demos` in Docker) |

## VS Code

`.vscode/` is tracked. It selects `.venv`, enables pytest, formats Python with
Black on save, uses Ruff for linting, and resolves imports from
`control_scripts` and `control_scripts/blockly`. Recommended extensions are in
`extensions.json`. Launch configs: **Blockly app**, **Fake robot**, the compound
**App + fake robot**, and **pytest current file**. Tasks: **Fetch vendor libs**,
**Run tests**, **Ruff check**.
