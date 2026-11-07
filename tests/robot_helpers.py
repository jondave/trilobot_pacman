"""Start robot_sender.py in --fake mode for tests (and browser end-to-end tests)."""

import contextlib
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROBOT_SENDER = Path(__file__).resolve().parents[1] / "robot_scripts" / "robot_sender.py"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _read_log(log):
    log.seek(0)
    return log.read().decode(errors="replace")


@contextlib.contextmanager
def fake_robot(timeout=10.0):
    """Run a fake robot on a free local port; yields its ws:// URL."""
    port = free_port()
    # A file, not a pipe, so a chatty robot log can never block the server.
    log = tempfile.TemporaryFile()
    process = subprocess.Popen(
        [
            sys.executable,
            str(ROBOT_SENDER),
            "--fake",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=log,
    )
    try:
        deadline = time.monotonic() + timeout
        while True:
            if process.poll() is not None:
                raise RuntimeError("fake robot exited: " + _read_log(log))
            with (
                contextlib.suppress(OSError),
                socket.create_connection(("127.0.0.1", port), timeout=0.2),
            ):
                break
            if time.monotonic() > deadline:
                raise RuntimeError("fake robot did not start")
            time.sleep(0.05)
        yield f"ws://127.0.0.1:{port}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()
