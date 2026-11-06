#!/usr/bin/env python3
"""Beginner-friendly Blockly control server for a Trilobot."""

from __future__ import annotations

import asyncio
import colorsys
import ctypes
from datetime import datetime, timezone
import functools
import ipaddress
import json
import logging
import math
import os
import re
import sys
import threading
import time
import traceback
import urllib.request
from collections import deque
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, render_template, request
from websockets.exceptions import ConnectionClosed, InvalidHandshake

CONTROL_SCRIPTS = Path(__file__).resolve().parents[1]
if str(CONTROL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CONTROL_SCRIPTS))
BLOCKLY_DIR = Path(__file__).resolve().parent
if str(BLOCKLY_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCKLY_DIR))

from blocks_python import (  # noqa: E402
    BUTTONS,
    COLOURS,
    Unsupported,
    blocks_to_python,
    python_to_blocks,
)
from client import (  # noqa: E402
    CLOSE_BUSY,
    CLOSE_REPLACED,
    CLOSE_TAKEN_OVER,
    RobotClient,
)

LOG = logging.getLogger("trilobot_blockly")
app = Flask(__name__)
LIBRARY_DIR = Path(__file__).resolve().parent / "demos"
LIBRARY_DIR.mkdir(exist_ok=True)
# User-saved demos live in their own folder so a Docker volume can persist them.
USER_LIBRARY_DIR = Path(
    os.environ.get("TRILOBOT_USER_DEMOS_DIR") or LIBRARY_DIR / "saved"
)
USER_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

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
ROBOT_DIRECTORY_URL = "https://findmyrobot.services.lcas.group/api/robots?filter=trilo"
ROBOT_DIRECTORY_TIMEOUT = 6
ROBOT_PING_GREEN_SECONDS = 10 * 60
ROBOT_PING_ORANGE_SECONDS = 30 * 60
STREAM_JPEG_QUALITY = 72
HEALTH_WINDOW_SECONDS = 3.0
MAX_PYTHON_CHARS = 50_000
# Connection supervision (see RobotSession).
CONNECTION_BACKOFF = (1, 2, 4, 8, 10)
OFFLINE_AFTER_SECONDS = 120
SLOW_RETRY_SECONDS = 10
TELEMETRY_TIMEOUT_SECONDS = 2.0
HELLO_TIMEOUT_SECONDS = 5.0
OPEN_TIMEOUT_SECONDS = 5.0
WEAK_EVENT_INTERVAL = 30.0
ACTIVE_STATES = ("connected", "weak")
EVENT_LIMIT = 50
COMMAND_QUEUE_LIMIT = 32
# The robot watchdog stops after 0.6s, so an older drive is not worth sending.
STALE_DRIVE_SECONDS = 0.5
PRIORITY_COMMANDS = frozenset({"stop"})
COALESCED_COMMANDS = frozenset({"drive"})
DEFAULT_PROGRAM_MAX_SECONDS = 900
# Student code stuck in pure Python is interrupted this long after a stop.
FORCE_STOP_SECONDS = 1.5
STOP_REASONS = {
    "wifi": "the robot's Wi-Fi connection dropped",
    "taken_over": "someone else took control of the robot",
    "busy": "the robot is being used by someone else",
    "user": "you disconnected from the robot",
    "refused": "the robot stopped accepting connections",
    "timeout": "the robot could not be reached",
}
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
    "forward": "forward",
    "backward": "backward",
    "left": "turn_left",
    "right": "turn_right",
}


class _Stopped(BaseException):
    """Raised inside student Python when Stop is pressed."""


def _finite(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
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
    return tuple(int(text[index : index + 2], 16) for index in (1, 3, 5))


def _video_config(payload, fallback=None):
    fallback = dict(fallback or DEFAULT_VIDEO_CONFIG)
    payload = payload if isinstance(payload, dict) else {}
    requested_size = (
        int(_number(payload.get("width"), fallback["width"])),
        int(_number(payload.get("height"), fallback["height"])),
    )
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
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
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


def _with_query(url, *, force=False, resume=None):
    """Return url with the robot's force/resume query parameters set."""
    parts = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in ("force", "resume")
    ]
    if force:
        query.append(("force", "1"))
    if resume:
        query.append(("resume", resume))
    return urlunparse(parts._replace(query=urlencode(query)))


