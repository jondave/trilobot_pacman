"""The /api/robots in-memory cache: stale-while-revalidate, no network."""

import threading
import time

import app as blockly_app
import pytest
import robot_directory
from robot_directory import RobotDirectoryCache

ROBOT = {"name": "trilo-1", "ip": "10.0.0.1", "url": "ws://10.0.0.1:8765"}


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FakeFetch:
    """Counts calls; can block (to see the refresh is in the background) or fail."""

    def __init__(self, result=None):
        self.calls = 0
        self.result = result if result is not None else [ROBOT]
        self.error = None
        self.gate = threading.Event()
        self.gate.set()
        self.finished = threading.Event()

    def __call__(self):
        self.calls += 1
        try:
            self.gate.wait(5)
            if self.error:
                raise self.error
            return list(self.result)
        finally:
            self.finished.set()

    def wait_finished(self):
        assert self.finished.wait(5)
        self.finished.clear()
        time.sleep(0.05)  # let the refresh thread store its result


def primed_cache(fetch, clock):
    cache = RobotDirectoryCache(fetch, ttl=60, first_wait=2.0, retry=10, clock=clock)
    assert cache.get()["robots"] == [ROBOT]
    fetch.wait_finished()
    return cache


def test_fresh_hit_does_not_call_upstream():
    fetch, clock = FakeFetch(), FakeClock()
    cache = primed_cache(fetch, clock)
    clock.now += 30
    answer = cache.get()
    assert answer["robots"] == [ROBOT]
    assert answer["stale"] is False
    assert "error" not in answer
    assert fetch.calls == 1


def test_stale_entry_served_at_once_with_one_background_refresh():
    fetch, clock = FakeFetch(), FakeClock()
    cache = primed_cache(fetch, clock)
    clock.now += 61
    fetch.gate.clear()  # the refresh blocks until released
    fetch.result = [ROBOT, {**ROBOT, "name": "trilo-2"}]
    started = time.monotonic()
    answers = [cache.get() for _ in range(5)]
    assert time.monotonic() - started < 0.5
    assert all(answer["robots"] == [ROBOT] for answer in answers)
    assert all(answer["stale"] for answer in answers)
    time.sleep(0.05)
    assert fetch.calls == 2  # one refresh, however many requests
    fetch.gate.set()
    fetch.wait_finished()
    answer = cache.get()
    assert len(answer["robots"]) == 2
    assert answer["stale"] is False
    assert fetch.calls == 2


def test_upstream_failure_keeps_last_good_list():
    fetch, clock = FakeFetch(), FakeClock()
    cache = primed_cache(fetch, clock)
    clock.now += 61
    fetch.error = OSError("directory down")
    cache.get()
    fetch.wait_finished()
    answer = cache.get()
    assert answer["robots"] == [ROBOT]
    assert answer["stale"] is True
    assert answer["error"]
    # No retry storm: within the back-off period upstream is left alone.
    calls = fetch.calls
    cache.get()
    assert fetch.calls == calls


def test_first_load_gives_up_after_about_two_seconds():
    fetch = FakeFetch()
    fetch.gate.clear()  # upstream never answers in time
    cache = RobotDirectoryCache(fetch, first_wait=2.0)
    started = time.monotonic()
    answer = cache.get()
    elapsed = time.monotonic() - started
    assert elapsed < 2.5
    assert answer["robots"] == []
    assert answer["error"]
    fetch.gate.set()


def test_first_load_failure_then_instant_answer():
    fetch = FakeFetch()
    fetch.error = OSError("no route to host")
    cache = RobotDirectoryCache(fetch)
    assert cache.get()["robots"] == []
    started = time.monotonic()
    answer = cache.get()
    assert time.monotonic() - started < 0.1
    assert answer["robots"] == [] and answer["error"]


@pytest.fixture()
def fresh_app_cache(monkeypatch):
    cache = RobotDirectoryCache()
    monkeypatch.setattr(blockly_app, "robot_directory_cache", cache)
    return cache


def test_route_uses_patched_fetch(monkeypatch, fresh_app_cache):
    calls = []

    def fake_fetch():
        calls.append(1)
        return [ROBOT]

    monkeypatch.setattr(robot_directory, "fetch_robot_directory", fake_fetch)
    client = blockly_app.app.test_client()
    for _ in range(3):
        response = client.get("/api/robots")
        assert response.status_code == 200
        assert response.get_json()["robots"] == [ROBOT]
    assert len(calls) == 1


def test_route_reports_error_when_nothing_cached(monkeypatch, fresh_app_cache):
    def failing_fetch():
        raise OSError("unreachable")

    monkeypatch.setattr(robot_directory, "fetch_robot_directory", failing_fetch)
    response = blockly_app.app.test_client().get("/api/robots")
    assert response.status_code == 200
    data = response.get_json()
    assert data["robots"] == [] and data["error"] and data["stale"] is True
