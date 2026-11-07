"""Closing the app tab stops the program and, later, lets go of the robot."""

import time

import pytest
from fake_ws import FakeRobot
from program_runner import (
    PAGE_CLOSED_MESSAGE,
    PAGE_SILENT_MESSAGE,
    PageWatch,
    ProgramRunner,
)
from robot_session import RobotSession
from test_connection import connected, state, wait_for

LOOP = "while True:\n    wait(0.05)\n"


@pytest.fixture()
def robot():
    fake = FakeRobot()
    yield fake
    fake.close()


@pytest.fixture()
def rig(robot):
    session = RobotSession(
        backoff=(0.1, 0.2), offline_after=5, slow_retry=0.2, telemetry_timeout=1.0
    )
    runner = ProgramRunner(session)
    watches = []

    def make(**timings):
        watch = PageWatch(session, runner, **timings)
        watches.append(watch)
        session.connect(robot.url)
        wait_for(lambda: connected(session))
        runner.start_python(LOOP)
        wait_for(runner.is_running)
        return watch

    yield session, runner, make
    for watch in watches:
        watch.shutdown()
    runner.stop()
    session.disconnect()


def test_closing_beacon_without_poll_stops_program(rig):
    session, runner, make = rig
    watch = make(close_grace=0.3, heartbeat_timeout=60, release_after=30)
    watch.beat("page-a")
    watch.closing("page-a")
    # A late poll from the page that is closing does not cancel it.
    watch.beat("page-a")
    wait_for(lambda: not runner.is_running(), timeout=3)
    assert runner.status()["error"] == PAGE_CLOSED_MESSAGE
    assert any(e["text"] == PAGE_CLOSED_MESSAGE for e in session.status()["events"])
    # Still connected: only the program stops at this point.
    assert connected(session)


def test_poll_within_grace_keeps_program_running(rig):
    _session, runner, make = rig
    watch = make(close_grace=0.4, heartbeat_timeout=60, release_after=1.0)
    watch.beat("page-a")
    watch.closing("page-a")
    time.sleep(0.1)
    watch.beat("page-b")  # the reloaded page
    time.sleep(1.3)
    assert runner.is_running()


def test_heartbeat_timeout_stops_program_and_releases(rig, robot):
    session, runner, make = rig
    watch = make(close_grace=0.1, heartbeat_timeout=0.5, release_after=0.2)
    watch.beat("page-a")
    time.sleep(0.25)
    watch.beat("page-a")  # regular polls keep it alive
    time.sleep(0.35)
    assert runner.is_running()
    wait_for(lambda: not runner.is_running(), timeout=3)
    assert runner.status()["error"] == PAGE_SILENT_MESSAGE
    wait_for(lambda: state(session) == "idle", timeout=3)
    assert session.status()["connection"]["reason"] == "tab_closed"


def test_release_after_closing_disconnects_without_reconnect(rig, robot):
    session, runner, make = rig
    watch = make(close_grace=0.1, heartbeat_timeout=60, release_after=0.4)
    watch.beat("page-a")
    watch.closing("page-a")
    wait_for(lambda: not runner.is_running(), timeout=3)
    assert connected(session)
    wait_for(lambda: state(session) == "idle", timeout=3)
    status = session.status()
    connection = status["connection"]
    assert connection["reason"] == "tab_closed"
    assert "tab was closed" in connection["message"]
    assert any("tab was closed" in e["text"] for e in status["events"])
    # The program keeps the more precise reason it was stopped with.
    assert runner.status()["error"] == PAGE_CLOSED_MESSAGE
    # The resume token is kept for a reopened tab to reclaim its name.
    assert connection["resume"]
    attempts = len(robot.requests)
    time.sleep(0.8)
    assert len(robot.requests) == attempts
    assert state(session) == "idle"


def test_polls_without_page_id_are_not_heartbeats(rig):
    _session, runner, make = rig
    watch = make(close_grace=0.2, heartbeat_timeout=60, release_after=30)
    watch.beat("page-a")
    watch.closing("page-a")
    watch.beat(None)  # e.g. a script reading /api/status
    wait_for(lambda: not runner.is_running(), timeout=3)


def test_timings_from_env(monkeypatch):
    monkeypatch.setenv("PAGE_CLOSE_GRACE_SECONDS", "1.5")
    monkeypatch.setenv("PAGE_HEARTBEAT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("PAGE_RELEASE_AFTER_SECONDS", "nonsense")
    session = RobotSession()
    watch = PageWatch(session, ProgramRunner(session))
    assert (watch.close_grace, watch.heartbeat_timeout, watch.release_after) == (
        1.5,
        7.0,
        60.0,
    )


def test_closing_route_and_page_polls():
    import app as blockly_app

    client = blockly_app.app.test_client()
    watch = blockly_app.page_watch
    assert client.get("/api/status?page=route-page").status_code == 200
    assert watch.last_beat is not None and watch.closing_at is None
    assert client.post("/api/page/closing", data="route-page").status_code == 204
    assert "route-page" in watch.closed_pages and watch.closing_at is not None
    response = client.post(
        "/api/page/closing", data="x", headers={"Origin": "http://evil.example"}
    )
    assert response.status_code == 403
    client.get("/api/status?page=route-page-2")
    assert watch.closing_at is None
