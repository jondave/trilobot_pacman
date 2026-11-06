# AGENTS.md

Guidance for AI coding agents and new contributors. See `docs/DEVELOPING.md` for more.

## What this is

A teaching tool: students program a Pimoroni Trilobot robot in Blockly or Python from the browser. Two parts:

- Robot server on the Pi: `robot_scripts/robot_sender.py` (websockets, port 8765).
- Lab-PC Flask app: `control_scripts/blockly/` (port 8750), usually run per-student in Docker.

## Layout

```
control_scripts/client.py          PUBLIC RobotClient library (students import it)
control_scripts/teleop_example.py  example student script
control_scripts/requirements.txt   client-library deps (pip-installable)
requirements-dev.txt               pip: runtime + pytest, ruff, playwright (pyproject/uv.lock mirror it for optional uv)
control_scripts/blockly/app.py     Flask routes, /api/status
  robot_session.py                 connection state machine, reconnect, command queue
  program_runner.py                runs student programs; PageWatch (tab-close handling)
  robot_config.py                  shared values (single source, embedded into the page)
  robot_directory.py               findmyrobot robot lookup
  blocks_python.py                 blocks <-> Python generator and parser
  static/blocks.json               block definitions
  static/js/*.js                   plain ES modules (main.js entry), static/style.css
  templates/index.html             page and Blockly toolbox
  demos/                           demo programs (.json blocks, .py)
robot_scripts/                     Pi side: robot_sender.py, session_words.json, systemd unit
scripts/fetch_vendor.sh            downloads Blockly + Monaco into static/vendor (gitignored)
tests/                             pytest; fake_ws.py, robot_helpers.py, conftest.py
docs/                              student and developer docs
```

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # runtime + dev deps
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/python control_scripts/blockly/app.py          # HOST (default 127.0.0.1), PORT (default 8750)
.venv/bin/python robot_scripts/robot_sender.py --fake --host 127.0.0.1 --port 8765
scripts/fetch_vendor.sh                   # optional: offline Blockly/Monaco
docker build -t trilobot-pacman .
docker run --rm -p 127.0.0.1:8750:8750 trilobot-pacman
```

Optional, uv instead of pip (never required): `uv sync`, `uv run pytest -q`, `uv add <pkg>`
(then mirror the pin in the requirements files and `pyproject.toml`).

## Hard rules

- `control_scripts/client.py` is a PUBLIC library imported by students' own scripts (`from client import RobotClient`). Do not move or rename it or break its API. `control_scripts/requirements.txt` must stay pip-installable.
- uv is opt-in and must never be required: pip + venv is the default path everywhere (Dockerfile, CI, VS Code tasks, docs). The pip requirements files (`control_scripts/requirements.txt`, `control_scripts/blockly/requirements.txt`, `requirements-dev.txt`) and `pyproject.toml`/`uv.lock` must stay in sync; change both together. `test_pip_requirements_match_pyproject` and `test_client_requirements_match_uv_lock` enforce it.
- `robot_scripts/robot_sender.py` runs on the Pi. Keep it standalone (no imports from `control_scripts`), compatible with Python 3.9, with `websockets>=12,<18`. Hardware imports stay lazy so `--fake` works on laptops.
- Protocol close codes (4001 busy, 4002 taken over/kicked, 4003 replaced) are duplicated deliberately in the robot and `client.py`; `test_close_codes_match_between_robot_and_client` checks them. Change both together.
- Block definitions live in `static/blocks.json`, shared values in `robot_config.py`. Add a block in `blocks.json`, the toolbox in `templates/index.html`, and `blocks_python.py` (generator and parser) together; drift tests in `tests/test_consistency.py` enforce this.
- Frontend: plain ES modules, no build step, no framework. Blockly 12.5.1 and Monaco are vendored at build time (`static/vendor` is gitignored) with a CDN fallback whose version must match `fetch_vendor.sh` (`test_blockly_version_matches_cdn_fallback`).
- Students are identified only by robot-given session names (word-word, from `session_words.json`). Never collect student names.
- Robots are reached across a VLAN: no mDNS or `.local` discovery. Use the findmyrobot directory or IP addresses.
- Security: the app executes student code and has no auth. Keep it bound to localhost in docs and Docker examples (`-p 127.0.0.1:8750:8750`).
- Stop must always stay enabled in the UI (`#stop-button`).

## Architecture notes

- Connection state machine: `RobotSession` (`robot_session.py`) states are idle, connecting, connected, weak, reconnecting, taken_over, busy, robot_offline. `/api/status` (`app.py`) exposes `connection.*` plus a bounded `events` list; the UI (`static/js/connection.js`) renders from it. Add states in both places.
- Resume tokens: the robot issues a `resume` token on connect; the session reuses it after the connection drops (and the app can pass `resume` on connect) so the robot treats it as the same student (`resumed` flag; the old socket is closed with 4003).
- Takeover/busy: a second client gets 4001 (busy) unless it connects with `force`, which evicts the holder with 4002.
- Tab close: `PageWatch` in `program_runner.py` uses the page's `/api/status?page=<id>` polls as a heartbeat; env-tunable `PAGE_CLOSE_GRACE_SECONDS`, `PAGE_HEARTBEAT_TIMEOUT_SECONDS`, `PAGE_RELEASE_AFTER_SECONDS` stop the program and release the robot.
- Program runner: `ProgramRunner` gives each run an id so stale output and stops from earlier runs are ignored; runs are capped by `PROGRAM_MAX_SECONDS` (default 900).
- Command coalescing: outgoing queue in `robot_session.py`; `stop` jumps the queue and `drive` (`COALESCED_COMMANDS`) keeps only the latest.

## Testing

Run `.venv/bin/pytest -q` and `.venv/bin/ruff check .` before finishing. For UI changes, also check in a browser against the fake robot (Playwright is in the dev group). `tests/fake_ws.py` is a protocol stub; `tests/robot_helpers.py` starts the real robot in `--fake` mode.

## Style

- Format Python with black (line length 88); ruff rules (E, F, W, I, B) come from `pyproject.toml`.
- CSS: use design tokens in `static/style.css` (no hard-coded colours); kebab-case class names.