def _minutes_text(seconds):
    minutes = seconds / 60
    if float(minutes).is_integer():
        return str(int(minutes))
    return f"{minutes:.1f}"


class RobotSession:
    """Own one asyncio RobotClient loop while Flask serves HTTP requests.

    A daemon thread runs a supervisor coroutine that connects, watches the link
    and reconnects after Wi-Fi drops. Flask threads read state under self.lock.
    """

    def __init__(
        self,
        *,
        backoff=CONNECTION_BACKOFF,
        offline_after=OFFLINE_AFTER_SECONDS,
        slow_retry=SLOW_RETRY_SECONDS,
        telemetry_timeout=TELEMETRY_TIMEOUT_SECONDS,
        hello_timeout=HELLO_TIMEOUT_SECONDS,
        open_timeout=OPEN_TIMEOUT_SECONDS,
    ):
        self.backoff = tuple(backoff)
        self.offline_after = offline_after
        self.slow_retry = slow_retry
        self.telemetry_timeout = telemetry_timeout
        self.hello_timeout = hello_timeout
        self.open_timeout = open_timeout
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
        self.last_command_ms = None
        self.command_times = deque(maxlen=30)
        self.video_config = dict(DEFAULT_VIDEO_CONFIG)
        self.session_name = ""
        self.busy_session = ""
        self.kicked = False
        # Set by ProgramRunner: did the last disconnect stop a running program?
        self.program_stopped = False
        # Connection state machine (see /api/status "connection").
        self.generation = 0
        self.state = "idle"
        self.reason = None
        self.state_since = time.time()
        self.attempt = 0
        self.holder = None
        self.holder_since = None
        self.robot_name = None
        self.resume_token = None
        self.connected_at = 0.0
        self._weak_since = None
        self._weak_event_at = 0.0
        self._main_task = None
        self._listeners = []
        self.events = deque(maxlen=EVENT_LIMIT)
        self._event_id = 0
        # Outgoing commands: stop jumps the queue, drive keeps only the latest.
        self._priority = deque(maxlen=COMMAND_QUEUE_LIMIT)
        self._pending_drive = None
        self._commands = deque(maxlen=COMMAND_QUEUE_LIMIT)
        self._command_wake = None

    # -- state and events -------------------------------------------------

    def add_state_listener(self, listener):
        """Call listener(old_state, new_state, reason) on every state change."""
        with self.lock:
            self._listeners.append(listener)

    def _event(self, level, text):
        getattr(LOG, level if level != "error" else "error")("%s", text)
        with self.lock:
            self._event_id += 1
            self.events.append(
                {"id": self._event_id, "t": time.time(), "level": level, "text": text}
            )

    def _alive(self, generation):
        with self.lock:
            return generation == self.generation and not self.stop_event.is_set()

    def _set_state(self, generation, state, reason=None, **fields):
        """Move to a new state. Returns False if this connection is stale."""
        with self.lock:
            if generation is not None and generation != self.generation:
                return False
            old = self.state
            if state != old or reason != self.reason:
                self.state_since = time.time()
            self.state = state
            self.reason = reason
            for name, value in fields.items():
                setattr(self, name, value)
            if state not in ACTIVE_STATES:
                self._weak_since = None
            listeners = list(self._listeners)
        if old != state:
            LOG.info("Connection state %s -> %s (%s)", old, state, reason)
            for listener in listeners:
                try:
                    listener(old, state, reason)
                except Exception:
                    LOG.exception("Connection state listener failed")
        with self.frame_condition:
            self.frame_condition.notify_all()
        return True

    def _robot_label(self, capital=False):
        if self.robot_name:
            return self.robot_name
        return "The robot" if capital else "the robot"

    def _connection_message(self, state, reason, wall):
        robot = self._robot_label()
        Robot = self._robot_label(capital=True)
        retry = f"Still trying every {self.slow_retry:g} seconds."
        if state == "idle":
            if reason == "user":
                return "You disconnected from the robot."
            return "Not connected. Choose a robot and press Connect."
        if state == "connecting":
            return f"Connecting to {robot}…"
        if state == "connected":
            if self.session_name:
                return f"Connected to {robot} as {self.session_name}."
            return f"Connected to {robot}."
        if state == "weak":
            return (
                f"Connected to {robot}, but the Wi-Fi signal is weak, "
                "so it may respond slowly."
            )
        if state == "reconnecting":
            return (
                f"Lost contact with {robot} over Wi-Fi. Reconnecting "
                f"(attempt {self.attempt})…"
            )
        if state == "taken_over":
            who = self.holder or "Someone else"
            return f"{who} took control of {robot}. Press Connect if you need it back."
        if state == "busy":
            who = self.holder or "someone else"
            since = ""
            if isinstance(self.holder_since, (int, float)):
                minutes = int((wall - self.holder_since) // 60)
                if minutes >= 1:
                    since = f" for {minutes} minute{'s' if minutes != 1 else ''}"
            return (
                f"{Robot} is being used by {who}{since}. Ask them before taking over."
            )
        if state == "robot_offline":
            if reason == "refused":
                return (
                    f"{Robot} is not accepting connections. Check it is switched "
                    f"on and its robot program is running. {retry}"
                )
            if reason == "timeout":
                return (
                    f"Could not reach {robot}. Check it is switched on and on "
                    f"the same Wi-Fi as this computer. {retry}"
                )
            return (
                f"Lost contact with {robot} for over "
                f"{_minutes_text(self.offline_after)} minutes. {retry}"
            )
        return ""

    # -- connect / disconnect ---------------------------------------------

    def connect(
        self, url, video_config=None, force=False, resume=None, robot_name=None
    ):
        url = str(url or "").strip()
        if not url.startswith(("ws://", "wss://")) or not urlparse(url).hostname:
            raise ValueError("Robot address must start with ws:// or wss://")
        config = _video_config(video_config, self.video_config)
        self._stop_worker()

        with self.lock:
            self.generation += 1
            generation = self.generation
            self.stop_event = threading.Event()
            self.url = url
            self.error = ""
            self.latest_frame = None
            self.latest_jpeg = _placeholder_jpeg()
            self.camera_overlay = None
            # Keep the sequence increasing so open camera streams never stall.
            self.frame_sequence += 1
            self.session_name = ""
            self.busy_session = ""
            self.kicked = False
            self.frame_times.clear()
            self.telemetry_times.clear()
            # last_frame_at is kept on purpose: "last picture Ns ago" must keep
            # counting up across disconnects and reconnect attempts.
            self.last_telemetry_at = 0.0
            self.program_stopped = False
            self.video_config = config
            self.client = None
            self.loop = None
            self.holder = None
            self.holder_since = None
            self.resume_token = str(resume).strip() if resume else None
            self.robot_name = str(robot_name).strip() if robot_name else None
            self._clear_commands()

        self._set_state(generation, "connecting", None, attempt=0)
        self._event("info", f"Connecting to {self.robot_name or url}")
        self.thread = threading.Thread(
            target=self._thread_main,
            args=(generation, url, config, bool(force)),
            daemon=True,
            name="trilobot-websocket",
        )
        self.thread.start()

    def _stop_worker(self):
        """Stop the websocket thread without changing the visible state."""
        with self.lock:
            self.generation += 1
            self.stop_event.set()
            loop = self.loop
            task = self._main_task
            thread = self.thread
        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                LOG.debug("Robot loop already closed")
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3)
            if thread.is_alive():
                LOG.warning("Robot connection thread did not stop within 3 seconds")
        with self.lock:
            self.client = None
            self._clear_commands()
        with self.frame_condition:
            self.frame_condition.notify_all()

    def disconnect(self):
        with self.lock:
            was = self.state
        self._stop_worker()
        self._set_state(
            None, "idle", "user", attempt=0, holder=None, holder_since=None, error=""
        )
        if was != "idle":
            self._event("info", "Disconnected from the robot.")

    # -- websocket thread -------------------------------------------------

    def _thread_main(self, generation, url, video_config, force):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with self.lock:
                if generation != self.generation:
                    return
                self.loop = loop
                task = loop.create_task(
                    self._supervise(generation, url, video_config, force)
                )
                self._main_task = task
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            LOG.debug("Robot connection task cancelled")
        except Exception as error:
            LOG.exception("Robot connection thread crashed")
            if self._set_state(generation, "idle", None, error=str(error)):
                self._event("error", f"The robot connection stopped: {error}")
        finally:
            with self.lock:
                if self.loop is loop:
                    self.loop = None
                    self.client = None
                    self._main_task = None
            try:
                loop.run_until_complete(loop.shutdown_default_executor())
            finally:
                loop.close()
            with self.frame_condition:
                self.frame_condition.notify_all()

    async def _supervise(self, generation, url, video_config, force):
        had_connected = False
        lost_at = None
        attempt = 0
        offline_logged = False
        use_force = force
        while self._alive(generation):
            with self.lock:
                resume = self.resume_token
            client = RobotClient(
                _with_query(url, force=use_force, resume=resume),
                on_message=functools.partial(self._on_message, generation),
                open_timeout=self.open_timeout,
            )
            # Only the first, user-requested attempt may take over.
            use_force = False
            try:
                outcome = await self._run_connection(
                    generation, client, video_config, had_connected
                )
            finally:
                with self.lock:
                    if self.client is client:
                        self.client = None
                await client.close()

            kind = outcome[0]
            if kind == "stop" or not self._alive(generation):
                return
            if kind == "busy":
                _, holder, since = outcome
                self._set_state(
                    generation,
                    "busy",
                    "busy",
                    holder=holder,
                    holder_since=since,
                    busy_session=holder,
                    error=f"Robot is in use by session {holder}",
                )
                self._event("warning", f"The robot is being used by {holder}.")
                return
            if kind == "taken_over":
                _, by = outcome
                self._set_state(
                    generation,
                    "taken_over",
                    "taken_over",
                    holder=by,
                    kicked=True,
                    error=f"{by} took over this robot",
                )
                self._event("warning", f"{by} took control of the robot.")
                return
            if kind == "superseded":
                # Another connection of ours resumed this session. While this
                # one is still current, treat it like a normal drop.
                LOG.info("Robot session was resumed elsewhere; reconnecting")
                kind = "lost"
            if kind == "lost":
                had_connected = True
                lost_at = time.monotonic()
                attempt = 0
                offline_logged = False
                self._event(
                    "warning", "Lost contact with the robot. Trying to reconnect…"
                )

            attempt += 1
            if lost_at is None:
                reason = outcome[1] if len(outcome) > 1 else "timeout"
                self._set_state(generation, "robot_offline", reason, attempt=attempt)
                if attempt == 1:
                    with self.lock:
                        text = self._connection_message(
                            "robot_offline", reason, time.time()
                        )
                    self._event("error", text)
                delay = self.slow_retry
            elif time.monotonic() - lost_at >= self.offline_after:
                self._set_state(generation, "robot_offline", "wifi", attempt=attempt)
                if not offline_logged:
                    offline_logged = True
                    self._event(
                        "error",
                        "The robot has not answered for "
                        f"{_minutes_text(self.offline_after)} minutes. "
                        "Still trying in the background.",
                    )
                delay = self.slow_retry
            else:
                self._set_state(generation, "reconnecting", "wifi", attempt=attempt)
                delay = self.backoff[min(attempt - 1, len(self.backoff) - 1)]
            LOG.info("Retrying robot connection in %ss (attempt %s)", delay, attempt)
            await asyncio.sleep(delay)

    async def _run_connection(self, generation, client, video_config, had_connected):
        """Run one websocket connection and say how it ended."""
        try:
            await client.open()
        except ConnectionRefusedError as error:
            LOG.info("Robot refused the connection: %s", error)
            return ("failed", "refused")
        except InvalidHandshake as error:
            LOG.warning("Robot rejected the websocket handshake: %s", error)
            return ("failed", "refused")
        except (TimeoutError, OSError) as error:
            LOG.info("Could not reach the robot: %r", error)
            return ("failed", "timeout")
        with self.lock:
            if generation != self.generation:
                return ("stop",)
            self.client = client

        waiters = [
            asyncio.create_task(client.hello_event.wait()),
            asyncio.create_task(client.closed_event.wait()),
        ]
        try:
            await asyncio.wait(
                waiters,
                timeout=self.hello_timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for waiter in waiters:
                waiter.cancel()
        if not client.hello_event.is_set():
            if not client.closed_event.is_set():
                LOG.warning("Robot did not say hello within %ss", self.hello_timeout)
            return self._closed_outcome(client, connected=False)

        now = time.monotonic()
        with self.lock:
            if generation != self.generation:
                return ("stop",)
            previous_name = self.session_name
            self.session_name = client.session_name
            if client.resume_token:
                self.resume_token = client.resume_token
            if client.robot_name and not self.robot_name:
                self.robot_name = client.robot_name
            # Give the robot a moment before telemetry counts as missing.
            self.last_telemetry_at = now
            self.connected_at = now
            self.frame_times.clear()
            self.telemetry_times.clear()
            self._clear_commands()
            wake = asyncio.Event()
            self._command_wake = wake
        self._set_state(
            generation,
            "connected",
            None,
            attempt=0,
            holder=None,
            holder_since=None,
            error="",
            busy_session="",
            kicked=False,
        )
        name = client.session_name or "a new session"
        if had_connected:
            text = f"Reconnected as {name}"
            if not client.resumed and previous_name and previous_name != name:
                text += f" (you were {previous_name} before)"
            self._event("info", text)
        else:
            self._event("info", f"Connected to {self._robot_label()} as {name}")

        tasks = []
        try:
            await client.configure_video(
                video_config["width"],
                video_config["height"],
                video_config["fps"],
                video_config["jpeg_quality"],
            )
            tasks = [
                asyncio.create_task(self._frame_pump(client)),
                asyncio.create_task(self._command_sender(client, wake)),
            ]
            watchdog = asyncio.create_task(self._telemetry_watchdog())
            closed = asyncio.create_task(client.closed_event.wait())
            tasks += [watchdog, closed]
            await asyncio.wait({watchdog, closed}, return_when=asyncio.FIRST_COMPLETED)
            if watchdog.done() and not client.closed_event.is_set():
                self._event(
                    "warning",
                    "No data from the robot for "
                    f"{self.telemetry_timeout:g} seconds (Wi-Fi problem?).",
                )
                await client.abort()
                return ("lost",)
        except ConnectionClosed as error:
            LOG.info("Robot connection closed during setup: %s", error)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            with self.lock:
                if self._command_wake is wake:
                    self._command_wake = None
        await client.closed_event.wait()
        return self._closed_outcome(client, connected=True)

    @staticmethod
    def _closed_outcome(client, connected):
        code = client.close_code
        if client.busy_holder or code == CLOSE_BUSY:
            holder = client.busy_holder or client.busy_session or "another user"
            return ("busy", holder, client.busy_since)
        if client.kicked or code == CLOSE_TAKEN_OVER:
            return ("taken_over", client.taken_over_by or "Another user")
        if code == CLOSE_REPLACED:
            return ("superseded",)
        LOG.info("Robot connection ended (code %s): %s", code, client.error)
        return ("lost",) if connected else ("failed", "timeout")

    def _on_message(self, generation, payload):
        if payload.get("type") != "telemetry":
            return
        with self.lock:
            if generation != self.generation:
                return
            now = time.monotonic()
            self.last_telemetry_at = now
            self.telemetry_times.append(now)

    async def _telemetry_watchdog(self):
        interval = max(0.02, min(0.25, self.telemetry_timeout / 4))
        while True:
            await asyncio.sleep(interval)
            with self.lock:
                age = time.monotonic() - self.last_telemetry_at
            if age > self.telemetry_timeout:
                LOG.warning("No telemetry from the robot for %.1fs", age)
                return age

    async def _frame_pump(self, client):
        # Awaits frames; the client only keeps the newest, so slow decoding
        # drops old frames instead of building up latency.
        while True:
            data = await client.next_frame_bytes()
            if data is None:
                return
            await asyncio.to_thread(self._store_jpeg_bytes, data)

    def _store_jpeg_bytes(self, data):
        frame = RobotClient.decode_frame(data)
        if frame is None:
            LOG.debug("Dropped a camera frame that could not be decoded")
            return
        self._store_frame(frame)

    # -- commands ---------------------------------------------------------

    def _clear_commands(self):
        with self.lock:
            self._priority.clear()
            self._commands.clear()
            self._pending_drive = None

    def _next_command(self):
        with self.lock:
            if self._priority:
                return self._priority.popleft()
            if self._commands:
                return self._commands.popleft()
            item, self._pending_drive = self._pending_drive, None
            return item

    async def _command_sender(self, client, wake):
        while True:
            await wake.wait()
            wake.clear()
            while (item := self._next_command()) is not None:
                method, args, queued_at = item
                age = time.monotonic() - queued_at
                if method in COALESCED_COMMANDS and age > STALE_DRIVE_SECONDS:
                    LOG.debug("Dropped a %.2fs old %s command", age, method)
                    continue
                try:
                    await getattr(client, method)(*args)
                except ConnectionClosed:
                    return
                except Exception:
                    LOG.exception("Sending %s to the robot failed", method)
                    continue
                self._record_command(time.monotonic() - queued_at)

    def _require_connection(self):
        with self.lock:
            loop = self.loop
            client = self.client
            state = self.state
        if (
            loop is None
            or client is None
            or not client.connected
            or state not in ACTIVE_STATES
        ):
            raise RuntimeError("Connect to the robot first")
        return loop, client

    def call(self, method, *args, timeout=5):
        loop, client = self._require_connection()
        started = time.monotonic()
        future = asyncio.run_coroutine_threadsafe(getattr(client, method)(*args), loop)
        try:
            result = future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise RuntimeError("The robot did not respond in time") from None
        self._record_command(time.monotonic() - started)
        return result

    def dispatch(self, method, *args):
        """Queue a command without waiting for an HTTP response or robot ACK.

        stop jumps the queue (and cancels a pending drive), drive keeps only
        the newest pending value, and other commands use a bounded FIFO.
        """
        if not callable(getattr(RobotClient, method, None)):
            raise ValueError(f"Unknown robot command {method!r}")
        loop, _client = self._require_connection()
        item = (method, args, time.monotonic())
        with self.lock:
            if method in PRIORITY_COMMANDS:
                self._pending_drive = None
                self._priority.append(item)
            elif method in COALESCED_COMMANDS:
                self._pending_drive = item
            else:
                if len(self._commands) == self._commands.maxlen:
                    LOG.warning("Robot command queue full; dropping the oldest")
                self._commands.append(item)
            wake = self._command_wake
        if wake is None:
            raise RuntimeError("Connect to the robot first")
        try:
            loop.call_soon_threadsafe(wake.set)
        except RuntimeError:
            raise RuntimeError("Connect to the robot first") from None

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

    # -- frames and status ------------------------------------------------

    def _store_frame(self, frame):
        with self.lock:
            config = dict(self.video_config)
            overlay = (
                None if self.camera_overlay is None else self.camera_overlay.copy()
            )
        display_frame = overlay if overlay is not None else frame
        if overlay is not None and overlay.shape[:2] != frame.shape[:2]:
            display_frame = cv2.resize(overlay, (frame.shape[1], frame.shape[0]))
        ok, encoded = cv2.imencode(
            ".jpg",
            display_frame,
            [cv2.IMWRITE_JPEG_QUALITY, config["jpeg_quality"]],
        )
        if not ok:
            LOG.debug("Could not encode a camera frame")
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
        wall = time.time()
        weak_event = None
        with self.lock:
            state = self.state
            connected = bool(
                state in ACTIVE_STATES and self.client and self.client.connected
            )
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

            # weak = connected but slow video or late telemetry, after a short
            # warm-up so a fresh connection is not flagged straight away.
            weak = (
                connected
                and health != "green"
                and now - self.connected_at > HEALTH_WINDOW_SECONDS
            )
            if weak and self._weak_since is None:
                self._weak_since = wall
                if wall - self._weak_event_at > WEAK_EVENT_INTERVAL:
                    self._weak_event_at = wall
                    weak_event = "The Wi-Fi signal to the robot is weak."
            elif not weak and state in ACTIVE_STATES:
                self._weak_since = None
            shown_state = "weak" if weak else state
            connection = {
                "state": shown_state,
                "reason": self.reason,
                "message": self._connection_message(shown_state, self.reason, wall),
                "since": self._weak_since if weak else self.state_since,
                "attempt": self.attempt,
                "session": self.session_name or None,
                "holder": self.holder,
                "robot": self.robot_name,
                "url": self.url or None,
                "resume": self.resume_token,
                "last_frame_age": (
                    None if frame_age is None else round(frame_age / 1000, 2)
                ),
                "telemetry_age": (
                    None if telemetry_age is None else round(telemetry_age / 1000, 2)
                ),
                "health": health,
                "health_text": health_text,
                "video_hz": round(frame_hz, 1),
                "telemetry_hz": round(telemetry_hz, 1),
                "command_hz": round(command_hz, 1),
                "last_frame_ms": frame_age,
                "last_telemetry_ms": telemetry_age,
                "last_command_ms": self.last_command_ms,
                "program_stopped": bool(self.program_stopped),
            }
            result = {
                "connected": connected,
                "url": self.url,
                "error": error,
                "session_name": self.session_name,
                "busy_session": self.busy_session,
                "kicked": self.kicked,
                "telemetry": self.telemetry_snapshot(),
                "video": config,
                "connection": connection,
            }
        if weak_event:
            self._event("warning", weak_event)
        with self.lock:
            result["events"] = list(self.events)
        return result


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
        if reason == "wifi":
            return STOP_REASONS["wifi"]
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
        # A program stopped earlier in this outage (say "Wi-Fi dropped") now
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
        except RuntimeError as error:
            LOG.debug("Could not reset the robot after a program: %s", error)

    def _python_main(self, compiled):
        me = threading.current_thread()
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
                self._drive_for(
                    _MOVES[kind](power_value(power)), seconds_value(seconds)
                )

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
                "set_button_led",
                button_value(button),
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
            text = (" " if sep is None else str(sep)).join(
                str(value) for value in values
            )
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


session = RobotSession()
runner = ProgramRunner(session)


@app.get("/")
def index():
    return render_template("index.html")


def _robot_directory_entries(payload):
    """Convert the robot directory response into safe WebSocket choices."""
    if isinstance(payload, dict):
        payload = payload.get("robots", payload.get("data", []))
    if not isinstance(payload, list):
        raise ValueError("Robot directory returned an unexpected response")

    entries = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        private_ip = item.get("privateIP") or item.get("private_ip") or item.get("ip")
        name = item.get("name") or item.get("hostname") or item.get("host")
        if not private_ip or not name:
            continue
        last_ping = item.get("lastPing") or item.get("last_ping")
        try:
            private_ip = str(ipaddress.ip_address(str(private_ip).strip()))
        except ValueError:
            continue
        ping_age = None
        if last_ping:
            try:
                ping_time = datetime.fromisoformat(
                    str(last_ping).replace("Z", "+00:00")
                )
                if ping_time.tzinfo is None:
                    ping_time = ping_time.replace(tzinfo=timezone.utc)
                ping_age = max(
                    0, (datetime.now(timezone.utc) - ping_time).total_seconds()
                )
            except ValueError:
                last_ping = None
        if ping_age is not None and ping_age <= ROBOT_PING_GREEN_SECONDS:
            ping_status = "green"
        elif ping_age is not None and ping_age <= ROBOT_PING_ORANGE_SECONDS:
            ping_status = "orange"
        else:
            ping_status = "red"
        entries.append(
            {
                "name": str(name).strip(),
                "hostname": str(item.get("hostname") or name).strip(),
                "ip": private_ip,
                "url": f"ws://{private_ip}:8765",
                "last_ping": last_ping,
                "ping_status": ping_status,
            }
        )
    return sorted(entries, key=lambda item: (item["name"].casefold(), item["ip"]))


@app.get("/api/robots")
def robot_directory():
    """Proxy the robot directory so the browser does not depend on CORS."""
    try:
        request = urllib.request.Request(
            ROBOT_DIRECTORY_URL,
            headers={"Accept": "application/json", "User-Agent": "Trilobot Blockly"},
        )
        with urllib.request.urlopen(
            request, timeout=ROBOT_DIRECTORY_TIMEOUT
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return jsonify({"robots": _robot_directory_entries(payload)})
    except (OSError, ValueError, json.JSONDecodeError) as error:
        LOG.warning("Could not load robot directory: %s", error)
        return (
            jsonify(
                {
                    "robots": [],
                    "error": "Robot list unavailable; enter an address manually.",
                }
            ),
            502,
        )


@app.post("/api/connect")
def connect():
    try:
        payload = request.get_json(silent=True) or {}
        resume = payload.get("resume")
        robot_name = payload.get("robot_name")
        session.connect(
            payload.get("url"),
            payload.get("video"),
            bool(payload.get("force")),
            resume=resume if isinstance(resume, str) else None,
            robot_name=robot_name if isinstance(robot_name, str) else None,
        )
        return jsonify(session.status())
    except Exception as error:
        LOG.info("Connect request failed: %s", error)
        return jsonify({"error": str(error)}), 400


@app.post("/api/disconnect")
def disconnect():
    # Disconnecting first lets the runner record why the program stopped.
    session.disconnect()
    runner.stop()
    return jsonify(session.status())


@app.get("/api/status")
def status():
    return jsonify({**session.status(), "program": runner.status()})


def _library_name(name):
    name = str(name or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _()-]{0,63}", name):
        raise ValueError(
            "Demo name may use letters, numbers, spaces, hyphens, underscores, and brackets"
        )
    return name


def _library_files(name, directory=None):
    """Return the safe (blocks .json, python .py) paths for a demo.

    Without a directory, the user's saved demos take priority over bundled ones.
    """
    name = _library_name(name)
    if directory is None:
        directory = USER_LIBRARY_DIR
        if (
            not (directory / f"{name}.json").is_file()
            and not (directory / f"{name}.py").is_file()
        ):
            directory = LIBRARY_DIR
    return directory / f"{name}.json", directory / f"{name}.py"


def _unique_library_name(name):
    """Never overwrite an existing demo: append (1), (2), ... when needed."""
    name = _library_name(name)
    candidate, number = name, 0
    while any(
        (directory / f"{candidate}{suffix}").exists()
        for directory in (LIBRARY_DIR, USER_LIBRARY_DIR)
        for suffix in (".json", ".py")
    ):
        number += 1
        suffix = f" ({number})"
        candidate = name[: 64 - len(suffix)].rstrip() + suffix
    return candidate


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
    seen = set()
    for directory, saved in ((USER_LIBRARY_DIR, True), (LIBRARY_DIR, False)):
        for pattern, kind in (("*.json", "blocks"), ("*.py", "python")):
            for path in directory.glob(pattern):
                if path.stem in seen:
                    continue
                seen.add(path.stem)
                demos.append(
                    {
                        "name": path.stem,
                        "kind": kind,
                        "saved": saved,
                        **_validate_demo(path, kind),
                    }
                )
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
        name = _unique_library_name(name)
        blocks_path, python_path = _library_files(name, USER_LIBRARY_DIR)
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
        path.write_text(text, encoding="utf-8")
        return jsonify({"name": path.stem, "saved": True})
    except (OSError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/video/config")
def video_config():
    try:
        return jsonify(
            {"video": session.configure_video(request.get_json(silent=True))}
        )
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
        return jsonify(
            {
                "ok": False,
                "syntax": error.syntax,
                "line": error.line,
                "message": error.message,
            }
        )


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
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8750")),
        threaded=True,
    )
