"""Two-way conversion between Blockly workspace JSON and student Python code.

Only a small Python subset maps onto blocks. Anything outside it raises
``Unsupported`` so the page can tell the student they have outgrown the blocks.
"""

from __future__ import annotations

import ast
import keyword
import math
import re

COLOURS = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "white": "#ffffff",
    "purple": "#ff00ff",
}
HEX_TO_NAME = {value: name for name, value in COLOURS.items()}
BUTTONS = ("A", "B", "X", "Y")
DIRECTIONS = ("forward", "backward", "left", "right")

MOVE_BLOCKS = {
    "forward": "robot_forward",
    "backward": "robot_backward",
    "turn_left": "robot_turn_left",
    "turn_right": "robot_turn_right",
    "turn_around": "robot_turn_around",
}
MOVE_FUNCTIONS = {block: name for name, block in MOVE_BLOCKS.items()}

API_NAMES = frozenset({
    *MOVE_BLOCKS, "drive", "wait", "stop", "take_picture", "sees_colour",
    "distance", "button_pressed", "wait_until", "set_lights", "lights_off",
    "flash_lights", "set_button_light", "count",
    "show_in_live_camera", "scan_robot_qr",
})
RESERVED_NAMES = API_NAMES | frozenset(keyword.kwlist) | {"range", "int", "print", "input", "_"}

# Blockly block types grouped by the socket type they plug into.
BOOLEAN_BLOCKS = {
    "logic_boolean", "logic_negate", "logic_operation", "logic_compare",
    "robot_button_pressed", "robot_distance_condition",
}
NUMBER_BLOCKS = {"math_number", "math_arithmetic", "opencv_count_nonzero", "robot_distance_value"}
IMAGE_BLOCKS = {
    "variables_get", "opencv_camera_image", "opencv_to_hsv", "opencv_blur",
    "opencv_box_blur", "opencv_hsv_mask", "opencv_mask_or",
}
HSV_BLOCKS = {"opencv_hsv_value"}
TEXT_BLOCKS = {"robot_scan_qr"}
EXPRESSION_BLOCKS = BOOLEAN_BLOCKS | NUMBER_BLOCKS | IMAGE_BLOCKS | HSV_BLOCKS | TEXT_BLOCKS | {"text"}

OR, AND, NOT, COMPARE, ADD, MUL, UNARY, POW, ATOM = range(1, 10)
ARITHMETIC_SYMBOLS = {
    "ADD": ("+", ADD), "MINUS": ("-", ADD), "MULTIPLY": ("*", MUL),
    "DIVIDE": ("/", MUL), "POWER": ("**", POW),
}
COMPARE_SYMBOLS = {"EQ": "==", "NEQ": "!=", "LT": "<", "LTE": "<=", "GT": ">", "GTE": ">="}
ARITHMETIC_OPS = {ast.Add: "ADD", ast.Sub: "MINUS", ast.Mult: "MULTIPLY", ast.Div: "DIVIDE", ast.Pow: "POWER"}
COMPARE_OPS = {ast.Eq: "EQ", ast.NotEq: "NEQ", ast.Lt: "LT", ast.LtE: "LTE", ast.Gt: "GT", ast.GtE: "GTE"}

MOVE_PARAMS = (("seconds", 1), ("power", 60))
_REQUIRED = object()


class Unsupported(Exception):
    def __init__(self, message, line=None, syntax=False):
        super().__init__(message)
        self.message = message
        self.line = line
        self.syntax = syntax


def _python_name(name):
    text = re.sub(r"\W", "_", str(name or "variable"))
    if text[0].isdigit():
        text = "_" + text
    return text + "_var" if text in RESERVED_NAMES else text


