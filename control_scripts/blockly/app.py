#!/usr/bin/env python3
"""Beginner-friendly Blockly control server for a Trilobot."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, Response, abort, jsonify, render_template, request

# robot_session adds control_scripts/ (for client.py) to sys.path itself.
BLOCKLY_DIR = Path(__file__).resolve().parent
if str(BLOCKLY_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCKLY_DIR))

from blocks_python import (  # noqa: E402
    Unsupported,
    blocks_to_python,
    python_to_blocks,
)
from program_runner import MAX_PYTHON_CHARS, PageWatch, ProgramRunner  # noqa: E402
from robot_config import block_definitions, browser_config  # noqa: E402
from robot_directory import RobotDirectoryCache  # noqa: E402
from robot_session import RobotSession, _clamp, _number  # noqa: E402
from student_name import pick_name  # noqa: E402

LOG = logging.getLogger("trilobot_blockly")
app = Flask(__name__)
LIBRARY_DIR = Path(__file__).resolve().parent / "demos"
LIBRARY_DIR.mkdir(exist_ok=True)
# User-saved demos live in their own folder so a Docker volume can persist them.
USER_LIBRARY_DIR = Path(
    os.environ.get("TRILOBOT_USER_DEMOS_DIR") or LIBRARY_DIR / "saved"
)
USER_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

session = RobotSession(student_name=pick_name(os.environ.get("TRILOBOT_SESSION_NAME")))
runner = ProgramRunner(session)
# Stops the program and lets go of the robot when the app tab goes away.
page_watch = PageWatch(session, runner)
robot_directory_cache = RobotDirectoryCache()
# Open /api/video.mjpg responses; logged so a stream left open is easy to spot.
_open_video_streams = 0
_video_streams_lock = threading.Lock()


@app.get("/")
def index():
    return render_template(
        "index.html", config=browser_config(), blocks=block_definitions()
    )


@app.get("/favicon.ico")
def favicon():
    """Browsers ask for /favicon.ico on their own; serve the SVG icon."""
    return app.send_static_file("favicon.svg")


@app.get("/api/robots")
def robot_directory():
    """Proxy the robot directory so the browser does not depend on CORS.

    Served from a short in-memory cache (see RobotDirectoryCache), so a slow
    or unreachable directory never holds up the page.
    """
    # Always 200: an unavailable directory is reported in "error" (with
    # "stale": true), so the browser logs no failed request for it.
    return jsonify(robot_directory_cache.get())


@app.post("/api/connect")
def connect():
    try:
        payload = request.get_json(silent=True) or {}
        resume = payload.get("resume")
        robot_name = payload.get("robot_name")
        session.connect(
            payload.get("url"),
            payload.get("video"),
            bool(payload.get("force")),
            resume=resume if isinstance(resume, str) else None,
            robot_name=robot_name if isinstance(robot_name, str) else None,
        )
        return jsonify(session.status())
    except Exception as error:
        LOG.info("Connect request failed: %s", error)
        return jsonify({"error": str(error)}), 400


@app.post("/api/disconnect")
def disconnect():
    # Disconnecting first lets the runner record why the program stopped.
    session.disconnect()
    runner.stop()
    return jsonify(session.status())


@app.get("/api/status")
def status():
    # Only the app page's own polls (?page=<id>) count as its heartbeat, so
    # scripts or tests reading the status cannot keep a closed tab alive.
    page_watch.beat(request.args.get("page"))
    return jsonify({**session.status(), "program": runner.status()})


@app.post("/api/page/closing")
def page_closing():
    """navigator.sendBeacon from pagehide: the tab is closing or reloading."""
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.host:
        abort(403)
    page_watch.closing(request.get_data(as_text=True).strip())
    return "", 204


def _library_name(name):
    name = str(name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _()-]{0,63}", name):
        raise ValueError(
            "Demo name may use letters, numbers, spaces, hyphens, underscores, and brackets"
        )
    return name


def _library_files(name, directory=None):
    """Return the safe (blocks .json, python .py) paths for a demo.

    Without a directory, the user's saved demos take priority over bundled ones.
    """
    name = _library_name(name)
    if directory is None:
        directory = USER_LIBRARY_DIR
        if (
            not (directory / f"{name}.json").is_file()
            and not (directory / f"{name}.py").is_file()
        ):
            directory = LIBRARY_DIR
    return directory / f"{name}.json", directory / f"{name}.py"


def _unique_library_name(name):
    """Never overwrite an existing demo: append (1), (2), ... when needed."""
    name = _library_name(name)
    candidate, number = name, 0
    while any(
        (directory / f"{candidate}{suffix}").exists()
        for directory in (LIBRARY_DIR, USER_LIBRARY_DIR)
        for suffix in (".json", ".py")
    ):
        number += 1
        suffix = f" ({number})"
        candidate = name[: 64 - len(suffix)].rstrip() + suffix
    return candidate


def _validate_demo(path, kind):
    """Check that a library demo can be represented and run as blocks."""
    try:
        if kind == "python":
            program, _ = python_to_blocks(path.read_text(encoding="utf-8"))
        else:
            program = json.loads(path.read_text(encoding="utf-8"))
            generated = blocks_to_python(program)
            if "unsupported block:" in generated:
                raise ValueError("the workspace contains an unsupported block")
            python_to_blocks(generated)
        return {"block_compatible": True, "block_error": ""}
    except (OSError, ValueError, json.JSONDecodeError, Unsupported) as error:
        return {
            "block_compatible": False,
            "block_error": getattr(error, "message", None) or str(error),
            "block_line": getattr(error, "line", None),
        }


@app.get("/api/library")
def list_library():
    demos = []
    seen = set()
    for directory, saved in ((USER_LIBRARY_DIR, True), (LIBRARY_DIR, False)):
        for pattern, kind in (("*.json", "blocks"), ("*.py", "python")):
            for path in directory.glob(pattern):
                if path.stem in seen:
                    continue
                seen.add(path.stem)
                demos.append(
                    {
                        "name": path.stem,
                        "kind": kind,
                        "saved": saved,
                        **_validate_demo(path, kind),
                    }
                )
    demos.sort(key=lambda item: item["name"].lower())
    return jsonify({"demos": demos})


@app.get("/api/library/<name>")
def load_library(name):
    try:
        blocks_path, python_path = _library_files(name)
        if blocks_path.is_file():
            return jsonify(json.loads(blocks_path.read_text(encoding="utf-8")))
        if python_path.is_file():
            return jsonify({"python": python_path.read_text(encoding="utf-8")})
        return jsonify({"error": "Demo not found"}), 404
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/library/<name>")
def save_library(name):
    try:
        name = _unique_library_name(name)
        blocks_path, python_path = _library_files(name, USER_LIBRARY_DIR)
        program = request.get_json(silent=True)
        if isinstance(program, dict) and isinstance(program.get("python"), str):
            code = program["python"]
            if len(code) > MAX_PYTHON_CHARS:
                raise ValueError("That Python program is too long")
            path = python_path
            text = code if code.endswith("\n") else code + "\n"
        elif isinstance(program, dict) and isinstance(program.get("blocks"), dict):
            path = blocks_path
            text = json.dumps(program, indent=2) + "\n"
        else:
            raise ValueError("The saved Blockly program is not valid JSON")
        path.write_text(text, encoding="utf-8")
        return jsonify({"name": path.stem, "saved": True})
    except (OSError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/video/config")
def video_config():
    try:
        return jsonify(
            {"video": session.configure_video(request.get_json(silent=True))}
        )
    except Exception as error:
        return jsonify({"error": str(error)}), 409


@app.get("/api/video.mjpg")
def video():
    def stream():
        global _open_video_streams
        sequence = -1
        with _video_streams_lock:
            _open_video_streams += 1
            count = _open_video_streams
        LOG.info("Camera stream opened (%d open)", count)
        try:
            while True:
                # wait_jpeg returns the latest frame again after the timeout,
                # so a closed tab is noticed within about a second.
                jpeg, sequence = session.wait_jpeg(sequence, timeout=1.0)
                if jpeg:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Cache-Control: no-cache\r\n"
                        b"Content-Length: "
                        + str(len(jpeg)).encode()
                        + b"\r\n\r\n"
                        + jpeg
                        + b"\r\n"
                    )
        finally:
            with _video_streams_lock:
                _open_video_streams -= 1
                count = _open_video_streams
            LOG.info("Camera stream closed (%d open)", count)

    return Response(
        stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/video.jpg")
def video_snapshot():
    """The latest camera picture as one JPEG: the page shows it, greyed out,
    while the live stream is off, without holding a connection open."""
    jpeg, _ = session.wait_jpeg(None, timeout=0)
    return Response(jpeg, mimetype="image/jpeg", headers={"Cache-Control": "no-store"})


@app.post("/api/teleop")
def teleop():
    payload = request.get_json(silent=True) or {}
    try:
        if payload.get("stop"):
            session.dispatch("stop")
        else:
            left = _clamp(_number(payload.get("left")), -100, 100) / 100.0
            right = _clamp(_number(payload.get("right")), -100, 100) / 100.0
            session.dispatch("drive", left, right)
        return jsonify({"ok": True, "queued": True}), 202
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 409


@app.post("/api/lights/reset")
def reset_lights():
    try:
        session.reset_lights()
        return jsonify({"ok": True}), 202
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 409


def _require_local_request():
    """Refuse code-running requests that did not come from this machine's own page."""
    host = request.host.rsplit(":", 1)[0].strip("[]")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        abort(403)
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.host:
        abort(403)


