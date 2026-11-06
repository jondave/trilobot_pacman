"""Connection state machine tests against a stub robot websocket server."""

import time

import pytest
from fake_ws import FakeRobot, free_port
from program_runner import ProgramRunner
from robot_session import COMMAND_QUEUE_LIMIT, RobotSession, _with_query


def wait_for(condition, timeout=5.0, interval=0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError("timed out waiting for condition")


@pytest.fixture()
def robot():
    fake = FakeRobot()
    yield fake
    fake.close()


@pytest.fixture()
def session():
    robot_session = RobotSession(
        backoff=(0.1, 0.2), offline_after=5, slow_retry=0.2, telemetry_timeout=1.0
    )
    transitions, reasons = [], []

    def record(old, new, reason):
        transitions.append(new)
        reasons.append((new, reason))

    robot_session.add_state_listener(record)
    robot_session.transitions = transitions
    robot_session.reasons = reasons
    yield robot_session
    robot_session.disconnect()


def state(session):
    return session.status()["connection"]["state"]


def connected(session):
    return state(session) in ("connected", "weak")


def test_connected_state_and_fields(robot, session):
    session.connect(robot.url, robot_name="trilo-07")
    wait_for(lambda: connected(session))
    wait_for(lambda: session.status()["connection"]["last_frame_age"] is not None)
    status = session.status()
    connection = status["connection"]
    assert status["connected"] is True
    assert connection["reason"] is None
    assert connection["session"] == "Fake-1"
    assert connection["robot"] == "trilo-07"
    assert connection["url"] == robot.url
    assert connection["resume"] in robot.sessions
    assert connection["attempt"] == 0
    assert connection["holder"] is None
    assert "Fake-1" in connection["message"]
    assert isinstance(connection["since"], float)
    assert connection["telemetry_age"] is not None
    # Existing health fields are kept alongside the new ones.
    assert {"health", "video_hz", "last_frame_ms"} <= connection.keys()
    assert any("Fake-1" in event["text"] for event in status["events"])
    ids = [event["id"] for event in status["events"]]
    assert ids == sorted(ids)
    assert robot.requests == [{}]

    session.disconnect()
    connection = session.status()["connection"]
    assert (connection["state"], connection["reason"]) == ("idle", "user")


def test_busy_reports_holder_and_does_not_retry(robot, session):
    robot.busy_holder = "Kiwi-Lemon"
    session.connect(robot.url)
    wait_for(lambda: state(session) == "busy")
    connection = session.status()["connection"]
    assert connection["reason"] == "busy"
    assert connection["holder"] == "Kiwi-Lemon"
    assert "Kiwi-Lemon" in connection["message"]
    time.sleep(0.6)
    assert len(robot.requests) == 1
    assert state(session) == "busy"


def test_force_is_sent_only_once(robot, session):
    session.connect(robot.url, force=True)
    wait_for(lambda: connected(session))
    assert robot.requests == [{"force": "1"}]
    robot.drop()
    wait_for(lambda: len(robot.requests) == 2 and connected(session))
    assert "force" not in robot.requests[1]


def test_taken_over_stops_program_and_does_not_retry(robot, session):
    runner = ProgramRunner(session)
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    runner.start_python("while True:\n    wait(0.05)\n")
    wait_for(runner.is_running)

    robot.take_over("Pear-Plum")
    wait_for(lambda: state(session) == "taken_over")
    connection = session.status()["connection"]
    assert connection["reason"] == "taken_over"
    assert connection["holder"] == "Pear-Plum"
    wait_for(lambda: not runner.is_running())
    program = runner.status()
    assert program["status"] == "stopped"
    assert program["error"] == (
        "Your program was stopped because Pear-Plum took control of the robot."
    )
    time.sleep(0.6)
    assert len(robot.requests) == 1
    assert state(session) == "taken_over"


def test_abrupt_drop_reconnects_with_resume_token(robot, session):
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    token = session.status()["connection"]["resume"]

    robot.drop()
    wait_for(lambda: "reconnecting" in session.transitions)
    wait_for(lambda: len(robot.requests) == 2 and connected(session))
    assert robot.requests[1] == {"resume": token}
    status = session.status()
    assert status["connection"]["session"] == "Fake-1"
    texts = [event["text"] for event in status["events"]]
    assert "Reconnected as Fake-1" in texts
    assert ("reconnecting", "wifi") in session.reasons
    reconnecting_at = session.transitions.index("reconnecting")
    assert "connected" in session.transitions[reconnecting_at:]


def test_reconnect_with_new_name_is_announced(robot, session):
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    robot.sessions.clear()  # the robot forgot us, so the token is rejected
    robot.drop()
    wait_for(lambda: len(robot.requests) == 2 and connected(session))
    texts = [event["text"] for event in session.status()["events"]]
    assert "Reconnected as Fake-2 (you were Fake-1 before)" in texts


def test_silent_robot_counts_as_wifi_drop(robot, session):
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    robot.send_telemetry = False
    wait_for(lambda: "reconnecting" in session.transitions, timeout=4)
    assert ("reconnecting", "wifi") in session.reasons
    robot.send_telemetry = True
    wait_for(lambda: len(robot.requests) >= 2 and connected(session))


def test_refused_first_connect_is_robot_offline(session):
    session.connect(f"ws://127.0.0.1:{free_port()}")  # nothing listening
    wait_for(lambda: state(session) == "robot_offline")
    connection = session.status()["connection"]
    assert connection["reason"] == "refused"
    # Slow retries keep going in the background.
    wait_for(lambda: session.status()["connection"]["attempt"] >= 2)


def test_max_run_time_stops_program():
    runner = ProgramRunner(RobotSession(), max_seconds=0.3)
    runner.start_python("while True:\n    wait(0.05)\n")
    wait_for(lambda: runner.status()["status"] != "running", timeout=3)
    program = runner.status()
    assert program["status"] == "stopped"
    assert program["error"].startswith("Your program was stopped after ")
    assert program["error"].endswith(" minutes (time limit).")


def test_max_run_time_from_env(monkeypatch):
    monkeypatch.setenv("PROGRAM_MAX_SECONDS", "0.2")
    runner = ProgramRunner(RobotSession())
    runner.start_python("while True:\n    pass\n")
    wait_for(lambda: runner.status()["status"] != "running", timeout=4)
    assert runner.status()["error"].endswith("(time limit).")
    monkeypatch.setenv("PROGRAM_MAX_SECONDS", "900")
    assert ProgramRunner(RobotSession())._program_max_seconds() == 900


def test_drive_commands_coalesce(robot, session):
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    # Holding the lock stalls the sender, as a slow link would.
    with session.lock:
        for step in range(1, 51):
            session.dispatch("drive", step / 100, step / 100)
        session.dispatch("set_underlights", (1, 2, 3))
    wait_for(lambda: robot.commands("drive"))
    time.sleep(0.2)
    drives = robot.commands("drive")
    assert len(drives) == 1
    assert drives[0]["left"] == 0.5
    assert robot.commands("underlights")


def test_stop_jumps_queue_and_cancels_pending_drive(robot, session):
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    with session.lock:
        session.dispatch("set_underlights", (1, 2, 3))
        session.dispatch("drive", 0.4, 0.4)
        session.dispatch("stop")
    wait_for(lambda: robot.commands("underlights"))
    kinds = [m["type"] for m in robot.commands() if m["type"] != "video_config"]
    assert kinds[:2] == ["stop", "underlights"]
    assert "drive" not in kinds


def test_command_queue_is_bounded(robot, session):
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    with session.lock:
        for _ in range(200):
            session.dispatch("set_button_led", "A", 1)
    wait_for(lambda: robot.commands("button_led"))
    time.sleep(0.3)
    assert len(robot.commands("button_led")) <= COMMAND_QUEUE_LIMIT


def test_dispatch_requires_connection():
    with pytest.raises(RuntimeError):
        RobotSession().dispatch("drive", 0, 0)


def test_with_query():
    assert _with_query("ws://h:1", force=True, resume="t") == (
        "ws://h:1?force=1&resume=t"
    )
    assert _with_query("ws://h:1?force=1&x=2") == "ws://h:1?x=2"


def test_restart_over_busy_loop_leaves_new_program_stoppable():
    runner = ProgramRunner(RobotSession())
    runner.start_python("while True:\n    pass\n")
    first = runner.thread
    time.sleep(0.2)
    runner.start_python("while True:\n    pass\n")
    second = runner.thread
    assert second is not first
    assert not first.is_alive()  # the restart waited for the forced stop
    time.sleep(2.0)  # past every timer the old run could have left behind
    assert second.is_alive()
    assert runner.status()["status"] == "running"
    assert runner.is_running()
    runner.stop()
    wait_for(lambda: not second.is_alive(), timeout=4)
    assert runner.status()["status"] == "stopped"


def test_stale_time_limit_does_not_stop_newer_run():
    runner = ProgramRunner(RobotSession(), max_seconds=60)
    runner.start_python("while True:\n    wait(0.05)\n")
    old_run = runner.run_id
    runner.start_python("while True:\n    wait(0.05)\n")
    assert runner.run_id != old_run
    runner._time_limit(old_run, 60)  # a timer from the first run firing late
    time.sleep(0.3)
    assert runner.status()["status"] == "running"
    assert runner.thread.is_alive()
    runner._time_limit(runner.run_id, 60)
    wait_for(lambda: runner.status()["status"] != "running", timeout=3)
    assert runner.status()["error"].endswith("(time limit).")


def test_takeover_stop_reason_names_taker_and_clears_on_reconnect(robot, session):
    runner = ProgramRunner(session)
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    assert session.status()["connection"]["program_stopped"] is False
    runner.start_python("while True:\n    wait(0.05)\n")
    robot.take_over("Rival-Robin")
    wait_for(lambda: state(session) == "taken_over")
    wait_for(lambda: runner.status()["status"] == "stopped", timeout=3)
    error = runner.status()["error"]
    assert "Rival-Robin took control of the robot" in error
    assert "Wi-Fi" not in error
    assert session.status()["connection"]["program_stopped"] is True

    session.connect(robot.url)
    wait_for(lambda: connected(session))
    assert runner.status()["error"] == ""
    assert session.status()["connection"]["program_stopped"] is False
    texts = [event["text"] for event in session.status()["events"]]
    assert any("Rival-Robin took control" in text for text in texts)


def test_takeover_without_program_reports_nothing_stopped(robot, session):
    ProgramRunner(session)
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    robot.take_over("Rival-Robin")
    wait_for(lambda: state(session) == "taken_over")
    assert session.status()["connection"]["program_stopped"] is False


def test_wifi_stop_reason_is_refined_by_takeover(robot, session):
    runner = ProgramRunner(session)
    session.connect(robot.url)
    wait_for(lambda: connected(session))
    runner.start_python("while True:\n    wait(0.05)\n")
    robot.busy_holder = "Rival-Robin"  # the resume attempt finds it busy
    robot.drop()
    wait_for(lambda: state(session) == "busy", timeout=5)
    wait_for(lambda: "Rival-Robin" in runner.status()["error"], timeout=3)
    assert "Wi-Fi" not in runner.status()["error"]


def test_last_frame_age_keeps_growing_after_disconnect(robot, session):
    session.connect(robot.url)
    wait_for(lambda: session.status()["connection"]["last_frame_age"] is not None)
    session.disconnect()
    first = session.status()["connection"]["last_frame_age"]
    time.sleep(0.5)
    assert session.status()["connection"]["last_frame_age"] >= first + 0.4
