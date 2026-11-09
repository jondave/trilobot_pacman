"""Drift checks between blocks.json, the toolbox, the generator and robot_config."""

import re
import tomllib
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
    script = (BLOCKLY.parents[1] / "scripts" / "fetch_vendor.sh").read_text(
        encoding="utf-8"
    )
    pinned = re.search(r"^BLOCKLY_VERSION=(\S+)", script, re.M).group(1)
    assert f"unpkg.com/blockly@{pinned}/blockly.min.js" in TEMPLATE


def test_fontawesome_version_matches_cdn_fallback():
    script = (BLOCKLY.parents[1] / "scripts" / "fetch_vendor.sh").read_text(
        encoding="utf-8"
    )
    pinned = re.search(r"^FONTAWESOME_VERSION=(\S+)", script, re.M).group(1)
    assert pinned.startswith("5."), pinned
    assert "/static/vendor/fontawesome/css/all.min.css" in TEMPLATE
    assert (
        f"cdnjs.cloudflare.com/ajax/libs/font-awesome/{pinned}/css/all.min.css"
        in TEMPLATE
    )


# Emoji and pictographic symbols (arrows, shapes, dingbats, emoji planes);
# the UI uses Font Awesome icons instead. Punctuation like "…" or "·" is fine.
PICTOGRAPHS = re.compile(
    "[\u2190-\u21ff\u2300-\u23ff\u2460-\u27bf\u2900-\u2bff"
    "\u2139\ufe0f\U0001f000-\U0001faff]"
)

ROBOT_PING_DOTS = {"\U0001f7e2", "\U0001f7e0", "\U0001f534"}  # green, orange, red


def test_ui_has_no_emoji():
    static = BLOCKLY / "static"
    paths = [
        BLOCKLY / "templates" / "index.html",
        static / "style.css",
        static / "blocks.json",
        *JS_MODULES,
    ]
    for path in paths:
        found = PICTOGRAPHS.findall(path.read_text(encoding="utf-8"))
        if path.name == "directory.js":
            # The one exception: traffic-light dots in the robot <option> text,
            # since a native option can't show a Font Awesome icon.
            found = [char for char in found if char not in ROBOT_PING_DOTS]
        assert not found, (path.name, found)


def test_toolbox_class_keeps_both_blockly_names():
    for path in [*JS_MODULES, BLOCKLY / "static" / "style.css"]:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"blocklyToolboxDiv", text):
            context = text[max(0, match.start() - 40) : match.end() + 40]
            assert (
                ".blocklyToolbox," in context or ".blocklyToolbox\n" in context
            ), path.name


def test_close_codes_match_between_robot_and_client():
    """robot_sender.py is parsed, not imported: it may need Pi hardware."""
    import ast

    import client

    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "robot_scripts" / "robot_sender.py").read_text("utf-8"))
    robot = {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id.startswith("CLOSE_")
    }
    # The robot calls the takeover code CLOSE_KICKED; the client CLOSE_TAKEN_OVER.
    robot_names = {"CLOSE_KICKED": "CLOSE_TAKEN_OVER"}
    robot = {robot_names.get(name, name): code for name, code in robot.items()}
    library = {n: v for n, v in vars(client).items() if n.startswith("CLOSE_")}
    assert robot
    assert robot == library


def test_session_name_pattern_matches_between_robot_and_app():
    """The app makes names; the robot must accept exactly the ones it makes."""
    import ast

    import student_name

    root = Path(__file__).resolve().parents[1]
    source = (root / "robot_scripts" / "robot_sender.py").read_text("utf-8")
    patterns = [
        node.value.args[0].value
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", None) == "NAME_PATTERN" for t in node.targets)
    ]
    assert patterns == [student_name.NAME_PATTERN.pattern]
    words = student_name.load_words()
    assert all(re.fullmatch(r"[a-z]{1,12}", word) for word in words)
    assert len(set(words)) == len(words) > 100


def test_python_reference_documents_every_student_function():
    """docs/PYTHON_REFERENCE.md has a heading with each function's real signature."""
    import inspect

    from program_runner import ProgramRunner
    from robot_session import RobotSession

    root = Path(__file__).resolve().parents[1]
    reference = (root / "docs" / "PYTHON_REFERENCE.md").read_text("utf-8")
    headings = "\n".join(
        line for line in reference.splitlines() if line.startswith("### ")
    )
    runner = ProgramRunner(RobotSession())
    functions = {**runner._student_robot_api(), **runner._student_builtins()}
    for name, function in functions.items():
        if name in ("print", "input"):
            assert f"`{name}(" in headings, name
            continue
        documented = f"`{name}{inspect.signature(function)}`"
        assert documented in headings, f"{documented} missing from PYTHON_REFERENCE.md"


def test_client_requirements_match_uv_lock():
    """control_scripts/requirements.txt (for library users) must not drift from uv.lock."""
    root = BLOCKLY.parents[1]
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked = {pkg["name"].lower(): pkg["version"] for pkg in lock["package"]}
    pins = {}
    for line in (
        (root / "control_scripts" / "requirements.txt").read_text().splitlines()
    ):
        line = line.split("#")[0].strip()
        if line:
            name, _, version = line.partition("==")
            assert version, f"requirements.txt line is not pinned with ==: {line!r}"
            pins[name.strip().lower().replace("_", "-")] = version.strip()
    assert pins, "no pins found in control_scripts/requirements.txt"
    for name, version in pins.items():
        assert (
            locked.get(name) == version
        ), f"{name}: requirements.txt {version} != uv.lock {locked.get(name)}"


def _parse_pins(path):
    pins = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-r"):
            continue
        name, _, version = line.partition("==")
        assert version, f"{path.name} line is not pinned with ==: {line!r}"
        pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


def _pyproject_pins(entries):
    pins = {}
    for entry in entries:
        name, _, version = entry.partition("==")
        assert version, f"pyproject entry is not pinned with ==: {entry!r}"
        pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


@pytest.mark.parametrize(
    ("path", "group"),
    [
        ("control_scripts/requirements.txt", None),
        ("control_scripts/blockly/requirements.txt", None),
        ("requirements-dev.txt", "dev"),
    ],
)
def test_pip_requirements_match_pyproject(path, group):
    """The pip files and the optional uv metadata must carry the same pins."""
    root = BLOCKLY.parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = _pyproject_pins(project["project"]["dependencies"])
    expected = (
        _pyproject_pins(project["dependency-groups"][group]) if group else runtime
    )
    pins = _parse_pins(root / path)
    assert pins, f"no pins found in {path}"
    for name, version in pins.items():
        assert (
            expected.get(name) == version
        ), f"{name}: {path} {version} != pyproject {expected.get(name)}"


def test_pyproject_runtime_and_dev_pins_are_all_in_pip_files():
    root = BLOCKLY.parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = _pyproject_pins(project["project"]["dependencies"])
    dev = _pyproject_pins(project["dependency-groups"]["dev"])
    pip_runtime = _parse_pins(root / "control_scripts" / "requirements.txt")
    pip_runtime |= _parse_pins(
        root / "control_scripts" / "blockly" / "requirements.txt"
    )
    assert pip_runtime == runtime
    assert _parse_pins(root / "requirements-dev.txt") == dev


def test_every_element_the_page_scripts_use_exists():
    """$("id") in the browser modules must match an id in index.html."""
    used = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', APP_JS))
    by_id = r'getElementById\("([A-Za-z0-9_-]+)"\)'
    used |= set(re.findall(by_id, APP_JS))
    ids = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', TEMPLATE))
    assert used and not used - ids, sorted(used - ids)
