#!/usr/bin/env python3
"""Beginner-friendly Blockly control server for a Trilobot."""

from __future__ import annotations

import asyncio
import colorsys
import ctypes
import functools
import logging
import math
import re
import sys
import threading
import time
import traceback
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, render_template, request

CONTROL_SCRIPTS = Path(__file__).resolve().parents[1]
if str(CONTROL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CONTROL_SCRIPTS))
BLOCKLY_DIR = Path(__file__).resolve().parent
if str(BLOCKLY_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCKLY_DIR))

from blocks_python import (  # noqa: E402
    BUTTONS, COLOURS, Unsupported, blocks_to_python, python_to_blocks,
)
from client import RobotClient  # noqa: E402


LOG = logging.getLogger("trilobot_blockly")
app = Flask(__name__)
LIBRARY_DIR = Path(__file__).resolve().parent / "demos"
LIBRARY_DIR.mkdir(exist_ok=True)

VIDEO_SIZES = (
    (640, 480),
    (1640, 1232),
    (1920, 1080),
    (3280, 2464),
)
VIDEO_FPS_CHOICES = (5, 10, 15, 20, 25, 30)
DEFAULT_VIDEO_CONFIG = {
    "width": 640,
    "height": 480,
    "fps": 20.0,
    "jpeg_quality": 60,
}
STREAM_JPEG_QUALITY = 72
HEALTH_WINDOW_SECONDS = 3.0
MAX_PYTHON_CHARS = 50_000
ROBOT_QR_PATTERN = re.compile(
    r"^https://lcastor\.lincoln\.ac\.uk/#(trilo-\d{2})$", re.IGNORECASE
)

_MOVES = {
    "forward": lambda speed: (speed, speed),
    "backward": lambda speed: (-speed, -speed),
    "turn_left": lambda speed: (-speed, speed),
    "turn_right": lambda speed: (speed, -speed),
    "turn_around": lambda speed: (speed, -speed),
}
_DIRECTION_MOVES = {
    "forward": "forward", "backward": "backward", "left": "turn_left", "right": "turn_right",
}


class _Stopped(BaseException):
    """Raised inside student Python when Stop is pressed."""


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TypeError(f"{name} must be a number")
    return float(value)


def _number(value, default=0.0):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def _clamp(value, low, high):
    return max(low, min(high, value))


def _hex_colour(value, default="#ff0000"):
    text = str(value or default).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        text = default
    return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))


def _video_config(payload, fallback=None):
    fallback = dict(fallback or DEFAULT_VIDEO_CONFIG)
    payload = payload if isinstance(payload, dict) else {}
    requested_size = (int(_number(payload.get("width"), fallback["width"])),
                      int(_number(payload.get("height"), fallback["height"])))
    if requested_size not in VIDEO_SIZES:
        supported = ", ".join(f"{w}x{h}" for w, h in VIDEO_SIZES)
        raise ValueError(f"video size must be one of: {supported}")

    fps = _number(payload.get("fps"), fallback["fps"])
    if fps not in VIDEO_FPS_CHOICES:
        choices = ", ".join(str(value) for value in VIDEO_FPS_CHOICES)
        raise ValueError(f"fps must be one of: {choices}")

    quality = int(_number(payload.get("jpeg_quality"), fallback["jpeg_quality"]))
    if quality not in range(10, 101):
        raise ValueError("JPEG quality must be between 10 and 100")

    return {
        "width": requested_size[0],
        "height": requested_size[1],
        "fps": float(fps),
        "jpeg_quality": quality,
    }


def _rate(samples, now):
    if len(samples) < 2:
        return 0.0
    first = samples[0]
    last = samples[-1]
    duration = max(0.001, last - first)
    return (len(samples) - 1) / duration


def _age_ms(last_seen, now):
    if last_seen <= 0:
        return None
    return round(max(0.0, now - last_seen) * 1000)


def _placeholder_jpeg():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (24, 24, 24)
    text = "Waiting for camera"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.9
    thickness = 2
    (text_width, text_height), _ = cv2.getTextSize(
        text, font, font_scale, thickness
    )
    x = (frame.shape[1] - text_width) // 2
    y = (frame.shape[0] + text_height) // 2
    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        font_scale,
        (220, 220, 220),
        thickness,
        cv2.LINE_AA,
    )
    ok, encoded = cv2.imencode(
        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, STREAM_JPEG_QUALITY]
    )
    return encoded.tobytes() if ok else b""


