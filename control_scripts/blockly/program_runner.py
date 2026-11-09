"""Run student programs (Blockly or Python) against a RobotSession."""

from __future__ import annotations

import colorsys
import ctypes
import functools
import logging
import math
import os
import re
import sys
import threading
import time
import traceback
from collections import deque

import cv2
import numpy as np
from blocks_python import BUTTONS, COLOURS, block_labels, blocks_to_python_with_map
from robot_session import ACTIVE_STATES, _clamp, _minutes_text

LOG = logging.getLogger("trilobot_blockly")

MAX_PYTHON_CHARS = 50_000
DEFAULT_PROGRAM_MAX_SECONDS = 900
# Student code stuck in pure Python is interrupted this long after a stop.
FORCE_STOP_SECONDS = 1.5
STOP_REASONS = {
    "connection_lost": "the connection to the robot was lost",
    "taken_over": "someone else took control of the robot",
    "busy": "the robot is being used by someone else",
    "user": "you disconnected from the robot",
    "refused": "the robot stopped accepting connections",
    "timeout": "the robot could not be reached",
    "tab_closed": "the browser tab was closed",
}
ROBOT_QR_PATTERN = re.compile(
    r"^https://lcastor\.lincoln\.ac\.uk/#(trilo-\d{2})$", re.IGNORECASE
)

# Box colours (BGR) for scan_robot_qr(), matching the green, orange and red
# design tokens in style.css: robot code, other code, unreadable code.
QR_ROBOT_COLOUR = (119, 180, 47)
QR_OTHER_COLOUR = (50, 154, 228)
QR_UNREADABLE_COLOUR = (90, 90, 231)

_MOVES = {
    "forward": lambda speed: (speed, speed),
    "backward": lambda speed: (-speed, -speed),
    "turn_left": lambda speed: (-speed, speed),
    "turn_right": lambda speed: (speed, -speed),
    "turn_around": lambda speed: (speed, -speed),
}
_DIRECTION_MOVES = {
    "forward": "forward",
    "backward": "backward",
    "left": "turn_left",
    "right": "turn_right",
}


class _Stopped(BaseException):
    """Raised inside student Python when Stop is pressed."""


STUDENT_FILENAME = "<student>"
MAX_LABEL_CHARS = 60


def _line_tracer(thread):
    """A sys.settrace function recording the running student line on thread.

    Only frames compiled from student code get a local tracer, so library
    code runs untraced. The hot path is one attribute write per line.
    """

    def local(frame, event, _arg):
        if event == "line":
            thread.current_line = frame.f_lineno
        return local

    def tracer(frame, _event, _arg):
        if frame.f_code.co_filename == STUDENT_FILENAME:
            return local
        return None

    return tracer


