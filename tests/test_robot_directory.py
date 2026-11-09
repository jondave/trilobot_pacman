"""/api/robots asks the robot directory afresh every time (no caching).

A local stub HTTP server stands in for findmyrobot; no real network.
"""

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import app as blockly_app
import pytest
import robot_directory

DIRECTORY_ROBOT = {
    "name": "trilo-1",
    "hostname": "trilo-1",
    "privateIP": "10.0.0.1",
    "lastPing": None,
}


class StubDirectory:
    """Counts requests; answers with ``robots``, a status code, or slowly."""

    def __init__(self):
        self.robots = [DIRECTORY_ROBOT]
        self.status = 200
        self.delay = 0.0
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - http.server API
                stub.requests.append(dict(self.headers))
                time.sleep(stub.delay)
                body = json.dumps(stub.robots).encode()
                try:
                    self.send_response(stub.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except OSError:
                    pass  # the client gave up (timeout test)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/robots"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def directory(monkeypatch):
    stub = StubDirectory()
    monkeypatch.setattr(robot_directory, "ROBOT_DIRECTORY_URL", stub.url)
    yield stub
    stub.close()


@pytest.fixture()
def client():
    return blockly_app.app.test_client()


def test_every_request_goes_to_the_directory(directory, client):
    for _ in range(3):
        response = client.get("/api/robots")
        assert response.status_code == 200
        robots = response.get_json()["robots"]
        assert [robot["ip"] for robot in robots] == ["10.0.0.1"]
    assert len(directory.requests) == 3


def test_directory_changes_show_at_once(directory, client):
    assert len(client.get("/api/robots").get_json()["robots"]) == 1
    directory.robots = [DIRECTORY_ROBOT, {**DIRECTORY_ROBOT, "privateIP": "10.0.0.2"}]
    assert len(client.get("/api/robots").get_json()["robots"]) == 2
    directory.robots = []
    assert client.get("/api/robots").get_json()["robots"] == []


def test_response_is_not_cacheable(directory, client):
    response = client.get("/api/robots")
    assert response.headers["Cache-Control"] == "no-store"
    # The directory itself is asked for a fresh answer too.
    assert directory.requests[0].get("Cache-Control") == "no-cache"


def test_no_old_list_after_directory_fails(directory, client):
    assert client.get("/api/robots").get_json()["robots"]
    directory.status = 500
    response = client.get("/api/robots")
    # Always 200, so the browser logs no failed request; the UI reads "error".
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()
    assert data["robots"] == []
    assert data["error"] == robot_directory.UNAVAILABLE_MESSAGE


def test_slow_directory_times_out(directory, client, monkeypatch):
    monkeypatch.setattr(robot_directory, "ROBOT_DIRECTORY_TIMEOUT", 0.3)
    directory.delay = 2.0
    started = time.monotonic()
    data = client.get("/api/robots").get_json()
    assert time.monotonic() - started < 1.5
    assert data["robots"] == [] and data["error"]


def test_unreachable_directory_reports_error(monkeypatch, client):
    with socket.socket() as sock:  # a port with nothing listening
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    monkeypatch.setattr(
        robot_directory, "ROBOT_DIRECTORY_URL", f"http://127.0.0.1:{port}/api/robots"
    )
    response = client.get("/api/robots")
    assert response.status_code == 200
    data = response.get_json()
    assert data["robots"] == [] and data["error"]


def test_unexpected_answer_reports_error(directory, client):
    directory.robots = "not a robot list"
    data = client.get("/api/robots").get_json()
    assert data["robots"] == [] and data["error"]


def test_default_timeout_is_short():
    assert 0 < robot_directory.ROBOT_DIRECTORY_TIMEOUT <= 3
