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
