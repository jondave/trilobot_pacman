# Developing

For using the app, see [GET_STARTED.md](GET_STARTED.md). This page is for
changing this repository.

## Setup

This repo uses [uv](https://docs.astral.sh/uv/) (install it first). From the repo root:

```bash
uv sync                        # creates .venv with runtime + dev dependencies
bash scripts/fetch_vendor.sh   # optional: Blockly/Monaco for offline use
```

Dependencies live in `pyproject.toml` (runtime in `[project]`, pytest, ruff and
playwright in the `dev` group) and are locked in `uv.lock`; commit both. Add a
dependency with `uv add <pkg>` (or `uv add --dev <pkg>`), then `uv lock` is
done for you. CI and Docker use `uv sync --frozen`, so they fail if the lock is
stale. Without `fetch_vendor.sh` the page falls back to CDNs.

Library users are unaffected: they can still
`pip install -r control_scripts/requirements.txt` to use `control_scripts/client.py`.
A test checks those pins match `uv.lock`, so update both together.

## Running the app

```bash
uv run python control_scripts/blockly/app.py
```

then open <http://127.0.0.1:8750>.

## Running a fake robot

```bash
uv run python robot_scripts/robot_sender.py --fake --host 127.0.0.1 --port 8765
```

Fake mode needs no `trilobot` or `picamera2`; it streams synthetic frames and
logs motor and LED commands. Connect the app to `ws://127.0.0.1:8765`. The
tests use it through `tests/robot_helpers.py`.

## Tests and linting

```bash
uv run pytest
uv run ruff check .
```

CI (`.github/workflows/test.yaml`) runs both. `tests/test_consistency.py`
checks that blocks, toolbox, generator, config and the robot/client close codes
agree.

## Docker

```bash
docker build -t trilobot-pacman .
```

The image installs the locked runtime dependencies with `uv sync --frozen --no-dev`, fetches the
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

`.vscode/` is tracked. It selects `.venv` (managed by uv), enables pytest, formats Python with
Black on save, uses Ruff for linting, and resolves imports from
`control_scripts` and `control_scripts/blockly`. Recommended extensions are in
`extensions.json`. Launch configs: **Blockly app**, **Fake robot**, the compound
**App + fake robot**, and **pytest current file**. Tasks: **Fetch vendor libs**,
**uv sync**, **Run Blockly app (uv)**, **Run fake robot (uv)**,
**Tests (uv)** and **Ruff (uv)**.