def _finite(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise TypeError(f"{name} must be a number")
    return float(value)


def _hex_colour(value, default="#ff0000"):
    text = str(value or default).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        text = default
    return tuple(int(text[index : index + 2], 16) for index in (1, 3, 5))


def _seconds_value(value):
    return max(0.0, _finite(value, "seconds"))


def _power_value(value):
    return _clamp(_finite(value, "power"), 0, 100)


def _colour_value(value):
    text = str(value).strip().lower()
    if text in COLOURS:
        return COLOURS[text]
    if re.fullmatch(r"#[0-9a-f]{6}", text):
        return text
    raise ValueError(
        f"Unknown colour {value!r}: use {', '.join(COLOURS)} or a #rrggbb code"
    )


def _button_value(value):
    text = str(value).strip().upper()
    if text not in BUTTONS:
        raise ValueError("button must be A, B, X or Y")
    return text


class ProgramRunner:
    """Run student programs, either Blockly blocks or plain Python."""

    def __init__(self, session, max_seconds=None):
        self.session = session
        self.max_seconds = max_seconds
        self.lock = threading.RLock()
        self.thread = None
        self.python_thread = None
        # Each run gets its own id and stop event, so a slow-to-die old
        # thread can never stop, reset or report over a newer run.
        self.run_id = 0
        self.stop_event = threading.Event()
        self._stop_message = ""
        self._stop_by_connection = False
        self._limit_timer = None
        self.picture = None
        self.camera_view = None
        self.output = deque(maxlen=200)
        self.vision = {
            "status": "No picture checked yet",
            "colour": "",
            "matched": False,
            "area": 0,
        }
        self._status = {"status": "idle", "current": "", "error": ""}
        self._mode = None
        session.add_state_listener(self._on_connection_state)

    def _program_max_seconds(self):
        if self.max_seconds is not None:
            return float(self.max_seconds)
        raw = os.environ.get("PROGRAM_MAX_SECONDS", DEFAULT_PROGRAM_MAX_SECONDS)
        try:
            seconds = float(raw)
        except (TypeError, ValueError):
            LOG.warning("Ignoring invalid PROGRAM_MAX_SECONDS=%r", raw)
            return float(DEFAULT_PROGRAM_MAX_SECONDS)
        return seconds if seconds > 0 else float(DEFAULT_PROGRAM_MAX_SECONDS)

    def is_running(self):
        with self.lock:
            thread = self.thread
            running = self._status.get("status") == "running"
        return running and thread is not None and thread.is_alive()

    def _connection_stop_reason(self, state, reason):
        holder = self.session.holder
        if state == "taken_over":
            return f"{holder or 'someone else'} took control of the robot"
        if state == "busy":
            return f"the robot is being used by {holder or 'someone else'}"
        if state == "idle" and reason == "user":
            return STOP_REASONS["user"]
        if state == "robot_offline":
            if reason in ("refused", "timeout"):
                return STOP_REASONS[reason]
            return "the robot went offline"
        if reason == "connection_lost":
            return STOP_REASONS["connection_lost"]
        return STOP_REASONS.get(reason, "the connection to the robot was lost")

    def _on_connection_state(self, old, new, reason):
        """Stop student code when the robot link stops being usable."""
        if new in ACTIVE_STATES:
            # Back online: the old "stopped because..." note is stale. It
            # stays in the events log; the program panel starts clean.
            with self.lock:
                if self._stop_by_connection and self._status.get("status") != "running":
                    self._status.update(error="")
                    self._stop_message = ""
                self._stop_by_connection = False
            self.session.program_stopped = False
            return
        if new in ("connecting", "reconnecting") and old not in ACTIVE_STATES:
            return
        because = self._connection_stop_reason(new, reason)
        message = f"Your program was stopped because {because}."
        if old in ACTIVE_STATES and self.is_running():
            with self.lock:
                self._stop_by_connection = True
            self.session.program_stopped = True
            self.stop(message)
            self.session._event("warning", message)
            return
        # A program stopped earlier in this outage (say "connection lost") now
        # has a more precise explanation: taken over, busy, offline, ...
        with self.lock:
            refine = (
                self._stop_by_connection
                and self._status.get("status") != "running"
                and self._status.get("error") != message
            )
            if refine:
                self._status.update(error=message)
                self._stop_message = message
        if refine:
            self.session._event("warning", message)

    def _time_limit(self, run_id, seconds):
        message = (
            f"Your program was stopped after {_minutes_text(seconds)} minutes "
            "(time limit)."
        )
        if self.stop(message, run_id=run_id):
            self.session._event("warning", message)

    def start(self, program):
        if not isinstance(program, dict):
            raise ValueError("The saved Blockly program is not valid JSON")
        blocks = program.get("blocks")
        top_blocks = blocks.get("blocks", []) if isinstance(blocks, dict) else []
        if not top_blocks:
            raise ValueError("Add an action block to the workspace before running")
        if len(top_blocks) > 1:
            raise ValueError(
                f"Join the {len(top_blocks)} separate block stacks together before running"
            )
        # Blocks are a teaching interface for the same Python API exposed in the
        # Python tab. Running the generated program keeps the two modes honest:
        # a block cannot silently behave differently from its real Python twin.
        code, line_map = blocks_to_python_with_map(program)
        self._start_code(code, "blocks", line_map, block_labels(program))

    def start_python(self, code):
        self._start_code(code, "python")

    def _start_code(self, code, mode, line_map=None, labels=None):
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Write some Python before running")
        if len(code) > MAX_PYTHON_CHARS:
            raise ValueError("That Python program is too long")
        try:
            compiled = compile(code, STUDENT_FILENAME, "exec")
        except (SyntaxError, ValueError) as error:
            line = getattr(error, "lineno", None)
            message = getattr(error, "msg", None) or str(error)
            raise ValueError(f"Line {line}: {message}" if line else message) from None
        self._launch(
            self._python_main,
            compiled,
            python=True,
            mode=mode,
            source_lines=code.splitlines(),
            line_map=line_map or {},
            labels=labels or {},
        )

    def _launch(self, target, payload, python=False, mode=None, **run_info):
        with self.lock:
            old_thread = self.thread
        self.stop()
        if (
            old_thread
            and old_thread.is_alive()
            and old_thread is not threading.current_thread()
        ):
            # Long enough for the forced stop (FORCE_STOP_SECONDS) to land.
            old_thread.join(timeout=FORCE_STOP_SECONDS + 1.5)
            if old_thread.is_alive():
                LOG.warning("The previous program did not stop; starting anyway")
        self.picture = None
        self.camera_view = None
        self.session.clear_camera_overlay()
        self.vision = {
            "status": "No picture checked yet",
            "colour": "",
            "matched": False,
            "area": 0,
        }
        stop_event = threading.Event()
        thread = threading.Thread(
            target=target,
            args=(payload,),
            daemon=True,
            name="trilobot-program",
        )
        thread.stop_event = stop_event
        thread.in_student_code = False
        # Written by the line tracer in the program thread, read by status().
        thread.current_line = None
        thread.mode = mode
        thread.source_lines = run_info.get("source_lines", [])
        thread.line_map = run_info.get("line_map", {})
        thread.labels = run_info.get("labels", {})
        seconds = self._program_max_seconds()
        with self.lock:
            if self._limit_timer is not None:
                self._limit_timer.cancel()
            self.run_id += 1
            thread.run_id = self.run_id
            self.stop_event = stop_event
            self._status = {"status": "running", "current": "", "error": ""}
            self._stop_message = ""
            self._stop_by_connection = False
            self.output.clear()
            self._mode = mode
            self.thread = thread
            self.python_thread = thread if python else None
            timer = threading.Timer(
                seconds, self._time_limit, args=(self.run_id, seconds)
            )
            timer.daemon = True
            self._limit_timer = timer
        self.session.program_stopped = False
        thread.start()
        timer.start()

    def _run_stop_event(self):
        """The stop event of the run that owns the calling thread."""
        event = getattr(threading.current_thread(), "stop_event", None)
        return event if event is not None else self.stop_event

    def stop(self, message=None, run_id=None):
        """Stop the program. message (if given) is shown as the reason.

        With run_id, only stop if that run is still the current one; returns
        whether anything was stopped.
        """
        with self.lock:
            if run_id is not None:
                thread = self.thread
                if run_id != self.run_id or thread is None or not thread.is_alive():
                    return False
            if message and not self._stop_message:
                self._stop_message = message
            self.stop_event.set()
            thread = self.python_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            # Student code that never calls a robot command can only be interrupted this way.
            timer = threading.Timer(
                FORCE_STOP_SECONDS, self._force_stop, args=(thread,)
            )
            timer.daemon = True
            timer.start()
        try:
            self.session.dispatch("stop")
        except RuntimeError as error:
            LOG.debug("Could not send stop: %s", error)
        return True

    @staticmethod
    def _force_stop(thread):
        # Only interrupt student code, never the cleanup that follows it.
        in_student = getattr(thread, "in_student_code", True)
        if thread.is_alive() and thread.ident and in_student:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(thread.ident), ctypes.py_object(_Stopped)
            )

    def status(self):
        with self.lock:
            result = dict(self._status)
            result["output"] = "\n".join(text for _, text in self.output)
            # Timestamped too, so the page can interleave print() output with
            # connection events in time order.
            result["output_lines"] = [{"t": t, "text": text} for t, text in self.output]
            result["camera_view"] = self.camera_view or "Live camera"
            thread = self.thread
            mode = self._mode
            running = result.get("status") == "running"
        result["vision"] = dict(self.vision)
        result["current_step"] = self._current_step(thread, mode, running)
        return result

    @staticmethod
    def _current_step(thread, mode, running):
        """Where the student program is: its line and, for blocks, the block."""
        step = {"mode": mode, "line": None, "block": None, "label": None}
        line = getattr(thread, "current_line", None) if running else None
        if line is None:
            return step
        step["line"] = line
        if mode == "blocks":
            block = thread.line_map.get(line)
            step["block"] = block
            step["label"] = thread.labels.get(block) if block else None
        else:
            lines = thread.source_lines
            text = lines[line - 1].strip() if 0 < line <= len(lines) else ""
            if len(text) > MAX_LABEL_CHARS:
                text = text[: MAX_LABEL_CHARS - 3] + "..."
            step["label"] = text or None
        return step

    def _set_status(self, **values):
        with self.lock:
            self._status.update(values)

    def _shutdown_robot(self):
        try:
            self.session.dispatch("stop")
            self.session.reset_lights()
        except RuntimeError as error:
            LOG.debug("Could not reset the robot after a program: %s", error)

    def _python_main(self, compiled):
        me = threading.current_thread()
        # Covers this thread only: report which student line is running.
        sys.settrace(_line_tracer(me))
        stop_event = self._run_stop_event()
        result = {}
        try:
            try:
                me.in_student_code = True
                exec(compiled, self._python_namespace())
            except (_Stopped, SystemExit):
                pass
            finally:
                me.in_student_code = False
                sys.settrace(None)
                me.current_line = None
            with self.lock:
                message = self._stop_message
            if message:
                result = dict(status="stopped", current="", error=message)
            else:
                result = dict(
                    status="stopped" if stop_event.is_set() else "complete",
                    current="",
                )
        except _Stopped:
            result = dict(status="stopped", current="")
        except Exception as error:
            with self.lock:
                message = self._stop_message
            if message:
                # A command failed because we were stopping; show why instead.
                LOG.info("Student Python stopped: %s (%s)", message, error)
                result = dict(status="stopped", current="", error=message)
            else:
                LOG.info("Student Python failed", exc_info=True)
                result = dict(
                    status="error", current="", error=self._student_error(error)
                )
        finally:
            sys.settrace(None)
            me.current_line = None
            with self.lock:
                # Only the current run may report, cancel the timer or reset
                # the robot; a newer run owns all of those otherwise.
                current = getattr(me, "run_id", None) == self.run_id
                if current:
                    self._status.update(result)
                    if self._limit_timer is not None:
                        self._limit_timer.cancel()
            if current:
                self._shutdown_robot()

    @staticmethod
    def _student_error(error):
        line = None
        for frame, frame_line in traceback.walk_tb(error.__traceback__):
            if frame.f_code.co_filename == STUDENT_FILENAME:
                line = frame_line
        text = f"{type(error).__name__}: {error}"
        return f"Line {line}: {text}" if line else text

    def _python_namespace(self):
        """The globals student code runs with: the robot API plus helpers."""
        return {
            "__name__": "__main__",
            # These are deliberately the real libraries. Students can copy the
            # same cv2/NumPy calls into a normal Python script later.
            "cv2": cv2,
            "np": np,
            "numpy": np,
            **self._student_robot_api(),
            **self._student_builtins(),
        }

    def _robot_command(self, label):
        """Decorate a student command: check Stop and show it as current."""

        def decorate(function):
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                self._check_stopped()
                self._set_status(current=label)
                result = function(*args, **kwargs)
                self._check_stopped()
                return result

            return wrapper

        return decorate

    def _student_robot_api(self):
        robot_command = self._robot_command

        def move(kind, label):
            @robot_command(label)
            def run(seconds=1, power=60):
                self._drive_for(
                    _MOVES[kind](_power_value(power)), _seconds_value(seconds)
                )

            return run

        @robot_command("Drive")
        def drive(direction, seconds=1, power=60):
            if direction not in _DIRECTION_MOVES:
                raise ValueError("direction must be forward, backward, left or right")
            speeds = _MOVES[_DIRECTION_MOVES[direction]](_power_value(power))
            self._drive_for(speeds, _seconds_value(seconds))

        @robot_command("Wait")
        def wait(seconds=1):
            self._wait(_seconds_value(seconds))

        @robot_command("Stop")
        def stop():
            self.session.call("stop")

        @robot_command("Take a picture")
        def take_picture():
            return self._take_picture()

        @robot_command("Show OpenCV image")
        def show_in_live_camera(image):
            self._show_in_live_camera(image)

        @robot_command("Scan robot QR code")
        def scan_robot_qr():
            return self._scan_robot_qr()

        @robot_command("OpenCV colour check")
        def sees_colour(colour, tolerance=18, min_area=500):
            return self._check_colour(
                _colour_value(colour),
                _clamp(_finite(tolerance, "tolerance"), 1, 90),
                max(1.0, _finite(min_area, "min_area")),
            )

        @robot_command("Distance check")
        def distance():
            reading = self._distance_cm()
            return math.nan if reading is None else reading

        @robot_command("Button check")
        def button_pressed(button):
            name = _button_value(button)
            self._wait(0.02)
            return self._button_pressed(name)

        @robot_command("Wait until")
        def wait_until(condition):
            while not (condition() if callable(condition) else condition):
                self._check_stopped()
                self._wait(0.05)

        @robot_command("Set lights")
        def set_lights(colour):
            self.session.call("set_underlights", _hex_colour(_colour_value(colour)))

        @robot_command("Turn off underlights")
        def lights_off():
            self.session.call("set_underlights", (0, 0, 0))

        @robot_command("Flash lights")
        def flash_lights(colour, times=3, on_seconds=0.2, off_seconds=0.2):
            self._flash(
                _colour_value(colour),
                max(0, int(_finite(times, "times"))),
                _seconds_value(on_seconds),
                _seconds_value(off_seconds),
            )

        @robot_command("Button light")
        def set_button_light(button, brightness=1):
            self.session.call(
                "set_button_led",
                _button_value(button),
                _clamp(_finite(brightness, "brightness"), 0, 1),
            )

        return {
            "forward": move("forward", "Move forward"),
            "backward": move("backward", "Move backward"),
            "turn_left": move("turn_left", "Turn left"),
            "turn_right": move("turn_right", "Turn right"),
            "turn_around": move("turn_around", "Turn around"),
            "drive": drive,
            "wait": wait,
            "stop": stop,
            "take_picture": take_picture,
            "show_in_live_camera": show_in_live_camera,
            "scan_robot_qr": scan_robot_qr,
            "sees_colour": sees_colour,
            "distance": distance,
            "button_pressed": button_pressed,
            "wait_until": wait_until,
            "set_lights": set_lights,
            "lights_off": lights_off,
            "flash_lights": flash_lights,
            "set_button_light": set_button_light,
        }

    def _student_builtins(self):
        def count(start, stop, step=1):
            start, stop = _finite(start, "start"), _finite(stop, "stop")
            step = abs(_finite(step, "step"))
            if step == 0:
                raise ValueError("count() needs a step that is not 0")
            step = step if start <= stop else -step
            value = start
            if start.is_integer() and step.is_integer():
                value, step = int(start), int(step)
            while value <= stop if step > 0 else value >= stop:
                self._check_stopped()
                yield value
                value += step

        def student_print(*values, sep=" ", **_ignored):
            text = (" " if sep is None else str(sep)).join(
                str(value) for value in values
            )
            now = time.time()
            with self.lock:
                self.output.extend((now, line) for line in text.split("\n"))

        def student_input(*_args):
            raise RuntimeError("input() is not available here")

        return {
            "count": count,
            "print": student_print,
            "input": student_input,
        }

    def _check_stopped(self):
        if self._run_stop_event().is_set():
            raise _Stopped()

    def _take_picture(self):
        picture = self.session.frame_copy()
        if picture is None:
            raise RuntimeError("No camera frame is available yet")
        self.picture = picture
        self.vision = {
            "status": "Picture ready for OpenCV colour check",
            "colour": "",
            "matched": False,
            "area": 0,
        }
        self.camera_view = "Fresh camera picture"
        return picture.copy()

    def _show_in_live_camera(self, image):
        """Show an OpenCV image in the camera panel when it is displayable."""
        if not isinstance(image, np.ndarray):
            raise TypeError("show_in_live_camera() needs a NumPy image")
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim != 3 or image.shape[2] not in (3, 4):
            raise ValueError("show_in_live_camera() needs a grayscale or colour image")
        image = image[:, :, :3]
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        self.session.set_camera_overlay(image)
        self.camera_view = f"OpenCV preview ({image.shape[1]}×{image.shape[0]})"

    def _scan_robot_qr(self):
        """Return the robot name from a Lincoln robot QR code, or an empty string."""
        frame = self.session.frame_copy()
        if frame is None:
            self.vision = {
                "status": "No camera frame for QR scan",
                "colour": "",
                "matched": False,
                "area": 0,
                "qr": "",
            }
            return ""

        detector = cv2.QRCodeDetector()
        # (text, corner points) for every code found; text is "" if unreadable.
        codes = []
        try:
            found, values, points, _ = detector.detectAndDecodeMulti(frame)
            if found and points is not None:
                codes.extend(zip(values, points, strict=False))
        except (AttributeError, cv2.error):
            pass
        if not any(value for value, _ in codes):
            try:
                value, points, _ = detector.detectAndDecode(frame)
                if points is not None:
                    codes = [(value, points)]
            except cv2.error:
                pass

        robot_name = ""
        marks = []
        for value, points in codes:
            match = ROBOT_QR_PATTERN.fullmatch(value.strip())
            if match:
                robot_name = robot_name or match.group(1).lower()
                marks.append((points, match.group(1).lower(), QR_ROBOT_COLOUR))
            elif value:
                # OpenCV's built-in font only draws plain ASCII.
                text = value.strip().encode("ascii", "replace").decode("ascii")
                label = text if len(text) <= 24 else text[:21] + "..."
                marks.append((points, label, QR_OTHER_COLOUR))
            else:
                marks.append((points, "unreadable QR", QR_UNREADABLE_COLOUR))
        # Show where the codes are (or clear old boxes when none are found).
        self.session.set_camera_marks(marks)
        self.vision = {
            "status": (
                f"Robot QR found: {robot_name}" if robot_name else "Robot QR not found"
            ),
            "colour": "",
            "matched": bool(robot_name),
            "area": 0,
            "qr": robot_name,
        }
        self.camera_view = (
            f"QR scan: {robot_name}" if robot_name else "QR scan: no robot code"
        )
        return robot_name

    def _check_colour(self, colour, tolerance, min_area):
        matched, area = self._detect_colour(colour, tolerance, min_area)
        self.vision = {
            "status": "Colour found" if matched else "Colour not found",
            "colour": colour,
            "matched": matched,
            "area": round(area),
        }
        return matched

    def _button_pressed(self, button):
        buttons = self.session.telemetry_snapshot().get("buttons")
        return bool(isinstance(buttons, dict) and buttons.get(button))

    def _wait(self, seconds):
        end = time.monotonic() + max(0, seconds)
        while time.monotonic() < end and not self._run_stop_event().is_set():
            time.sleep(max(0.0, min(0.03, end - time.monotonic())))

    def _drive_for(self, speeds, seconds):
        # The robot sender stops the motors after 0.6 seconds without a
        # drive packet. Keep refreshing the command while this block runs.
        left = speeds[0] / 100.0
        right = speeds[1] / 100.0
        deadline = time.monotonic() + max(0.0, seconds)
        try:
            while not self._run_stop_event().is_set() and time.monotonic() < deadline:
                self.session.dispatch("drive", left, right)
                remaining = deadline - time.monotonic()
                self._wait(min(0.18, max(0.0, remaining)))
        finally:
            try:
                self.session.dispatch("stop")
            except RuntimeError as error:
                LOG.debug("Could not stop the motors: %s", error)

    def _distance_cm(self):
        try:
            self.session.dispatch("request_distance")
        except RuntimeError as error:
            LOG.debug("Could not request distance: %s", error)
            return None
        self._wait(0.08)
        value = self.session.telemetry_snapshot().get("distance_cm")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _flash(self, colour, times, on_seconds, off_seconds):
        rgb = _hex_colour(colour, "#00ff00")
        for _ in range(times):
            if self._run_stop_event().is_set():
                break
            self.session.call("set_underlights", rgb)
            self._wait(on_seconds)
            self.session.call("set_underlights", (0, 0, 0))
            self._wait(off_seconds)

    def _detect_colour(self, colour, tolerance, min_area):
        frame = self.picture if self.picture is not None else self.session.frame_copy()
        if frame is None:
            return False, 0.0

        rgb = _hex_colour(colour)
        hue, saturation, value = colorsys.rgb_to_hsv(
            *(component / 255 for component in rgb)
        )
        target_hue = int(hue * 179)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # This mirrors the normal OpenCV teaching pattern: HSV bounds,
        # cv2.inRange(), a small cleanup kernel, then contour area.
        low_s = max(40, int(saturation * 255) - 70)
        low_v = max(40, int(value * 255) - 100)
        high_s = min(255, int(saturation * 255) + 70)
        high_v = min(255, int(value * 255) + 100)
        hue_width = max(1, int(tolerance))

        if target_hue - hue_width < 0:
            mask = cv2.inRange(
                hsv,
                (0, low_s, low_v),
                (target_hue + hue_width, high_s, high_v),
            )
            mask |= cv2.inRange(
                hsv,
                (179 + target_hue - hue_width, low_s, low_v),
                (179, high_s, high_v),
            )
        elif target_hue + hue_width > 179:
            mask = cv2.inRange(
                hsv,
                (target_hue - hue_width, low_s, low_v),
                (179, high_s, high_v),
            )
            mask |= cv2.inRange(
                hsv,
                (0, low_s, low_v),
                (target_hue + hue_width - 179, high_s, high_v),
            )
        else:
            mask = cv2.inRange(
                hsv,
                (target_hue - hue_width, low_s, low_v),
                (target_hue + hue_width, high_s, high_v),
            )

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = max(
            (cv2.contourArea(contour) for contour in contours),
            default=0.0,
        )
        return area >= min_area, area