def _number_text(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    if not math.isfinite(number):
        return "0"
    return str(int(number)) if number == int(number) else repr(number)


def _colour_text(value):
    text = str(value or "#ff0000").lower()
    return HEX_TO_NAME.get(text, text)


def _child(block, name):
    value = (block.get("inputs") or {}).get(name)
    if not isinstance(value, dict):
        return None
    return value.get("block") or value.get("shadow")


def _following(block):
    follow = block.get("next")
    return follow.get("block") if isinstance(follow, dict) else None


def blocks_to_python(workspace):
    return _Generator(workspace).program()


class _Generator:
    def __init__(self, workspace):
        workspace = workspace if isinstance(workspace, dict) else {}
        raw = workspace.get("variables")
        if isinstance(raw, dict):
            raw = raw.get("variables")
        self.names = {}
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict) and item.get("id"):
                self.names[item["id"]] = _python_name(item.get("name") or item["id"])
        blocks = workspace.get("blocks")
        self.stacks = blocks.get("blocks", []) if isinstance(blocks, dict) else []

    def program(self):
        chunks = []
        for stack in self.stacks:
            if isinstance(stack, dict) and stack.get("type") not in EXPRESSION_BLOCKS:
                chunks.append("\n".join(self.chain(stack, 0)))
        return "\n\n".join(chunks) + "\n" if chunks else ""

    def chain(self, block, depth):
        lines = []
        while isinstance(block, dict):
            lines.extend(self.statement(block, depth))
            block = _following(block)
        return lines

    def body(self, block, name, depth):
        lines = self.chain(_child(block, name), depth + 1)
        return lines or [_pad(depth + 1) + "pass"]

    def else_lines(self, block, name, depth):
        if _child(block, name) is None:
            return []
        return [f"{_pad(depth)}else:"] + self.body(block, name, depth)

    def variable(self, field):
        if isinstance(field, dict):
            return self.names.get(field.get("id")) or _python_name(field.get("name") or field.get("id"))
        return _python_name(field)

    def value(self, block, name, min_prec=0, default="0"):
        child = _child(block, name)
        if child is None:
            return default
        code, prec = self.expression(child)
        return f"({code})" if prec < min_prec else code

    def statement(self, block, depth):
        kind = block.get("type")
        fields = block.get("fields") or {}
        pad = _pad(depth)

        if kind in MOVE_FUNCTIONS:
            seconds = self.value(block, "SECONDS", default="1")
            power = self.value(block, "SPEED", default="60")
            return [f"{pad}{MOVE_FUNCTIONS[kind]}(seconds={seconds}, power={power})"]
        if kind == "robot_drive_for":
            direction = str(fields.get("DIRECTION", "FORWARD")).lower()
            seconds = self.value(block, "SECONDS", default="1")
            power = self.value(block, "SPEED", default="60")
            return [f'{pad}drive("{direction}", seconds={seconds}, power={power})']
        if kind == "robot_wait":
            return [f"{pad}wait({self.value(block, 'SECONDS', default='1')})"]
        if kind == "robot_stop":
            return [f"{pad}stop()"]
        if kind == "robot_print":
            first = self.value(block, "VALUE", default="None")
            second = _child(block, "VALUE2")
            if second:
                return [f"{pad}print({first}, {self.expression(second)[0]})"]
            return [f"{pad}print({first})"]
        if kind == "robot_take_picture":
            return [f"{pad}take_picture()"]
        if kind == "robot_show_live_camera":
            image = _child(block, "IMAGE")
            image_code = self.expression(image)[0] if image else "take_picture()"
            return [f"{pad}show_in_live_camera({image_code})"]
        if kind == "robot_underlights_on":
            return [f'{pad}set_lights("white")']
        if kind == "robot_underlights_off":
            return [f"{pad}lights_off()"]
        if kind and kind.startswith("robot_lights_") and kind[13:] in COLOURS:
            return [f'{pad}set_lights("{kind[13:]}")']
        if kind == "robot_set_lights":
            return [f'{pad}set_lights("{_colour_text(fields.get("COLOR"))}")']
        if kind == "robot_flash_lights":
            times = self.value(block, "TIMES", default="3")
            return [f'{pad}flash_lights("{_colour_text(fields.get("COLOR"))}", times={times})']
        if kind == "robot_button_light":
            brightness = self.value(block, "BRIGHTNESS", default="1")
            return [f'{pad}set_button_light("{fields.get("BUTTON", "A")}", {brightness})']
        if kind == "robot_wait_until":
            return [f"{pad}wait_until(lambda: {self.value(block, 'CONDITION', default='False')})"]
        if kind == "robot_if_color":
            header = (
                f'{pad}if sees_colour("{_colour_text(fields.get("COLOR"))}", '
                f'tolerance={self.value(block, "TOLERANCE", default="18")}, '
                f'min_area={self.value(block, "MIN_AREA", default="500")}):'
            )
            return [header] + self.body(block, "THEN", depth) + self.else_lines(block, "ELSE", depth)
        if kind == "robot_if_distance":
            symbol = "<" if fields.get("OPERATOR", "LESS_THAN") == "LESS_THAN" else ">"
            limit = self.value(block, "CENTIMETRES", COMPARE + 1, "20")
            header = f"{pad}if distance() {symbol} {limit}:"
            return [header] + self.body(block, "THEN", depth) + self.else_lines(block, "ELSE", depth)
        if kind in {"robot_repeat", "controls_repeat_ext"}:
            times = self.value(block, "TIMES", default="2")
            if not re.fullmatch(r"\d+", times):
                times = f"int({times})"
            return [f"{pad}for _ in range({times}):"] + self.body(block, "DO", depth)
        if kind == "controls_whileUntil":
            if fields.get("MODE") == "UNTIL":
                header = f"{pad}while not {self.value(block, 'BOOL', NOT, 'False')}:"
            else:
                header = f"{pad}while {self.value(block, 'BOOL', default='False')}:"
            return [header] + self.body(block, "DO", depth)
        if kind == "controls_for":
            start = self.value(block, "FROM", default="1")
            end = self.value(block, "TO", default="10")
            step = self.value(block, "BY", default="1")
            arguments = f"{start}, {end}" if step == "1" else f"{start}, {end}, {step}"
            header = f"{pad}for {self.variable(fields.get('VAR'))} in count({arguments}):"
            return [header] + self.body(block, "DO", depth)
        if kind == "controls_if":
            inputs = block.get("inputs") or {}
            indexes = sorted({
                int(match.group(1)) for key in inputs
                if (match := re.fullmatch(r"(?:IF|DO)(\d+)", key))
            }) or [0]
            lines = []
            for position, index in enumerate(indexes):
                word = "if" if position == 0 else "elif"
                lines.append(f"{pad}{word} {self.value(block, f'IF{index}', default='False')}:")
                lines.extend(self.body(block, f"DO{index}", depth))
            return lines + self.else_lines(block, "ELSE", depth)
        if kind == "variables_set":
            name = self.variable(fields.get("VAR"))
            return [f"{pad}{name} = {self.value(block, 'VALUE', default='0')}"]
        if kind == "math_change":
            name = self.variable(fields.get("VAR"))
            delta = self.value(block, "DELTA", default="1")
            return [f"{pad}{name} += {delta}"]
        return [f"{pad}pass  # unsupported block: {kind}"]

    def expression(self, block):
        kind = block.get("type")
        fields = block.get("fields") or {}

        if kind == "math_number":
            text = _number_text(fields.get("NUM"))
            return text, UNARY if text.startswith("-") else ATOM
        if kind == "variables_get":
            return self.variable(fields.get("VAR")), ATOM
        if kind == "text":
            return repr(str(fields.get("TEXT", ""))), ATOM
        if kind == "opencv_camera_image":
            return "take_picture()", ATOM
        if kind == "opencv_to_hsv":
            image = self.value(block, "IMAGE", default="take_picture()")
            conversion = fields.get("CONVERSION", "BGR_TO_HSV")
            constant = "COLOR_HSV2BGR" if conversion == "HSV_TO_BGR" else "COLOR_BGR2HSV"
            return f"cv2.cvtColor({image}, cv2.{constant})", ATOM
        if kind == "opencv_blur":
            image = self.value(block, "IMAGE", default="take_picture()")
            kernel = self.value(block, "KERNEL", default="5")
            return f"cv2.GaussianBlur({image}, ({kernel}, {kernel}), 0)", ATOM
        if kind == "opencv_box_blur":
            image = self.value(block, "IMAGE", default="take_picture()")
            kernel = self.value(block, "KERNEL", default="5")
            return f"cv2.blur({image}, ({kernel}, {kernel}))", ATOM
        if kind == "opencv_hsv_value":
            values = ", ".join(
                self.value(block, name, default=default)
                for name, default in (("H", 40), ("S", 70), ("V", 70))
            )
            return f"({values})", ATOM
        if kind == "opencv_hsv_mask":
            image = self.value(block, "IMAGE", default="take_picture()")
            low_block = _child(block, "LOW")
            high_block = _child(block, "HIGH")
            if low_block and high_block:
                low = self.expression(low_block)[0]
                high = self.expression(high_block)[0]
                return f"cv2.inRange({image}, {low}, {high})", ATOM
            else:
                low = ", ".join(
                    self.value(block, name, default=default)
                    for name, default in (("LOW_H", 40), ("LOW_S", 70), ("LOW_V", 70))
                )
                high = ", ".join(
                    self.value(block, name, default=default)
                    for name, default in (("HIGH_H", 80), ("HIGH_S", 255), ("HIGH_V", 255))
                )
            return f"cv2.inRange({image}, ({low}), ({high}))", ATOM
        if kind == "opencv_mask_or":
            left = self.value(block, "IMAGE1", default="None")
            right = self.value(block, "IMAGE2", default="None")
            return f"cv2.bitwise_or({left}, {right})", ATOM
        if kind == "opencv_count_nonzero":
            image = self.value(block, "IMAGE", default="None")
            return f"cv2.countNonZero({image})", ATOM
        if kind == "robot_scan_qr":
            return "scan_robot_qr()", ATOM
        if kind == "robot_distance_value":
            return "distance()", ATOM
        if kind == "math_arithmetic":
            symbol, prec = ARITHMETIC_SYMBOLS.get(fields.get("OP", "ADD"), ("+", ADD))
            if prec == POW:
                left = self.value(block, "A", ATOM)
                right = self.value(block, "B", UNARY)
            else:
                left = self.value(block, "A", prec)
                right = self.value(block, "B", prec + 1)
            return f"{left} {symbol} {right}", prec
        if kind == "logic_boolean":
            return ("True" if fields.get("BOOL") == "TRUE" else "False"), ATOM
        if kind == "logic_negate":
            return f"not {self.value(block, 'BOOL', NOT, 'False')}", NOT
        if kind == "logic_operation":
            word, prec = ("or", OR) if fields.get("OP") == "OR" else ("and", AND)
            left = self.value(block, "A", prec, "False")
            right = self.value(block, "B", prec + 1, "False")
            return f"{left} {word} {right}", prec
        if kind == "logic_compare":
            symbol = COMPARE_SYMBOLS.get(fields.get("OP", "EQ"), "==")
            left = self.value(block, "A", COMPARE + 1)
            right = self.value(block, "B", COMPARE + 1)
            return f"{left} {symbol} {right}", COMPARE
        if kind == "robot_button_pressed":
            return f'button_pressed("{fields.get("BUTTON", "A")}")', ATOM
        if kind == "robot_distance_condition":
            symbol = "<" if fields.get("OPERATOR", "LESS_THAN") == "LESS_THAN" else ">"
            limit = self.value(block, "CENTIMETRES", COMPARE + 1, "20")
            return f"distance() {symbol} {limit}", COMPARE
        return "None", ATOM


