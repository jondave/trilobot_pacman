import json
import re
from pathlib import Path

import pytest
from blocks_python import blocks_to_python, python_to_blocks

DEMOS = Path(__file__).resolve().parents[1] / "control_scripts" / "blockly" / "demos"
DEMO_FILES = sorted(DEMOS.glob("*.json"))


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalise(code):
    lines = (re.sub(r"[ \t]+", " ", line.strip()) for line in code.splitlines())
    return "\n".join(line for line in lines if line)


@pytest.mark.parametrize("path", DEMO_FILES, ids=lambda p: p.stem)
def test_demo_generates_compilable_python(path):
    code = blocks_to_python(_load(path))
    assert code.strip()
    compile(code, path.name, "exec")


@pytest.mark.parametrize("path", DEMO_FILES, ids=lambda p: p.stem)
def test_demo_round_trips(path):
    code = blocks_to_python(_load(path))
    workspace, _ = python_to_blocks(code)
    again = blocks_to_python(workspace)
    assert _normalise(again) == _normalise(code)


@pytest.mark.parametrize("kind", ["not_a_real_block", None])
def test_unknown_statement_block_fails_loudly(kind):
    block = {"type": kind} if kind else {}
    workspace = {"blocks": {"blocks": [block]}}
    with pytest.raises(ValueError, match=str(kind)):
        blocks_to_python(workspace)


def test_unknown_expression_block_fails_loudly():
    workspace = {
        "blocks": {
            "blocks": [
                {
                    "type": "robot_wait",
                    "inputs": {"SECONDS": {"block": {"type": "mystery_value"}}},
                }
            ]
        }
    }
    with pytest.raises(ValueError, match="mystery_value"):
        blocks_to_python(workspace)


COMMENTED = """# Count obstacles while driving forwards.
import cv2
bumps = 0  # how many so far
for step in count(1, 10):
    # check the sensor
    if distance() < 20:  # close!
        bumps += 1
    else:
        forward(seconds=0.5, power=50)
stop()
# the end
"""


def test_comments_survive_python_to_blocks_and_back():
    state, code = python_to_blocks(COMMENTED)
    assert code == (
        "# Count obstacles while driving forwards.\n"
        "# how many so far\n"
        "bumps = 0\n"
        "for step in count(1, 10):\n"
        "    # check the sensor\n"
        "    # close!\n"
        "    if distance() < 20:\n"
        "        bumps += 1\n"
        "    else:\n"
        "        forward(seconds=0.5, power=50)\n"
        "# the end\n"
        "stop()\n"
    )
    assert python_to_blocks(code)[1] == code  # stable on a second round trip
    first = state["blocks"]["blocks"][0]
    assert first["icons"]["comment"]["text"] == (
        "Count obstacles while driving forwards.\nhow many so far"
    )


def test_block_comment_added_in_blockly_becomes_python_comment():
    state, _ = python_to_blocks("while True:\n    stop()\n")
    inner = state["blocks"]["blocks"][0]["inputs"]["DO"]["block"]
    inner["icons"] = {"comment": {"text": "line one\n\nline three", "pinned": False}}
    assert blocks_to_python(state) == (
        "while True:\n    # line one\n    #\n    # line three\n    stop()\n"
    )


def test_comment_only_lines_without_statements_do_not_break_conversion():
    state, code = python_to_blocks("# just a note\n")
    assert state["blocks"]["blocks"] == []
    assert code == ""