# -- the app page going away ---------------------------------------------------

# A reload polls again well inside this window and cancels the stop.
PAGE_CLOSE_GRACE_SECONDS = 5.0
# Without a closing beacon (crash, laptop asleep). Long on purpose: Chrome
# throttles hidden tabs and may space their polls about a minute apart.
PAGE_HEARTBEAT_TIMEOUT_SECONDS = 150.0
# How long after a closing beacon the robot is handed back for others.
PAGE_RELEASE_AFTER_SECONDS = 60.0
PAGE_CLOSED_MESSAGE = "Your program was stopped because the browser tab was closed."
PAGE_SILENT_MESSAGE = (
    "Your program was stopped because the app page stopped responding "
    "(tab closed or computer asleep)."
)


def _env_seconds(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return float(default)
    try:
        seconds = float(raw)
    except ValueError:
        LOG.warning("Ignoring invalid %s=%r", name, raw)
        return float(default)
    return seconds if seconds > 0 else float(default)


class PageWatch:
    """Stop the program and release the robot when the app page goes away.

    The page's /api/status polls are its heartbeat. pagehide sends a closing
    beacon; if no poll follows within close_grace the program is stopped, and
    after release_after the robot is disconnected so others can use it. With
    no beacon at all, heartbeat_timeout of silence does both. One daemon
    thread sleeps on a condition until the next deadline (never busy-waits).

    Each page load has its own id, so a late poll from the page that just
    closed cannot cancel its own closing.
    """

    def __init__(
        self,
        session,
        runner,
        *,
        close_grace=None,
        heartbeat_timeout=None,
        release_after=None,
        clock=time.monotonic,
    ):
        self.session = session
        self.runner = runner
        self.close_grace = float(
            close_grace
            if close_grace is not None
            else _env_seconds("PAGE_CLOSE_GRACE_SECONDS", PAGE_CLOSE_GRACE_SECONDS)
        )
        self.heartbeat_timeout = float(
            heartbeat_timeout
            if heartbeat_timeout is not None
            else _env_seconds(
                "PAGE_HEARTBEAT_TIMEOUT_SECONDS", PAGE_HEARTBEAT_TIMEOUT_SECONDS
            )
        )
        self.release_after = float(
            release_after
            if release_after is not None
            else _env_seconds("PAGE_RELEASE_AFTER_SECONDS", PAGE_RELEASE_AFTER_SECONDS)
        )
        self.clock = clock
        self.condition = threading.Condition()
        self.last_beat = None
        self.closing_at = None
        self.closed_pages = deque(maxlen=16)
        # What has already been done for the current absence of the page.
        self._stopped = False
        self._released = False
        self._thread = None
        self._shutdown = False

    def _ensure_thread(self):
        # Called with self.condition held.
        if self._thread is None and not self._shutdown:
            self._thread = threading.Thread(
                target=self._main, daemon=True, name="trilobot-page-watch"
            )
            self._thread.start()

    def beat(self, page_id):
        """A status poll from the app page with this page id."""
        page_id = str(page_id or "")[:64]
        if not page_id:
            return
        with self.condition:
            if page_id in self.closed_pages:
                return
            # Wake the thread only if it may be sleeping on an old plan:
            # a closing deadline, or nothing at all. Ordinary polls just
            # move last_beat; the thread re-plans when its deadline comes.
            replan = (
                self.last_beat is None
                or self.closing_at is not None
                or self._stopped
                or self._released
            )
            self.last_beat = self.clock()
            self.closing_at = None
            self._stopped = self._released = False
            if replan:
                self._ensure_thread()
                self.condition.notify_all()

    def closing(self, page_id):
        """The page sent its pagehide beacon: it is closing or reloading."""
        page_id = str(page_id or "")[:64]
        with self.condition:
            if page_id:
                self.closed_pages.append(page_id)
            self.closing_at = self.clock()
            self._stopped = self._released = False
            self._ensure_thread()
            self.condition.notify_all()

    def shutdown(self):
        with self.condition:
            self._shutdown = True
            self.condition.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _plan(self, now):
        """Return (action, closed, seconds until next deadline or None)."""
        if self.closing_at is not None:
            closed, base = True, self.closing_at
            stop_at = base + self.close_grace
            release_at = base + self.release_after
        elif self.last_beat is not None:
            closed, base = False, self.last_beat
            stop_at = release_at = base + self.heartbeat_timeout
        else:
            return None, False, None
        if not self._stopped and now >= stop_at:
            self._stopped = True
            return "stop", closed, 0
        if not self._released and now >= release_at:
            self._released = True
            return "release", closed, 0
        pending = [
            when
            for when, done in ((stop_at, self._stopped), (release_at, self._released))
            if not done
        ]
        return None, closed, (min(pending) - now if pending else None)

    def _run(self, action, closed):
        try:
            if action == "stop":
                self._stop_program(closed)
            else:
                self._release_robot(closed)
        except Exception:
            LOG.exception("Page watch %s failed", action)

    def check(self):
        """Run every action that is due now; return the seconds to the next."""
        while True:
            with self.condition:
                action, closed, wait = self._plan(self.clock())
            if action is None:
                return wait
            self._run(action, closed)

    def _stop_program(self, closed):
        if not self.runner.is_running():
            return
        message = PAGE_CLOSED_MESSAGE if closed else PAGE_SILENT_MESSAGE
        if self.runner.stop(message):
            self.session._event("warning", message)

    def _release_robot(self, closed):
        # A program still going (heartbeat path) is stopped first, so its
        # stop reason is the page, not the disconnect.
        self._stop_program(closed)
        with self.session.lock:
            state = self.session.state
        if state == "idle":
            return
        self.session.disconnect(reason="tab_closed")
        self.runner.stop()

    def _main(self):
        while True:
            with self.condition:
                if self._shutdown:
                    return
                action, closed, wait = self._plan(self.clock())
                if action is None:
                    # Planned and waited under one lock: no lost wake-ups.
                    self.condition.wait(timeout=wait)
                    continue
            self._run(action, closed)