class RobotSession:
    """Own one asyncio RobotClient loop while Flask serves HTTP requests."""

    def __init__(self):
        self.lock = threading.RLock()
        self.frame_condition = threading.Condition(self.lock)
        self.loop = None
        self.client = None
        self.thread = None
        self.stop_event = threading.Event()
        self.url = ""
        self.error = ""
        self.latest_frame = None
        self.latest_jpeg = _placeholder_jpeg()
        self.camera_overlay = None
        self.frame_sequence = 0
        self.frame_times = deque(maxlen=90)
        self.telemetry_times = deque(maxlen=30)
        self.last_frame_at = 0.0
        self.last_telemetry_at = 0.0
        self.last_telemetry_object = None
        self.last_command_ms = None
        self.command_times = deque(maxlen=30)
        self.video_config = dict(DEFAULT_VIDEO_CONFIG)

    def connect(self, url, video_config=None):
        url = str(url or "").strip()
        if not url.startswith(("ws://", "wss://")):
            raise ValueError("Robot address must start with ws:// or wss://")
        config = _video_config(video_config, self.video_config)
        self.disconnect()

        event = threading.Event()
        with self.lock:
            self.stop_event = event
            self.url = url
            self.error = ""
            self.latest_frame = None
            self.latest_jpeg = _placeholder_jpeg()
            self.camera_overlay = None
            self.frame_sequence = 0
            self.frame_times.clear()
            self.telemetry_times.clear()
            self.last_frame_at = 0.0
            self.last_telemetry_at = 0.0
            self.last_telemetry_object = None
            self.video_config = config
            self.client = None
            self.loop = None

        self.thread = threading.Thread(
            target=self._thread_main,
            args=(url, config, event),
            daemon=True,
            name="trilobot-websocket",
        )
        self.thread.start()

    def disconnect(self):
        with self.lock:
            event = self.stop_event
            loop = self.loop
            client = self.client
        event.set()
        if loop and client:
            try:
                future = asyncio.run_coroutine_threadsafe(client.close(), loop)
                future.result(timeout=2)
            except Exception:
                pass
        with self.frame_condition:
            self.frame_condition.notify_all()

    def _thread_main(self, url, video_config, event):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self.lock:
            self.loop = loop
        try:
            loop.run_until_complete(self._client_main(url, video_config, event))
        except Exception as error:
            if not event.is_set():
                with self.lock:
                    self.error = str(error)
        finally:
            with self.lock:
                self.client = None
                self.loop = None
            loop.close()
            with self.frame_condition:
                self.frame_condition.notify_all()

    async def _client_main(self, url, video_config, event):
        async with RobotClient(url) as client:
            with self.lock:
                self.client = client

            # A low-latency default is requested immediately after connection.
            await client.configure_video(
                video_config["width"],
                video_config["height"],
                video_config["fps"],
                video_config["jpeg_quality"],
            )

            while not event.is_set() and client.connected:
                frame = client.take_frame()
                if frame is not None:
                    self._store_frame(frame)

                telemetry = client.telemetry
                if telemetry is not self.last_telemetry_object:
                    self.last_telemetry_object = telemetry
                    with self.lock:
                        now = time.monotonic()
                        self.last_telemetry_at = now
                        self.telemetry_times.append(now)

                await asyncio.sleep(0.001)

            if client.error and not event.is_set():
                with self.lock:
                    self.error = str(client.error)

    def _store_frame(self, frame):
        with self.lock:
            config = dict(self.video_config)
            overlay = None if self.camera_overlay is None else self.camera_overlay.copy()
        display_frame = overlay if overlay is not None else frame
        if overlay is not None and overlay.shape[:2] != frame.shape[:2]:
            display_frame = cv2.resize(overlay, (frame.shape[1], frame.shape[0]))
        ok, encoded = cv2.imencode(
            ".jpg",
            display_frame,
            [cv2.IMWRITE_JPEG_QUALITY, config["jpeg_quality"]],
        )
        if not ok:
            return
        now = time.monotonic()
        with self.frame_condition:
            self.latest_frame = frame.copy()
            self.latest_jpeg = encoded.tobytes()
            self.frame_sequence += 1
            self.last_frame_at = now
            self.frame_times.append(now)
            self.frame_condition.notify_all()

    def set_camera_overlay(self, frame):
        with self.lock:
            self.camera_overlay = frame.copy()
        with self.frame_condition:
            self.frame_sequence += 1
            self.frame_condition.notify_all()

    def clear_camera_overlay(self):
        with self.lock:
            self.camera_overlay = None

    def call(self, method, *args, timeout=5):
        with self.lock:
            loop = self.loop
            client = self.client
        if loop is None or client is None or not client.connected:
            raise RuntimeError("Connect to the robot first")
        started = time.monotonic()
        future = asyncio.run_coroutine_threadsafe(
            getattr(client, method)(*args), loop
        )
        result = future.result(timeout=timeout)
        self._record_command(time.monotonic() - started)
        return result

    def dispatch(self, method, *args):
        """Queue a command without waiting for an HTTP response or robot ACK."""
        with self.lock:
            loop = self.loop
            client = self.client
        if loop is None or client is None or not client.connected:
            raise RuntimeError("Connect to the robot first")
        started = time.monotonic()
        future = asyncio.run_coroutine_threadsafe(
            getattr(client, method)(*args), loop
        )
        future.add_done_callback(
            lambda completed: self._record_command(time.monotonic() - started)
        )

    def reset_lights(self):
        """Turn off the underlights and all button LEDs."""
        self.dispatch("set_underlights", (0, 0, 0))
        for button in ("A", "B", "X", "Y"):
            self.dispatch("set_button_led", button, 0)

    def _record_command(self, elapsed):
        with self.lock:
            self.last_command_ms = round(elapsed * 1000, 1)
            self.command_times.append(time.monotonic())

    def configure_video(self, payload):
        config = _video_config(payload, self.video_config)
        self.call(
            "configure_video",
            config["width"],
            config["height"],
            config["fps"],
            config["jpeg_quality"],
            timeout=8,
        )
        with self.lock:
            self.video_config = config
        return config

    def frame_copy(self):
        with self.lock:
            return None if self.latest_frame is None else self.latest_frame.copy()

    def telemetry_snapshot(self):
        with self.lock:
            return dict(self.client.telemetry) if self.client else {}

    def wait_jpeg(self, last_sequence, timeout=1.0):
        with self.frame_condition:
            if self.frame_sequence == last_sequence:
                self.frame_condition.wait(timeout)
            return self.latest_jpeg, self.frame_sequence

    def status(self):
        now = time.monotonic()
        with self.lock:
            connected = bool(self.client and self.client.connected)
            frame_hz = _rate(self.frame_times, now)
            telemetry_hz = _rate(self.telemetry_times, now)
            frame_age = _age_ms(self.last_frame_at, now)
            telemetry_age = _age_ms(self.last_telemetry_at, now)
            command_hz = _rate(self.command_times, now)
            config = dict(self.video_config)
            error = self.error

        if not connected or error:
            health = "red"
            health_text = "Offline"
        elif frame_age is None or frame_age > 2000:
            health = "red"
            health_text = "No camera data"
        elif frame_hz < max(1.0, config["fps"] * 0.55) or telemetry_age > 1500:
            health = "orange"
            health_text = "Slow"
        else:
            health = "green"
            health_text = "Good"

        return {
            "connected": connected,
            "url": self.url,
            "error": error,
            "telemetry": self.telemetry_snapshot(),
            "video": config,
            "connection": {
                "health": health,
                "health_text": health_text,
                "video_hz": round(frame_hz, 1),
                "telemetry_hz": round(telemetry_hz, 1),
                "command_hz": round(command_hz, 1),
                "last_frame_ms": frame_age,
                "last_telemetry_ms": telemetry_age,
                "last_command_ms": self.last_command_ms,
            },
        }


