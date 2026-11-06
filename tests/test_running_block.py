"""The running program reports which block (or Python line) it is on."""

import itertools
import json
import sys
import threading
import time
from pathlib import Path

import pytest
from blocks_python import (
    EXPRESSION_BLOCKS,
    block_labels,
    blocks_to_python,
    blocks_to_python_with_map,
    python_to_blocks,
)
from fake_ws import FakeRobot
from program_runner import STUDENT_FILENAME, ProgramRunner, _line_tracer
from robot_session import RobotSession

DEMOS = Path(__file__).resolve().parents[1] / "control_scripts" / "blockly" / "demos"
DEMO_FILES = sorted(DEMOS.glob("*.json")) + sorted(DEMOS.glob("*.py"))


def wait_for(condition, timeout=5.0, interval=0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError("timed out waiting for condition")


def _load(path):
    if path.suffix == ".py":
        return python_to_blocks(path.read_text(encoding="utf-8"))[0]
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(block):
    """Yield every block (and shadow) under block, including itself."""
    if not isinstance(block, dict):
        return
    yield block
    for value in (block.get("inputs") or {}).values():
        if isinstance(value, dict):
            yield from _walk(value.get("block"))
            yield from _walk(value.get("shadow"))
    follow = block.get("next")
    if isinstance(follow, dict):
        yield from _walk(follow.get("block"))


def _with_ids(workspace):
    """Give every block an id, as Blockly does when it saves a workspace."""
    counter = itertools.count(1)
    for stack in workspace["blocks"]["blocks"]:
        for block in _walk(stack):
            block["id"] = f"b{next(counter)}"
    return workspace


def _statement_ids(workspace):
    return {
        block["id"]
        for stack in workspace["blocks"]["blocks"]
        for block in _walk(stack)
        if block.get("type") not in EXPRESSION_BLOCKS
    }


def _number(value):
    return {"shadow": {"type": "math_number", "fields": {"NUM": value}}}


def _program(*blocks):
    """Chain blocks into a single stack workspace."""
    blocks = [dict(block) for block in blocks]
    for block, following in itertools.pairwise(blocks):
        block["next"] = {"block": following}
    return {"blocks": {"languageVersion": 0, "blocks": [blocks[0]]}}


def _observe(runner, timeout=10.0):
    """Poll current_step until the run ends; return the distinct steps seen."""
    seen = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = runner.status()
        step = status["current_step"]
        if step["line"] is not None and (not seen or seen[-1] != step):
            seen.append(step)
        if status["status"] != "running":
            return seen, status
        time.sleep(0.01)
    raise AssertionError("program did not finish")


@pytest.fixture()
def robot():
    fake = FakeRobot()
    yield fake
    fake.close()


@pytest.fixture()
def session(robot):
    robot_session = RobotSession(
        backoff=(0.1, 0.2), offline_after=5, slow_retry=0.2, telemetry_timeout=1.0
    )
    robot_session.connect(robot.url)
    wait_for(lambda: robot_session.status()["connection"]["state"] == "connected")
    yield robot_session
    robot_session.disconnect()


@pytest.mark.parametrize("path", DEMO_FILES, ids=lambda p: p.stem)
def test_line_map_covers_every_statement_block(path):
    workspace = _with_ids(_load(path))
    code, line_map = blocks_to_python_with_map(workspace)
    assert code == blocks_to_python(workspace)
    assert set(line_map.values()) == _statement_ids(workspace)
    lines = code.splitlines()
    # Every non-blank generated line is mapped; blank separators are not.
    assert set(line_map) == {n for n, text in enumerate(lines, 1) if text.strip()}
    assert set(block_labels(workspace)) == _statement_ids(workspace)


@pytest.mark.parametrize("path", DEMO_FILES, ids=lambda p: p.stem)
def test_blocks_to_python_is_unchanged_by_ids(path):
    plain = _load(path)
    expected = blocks_to_python(plain)
    assert blocks_to_python(_with_ids(json.loads(json.dumps(plain)))) == expected
    without_ids = json.loads(json.dumps(plain))
    for stack in without_ids["blocks"]["blocks"]:
        for block in _walk(stack):
            block.pop("id", None)
    assert blocks_to_python(without_ids) == expected
    assert blocks_to_python_with_map(without_ids) == (expected, {})


def test_headers_and_nested_lines_map_to_the_right_block():
    loop = {
        "type": "controls_whileUntil",
        "id": "loop",
        "fields": {"MODE": "WHILE"},
        "inputs": {
            "BOOL": {"block": {"type": "logic_boolean", "fields": {"BOOL": "TRUE"}}},
            "DO": {
                "block": {
                    "type": "controls_if",
                    "id": "check",
                    "inputs": {
                        "IF0": {"block": {"type": "robot_button_pressed", "id": "e"}},
                        "DO0": {"block": {"type": "robot_stop", "id": "halt"}},
                        "ELSE": {
                            "block": {
                                "type": "robot_wait",
                                "id": "pause",
                                "inputs": {"SECONDS": _number(1)},
                            }
                        },
                    },
                }
            },
        },
    }
    code, line_map = blocks_to_python_with_map(_program(loop))
    assert code.splitlines() == [
        "while True:",
        '    if button_pressed("A"):',
        "        stop()",
        "    else:",
        "        wait(1)",
    ]
    assert line_map == {1: "loop", 2: "check", 3: "halt", 4: "check", 5: "pause"}
    labels = block_labels(_program(loop))
    assert labels == {
        "loop": "repeat while",
        "check": "if",
        "halt": "stop the motors",
        "pause": "wait 1 second",
    }


def test_labels_for_common_blocks():
    workspace = _program(
        {
            "type": "robot_drive_for",
            "id": "d",
            "fields": {"DIRECTION": "FORWARD"},
            "inputs": {"SECONDS": _number(2), "SPEED": _number(60)},
        },
        {"type": "robot_wait", "id": "w", "inputs": {"SECONDS": _number(0.5)}},
        {"type": "robot_set_lights", "id": "l", "fields": {"COLOR": "#ff0000"}},
        {"type": "robot_repeat", "id": "r", "inputs": {"TIMES": _number(4)}},
        {"type": "robot_turn_left", "id": "t"},
    )
    assert block_labels(workspace) == {
        "d": "drive forward for 2 seconds",
        "w": "wait 0.5 seconds",
        "l": "set lights red",
        "r": "repeat 4 times",
        "t": "turn left for 1 second",
    }


def test_blocks_run_reports_each_block_in_order(session):
    runner = ProgramRunner(session)
    runner.start(
        _program(
            {
                "type": "robot_set_lights",
                "id": "lights",
                "fields": {"COLOR": "#ff0000"},
            },
            {"type": "robot_wait", "id": "w1", "inputs": {"SECONDS": _number(0.3)}},
            {
                "type": "robot_drive_for",
                "id": "drive",
                "fields": {"DIRECTION": "FORWARD"},
                "inputs": {"SECONDS": _number(0.3), "SPEED": _number(50)},
            },
            {"type": "robot_wait", "id": "w2", "inputs": {"SECONDS": _number(0.3)}},
        )
    )
    seen, status = _observe(runner)
    assert status["status"] == "complete", status
    slow = [step["block"] for step in seen if step["block"] != "lights"]
    assert slow == ["w1", "drive", "w2"]
    by_block = {step["block"]: step for step in seen}
    assert by_block["w1"] == {
        "mode": "blocks",
        "line": 2,
        "block": "w1",
        "label": "wait 0.3 seconds",
    }
    assert by_block["drive"]["label"] == "drive forward for 0.3 seconds"
    # Cleared once the program is over; the mode of the last run is kept.
    assert status["current_step"] == {
        "mode": "blocks",
        "line": None,
        "block": None,
        "label": None,
    }


def test_python_mode_reports_line_numbers():
    runner = ProgramRunner(RobotSession())
    assert runner.status()["current_step"] == {
        "mode": None,
        "line": None,
        "block": None,
        "label": None,
    }
    runner.start_python("wait(0.3)\nx = 1\n\nwait(0.3)  # " + "z" * 80 + "\n")
    seen, status = _observe(runner)
    assert status["status"] == "complete", status
    slow = [step for step in seen if step["line"] in (1, 4)]
    assert [step["line"] for step in slow] == [1, 4]
    assert slow[0] == {"mode": "python", "line": 1, "block": None, "label": "wait(0.3)"}
    assert len(slow[1]["label"]) == 60 and slow[1]["label"].endswith("...")
    assert status["current_step"]["line"] is None


def test_busy_loop_block_is_reported_and_still_stops_promptly():
    loop = {
        "type": "controls_whileUntil",
        "id": "forever",
        "fields": {"MODE": "WHILE"},
        "inputs": {
            "BOOL": {"block": {"type": "logic_boolean", "fields": {"BOOL": "TRUE"}}}
        },
    }
    runner = ProgramRunner(RobotSession())
    runner.start(_program(loop))
    wait_for(lambda: runner.status()["current_step"]["block"] == "forever")
    thread = runner.thread
    started = time.monotonic()
    runner.stop()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert time.monotonic() - started < 3.0
    status = runner.status()
    assert status["status"] == "stopped"
    assert status["current_step"]["line"] is None


def test_busy_loop_still_hits_the_time_limit():
    runner = ProgramRunner(RobotSession(), max_seconds=0.3)
    runner.start_python("while True:\n    pass\n")
    wait_for(lambda: runner.status()["current_step"]["line"] in (1, 2))
    wait_for(lambda: runner.status()["status"] != "running", timeout=4)
    status = runner.status()
    assert status["error"].endswith("(time limit).")
    assert status["current_step"]["line"] is None


def _time_loop(compiled, traced):
    timings = []
    for _ in range(5):
        result = {}

        def run(result=result):
            if traced:
                sys.settrace(_line_tracer(threading.current_thread()))
            started = time.perf_counter()
            exec(compiled, {})
            result["seconds"] = time.perf_counter() - started
            sys.settrace(None)

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()
        timings.append(result["seconds"])
    return min(timings)


def test_tracer_overhead_is_acceptable():
    code = "x = 0\nfor i in range(200000):\n    x += i\n"
    compiled = compile(code, STUDENT_FILENAME, "exec")
    plain = _time_loop(compiled, traced=False)
    traced = _time_loop(compiled, traced=True)
    factor = traced / plain
    print(
        f"\ntracer slowdown: {factor:.2f}x ({plain * 1e3:.1f} ms -> {traced * 1e3:.1f} ms)"
    )
    assert factor < 8, f"tracer slowdown {factor:.1f}x"