def _pad(depth):
    return "    " * depth


def python_to_blocks(code):
    """Return ``(workspace_state, normalised_code)`` or raise ``Unsupported``."""
    try:
        tree = ast.parse(code)
        parser = _Parser(code)
        first = parser.chain(parser.statements(tree.body))
    except SyntaxError as error:
        raise Unsupported(f"Syntax error: {error.msg}", error.lineno, syntax=True) from None
    except (ValueError, RecursionError, MemoryError):
        raise Unsupported("This code is too tangled to read", syntax=True) from None
    state = {
        "blocks": {"languageVersion": 0, "blocks": [first] if first else []},
        "variables": [{"name": name, "id": f"var_{name}"} for name in parser.names],
    }
    return state, blocks_to_python(state)


class _Parser:
    def __init__(self, source):
        self.source = source
        self.names = []
        self.imported_modules = set()

    def fail(self, node, message=None):
        raise Unsupported(message or f"Blocks can't do `{self.snippet(node)}` yet", getattr(node, "lineno", None))

    def snippet(self, node):
        text = ast.get_source_segment(self.source, node) or type(node).__name__
        line = text.strip().splitlines()[0] if text.strip() else type(node).__name__
        return line if len(line) <= 50 else line[:47] + "..."

    @staticmethod
    def make(kind, fields=None, inputs=None):
        block = {"type": kind}
        if fields:
            block["fields"] = fields
        if inputs:
            block["inputs"] = inputs
        return block

    @staticmethod
    def is_call(node, name):
        return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name

    @staticmethod
    def is_attribute(node, dotted_name):
        if not isinstance(node, ast.Attribute):
            return False
        parts = [node.attr]
        value = node.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if not isinstance(value, ast.Name):
            return False
        parts.append(value.id)
        return ".".join(reversed(parts)) == dotted_name

    @classmethod
    def is_attribute_call(cls, node, dotted_name):
        return isinstance(node, ast.Call) and cls.is_attribute(node.func, dotted_name)

    @staticmethod
    def is_cv2_constant(node, name):
        return _Parser.is_attribute(node, f"cv2.{name}")

    def statements(self, nodes):
        blocks = [self.statement(node) for node in nodes]
        return [block for block in blocks if block is not None]

    @staticmethod
    def chain(blocks):
        following = None
        for block in reversed(blocks):
            if following is not None:
                block["next"] = {"block": following}
            following = block
        return following

    def set_statement(self, inputs, name, nodes):
        first = self.chain(self.statements(nodes))
        if first is not None:
            inputs[name] = {"block": first}

    def variable(self, node):
        if node.id in RESERVED_NAMES:
            self.fail(node, f"`{node.id}` is a robot command or Python word, so it can't be a variable name")
        if node.id not in self.names:
            self.names.append(node.id)
        return {"id": f"var_{node.id}"}

    def bind(self, call, params):
        if any(isinstance(arg, ast.Starred) for arg in call.args) or any(key.arg is None for key in call.keywords):
            self.fail(call)
        names = [name for name, _ in params]
        if len(call.args) > len(names):
            self.fail(call, f"`{call.func.id}` was given too many values")
        bound = dict(zip(names, call.args))
        for key in call.keywords:
            if key.arg not in names or key.arg in bound:
                self.fail(call, f"Blocks can't show `{call.func.id}` with the option `{key.arg}`")
            bound[key.arg] = key.value
        for name, default in params:
            if name not in bound:
                if default is _REQUIRED:
                    self.fail(call, f"`{call.func.id}` needs a value for `{name}`")
                bound[name] = ast.Constant(default)
        return bound

    def literal_number(self, node):
        sign = 1
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            sign, node = -1, node.operand
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if not math.isfinite(node.value):
                self.fail(node, "That number is too big for blocks")
            return sign * node.value
        return None

    def typed(self, node, wanted):
        block = self.expr(node)
        kind = block["type"]
        actual = "boolean" if kind in BOOLEAN_BLOCKS else "number" if kind in NUMBER_BLOCKS else "any"
        if wanted != "any" and actual not in (wanted, "any"):
            self.fail(node, f"`{self.snippet(node)}` is a {actual}, but blocks need a {wanted} here")
        return block

    def value_input(self, node, wanted):
        if wanted != "boolean":
            number = self.literal_number(node)
            if number is not None:
                return {"shadow": {"type": "math_number", "fields": {"NUM": number}}}
        return {"block": self.typed(node, wanted)}

    def number_input(self, node):
        return self.value_input(node, "number")

    def condition_input(self, node):
        return self.value_input(node, "boolean")

    def string_option(self, node, options):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in options:
            return node.value
        self.fail(node, "Blocks only accept: " + ", ".join(options))

    def colour(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value.strip().lower()
            if text in COLOURS:
                return COLOURS[text]
            if text in HEX_TO_NAME:
                return text
        self.fail(node, "Blocks only know these colours: " + ", ".join(COLOURS))

    def expr(self, node):
        number = self.literal_number(node)
        if number is not None:
            return self.make("math_number", {"NUM": number})
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return self.make("logic_boolean", {"BOOL": "TRUE" if node.value else "FALSE"})
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return self.make("text", {"TEXT": node.value})
        opencv_block = self._opencv_expression(node)
        if opencv_block is not None:
            return opencv_block
        if isinstance(node, ast.Name):
            return self.make("variables_get", {"VAR": self.variable(node)})
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self.make("logic_negate", inputs={"BOOL": self.condition_input(node.operand)})
        if isinstance(node, ast.BoolOp):
            operator = "AND" if isinstance(node.op, ast.And) else "OR"
            result = self.typed(node.values[0], "boolean")
            for value in node.values[1:]:
                result = self.make(
                    "logic_operation", {"OP": operator},
                    {"A": {"block": result}, "B": self.condition_input(value)},
                )
            return result
        if isinstance(node, ast.BinOp) and type(node.op) in ARITHMETIC_OPS:
            return self.make(
                "math_arithmetic", {"OP": ARITHMETIC_OPS[type(node.op)]},
                {"A": self.number_input(node.left), "B": self.number_input(node.right)},
            )
        if isinstance(node, ast.Compare):
            operator, right = node.ops[0], node.comparators[0]
            if len(node.ops) != 1:
                self.fail(node, "Blocks can only compare two things at a time")
            if self.is_call(node.left, "distance") and not node.left.args and not node.left.keywords \
                    and type(operator) in (ast.Lt, ast.Gt):
                return self.make(
                    "robot_distance_condition",
                    {"OPERATOR": "LESS_THAN" if isinstance(operator, ast.Lt) else "MORE_THAN"},
                    {"CENTIMETRES": self.number_input(right)},
                )
            if type(operator) not in COMPARE_OPS:
                self.fail(node)
            return self.make(
                "logic_compare", {"OP": COMPARE_OPS[type(operator)]},
                {"A": self.value_input(node.left, "any"), "B": self.value_input(right, "any")},
            )
        if self.is_call(node, "button_pressed"):
            args = self.bind(node, (("button", _REQUIRED),))
            return self.make("robot_button_pressed", {"BUTTON": self.string_option(args["button"], BUTTONS)})
        if self.is_call(node, "distance") and not node.args and not node.keywords:
            return self.make("robot_distance_value")
        if self.is_call(node, "scan_robot_qr") and not node.args and not node.keywords:
            return self.make("robot_scan_qr")
        self.fail(node)

    def statement(self, node):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = []
            if isinstance(node, ast.Import):
                module_names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif node.module:
                module_names = [node.module.split(".", 1)[0]]
            allowed = {"cv2", "numpy"}
            if not module_names or any(name not in allowed for name in module_names):
                self.fail(node, "Blocks load OpenCV and NumPy in the background; other imports need Python mode")
            self.imported_modules.update(module_names)
            return None
        if isinstance(node, ast.Pass):
            return None
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return None
            if isinstance(node.value, ast.Call):
                return self.call_statement(node.value)
            self.fail(node)
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                self.fail(node)
            return self.make(
                "variables_set", {"VAR": self.variable(node.targets[0])},
                {"VALUE": self.value_input(node.value, "any")},
            )
        if isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name) or not isinstance(node.op, ast.Add):
                self.fail(node)
            return self.make(
                "math_change", {"VAR": self.variable(node.target)},
                {"DELTA": self.number_input(node.value)},
            )
        if isinstance(node, ast.If):
            return self.if_statement(node)
        if isinstance(node, ast.While):
            return self.while_statement(node)
        if isinstance(node, ast.For):
            return self.for_statement(node)
        self.fail(node)

    def call_statement(self, call):
        if not isinstance(call.func, ast.Name):
            self.fail(call)
        name = call.func.id
        if name in MOVE_BLOCKS:
            args = self.bind(call, MOVE_PARAMS)
            return self.make(MOVE_BLOCKS[name], inputs={
                "SECONDS": self.number_input(args["seconds"]),
                "SPEED": self.number_input(args["power"]),
            })
        if name == "drive":
            args = self.bind(call, (("direction", _REQUIRED),) + MOVE_PARAMS)
            direction = self.string_option(args["direction"], DIRECTIONS)
            return self.make("robot_drive_for", {"DIRECTION": direction.upper()}, {
                "SECONDS": self.number_input(args["seconds"]),
                "SPEED": self.number_input(args["power"]),
            })
        if name == "wait":
            args = self.bind(call, (("seconds", 1),))
            return self.make("robot_wait", inputs={"SECONDS": self.number_input(args["seconds"])})
        if name == "stop":
            self.bind(call, ())
            return self.make("robot_stop")
        if name == "print":
            if len(call.args) > 2 or any(key.arg not in {None, "sep"} for key in call.keywords):
                self.fail(call, "Blocks can print one or two values")
            if call.keywords and any(key.arg == "sep" for key in call.keywords):
                self.fail(call, "Blocks use the default print separator")
            if not call.args:
                self.fail(call, "`print` needs a value")
            inputs = {"VALUE": self.value_input(call.args[0], "any")}
            if len(call.args) == 2:
                inputs["VALUE2"] = self.value_input(call.args[1], "any")
            return self.make("robot_print", inputs=inputs)
        if name == "take_picture":
            self.bind(call, ())
            return self.make("robot_take_picture")
        if name == "show_in_live_camera":
            args = self.bind(call, (("image", _REQUIRED),))
            image = args["image"]
            if self.is_call(image, "take_picture") and not image.args and not image.keywords:
                return self.make("robot_show_live_camera")
            return self.make("robot_show_live_camera", inputs={"IMAGE": {"block": self.expr(image)}})
        if name == "set_lights":
            args = self.bind(call, (("colour", _REQUIRED),))
            return self.make("robot_set_lights", {"COLOR": self.colour(args["colour"])})
        if name == "lights_off":
            self.bind(call, ())
            return self.make("robot_underlights_off")
        if name == "flash_lights":
            args = self.bind(call, (("colour", _REQUIRED), ("times", 3)))
            return self.make(
                "robot_flash_lights", {"COLOR": self.colour(args["colour"])},
                {"TIMES": self.number_input(args["times"])},
            )
        if name == "set_button_light":
            args = self.bind(call, (("button", _REQUIRED), ("brightness", 1)))
            return self.make(
                "robot_button_light", {"BUTTON": self.string_option(args["button"], BUTTONS)},
                {"BRIGHTNESS": self.number_input(args["brightness"])},
            )
        if name == "wait_until":
            condition = self.bind(call, (("condition", _REQUIRED),))["condition"]
            arguments = condition.args if isinstance(condition, ast.Lambda) else None
            if arguments is None or arguments.args or arguments.posonlyargs or arguments.kwonlyargs \
                    or arguments.vararg or arguments.kwarg:
                self.fail(call, "Blocks understand `wait_until(lambda: ...)` with a condition after the colon")
            return self.make("robot_wait_until", inputs={"CONDITION": self.condition_input(condition.body)})
        self.fail(call, f"Blocks don't know `{name}(...)`")

    def _opencv_args(self, call, count, label):
        if len(call.args) != count or call.keywords:
            self.fail(call, f"Blocks use the simple form `cv2.{label}(...)`")
        return call.args

    def _kernel_size(self, node):
        value = self.literal_number(node)
        if not isinstance(value, int) or value < 1 or value % 2 == 0:
            self.fail(node, "The OpenCV blur kernel must be a positive odd whole number")
        return value

    def _number_tuple(self, node, length, label):
        if not isinstance(node, (ast.Tuple, ast.List)) or len(node.elts) != length:
            self.fail(node, f"Blocks need {label} to be a tuple of {length} numbers")
        values = [self.literal_number(item) for item in node.elts]
        if any(value is None for value in values):
            self.fail(node, f"Blocks need {label} to contain plain numbers")
        return values

    def _opencv_expression(self, node):
        if self.is_call(node, "take_picture") and not node.args and not node.keywords:
            return self.make("opencv_camera_image")
        if self.is_attribute_call(node, "cv2.cvtColor"):
            image, colour_space = self._opencv_args(node, 2, "cvtColor")
            if self.is_cv2_constant(colour_space, "COLOR_BGR2HSV"):
                conversion = "BGR_TO_HSV"
            elif self.is_cv2_constant(colour_space, "COLOR_HSV2BGR"):
                conversion = "HSV_TO_BGR"
            else:
                self.fail(colour_space, "Blocks use cv2.COLOR_BGR2HSV or cv2.COLOR_HSV2BGR")
            return self.make(
                "opencv_to_hsv", {"CONVERSION": conversion},
                {"IMAGE": {"block": self.expr(image)}},
            )
        if self.is_attribute_call(node, "cv2.GaussianBlur"):
            image, kernel, sigma = self._opencv_args(node, 3, "GaussianBlur")
            kernel_values = self._number_tuple(kernel, 2, "the blur kernel")
            if (
                any(not isinstance(value, int) or value < 1 or value % 2 == 0 for value in kernel_values)
                or kernel_values[0] != kernel_values[1]
            ):
                self.fail(kernel, "Blocks use a positive odd square OpenCV blur kernel")
            if self.literal_number(sigma) != 0:
                self.fail(sigma, "Blocks use a Gaussian blur sigma of 0")
            return self.make(
                "opencv_blur",
                inputs={
                    "IMAGE": {"block": self.expr(image)},
                    "KERNEL": {"shadow": {"type": "math_number", "fields": {"NUM": kernel_values[0]}}},
                },
            )
        if self.is_attribute_call(node, "cv2.blur"):
            image, kernel = self._opencv_args(node, 2, "blur")
            kernel_values = self._number_tuple(kernel, 2, "the blur kernel")
            if (
                any(not isinstance(value, int) or value < 1 or value % 2 == 0 for value in kernel_values)
                or kernel_values[0] != kernel_values[1]
            ):
                self.fail(kernel, "Blocks use a positive odd square OpenCV blur kernel")
            return self.make(
                "opencv_box_blur",
                inputs={
                    "IMAGE": {"block": self.expr(image)},
                    "KERNEL": {"shadow": {"type": "math_number", "fields": {"NUM": kernel_values[0]}}},
                },
            )
        if self.is_attribute_call(node, "cv2.inRange"):
            image, low, high = self._opencv_args(node, 3, "inRange")
            low_values = self._number_tuple(low, 3, "the low HSV bound")
            high_values = self._number_tuple(high, 3, "the high HSV bound")
            def hsv_bound(values):
                return {
                    "block": self.make(
                        "opencv_hsv_value",
                        inputs={
                            name: {"shadow": {"type": "math_number", "fields": {"NUM": value}}}
                            for name, value in zip(("H", "S", "V"), values)
                        },
                    )
                }
            inputs = {
                "IMAGE": {"block": self.expr(image)},
                "LOW": hsv_bound(low_values),
                "HIGH": hsv_bound(high_values),
            }
            return self.make("opencv_hsv_mask", inputs=inputs)
        if self.is_attribute_call(node, "cv2.countNonZero"):
            (image,) = self._opencv_args(node, 1, "countNonZero")
            return self.make("opencv_count_nonzero", inputs={"IMAGE": {"block": self.expr(image)}})
        if self.is_attribute_call(node, "cv2.bitwise_or"):
            left, right = self._opencv_args(node, 2, "bitwise_or")
            return self.make(
                "opencv_mask_or",
                inputs={
                    "IMAGE1": {"block": self.expr(left)},
                    "IMAGE2": {"block": self.expr(right)},
                },
            )
        return None

    def if_statement(self, node):
        if self.is_call(node.test, "sees_colour"):
            args = self.bind(node.test, (("colour", _REQUIRED), ("tolerance", 18), ("min_area", 500)))
            inputs = {
                "TOLERANCE": self.number_input(args["tolerance"]),
                "MIN_AREA": self.number_input(args["min_area"]),
            }
            self.set_statement(inputs, "THEN", node.body)
            self.set_statement(inputs, "ELSE", node.orelse)
            return self.make("robot_if_color", {"COLOR": self.colour(args["colour"])}, inputs)

        inputs = {}
        current, index = node, 0
        while True:
            inputs[f"IF{index}"] = self.condition_input(current.test)
            self.set_statement(inputs, f"DO{index}", current.body)
            orelse = current.orelse
            if len(orelse) == 1 and isinstance(orelse[0], ast.If) and not self.is_call(orelse[0].test, "sees_colour"):
                current, index = orelse[0], index + 1
                continue
            break
        self.set_statement(inputs, "ELSE", orelse)
        block = self.make("controls_if", inputs=inputs)
        extra = {}
        if index:
            extra["elseIfCount"] = index
        if "ELSE" in inputs:
            extra["hasElse"] = True
        if extra:
            block["extraState"] = extra
        return block

    def while_statement(self, node):
        if node.orelse:
            self.fail(node, "Blocks can't do `while ... else` yet")
        test, mode = node.test, "WHILE"
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            test, mode = test.operand, "UNTIL"
        inputs = {"BOOL": self.condition_input(test)}
        self.set_statement(inputs, "DO", node.body)
        return self.make("controls_whileUntil", {"MODE": mode}, inputs)

    def for_statement(self, node):
        call = node.iter
        if node.orelse or not isinstance(node.target, ast.Name) or not isinstance(call, ast.Call) \
                or not isinstance(call.func, ast.Name):
            self.fail(node, "Blocks only understand `for _ in range(...)` and `for i in count(...)` loops")
        name = call.func.id
        inputs = {}
        if node.target.id == "_" and name == "range":
            times = self.bind(call, (("times", _REQUIRED),))["times"]
            if self.is_call(times, "int") and len(times.args) == 1 and not times.keywords:
                times = times.args[0]
            inputs["TIMES"] = self.number_input(times)
            self.set_statement(inputs, "DO", node.body)
            return self.make("robot_repeat", inputs=inputs)

        if node.target.id == "_":
            self.fail(node, "Blocks only understand `for _ in range(...)` and `for i in count(...)` loops")
        variable = {"VAR": self.variable(node.target)}
        if name == "count":
            args = self.bind(call, (("start", _REQUIRED), ("stop", _REQUIRED), ("step", 1)))
            inputs.update(
                FROM=self.number_input(args["start"]),
                TO=self.number_input(args["stop"]),
                BY=self.number_input(args["step"]),
            )
        elif name == "range" and 1 <= len(call.args) <= 3 and not call.keywords:
            numbers = [self.literal_number(arg) for arg in call.args]
            if any(not isinstance(number, int) for number in numbers):
                self.fail(node, "Blocks can only use `range()` with plain whole numbers")
            if len(numbers) == 1:
                start, stop, step = 0, numbers[0], 1
            elif len(numbers) == 2:
                (start, stop), step = numbers, 1
            else:
                start, stop, step = numbers
            if step <= 0 or start >= stop:
                self.fail(node, "Blocks can only count upwards with at least one number to count")
            last = start + ((stop - start - 1) // step) * step
            for key, number in (("FROM", start), ("TO", last), ("BY", step)):
                inputs[key] = {"shadow": {"type": "math_number", "fields": {"NUM": number}}}
        else:
            self.fail(node, "Blocks only understand `for _ in range(...)` and `for i in count(...)` loops")
        self.set_statement(inputs, "DO", node.body)
        return self.make("controls_for", variable, inputs)