@app.post("/api/python/generate")
def python_from_blocks():
    try:
        program = (request.get_json(silent=True) or {}).get("program")
        return jsonify({"code": blocks_to_python(program)})
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/python/to_blocks")
def python_to_blocks_route():
    code = (request.get_json(silent=True) or {}).get("code")
    if not isinstance(code, str) or len(code) > MAX_PYTHON_CHARS:
        return jsonify({"error": "The Python code is missing or too long"}), 400
    try:
        program, normalised = python_to_blocks(code)
        return jsonify({"ok": True, "program": program, "code": normalised})
    except Unsupported as error:
        return jsonify(
            {
                "ok": False,
                "syntax": error.syntax,
                "line": error.line,
                "message": error.message,
            }
        )


@app.post("/api/python/format")
def format_python():
    code = (request.get_json(silent=True) or {}).get("code")
    if not isinstance(code, str) or len(code) > MAX_PYTHON_CHARS:
        return jsonify({"error": "The Python code is missing or too long"}), 400
    try:
        import black

        formatted = black.format_str(code, mode=black.Mode(line_length=88))
        return jsonify({"code": formatted})
    except SyntaxError as error:
        return jsonify({"error": f"Line {getattr(error, 'lineno', '?')}: {error}"}), 400
    except Exception as error:
        # black raises InvalidInput for incomplete code; keep the editor intact.
        return jsonify({"error": str(error)}), 400


@app.post("/api/program/start")
def start_program():
    payload = request.get_json(silent=True) or {}
    if "python" in payload:
        _require_local_request()
    try:
        if "python" in payload:
            runner.start_python(payload["python"])
        else:
            runner.start(payload.get("program"))
        return jsonify(runner.status())
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/program/stop")
def stop_program():
    runner.stop()
    return jsonify(runner.status())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8750")),
        threaded=True,
    )
