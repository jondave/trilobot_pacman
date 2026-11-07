# Developing

For using the app, see [GET_STARTED.md](GET_STARTED.md). This page is for
changing this repository.

## Setup

Plain `venv` and `pip` are the supported way. From the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # runtime + pytest, ruff, playwright
bash scripts/fetch_vendor.sh                    # optional: Blockly/Monaco/Font Awesome for offline use
```

(Activate with `source .venv/bin/activate` if you prefer, then drop the
`.venv/bin/` prefixes below.) Without `fetch_vendor.sh` the page falls back to CDNs.
UI icons are Font Awesome Free 5 (`<i class="fas fa-…" aria-hidden="true">`, coloured
with the `.icon-*` classes in `style.css`), not emoji; `test_ui_has_no_emoji` checks this.
The one exception is the 🟢/🟠/🔴 ping dot in each robot `<option>` (an option can't hold an icon).

Pins live in the requirements files: `control_scripts/requirements.txt` (client
library), `control_scripts/blockly/requirements.txt` (adds Flask and black) and
`requirements-dev.txt` (adds pytest, ruff, playwright). To add a dependency, pin
it in the right requirements file AND in `pyproject.toml` (`[project]
dependencies` or the `dev` group). Tests in `tests/test_consistency.py`
(`test_pip_requirements_match_pyproject`, `test_client_requirements_match_uv_lock`)
fail if they drift. If you have uv, also run `uv lock`; otherwise say in your PR
that `uv.lock` needs refreshing.

Library users can `pip install -r control_scripts/requirements.txt` to use
`control_scripts/client.py`.

### Optional: uv

[uv](https://docs.astral.sh/uv/) works too, but is never required. `pyproject.toml`
and `uv.lock` exist for uv users only.

```bash
uv sync                  # creates .venv with runtime + dev dependencies
uv run pytest -q         # or: uv run ruff check ., uv run python control_scripts/blockly/app.py
```

With uv, add dependencies with `uv add <pkg>` (or `uv add --dev <pkg>`) AND mirror
the pin in the requirements files, since the tests enforce it.

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
.venv/bin/ruff check .
```

CI (`.github/workflows/test.yaml`) runs both with pip. `tests/test_consistency.py`
checks that blocks, toolbox, generator, config, the robot/client close codes and
the dependency pins agree.

## Docker

```bash
docker build -t trilobot-pacman .
```

The image installs `control_scripts/blockly/requirements.txt` with pip, fetches the
vendor libraries, migrates existing `/data/demos` volume ownership at startup, then
runs as a non-root user. To run it, see
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

## Dev container

`.devcontainer/devcontainer.json` builds the same setup automatically: it
installs OpenCV's system libraries, creates `.venv` with pip from
`requirements-dev.txt` and fetches the vendor libraries. The container's
`.venv` lives in a Docker volume, so it never clashes with a `.venv` on your
host. uv is installed in the container but stays optional. Ports 8750 (app)
and 8765 (fake robot) are forwarded.

## VS Code

`.vscode/` is tracked. It selects `.venv` (a plain venv or uv), enables pytest, formats Python with
Black on save, uses Ruff for linting, and resolves imports from
`control_scripts` and `control_scripts/blockly`. Recommended extensions are in
`extensions.json`. Launch configs: **Blockly app**, **Fake robot**, the compound
**App + fake robot**, and **pytest current file**. Tasks: **Fetch vendor libs**,
**Install deps (pip)**, **Run Blockly app**, **Run fake robot**, **Tests** and
**Ruff**, plus optional uv variants (**uv sync (optional)** and the
`(optional, uv)` tasks).
