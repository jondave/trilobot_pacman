"""The robot connection: one supervised websocket per Blockly server."""

from __future__ import annotations

import asyncio
import functools
import logging
import math
import sys
import threading
import time
from collections import deque
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import cv2
import numpy as np
from websockets.exceptions import ConnectionClosed, InvalidHandshake

CONTROL_SCRIPTS = Path(__file__).resolve().parents[1]
if str(CONTROL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CONTROL_SCRIPTS))

from client import (  # noqa: E402
    CLOSE_BUSY,
    CLOSE_REPLACED,
    CLOSE_TAKEN_OVER,
    RobotClient,
)
from robot_config import (  # noqa: E402
    DEFAULT_VIDEO_CONFIG,
    VIDEO_FPS_CHOICES,
    VIDEO_SIZES,
)

LOG = logging.getLogger("trilobot_blockly")

STREAM_JPEG_QUALITY = 72
HEALTH_WINDOW_SECONDS = 3.0
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


def _number(value, default=0.0):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def _clamp(value, low, high):
    return max(low, min(high, value))


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
