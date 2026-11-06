"""Drift checks between blocks.json, the toolbox, the generator and robot_config."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import blocks_python
import pytest
import robot_config
from blocks_python import blocks_to_python, python_to_blocks

BLOCKLY = Path(__file__).resolve().parents[1] / "control_scripts" / "blockly"
TEMPLATE = (BLOCKLY / "templates" / "index.html").read_text(encoding="utf-8")
JS_MODULES = sorted((BLOCKLY / "static" / "js").glob("*.js"))
assert JS_MODULES, "no browser modules found in static/js"
APP_JS = "\n".join(path.read_text(encoding="utf-8") for path in JS_MODULES)
DEFINITIONS = robot_config.block_definitions()
DEFINED = {block["type"] for block in DEFINITIONS}

# Defined in blocks.json but deliberately not turned into Python. These colour
# value blocks are kept for old saved programs; nothing in the toolbox uses them.
GENERATOR_UNSUPPORTED = {f"robot_colour_{name}" for name, _ in robot_config.LED_COLOURS}
# Standard Blockly blocks the toolbox uses without a definition in blocks.json.
BLOCKLY_BUILTINS = {
    "controls_if",
    "controls_for",
    "controls_whileUntil",
    "logic_boolean",
    "logic_compare",
    "logic_negate",
    "logic_operation",
    "math_number",
    "math_arithmetic",
    "math_change",
}
# Toolbox blocks whose image inputs are empty need something to read.
CAMERA = {"block": {"type": "opencv_camera_image"}}
EMPTY_INPUT_FILL = {
    "opencv_count_nonzero": {"IMAGE": CAMERA},
    "opencv_mask_or": {"IMAGE1": CAMERA, "IMAGE2": CAMERA},
}


def _toolbox():
    match = re.search(r'<xml id="toolbox"[^>]*>.*?</xml>', TEMPLATE, re.DOTALL)
    assert match, "toolbox XML not found in index.html"
    return ET.fromstring(match.group(0).replace("&amp;", "and"))


def _xml_to_block(element):
    block = {"type": element.get("type")}
    fields = {f.get("name"): f.text or "" for f in element.findall("field")}
    inputs = {}
    for value in element.findall("value"):
        child = value.find("block")
        slot = "block"
        if child is None:
            child, slot = value.find("shadow"), "shadow"
        if child is not None:
            inputs[value.get("name")] = {slot: _xml_to_block(child)}
    if fields:
        block["fields"] = fields
    if inputs:
        block["inputs"] = inputs
    return block


TOOLBOX_BLOCKS = [
    _xml_to_block(el)
    for el in _toolbox().iter("category")
    for el in el.findall("block")
]
TOOLBOX_TYPES = {block["type"] for block in TOOLBOX_BLOCKS}


def _as_program(block):
    """Put an expression block into a socket that accepts it."""
    block = dict(block)
    fill = EMPTY_INPUT_FILL.get(block["type"])
    if fill:
        block["inputs"] = {**fill, **block.get("inputs", {})}
    kind = block["type"]
    if kind in blocks_python.BOOLEAN_BLOCKS:
        return {"type": "controls_if", "inputs": {"IF0": {"block": block}}}
    if kind in blocks_python.NUMBER_BLOCKS | blocks_python.TEXT_BLOCKS:
        return {"type": "robot_print", "inputs": {"VALUE": {"block": block}}}
    if kind in blocks_python.IMAGE_BLOCKS:
        return {"type": "robot_show_live_camera", "inputs": {"IMAGE": {"block": block}}}
    if kind in blocks_python.HSV_BLOCKS:
        mask = {
            "type": "opencv_hsv_mask",
            "inputs": {"LOW": {"block": block}, "HIGH": {"block": block}},
        }
        return {"type": "robot_show_live_camera", "inputs": {"IMAGE": {"block": mask}}}
    return block


def _workspace(block):
    return {"blocks": {"blocks": [_as_program(block)]}}


def _colour_dropdowns():
    for block in DEFINITIONS:
        for key, args in block.items():
            if re.fullmatch(r"args\d+", key):
                for arg in args:
                    if (
                        arg.get("type") == "field_dropdown"
                        and arg.get("name") == "COLOR"
                    ):
                        yield block["type"], arg


def test_block_definitions_are_unique():
    assert len(DEFINED) == len(DEFINITIONS)


@pytest.mark.parametrize("kind", sorted(DEFINED))
def test_every_defined_block_is_generated_or_listed(kind):
    if kind in GENERATOR_UNSUPPORTED:
        with pytest.raises(ValueError, match=kind):
            blocks_to_python(_workspace({"type": kind}))
    else:
        assert blocks_to_python(_workspace({"type": kind})).strip()


def test_unsupported_list_has_no_stale_entries():
    assert GENERATOR_UNSUPPORTED <= DEFINED
    assert not GENERATOR_UNSUPPORTED & TOOLBOX_TYPES


def test_every_toolbox_block_is_defined():
    assert TOOLBOX_TYPES - DEFINED - BLOCKLY_BUILTINS == set()
    assert BLOCKLY_BUILTINS & DEFINED == set(), "builtin listed but now defined"


def _round_trip_cases():
    cases = [(block["type"] + "@toolbox", block) for block in TOOLBOX_BLOCKS]
    cases += [
        (kind, {"type": kind})
        for kind in sorted(DEFINED - TOOLBOX_TYPES)
        if kind not in GENERATOR_UNSUPPORTED
    ]
    return cases


@pytest.mark.parametrize(
    "block",
    [c[1] for c in _round_trip_cases()],
    ids=[c[0] for c in _round_trip_cases()],
)
def test_block_round_trips(block):
    code = blocks_to_python(_workspace(block))
    workspace, normalised = python_to_blocks(code)
    assert normalised == code
    assert blocks_to_python(workspace) == code


def test_colour_dropdowns_use_the_shared_placeholder():
    dropdowns = list(_colour_dropdowns())
    assert {kind for kind, _ in dropdowns} == {
        "robot_if_color",
        "robot_set_lights",
        "robot_flash_lights",
    }
    for kind, arg in dropdowns:
        assert arg["options"] == robot_config.LED_COLOUR_OPTIONS_PLACEHOLDER, kind


def test_colour_names_match_robot_config():
    names = [name for name, _ in robot_config.LED_COLOURS]
    assert list(blocks_python.COLOURS) == names
    assert blocks_python.COLOURS == dict(robot_config.LED_COLOURS)
    for prefix in ("robot_lights_", "robot_colour_"):
        assert {k[len(prefix) :] for k in DEFINED if k.startswith(prefix)} == set(names)
    for name, value in robot_config.LED_COLOURS:
        block = {"type": "robot_set_lights", "fields": {"COLOR": value}}
        assert blocks_to_python(_workspace(block)) == f'set_lights("{name}")\n'
        assert blocks_to_python(_workspace({"type": f"robot_lights_{name}"})) == (
            f'set_lights("{name}")\n'
        )


def test_toolbox_colour_fields_are_known_colours():
    hexes = {value for _, value in robot_config.LED_COLOURS}
    for block in TOOLBOX_BLOCKS:
        colour = block.get("fields", {}).get("COLOR")
        if colour is not None:
            assert colour in hexes, block["type"]


def test_browser_has_no_hardcoded_copies():
    for _, value in robot_config.LED_COLOURS:
        assert value not in APP_JS.lower(), value
    assert "red,green,blue" not in APP_JS
    assert "10 * 60" not in APP_JS and "30 * 60" not in APP_JS
    assert "defineBlocksWithJsonArray([" not in APP_JS
    for width, height in robot_config.VIDEO_SIZES:
        assert f"{width}x{height}" not in TEMPLATE


def test_index_embeds_config_and_blocks():
    import json

    import app as blockly_app

    html = blockly_app.app.test_client().get("/").get_data(as_text=True)

    def embedded(element_id):
        match = re.search(
            rf'<script id="{element_id}" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        assert match, element_id
        return json.loads(match.group(1))

    assert embedded("app-config") == robot_config.browser_config()
    assert embedded("block-definitions") == DEFINITIONS
    sizes = re.findall(r'<option value="(\d+)x(\d+)"', html)
    assert [tuple(map(int, s)) for s in sizes] == list(robot_config.VIDEO_SIZES)
    default = robot_config.DEFAULT_VIDEO_CONFIG
    assert re.search(rf"<option selected>{int(default['fps'])}</option>", html)
    assert re.search(rf"<option selected>{default['jpeg_quality']}</option>", html)


def test_blockly_version_matches_cdn_fallback():
    script = (BLOCKLY.parents[1] / "scripts" / "fetch_vendor.sh").read_text(encoding="utf-8")
    pinned = re.search(r"^BLOCKLY_VERSION=(\S+)", script, re.M).group(1)
    assert f"unpkg.com/blockly@{pinned}/blockly.min.js" in TEMPLATE


def test_toolbox_class_keeps_both_blockly_names():
    for path in [*JS_MODULES, BLOCKLY / "static" / "style.css"]:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"blocklyToolboxDiv", text):
            context = text[max(0, match.start() - 40) : match.end() + 40]
            assert ".blocklyToolbox," in context or ".blocklyToolbox\n" in context, path.name