class ProgramRunner:
    """Run student programs, either Blockly blocks or plain Python."""

    def __init__(self, session):
        self.session = session
        self.lock = threading.RLock()
        self.thread = None
        self.python_thread = None
        self.stop_event = threading.Event()
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
        self.start_python(blocks_to_python(program))

    def start_python(self, code):
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Write some Python before running")
        if len(code) > MAX_PYTHON_CHARS:
            raise ValueError("That Python program is too long")
        try:
            compiled = compile(code, "<student>", "exec")
        except (SyntaxError, ValueError) as error:
            line = getattr(error, "lineno", None)
            message = getattr(error, "msg", None) or str(error)
            raise ValueError(f"Line {line}: {message}" if line else message) from None
        self._launch(self._python_main, compiled, python=True)

    def _launch(self, target, payload, python=False):
        self.stop()
        old_thread = self.thread
        if old_thread and old_thread.is_alive() and old_thread is not threading.current_thread():
            old_thread.join(timeout=1)
        self.stop_event.clear()
        self.picture = None
        self.camera_view = None
        self.session.clear_camera_overlay()
        self.vision = {
            "status": "No picture checked yet",
            "colour": "",
            "matched": False,
            "area": 0,
        }
        with self.lock:
            self._status = {"status": "running", "current": "", "error": ""}
            self.output.clear()
        thread = threading.Thread(
            target=target,
            args=(payload,),
            daemon=True,
            name="trilobot-program",
        )
        self.thread = thread
        self.python_thread = thread if python else None
        thread.start()

    def stop(self):
        self.stop_event.set()
        thread = self.python_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            # Student code that never calls a robot command can only be interrupted this way.
            timer = threading.Timer(1.5, self._force_stop, args=(thread,))
            timer.daemon = True
            timer.start()
        try:
            self.session.dispatch("stop")
        except Exception:
            pass

    @staticmethod
    def _force_stop(thread):
        if thread.is_alive() and thread.ident:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(thread.ident), ctypes.py_object(_Stopped)
            )

    def status(self):
        with self.lock:
            result = dict(self._status)
            result["output"] = "\n".join(self.output)
            result["camera_view"] = self.camera_view or "Live camera"
        result["vision"] = dict(self.vision)
        return result

    def _set_status(self, **values):
        with self.lock:
            self._status.update(values)

    def _shutdown_robot(self):
        try:
            self.session.dispatch("stop")
            self.session.reset_lights()
        except Exception:
            pass

    def _thread_main(self, program):
        try:
            variables = self._variables(program)
            blocks = program.get("blocks", {})
            top_blocks = blocks.get("blocks", []) if isinstance(blocks, dict) else []
            if not top_blocks:
                raise ValueError("Add an action block to the workspace before running")
            if len(top_blocks) > 1:
                raise ValueError(
                    f"Join the {len(top_blocks)} separate block stacks together before running"
                )
            self._run_chain(top_blocks[0], variables)
            self._set_status(
                status="stopped" if self.stop_event.is_set() else "complete",
                current="",
            )
        except Exception as error:
            LOG.exception("Blockly program failed")
            self._set_status(status="error", current="", error=str(error))
        finally:
            self._shutdown_robot()

    def _python_main(self, compiled):
        try:
            try:
                exec(compiled, self._python_namespace())
            except (_Stopped, SystemExit):
                pass
            self._set_status(
                status="stopped" if self.stop_event.is_set() else "complete",
                current="",
            )
        except Exception as error:
            LOG.info("Student Python failed", exc_info=True)
            self._set_status(status="error", current="", error=self._student_error(error))
        finally:
            self._shutdown_robot()

    @staticmethod
    def _student_error(error):
        line = None
        for frame, frame_line in traceback.walk_tb(error.__traceback__):
            if frame.f_code.co_filename == "<student>":
                line = frame_line
        text = f"{type(error).__name__}: {error}"
        return f"Line {line}: {text}" if line else text

    def _python_namespace(self):
        def robot_command(label):
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

        def seconds_value(value):
            return max(0.0, _finite(value, "seconds"))

        def power_value(value):
            return _clamp(_finite(value, "power"), 0, 100)

        def colour_value(value):
            text = str(value).strip().lower()
            if text in COLOURS:
                return COLOURS[text]
            if re.fullmatch(r"#[0-9a-f]{6}", text):
                return text
            raise ValueError(
                f"Unknown colour {value!r}: use {', '.join(COLOURS)} or a #rrggbb code"
            )

        def button_value(value):
            text = str(value).strip().upper()
            if text not in BUTTONS:
                raise ValueError("button must be A, B, X or Y")
            return text

        def move(kind, label):
            @robot_command(label)
            def run(seconds=1, power=60):
                self._drive_for(_MOVES[kind](power_value(power)), seconds_value(seconds))
            return run

        @robot_command("Drive")
        def drive(direction, seconds=1, power=60):
            if direction not in _DIRECTION_MOVES:
                raise ValueError("direction must be forward, backward, left or right")
            speeds = _MOVES[_DIRECTION_MOVES[direction]](power_value(power))
            self._drive_for(speeds, seconds_value(seconds))

        @robot_command("Wait")
        def wait(seconds=1):
            self._wait(seconds_value(seconds))

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
                colour_value(colour),
                _clamp(_finite(tolerance, "tolerance"), 1, 90),
                max(1.0, _finite(min_area, "min_area")),
            )

        @robot_command("Distance check")
        def distance():
            reading = self._distance_cm()
            return math.nan if reading is None else reading

        @robot_command("Button check")
        def button_pressed(button):
            name = button_value(button)
            self._wait(0.02)
            return self._button_pressed(name)

        @robot_command("Wait until")
        def wait_until(condition):
            while not (condition() if callable(condition) else condition):
                self._check_stopped()
                self._wait(0.05)

        @robot_command("Set lights")
        def set_lights(colour):
            self.session.call("set_underlights", _hex_colour(colour_value(colour)))

        @robot_command("Turn off underlights")
        def lights_off():
            self.session.call("set_underlights", (0, 0, 0))

        @robot_command("Flash lights")
        def flash_lights(colour, times=3, on_seconds=0.2, off_seconds=0.2):
            self._flash(
                colour_value(colour),
                max(0, int(_finite(times, "times"))),
                seconds_value(on_seconds),
                seconds_value(off_seconds),
            )

        @robot_command("Button light")
        def set_button_light(button, brightness=1):
            self.session.call(
                "set_button_led", button_value(button),
                _clamp(_finite(brightness, "brightness"), 0, 1),
            )

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
            text = (" " if sep is None else str(sep)).join(str(value) for value in values)
            with self.lock:
                self.output.extend(text.split("\n"))

        def student_input(*_args):
            raise RuntimeError("input() is not available here")

        return {
            "__name__": "__main__",
            # These are deliberately the real libraries. Students can copy the
            # same cv2/NumPy calls into a normal Python script later.
            "cv2": cv2,
            "np": np,
            "numpy": np,
            "forward": move("forward", "Move forward"),
            "backward": move("backward", "Move backward"),
            "turn_left": move("turn_left", "Turn left"),
            "turn_right": move("turn_right", "Turn right"),
            "turn_around": move("turn_around", "Turn around"),
            "drive": drive, "wait": wait, "stop": stop, "take_picture": take_picture,
            "show_in_live_camera": show_in_live_camera,
            "scan_robot_qr": scan_robot_qr,
            "sees_colour": sees_colour, "distance": distance,
            "button_pressed": button_pressed, "wait_until": wait_until,
            "set_lights": set_lights, "lights_off": lights_off,
            "flash_lights": flash_lights, "set_button_light": set_button_light,
            "count": count, "print": student_print, "input": student_input,
        }

    def _check_stopped(self):
        if self.stop_event.is_set():
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
        decoded = []
        try:
            value, _, _ = detector.detectAndDecode(frame)
            if value:
                decoded.append(value)
        except cv2.error:
            pass
        try:
            found, values, _, _ = detector.detectAndDecodeMulti(frame)
            if found:
                decoded.extend(value for value in values if value)
        except (AttributeError, cv2.error):
            pass

        robot_name = ""
        for value in decoded:
            match = ROBOT_QR_PATTERN.fullmatch(value.strip())
            if match:
                robot_name = match.group(1).lower()
                break
        self.vision = {
            "status": f"Robot QR found: {robot_name}" if robot_name else "Robot QR not found",
            "colour": "",
            "matched": bool(robot_name),
            "area": 0,
            "qr": robot_name,
        }
        self.camera_view = f"QR scan: {robot_name}" if robot_name else "QR scan: no robot code"
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

    def _variables(self, program):
        result = {}
        raw = program.get("variables", {})
        if isinstance(raw, dict):
            for item in raw.get("variables", []):
                if isinstance(item, dict) and item.get("id"):
                    variable_id = item["id"]
                    variable_name = item.get("name", variable_id)
                    result[variable_id] = None
                    result[variable_name] = None
        return result

    def _run_chain(self, block, variables):
        while block and not self.stop_event.is_set():
            block_type = block.get("type")
            self._set_status(current=self._friendly_block_name(block_type))

            if block_type in {
                "robot_forward",
                "robot_backward",
                "robot_turn_left",
                "robot_turn_right",
                "robot_drive_for",
            }:
                self._run_movement(block, block_type, variables)
            elif block_type == "robot_turn_around":
                seconds = self._value(block, "SECONDS", variables, 1)
                speed = _clamp(self._value(block, "SPEED", variables, 60), 0, 100)
                self._drive_for((speed, -speed), seconds)
            elif block_type == "robot_take_picture":
                self._take_picture()
            elif block_type == "robot_show_live_camera":
                image = self._any_value(block, "IMAGE", variables)
                self._show_in_live_camera(self._take_picture() if image is None else image)
            elif block_type == "robot_if_color":
                colour = self._colour_value(block, "COLOR", variables, "#ff0000")
                tolerance = _clamp(
                    self._value(block, "TOLERANCE", variables, 18), 1, 90
                )
                min_area = max(
                    1, self._value(block, "MIN_AREA", variables, 500)
                )
                matched = self._check_colour(colour, tolerance, min_area)
                nested = self._statement(block, "THEN" if matched else "ELSE")
                if nested:
                    self._run_chain(nested, variables)
            elif block_type == "robot_if_distance":
                distance = self._distance_cm()
                limit = self._value(block, "CENTIMETRES", variables, 20)
                operator = block.get("fields", {}).get("OPERATOR", "LESS_THAN")
                matched = (
                    distance is not None
                    and (
                        distance < limit
                        if operator == "LESS_THAN"
                        else distance > limit
                    )
                )
                nested = self._statement(block, "THEN" if matched else "ELSE")
                if nested:
                    self._run_chain(nested, variables)
            elif block_type == "robot_underlights_on":
                self.session.call("set_underlights", (255, 255, 255))
            elif block_type == "robot_underlights_off":
                self.session.call("set_underlights", (0, 0, 0))
            elif block_type in {
                "robot_lights_red",
                "robot_lights_green",
                "robot_lights_blue",
                "robot_lights_yellow",
                "robot_lights_white",
                "robot_lights_purple",
            }:
                named_lights = {
                    "robot_lights_red": (255, 0, 0),
                    "robot_lights_green": (0, 255, 0),
                    "robot_lights_blue": (0, 0, 255),
                    "robot_lights_yellow": (255, 255, 0),
                    "robot_lights_white": (255, 255, 255),
                    "robot_lights_purple": (255, 0, 255),
                }
                self.session.call("set_underlights", named_lights[block_type])
            elif block_type == "robot_set_lights":
                self.session.call(
                    "set_underlights",
                    _hex_colour(
                        self._colour_value(block, "COLOR", variables, "#00ff00"),
                        "#00ff00",
                    ),
                )
            elif block_type == "robot_flash_lights":
                colour = self._colour_value(block, "COLOR", variables, "#00ff00")
                times = max(0, int(self._value(block, "TIMES", variables, 3)))
                on_seconds = max(
                    0, self._value(block, "ON_SECONDS", variables, 0.2)
                )
                off_seconds = max(
                    0, self._value(block, "OFF_SECONDS", variables, 0.2)
                )
                self._flash(colour, times, on_seconds, off_seconds)
            elif block_type == "robot_button_light":
                button = block.get("fields", {}).get("BUTTON", "A")
                brightness = _clamp(
                    self._value(block, "BRIGHTNESS", variables, 1), 0, 1
                )
                self.session.call("set_button_led", button, brightness)
            elif block_type in {"robot_repeat", "controls_repeat_ext"}:
                times = max(0, int(self._value(block, "TIMES", variables, 2)))
                nested = self._statement(block, "DO")
                for _ in range(times):
                    if self.stop_event.is_set() or not nested:
                        break
                    self._run_chain(nested, variables)
            elif block_type == "controls_whileUntil":
                until = block.get("fields", {}).get("MODE") == "UNTIL"
                nested = self._statement(block, "DO")
                while (
                    not self.stop_event.is_set()
                    and self._condition(block, "BOOL", variables) != until
                ):
                    if nested:
                        self._run_chain(nested, variables)
                    self._wait(0.02)
            elif block_type == "controls_for":
                key = self._variable_key(block.get("fields", {}).get("VAR"))
                start = self._value(block, "FROM", variables, 1)
                end = self._value(block, "TO", variables, 10)
                step = abs(self._value(block, "BY", variables, 1))
                if step == 0:
                    raise ValueError("The 'by' step of a count loop cannot be 0")
                step = step if start <= end else -step
                nested = self._statement(block, "DO")
                value = start
                while (
                    not self.stop_event.is_set()
                    and (value <= end if step > 0 else value >= end)
                ):
                    variables[key] = value
                    if nested:
                        self._run_chain(nested, variables)
                    value += step
            elif block_type == "controls_if":
                inputs = block.get("inputs", {})
                index = 0
                matched = False
                while f"IF{index}" in inputs and not self.stop_event.is_set():
                    if self._condition(block, f"IF{index}", variables):
                        matched = True
                        nested = self._statement(block, f"DO{index}")
                        if nested:
                            self._run_chain(nested, variables)
                        break
                    index += 1
                if not matched:
                    nested = self._statement(block, "ELSE")
                    if nested:
                        self._run_chain(nested, variables)
            elif block_type == "robot_wait_until":
                while (
                    not self.stop_event.is_set()
                    and not self._condition(block, "CONDITION", variables)
                ):
                    self._wait(0.05)
            elif block_type == "robot_wait":
                self._wait(self._value(block, "SECONDS", variables, 1))
            elif block_type == "robot_stop":
                self.session.call("stop")
            elif block_type == "robot_print":
                values = [self._any_value(block, "VALUE", variables)]
                second = self._input_block(block, "VALUE2")
                if second is not None:
                    values.append(self._evaluate(second, variables))
                with self.lock:
                    self.output.append(" ".join(str(value) for value in values))
            elif block_type == "variables_set":
                variables[self._variable_key(block.get("fields", {}).get("VAR"))] = (
                    self._any_value(block, "VALUE", variables)
                )
            elif block_type == "math_change":
                key = self._variable_key(block.get("fields", {}).get("VAR"))
                variables[key] = _number(variables.get(key)) + self._value(
                    block, "DELTA", variables, 1
                )

            # Blockly serialises the following block as {"next": {"block": {...}}}.
            following = block.get("next")
            block = following.get("block") if isinstance(following, dict) else None

    def _run_movement(self, block, block_type, variables):
        seconds = self._value(block, "SECONDS", variables, 1)
        speed = _clamp(self._value(block, "SPEED", variables, 60), 0, 100)
        if block_type == "robot_forward":
            speeds = (speed, speed)
        elif block_type == "robot_backward":
            speeds = (-speed, -speed)
        elif block_type == "robot_turn_left":
            speeds = (-speed, speed)
        elif block_type == "robot_turn_right":
            speeds = (speed, -speed)
        else:
            direction = block.get("fields", {}).get("DIRECTION", "FORWARD")
            speeds = {
                "FORWARD": (speed, speed),
                "BACKWARD": (-speed, -speed),
                "LEFT": (-speed, speed),
                "RIGHT": (speed, -speed),
            }.get(direction, (0, 0))
        self._drive_for(speeds, seconds)

    @staticmethod
    def _friendly_block_name(block_type):
        return {
            "robot_forward": "Move forward",
            "robot_backward": "Move backward",
            "robot_turn_left": "Turn left",
            "robot_turn_right": "Turn right",
            "robot_turn_around": "Turn around",
            "robot_take_picture": "Take a picture",
            "opencv_camera_image": "Take an OpenCV image",
            "opencv_to_hsv": "Convert image to HSV",
            "opencv_blur": "Blur image",
            "opencv_box_blur": "Box blur image",
            "opencv_hsv_value": "HSV bound",
            "opencv_hsv_mask": "Make HSV mask",
            "opencv_count_nonzero": "Count mask pixels",
            "opencv_mask_or": "Combine masks",
            "robot_show_live_camera": "Show OpenCV image",
            "robot_scan_qr": "Scan robot QR code",
            "robot_distance_value": "Read distance",
            "robot_if_color": "OpenCV colour check",
            "robot_if_distance": "Distance check",
            "robot_underlights_on": "Turn on underlights",
            "robot_underlights_off": "Turn off underlights",
            "robot_lights_red": "Set lights red",
            "robot_lights_green": "Set lights green",
            "robot_lights_blue": "Set lights blue",
            "robot_lights_yellow": "Set lights yellow",
            "robot_lights_white": "Set lights white",
            "robot_lights_purple": "Set lights purple",
            "robot_repeat": "Repeat",
            "controls_repeat_ext": "Repeat",
            "controls_whileUntil": "Repeat while",
            "controls_for": "Count loop",
            "controls_if": "If",
            "robot_wait_until": "Wait until",
            "robot_set_lights": "Set lights",
            "robot_flash_lights": "Flash lights",
            "robot_button_light": "Button light",
            "robot_wait": "Wait",
            "robot_stop": "Stop",
        }.get(block_type, block_type or "Block")

    def _statement(self, block, name):
        value = block.get("inputs", {}).get(name, {})
        if not isinstance(value, dict):
            return None
        return value.get("block") or value.get("shadow")

    def _input_block(self, block, name):
        value = block.get("inputs", {}).get(name, {})
        if not isinstance(value, dict):
            return None
        return value.get("block") or value.get("shadow")

    def _any_value(self, block, name, variables):
        return self._evaluate(self._input_block(block, name), variables)

    @staticmethod
    def _variable_key(field):
        # Blockly saves variable fields as {"id": ...}.
        if isinstance(field, dict):
            return str(field.get("id") or field.get("name") or "variable")
        return str(field or "variable")

    def _condition(self, block, name, variables):
        if self._input_block(block, name) is None:
            raise ValueError("A block is missing its condition")
        return bool(self._any_value(block, name, variables))

    def _button_pressed(self, button):
        buttons = self.session.telemetry_snapshot().get("buttons")
        return bool(isinstance(buttons, dict) and buttons.get(button))

    def _evaluate(self, child, variables):
        if not child:
            return None
        child_type = child.get("type")
        fields = child.get("fields", {})
        if child_type == "math_number":
            return _number(fields.get("NUM"))
        if child_type == "colour_picker":
            return fields.get("COLOUR", "#ff0000")
        if child_type == "text":
            return str(fields.get("TEXT", ""))
        if child_type == "variables_get":
            return variables.get(self._variable_key(fields.get("VAR")))
        if child_type == "opencv_camera_image":
            return self._take_picture()
        if child_type == "opencv_to_hsv":
            image = self._any_value(child, "IMAGE", variables)
            if image is None:
                image = self._take_picture()
            return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        if child_type == "opencv_blur":
            image = self._any_value(child, "IMAGE", variables)
            if image is None:
                image = self._take_picture()
            kernel = max(1, int(self._value(child, "KERNEL", variables, 5)))
            if kernel % 2 == 0:
                kernel += 1
            return cv2.GaussianBlur(image, (kernel, kernel), 0)
        if child_type == "opencv_box_blur":
            image = self._any_value(child, "IMAGE", variables)
            if image is None:
                image = self._take_picture()
            kernel = max(1, int(self._value(child, "KERNEL", variables, 5)))
            if kernel % 2 == 0:
                kernel += 1
            return cv2.blur(image, (kernel, kernel))
        if child_type == "opencv_hsv_value":
            return tuple(
                int(_clamp(self._value(child, name, variables, default), 0, limit))
                for name, default, limit in (
                    ("H", 40, 179), ("S", 70, 255), ("V", 70, 255),
                )
            )
        if child_type == "opencv_hsv_mask":
            image = self._any_value(child, "IMAGE", variables)
            if image is None:
                image = self._take_picture()
            low = self._any_value(child, "LOW", variables)
            high = self._any_value(child, "HIGH", variables)
            if low is None or high is None:
                low = tuple(
                    int(_clamp(self._value(child, name, variables, default), 0, limit))
                    for name, default, limit in (
                        ("LOW_H", 40, 179), ("LOW_S", 70, 255), ("LOW_V", 70, 255),
                    )
                )
                high = tuple(
                    int(_clamp(self._value(child, name, variables, default), 0, limit))
                    for name, default, limit in (
                        ("HIGH_H", 80, 179), ("HIGH_S", 255, 255), ("HIGH_V", 255, 255),
                    )
                )
            return cv2.inRange(image, low, high)
        if child_type == "opencv_count_nonzero":
            image = self._any_value(child, "IMAGE", variables)
            if image is None:
                return 0
            return int(cv2.countNonZero(image))
        if child_type == "opencv_mask_or":
            left = self._any_value(child, "IMAGE1", variables)
            right = self._any_value(child, "IMAGE2", variables)
            return cv2.bitwise_or(left, right)
        if child_type == "robot_scan_qr":
            return self._scan_robot_qr()
        if child_type == "math_arithmetic":
            left = _number(self._any_value(child, "A", variables))
            right = _number(self._any_value(child, "B", variables))
            operator = fields.get("OP", "ADD")
            if operator == "ADD":
                return left + right
            if operator == "MINUS":
                return left - right
            if operator == "MULTIPLY":
                return left * right
            if operator == "DIVIDE":
                return left / right if right else 0.0
            if operator == "POWER":
                try:
                    return _number(left ** right)
                except (OverflowError, ZeroDivisionError):
                    return 0.0
            return 0.0
        if child_type == "logic_boolean":
            return fields.get("BOOL") == "TRUE"
        if child_type == "logic_compare":
            left = _number(self._any_value(child, "A", variables))
            right = _number(self._any_value(child, "B", variables))
            return {
                "EQ": left == right, "NEQ": left != right, "LT": left < right,
                "LTE": left <= right, "GT": left > right, "GTE": left >= right,
            }.get(fields.get("OP", "EQ"), False)
        if child_type == "logic_negate":
            return not self._any_value(child, "BOOL", variables)
        if child_type == "logic_operation":
            left = bool(self._any_value(child, "A", variables))
            if fields.get("OP") == "OR":
                return left or bool(self._any_value(child, "B", variables))
            return left and bool(self._any_value(child, "B", variables))
        if child_type == "robot_button_pressed":
            return self._button_pressed(fields.get("BUTTON", "A"))
        if child_type == "robot_distance_condition":
            distance = self._distance_cm()
            limit = self._value(child, "CENTIMETRES", variables, 20)
            if distance is None:
                return False
            if fields.get("OPERATOR", "LESS_THAN") == "LESS_THAN":
                return distance < limit
            return distance > limit
        if child_type == "robot_distance_value":
            return self._distance_cm()
        named_colours = {
            "robot_colour_red": "#ff0000",
            "robot_colour_green": "#00ff00",
            "robot_colour_blue": "#0000ff",
            "robot_colour_yellow": "#ffff00",
            "robot_colour_white": "#ffffff",
            "robot_colour_purple": "#ff00ff",
        }
        if child_type in named_colours:
            return named_colours[child_type]
        return None

    def _value(self, block, name, variables, default):
        value = self._any_value(block, name, variables)
        return _number(default if value is None else value, default)

    def _colour_value(self, block, name, variables, default):
        field_value = block.get("fields", {}).get(name)
        if isinstance(field_value, str) and field_value:
            return field_value
        value = self._any_value(block, name, variables)
        return value if isinstance(value, str) else default

    def _wait(self, seconds):
        end = time.monotonic() + max(0, seconds)
        while time.monotonic() < end and not self.stop_event.is_set():
            time.sleep(max(0.0, min(0.03, end - time.monotonic())))

    def _drive_for(self, speeds, seconds):
        # The robot sender stops the motors after 0.6 seconds without a
        # drive packet. Keep refreshing the command while this block runs.
        left = speeds[0] / 100.0
        right = speeds[1] / 100.0
        deadline = time.monotonic() + max(0.0, seconds)
        try:
            while not self.stop_event.is_set() and time.monotonic() < deadline:
                self.session.dispatch("drive", left, right)
                remaining = deadline - time.monotonic()
                self._wait(min(0.18, max(0.0, remaining)))
        finally:
            try:
                self.session.dispatch("stop")
            except Exception:
                pass

    def _distance_cm(self):
        try:
            self.session.dispatch("request_distance")
        except Exception:
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
            if self.stop_event.is_set():
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
                hsv, (0, low_s, low_v),
                (target_hue + hue_width, high_s, high_v),
            )
            mask |= cv2.inRange(
                hsv, (179 + target_hue - hue_width, low_s, low_v),
                (179, high_s, high_v),
            )
        elif target_hue + hue_width > 179:
            mask = cv2.inRange(
                hsv, (target_hue - hue_width, low_s, low_v),
                (179, high_s, high_v),
            )
            mask |= cv2.inRange(
                hsv, (0, low_s, low_v),
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
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        area = max(
            (cv2.contourArea(contour) for contour in contours),
            default=0.0,
        )
        return area >= min_area, area


session = RobotSession()
runner = ProgramRunner(session)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/connect")
def connect():
    try:
        payload = request.get_json(silent=True) or {}
        session.connect(payload.get("url"), payload.get("video"))
        return jsonify(session.status())
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/disconnect")
def disconnect():
    runner.stop()
    session.disconnect()
    return jsonify(session.status())


@app.get("/api/status")
def status():
    return jsonify({**session.status(), "program": runner.status()})


def _library_files(name):
    """Return the safe (blocks .json, python .py) paths inside the demo library."""
    name = str(name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,63}", name):
        raise ValueError("Demo name may use letters, numbers, spaces, hyphens, and underscores")
    return LIBRARY_DIR / f"{name}.json", LIBRARY_DIR / f"{name}.py"


def _validate_demo(path, kind):
    """Check that a library demo can be represented and run as blocks."""
    import json

    try:
        if kind == "python":
            program, _ = python_to_blocks(path.read_text(encoding="utf-8"))
        else:
            program = json.loads(path.read_text(encoding="utf-8"))
            generated = blocks_to_python(program)
            if "unsupported block:" in generated:
                raise ValueError("the workspace contains an unsupported block")
            python_to_blocks(generated)
        return {"block_compatible": True, "block_error": ""}
    except (OSError, ValueError, json.JSONDecodeError, Unsupported) as error:
        return {
            "block_compatible": False,
            "block_error": getattr(error, "message", None) or str(error),
            "block_line": getattr(error, "line", None),
        }


@app.get("/api/library")
def list_library():
    demos = []
    for pattern, kind in (("*.json", "blocks"), ("*.py", "python")):
        for path in LIBRARY_DIR.glob(pattern):
            demos.append({"name": path.stem, "kind": kind, **_validate_demo(path, kind)})
    demos.sort(key=lambda item: item["name"].lower())
    return jsonify({"demos": demos})


@app.get("/api/library/<name>")
def load_library(name):
    import json

    try:
        blocks_path, python_path = _library_files(name)
        if blocks_path.is_file():
            return jsonify(json.loads(blocks_path.read_text(encoding="utf-8")))
        if python_path.is_file():
            return jsonify({"python": python_path.read_text(encoding="utf-8")})
        return jsonify({"error": "Demo not found"}), 404
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/library/<name>")
def save_library(name):
    import json

    try:
        blocks_path, python_path = _library_files(name)
        program = request.get_json(silent=True)
        if isinstance(program, dict) and isinstance(program.get("python"), str):
            code = program["python"]
            if len(code) > MAX_PYTHON_CHARS:
                raise ValueError("That Python program is too long")
            path, other = python_path, blocks_path
            text = code if code.endswith("\n") else code + "\n"
        elif isinstance(program, dict) and isinstance(program.get("blocks"), dict):
            path, other = blocks_path, python_path
            text = json.dumps(program, indent=2) + "\n"
        else:
            raise ValueError("The saved Blockly program is not valid JSON")
        if other.exists():
            raise ValueError("A demo with that name already exists as a different kind; pick another name")
        path.write_text(text, encoding="utf-8")
        return jsonify({"name": path.stem, "saved": True})
    except (OSError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/video/config")
def video_config():
    try:
        return jsonify({"video": session.configure_video(request.get_json(silent=True))})
    except Exception as error:
        return jsonify({"error": str(error)}), 409


@app.get("/api/video.mjpg")
def video():
    def stream():
        sequence = -1
        while True:
            jpeg, sequence = session.wait_jpeg(sequence, timeout=1.0)
            if jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n"
                    b"Content-Length: "
                    + str(len(jpeg)).encode()
                    + b"\r\n\r\n"
                    + jpeg
                    + b"\r\n"
                )

    return Response(
        stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/teleop")
def teleop():
    payload = request.get_json(silent=True) or {}
    try:
        if payload.get("stop"):
            session.dispatch("stop")
        else:
            left = _clamp(_number(payload.get("left")), -100, 100) / 100.0
            right = _clamp(_number(payload.get("right")), -100, 100) / 100.0
            session.dispatch("drive", left, right)
        return jsonify({"ok": True, "queued": True}), 202
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 409


@app.post("/api/lights/reset")
def reset_lights():
    try:
        session.reset_lights()
        return jsonify({"ok": True}), 202
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 409


def _require_local_request():
    """Refuse code-running requests that did not come from this machine's own page."""
    host = request.host.rsplit(":", 1)[0].strip("[]")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        abort(403)
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.host:
        abort(403)


@app.post("/api/python/generate")
def python_from_blocks():
    try:
        program = (request.get_json(silent=True) or {}).get("program")
        return jsonify({"code": blocks_to_python(program)})
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/python/to_blocks")
def python_to_blocks_route():
    code = (request.get_json(silent=True) or {}).get("code")
    if not isinstance(code, str) or len(code) > MAX_PYTHON_CHARS:
        return jsonify({"error": "The Python code is missing or too long"}), 400
    try:
        program, normalised = python_to_blocks(code)
        return jsonify({"ok": True, "program": program, "code": normalised})
    except Unsupported as error:
        return jsonify({
            "ok": False, "syntax": error.syntax, "line": error.line, "message": error.message,
        })


@app.post("/api/python/format")
def format_python():
    code = (request.get_json(silent=True) or {}).get("code")
    if not isinstance(code, str) or len(code) > MAX_PYTHON_CHARS:
        return jsonify({"error": "The Python code is missing or too long"}), 400
    try:
        import black

        formatted = black.format_str(code, mode=black.Mode(line_length=88))
        return jsonify({"code": formatted})
    except SyntaxError as error:
        return jsonify({"error": f"Line {getattr(error, 'lineno', '?')}: {error}"}), 400
    except Exception as error:
        # black raises InvalidInput for incomplete code; keep the editor intact.
        return jsonify({"error": str(error)}), 400


@app.post("/api/program/start")
def start_program():
    payload = request.get_json(silent=True) or {}
    if "python" in payload:
        _require_local_request()
    try:
        if "python" in payload:
            runner.start_python(payload["python"])
        else:
            runner.start(payload.get("program"))
        return jsonify(runner.status())
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/program/stop")
def stop_program():
    runner.stop()
    return jsonify(runner.status())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="127.0.0.1", port=6767, threaded=True)
