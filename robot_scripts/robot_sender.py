#!/usr/bin/env python3
"""Simple configurable WebSocket server for a Trilobot.

Run this file on the Raspberry Pi. It receives JSON commands and sends
binary JPEG camera frames plus JSON telemetry to the connected control PC.

Run with --fake on a laptop to serve synthetic camera frames and telemetry
without the Trilobot or Picamera2 libraries (used by the tests). The fake
frames show a simulated robot that drives with the motor commands and takes
the colour of its underlights.
"""

import argparse
import asyncio
import json
import logging
import math
import random
import re
import secrets
import socket
import time
from contextlib import suppress
from io import BytesIO
from urllib.parse import parse_qs, urlparse
from threading import Lock

try:
    from websockets.asyncio.server import serve
except ImportError:
    from websockets.server import serve
from websockets.exceptions import ConnectionClosed

HOST = "0.0.0.0"
PORT = 8765

# Sensor modes reported by this IMX219 camera:
#   (640, 480)    4:3
#   (1640, 1232)  4:3
#   (1920, 1080) 16:9
#   (3280, 2464) 4:3
VIDEO_SIZES = (
    (640, 480),
    (1640, 1232),
    (1920, 1080),
    (3280, 2464),
)
DEFAULT_VIDEO_SIZE = (1640, 1232)
DEFAULT_VIDEO_FPS = 15.0
DEFAULT_JPEG_QUALITY = 75
MAX_VIDEO_FPS = 30.0
MOTION_EXPOSURE_US = 10000  # Short exposure reduces motion blur.
WATCHDOG_SECONDS = 0.6
PING_INTERVAL = 5
PING_TIMEOUT = 5
RESUME_GRACE = 60.0  # Seconds a dropped session's resume token stays valid.

# Session names come from the app (?name=Grapes-Escape) so a student keeps one
# name on every robot. Must match NAME_PATTERN in control_scripts/blockly/
# student_name.py. Clients that send none (or a bad one) get a LEARNER- name.
NAME_PATTERN = re.compile(r"[A-Za-z0-9]{1,64}(?:-[A-Za-z0-9]{1,64}){1,2}")
GUEST_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
GUEST_PREFIX = "LEARNER-"
CLOSE_BUSY = 4001
CLOSE_KICKED = 4002
CLOSE_REPLACED = 4003

# Filled in by setup_hardware(): button name -> Trilobot button constant.
BUTTONS = {}

tbot = None
camera = None
hardware_lock = Lock()
camera_lock = Lock()

video_size = DEFAULT_VIDEO_SIZE
video_fps = DEFAULT_VIDEO_FPS
jpeg_quality = DEFAULT_JPEG_QUALITY

last_drive_command = time.monotonic()


class FakeRobotSim:
    """A pretend robot on the fake camera's floor, shared by the fakes.

    Position is frame-normalised (x and y from 0 to 1, y downwards) and
    heading is in radians, 0 facing right and increasing anticlockwise on
    screen. Differential drive: the mean wheel speed moves the robot along
    its heading and the difference turns it. Thread-safe: commands arrive
    on the asyncio side while frames are drawn in a worker thread.
    """

    TOP_SPEED = 0.35  # Frame widths per second at full speed.
    TURN_RATE = math.pi  # Radians per second spinning on the spot.
    RADIUS = 0.06  # Fraction of the frame height.
    WIDTH_CM = 200.0  # The frame width, as far as the distance sensor knows.
    MAX_DISTANCE_CM = 400.0
    NUM_UNDERLIGHTS = 6
    OFF_COLOUR = (150, 150, 150)
    MAX_STEP = 0.02  # Seconds per integration step.

    def __init__(self, aspect=4 / 3, clock=time.monotonic):
        self._lock = Lock()
        self._clock = clock
        self._updated = clock()
        self.aspect = aspect  # Frame width / height.
        self.x = 0.5
        self.y = 0.75
        self.heading = math.pi / 2  # Facing up the frame.
        self.left = 0.0
        self.right = 0.0
        self.lights = [(0, 0, 0)] * self.NUM_UNDERLIGHTS

    def _advance(self):
        """Integrate motion up to now (call with the lock held)."""
        now = self._clock()
        elapsed = max(0.0, now - self._updated)
        self._updated = now
        if self.left == 0.0 and self.right == 0.0:
            return
        speed = (self.left + self.right) / 2 * self.TOP_SPEED
        turn = (self.right - self.left) / 2 * self.TURN_RATE
        margin_x = self.RADIUS / self.aspect
        margin_y = self.RADIUS
        while elapsed > 0:
            step = min(elapsed, self.MAX_STEP)
            elapsed -= step
            self.heading = (self.heading + turn * step) % (2 * math.pi)
            # Speed is in frame widths, so y (in heights) moves aspect times as far.
            x = self.x + speed * step * math.cos(self.heading)
            y = self.y - speed * step * math.sin(self.heading) * self.aspect
            self.x = min(max(x, margin_x), 1.0 - margin_x)
            self.y = min(max(y, margin_y), 1.0 - margin_y)

    def set_aspect(self, aspect):
        with self._lock:
            self._advance()
            self.aspect = aspect
            margin_x = self.RADIUS / aspect
            self.x = min(max(self.x, margin_x), 1.0 - margin_x)

    def set_speeds(self, left, right):
        with self._lock:
            self._advance()
            self.left = float(left)
            self.right = float(right)

    def set_light(self, index, rgb):
        with self._lock:
            self.lights[index] = tuple(int(c) for c in rgb)

    def fill_lights(self, rgb):
        with self._lock:
            self.lights = [tuple(int(c) for c in rgb)] * self.NUM_UNDERLIGHTS

    def colour(self):
        """RGB body colour: the mean of the lit underlights, else grey."""
        with self._lock:
            return self._colour()

    def _colour(self):
        lit = [light for light in self.lights if any(light)]
        if not lit:
            return self.OFF_COLOUR
        return tuple(round(sum(light[i] for light in lit) / len(lit)) for i in range(3))

    def distance_cm(self):
        """Distance from the robot's front to the frame edge it is facing."""
        with self._lock:
            self._advance()
            # Work in frame-width units so both axes share a scale.
            x, y = self.x, self.y / self.aspect
            dx, dy = math.cos(self.heading), -math.sin(self.heading)
            bottom = 1.0 / self.aspect
            hits = []
            if dx > 1e-9:
                hits.append((1.0 - x) / dx)
            elif dx < -1e-9:
                hits.append(-x / dx)
            if dy > 1e-9:
                hits.append((bottom - y) / dy)
            elif dy < -1e-9:
                hits.append(-y / dy)
            ray = min(hits) - self.RADIUS / self.aspect
        return min(self.MAX_DISTANCE_CM, max(0.0, ray * self.WIDTH_CM))

    def snapshot(self):
        with self._lock:
            self._advance()
            return {
                "x": round(self.x, 4),
                "y": round(self.y, 4),
                "heading_deg": round(math.degrees(self.heading), 1),
                "left": self.left,
                "right": self.right,
                "colour": list(self._colour()),
            }


class FakeTrilobot:
    """Stand-in for Trilobot: logs motor/LED commands and drives a FakeRobotSim."""

    def __init__(self, sim=None):
        self.sim = sim if sim is not None else FakeRobotSim()

    def stop(self):
        self.sim.set_speeds(0.0, 0.0)

    def set_motor_speeds(self, left, right):
        logging.info("[fake] motors left=%.2f right=%.2f", left, right)
        self.sim.set_speeds(left, right)

    def set_left_speed(self, speed):
        self.sim.set_speeds(speed, self.sim.right)

    def set_right_speed(self, speed):
        self.sim.set_speeds(self.sim.left, speed)

    def fill_underlighting(self, rgb, g=None, b=None, show=True):
        rgb = list(rgb) if g is None else [rgb, g, b]
        logging.info("[fake] underlights %s", rgb)
        self.sim.fill_lights(rgb)

    def set_underlight(self, light, rgb, g=None, b=None, show=True):
        rgb = list(rgb) if g is None else [rgb, g, b]
        logging.info("[fake] underlight %s %s", light, rgb)
        self.sim.set_light(light, rgb)

    def clear_underlighting(self, show=True):
        self.sim.fill_lights((0, 0, 0))

    def set_button_led(self, button, value):
        logging.info("[fake] button LED %s=%.2f", button, value)

    def read_button(self, button):
        return False

    def read_distance(self, timeout=25, samples=3):
        # How far the robot's front is from the frame edge it faces.
        return self.sim.distance_cm()


class FakeCamera:
    """Stand-in for Picamera2 that draws synthetic JPEG frames."""

    def __init__(self, sim=None):
        self.size = DEFAULT_VIDEO_SIZE
        self._frame = 0
        self.sim = sim if sim is not None else FakeRobotSim()
        self.sim.set_aspect(self.size[0] / self.size[1])

    def create_preview_configuration(self, main):
        return main

    def configure(self, config):
        self.size = tuple(config["size"])
        self.sim.set_aspect(self.size[0] / self.size[1])

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def set_controls(self, controls):
        pass

    def _robot_shape(self, width, height):
        """Pixel geometry and RGB colours for the simulated robot."""
        state = self.sim.snapshot()
        body = tuple(state["colour"])
        centre = (int(round(state["x"] * width)), int(round(state["y"] * height)))
        radius = max(6, int(round(FakeRobotSim.RADIUS * height)))
        heading = math.radians(state["heading_deg"])
        dx, dy = math.cos(heading), -math.sin(heading)
        # The heading line starts away from the centre, so the centre pixel
        # always shows the body colour.
        line = (
            (int(centre[0] + dx * radius * 0.35), int(centre[1] + dy * radius * 0.35)),
            (int(centre[0] + dx * radius * 1.5), int(centre[1] + dy * radius * 1.5)),
        )
        return {
            "centre": centre,
            "radius": radius,
            "body": body,
            "outline": tuple(c // 2 for c in body),
            "line": line,
            "thickness": max(2, radius // 6),
            "label": (centre[0] - radius, centre[1] + radius + max(12, radius // 2)),
        }

    def capture_jpeg(self, quality):
        self._frame += 1
        width, height = self.size
        label = current_session_name() or "no session"
        lines = (time.strftime("%H:%M:%S"), label, f"frame {self._frame}")
        phase = self._frame / 30.0
        background = (40, 90 + int(60 * math.sin(phase)), 140)
        marker_x = int((0.5 + 0.4 * math.sin(phase * 2)) * width)
        marker_y = height // 2
        radius = max(8, height // 12)
        robot = self._robot_shape(width, height)
        try:
            import cv2
            import numpy as np
        except ImportError:
            cv2 = None
        if cv2 is not None:

            def bgr(rgb):
                return tuple(int(c) for c in rgb[::-1])  # OpenCV is BGR.

            image = np.empty((height, width, 3), dtype=np.uint8)
            image[:] = bgr(background)
            cv2.circle(image, (marker_x, marker_y), radius, (0, 220, 255), -1)
            scale = max(0.6, height / 400)
            cv2.circle(image, robot["centre"], robot["radius"], bgr(robot["body"]), -1)
            cv2.circle(
                image,
                robot["centre"],
                robot["radius"],
                bgr(robot["outline"]),
                robot["thickness"],
            )
            cv2.line(image, *robot["line"], bgr(robot["outline"]), robot["thickness"])
            cv2.putText(
                image,
                "robot",
                robot["label"],
                cv2.FONT_HERSHEY_SIMPLEX,
                scale * 0.6,
                (255, 255, 255),
                max(1, int(scale)),
            )
            for row, text in enumerate(lines):
                position = (20, int((row + 1) * 40 * scale))
                cv2.putText(
                    image,
                    text,
                    position,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    scale,
                    (255, 255, 255),
                    max(1, int(scale * 2)),
                )
            ok, encoded = cv2.imencode(
                ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
            )
            if not ok:
                raise RuntimeError("fake frame encoding failed")
            return encoded.tobytes()
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", (width, height), background)
        draw = ImageDraw.Draw(image)
        draw.ellipse(
            (
                marker_x - radius,
                marker_y - radius,
                marker_x + radius,
                marker_y + radius,
            ),
            fill=(255, 220, 0),
        )
        (cx, cy), r = robot["centre"], robot["radius"]
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=robot["body"],
            outline=robot["outline"],
            width=robot["thickness"],
        )
        draw.line(robot["line"], fill=robot["outline"], width=robot["thickness"])
        try:
            font = ImageFont.load_default(size=max(12, height // 20))
            small = ImageFont.load_default(size=max(10, height // 32))
        except TypeError:  # Pillow < 10.1
            font = small = ImageFont.load_default()
        label_x, label_y = robot["label"]
        draw.text(
            (label_x, label_y - max(10, height // 32)),
            "robot",
            fill=(255, 255, 255),
            font=small,
        )
        draw.multiline_text((20, 20), "\n".join(lines), fill=(255, 255, 255), font=font)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


def setup_hardware(fake=False):
    """Create the robot and camera (real or fake) and start the camera."""
    global tbot, camera
    if fake:
        sim = FakeRobotSim()
        tbot = FakeTrilobot(sim)
        camera = FakeCamera(sim)
        BUTTONS.update({"A": "A", "B": "B", "X": "X", "Y": "Y"})
    else:
        from picamera2 import Picamera2
        from trilobot import BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y, Trilobot

        tbot = Trilobot()
        camera = Picamera2()
        BUTTONS.update({"A": BUTTON_A, "B": BUTTON_B, "X": BUTTON_X, "Y": BUTTON_Y})

    camera.configure(
        camera.create_preview_configuration(
            main={"format": "BGR888", "size": video_size}
        )
    )
    camera.start()
    camera.set_controls(
        {
            "ExposureTime": MOTION_EXPOSURE_US,
            "FrameDurationLimits": (
                round(1_000_000 / video_fps),
                round(1_000_000 / video_fps),
            ),
        }
    )


def stop_robot():
    global last_drive_command
    with hardware_lock:
        tbot.stop()
    last_drive_command = time.monotonic()


def set_drive(left, right):
    global last_drive_command
    left = float(left)
    right = float(right)
    if not math.isfinite(left) or not math.isfinite(right):
        raise ValueError("motor speeds must be finite")
    left = max(-1.0, min(1.0, left))
    right = max(-1.0, min(1.0, right))
    with hardware_lock:
        tbot.set_motor_speeds(left, right)
    last_drive_command = time.monotonic()


def read_telemetry():
    with hardware_lock:
        buttons = {
            name: bool(tbot.read_button(button)) for name, button in BUTTONS.items()
        }
        distance = tbot.read_distance(timeout=25, samples=3)
    telemetry = {
        "type": "telemetry",
        "distance_cm": round(float(distance), 1),
        "buttons": buttons,
    }
    if isinstance(tbot, FakeTrilobot):
        telemetry["sim"] = tbot.sim.snapshot()  # Fake mode only, for debugging.
    return telemetry


def colour(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("color must be [red, green, blue]")
    values = [int(channel) for channel in value]
    if any(channel < 0 or channel > 255 for channel in values):
        raise ValueError("color channels must be between 0 and 255")
    return values


def configure_video(message):
    """Safely change camera output size, frame rate, and JPEG quality."""
    global video_size, video_fps, jpeg_quality

    requested_size = (int(message["width"]), int(message["height"]))
    if requested_size not in VIDEO_SIZES:
        supported = ", ".join(f"{w}x{h}" for w, h in VIDEO_SIZES)
        raise ValueError(f"video size must be one of: {supported}")

    requested_fps = float(message["fps"])
    if not math.isfinite(requested_fps) or not 1.0 <= requested_fps <= MAX_VIDEO_FPS:
        raise ValueError(f"fps must be between 1 and {MAX_VIDEO_FPS:g}")

    requested_quality = int(message["jpeg_quality"])
    if requested_quality not in range(10, 101):
        raise ValueError("jpeg_quality must be between 10 and 100")

    with camera_lock:
        camera.stop()
        camera.configure(
            camera.create_preview_configuration(
                main={"format": "BGR888", "size": requested_size}
            )
        )
        camera.start()
        camera.set_controls(
            {
                "ExposureTime": MOTION_EXPOSURE_US,
                "FrameDurationLimits": (
                    round(1_000_000 / requested_fps),
                    round(1_000_000 / requested_fps),
                ),
            }
        )
        video_size = requested_size
        video_fps = requested_fps
        jpeg_quality = requested_quality

    return {
        "type": "ack",
        "command": "video_config",
        "width": requested_size[0],
        "height": requested_size[1],
        "fps": requested_fps,
        "jpeg_quality": requested_quality,
    }


def current_video_config():
    with camera_lock:
        return {
            "width": video_size[0],
            "height": video_size[1],
            "fps": video_fps,
            "jpeg_quality": jpeg_quality,
        }


def handle_command(message):
    if not isinstance(message, dict):
        raise ValueError("command must be a JSON object")

    command_type = message.get("type")

    if command_type == "drive":
        set_drive(message["left"], message["right"])
        return {"type": "ack", "command": "drive"}

    if command_type == "stop":
        stop_robot()
        return {"type": "ack", "command": "stop"}

    if command_type == "underlights":
        with hardware_lock:
            tbot.fill_underlighting(colour(message["color"]))
        return {"type": "ack", "command": "underlights"}

    if command_type == "button_led":
        button = str(message["button"]).upper()
        if button not in BUTTONS:
            raise ValueError("button must be A, B, X, or Y")
        value = float(message["value"])
        if not math.isfinite(value):
            raise ValueError("LED value must be finite")
        value = max(0.0, min(1.0, value))
        with hardware_lock:
            tbot.set_button_led(BUTTONS[button], value)
        return {"type": "ack", "command": "button_led"}

    if command_type == "distance_request":
        return read_telemetry()

    raise ValueError(f"unknown command type: {command_type!r}")


def encode_jpeg(image, quality):
    from PIL import Image

    buffer = BytesIO()
    # Keep the camera byte order unchanged for this camera setup.
    Image.fromarray(image).save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def capture_jpeg():
    with camera_lock:
        current_fps = video_fps
        current_quality = jpeg_quality
        if isinstance(camera, FakeCamera):
            jpeg = camera.capture_jpeg(current_quality)
        else:
            image = camera.capture_array()
            jpeg = encode_jpeg(image, current_quality)
    return jpeg, current_fps


async def send_json(websocket, message, send_lock):
    async with send_lock:
        await websocket.send(json.dumps(message))


async def send_video(websocket):
    """Stream frames without ever queueing them.

    Each frame is sent from its own task, outside send_lock, so command
    replies and telemetry never wait behind a video frame. If the previous
    frame is still being sent (slow link), this frame is skipped.
    """
    pending = None
    try:
        while True:
            started = time.monotonic()
            current_fps = video_fps
            if pending is not None and pending.done():
                if pending.cancelled() or pending.exception() is not None:
                    return  # Connection closed; the handler cleans up.
                pending = None
            if pending is None:
                jpeg, current_fps = await asyncio.to_thread(capture_jpeg)
                # spawn() retrieves the exception even if we stop watching it.
                pending = spawn(websocket.send(jpeg))
            remaining = (1.0 / current_fps) - (time.monotonic() - started)
            if remaining > 0:
                await asyncio.sleep(remaining)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            with suppress(BaseException):
                await pending


async def send_telemetry(websocket, send_lock):
    while True:
        telemetry = await asyncio.to_thread(read_telemetry)
        await send_json(websocket, telemetry, send_lock)
        await asyncio.sleep(0.25)


async def motor_watchdog():
    while True:
        if time.monotonic() - last_drive_command > WATCHDOG_SECONDS:
            stop_robot()
        await asyncio.sleep(0.1)


active_sessions = {}
# Recently disconnected sessions that can still be resumed: token -> session.
recent_sessions = {}
# Serialises admission (busy/resume check, kicks, registration) so two
# clients can never both end up holding the robot. Created lazily so it is
# bound to the running loop (asyncio.Lock() outside a loop breaks on 3.9).
_admission_lock = None
_admission_loop = None
# Fire-and-forget tasks, kept referenced until they finish.
background_tasks = set()


def admission_lock():
    global _admission_lock, _admission_loop
    loop = asyncio.get_running_loop()
    if _admission_lock is None or _admission_loop is not loop:
        _admission_lock = asyncio.Lock()
        _admission_loop = loop
    return _admission_lock


def _task_done(task):
    background_tasks.discard(task)
    if not task.cancelled():
        task.exception()  # Retrieve it so asyncio never logs "never retrieved".


def spawn(coroutine):
    """Start a background task, keep a reference and swallow its exception."""
    task = asyncio.ensure_future(coroutine)
    background_tasks.add(task)
    task.add_done_callback(_task_done)
    return task


def current_session_name():
    for session in list(active_sessions.values()):
        return session["name"]
    return None


def new_session_name(requested=""):
    """The client's own name if valid, else a fresh LEARNER- name."""
    if NAME_PATTERN.fullmatch(requested or ""):
        return requested
    taken = {session["name"] for session in active_sessions.values()}
    while True:
        name = GUEST_PREFIX + "".join(random.choice(GUEST_LETTERS) for _ in range(4))
        if name not in taken:
            return name


def query_param(websocket, name, default=""):
    request = getattr(websocket, "request", None)
    path = getattr(request, "path", None) or getattr(websocket, "path", "") or ""
    return parse_qs(urlparse(path).query).get(name, [default])[0]


def wants_takeover(websocket):
    return query_param(websocket, "force", "0") in ("1", "true")


async def close_later(websocket, code, reason):
    """Close a socket without blocking on a peer that may never answer."""
    with suppress(Exception):
        await websocket.close(code, reason)


def evict_session(key, code, reason):
    """Drop a session from the active set now and close its socket behind."""
    session = active_sessions.pop(key, None)
    if session is not None:
        session["evicted"] = True
        spawn(close_later(session["websocket"], code, reason))
    return session


async def kick_all_sessions(new_name):
    """Close every active session so a new client can take over the robot."""
    for key, session in list(active_sessions.items()):
        logging.info("%s took over from %s", new_name, session["name"])
        for message in (
            {"type": "taken_over", "by": new_name, "at": time.time()},
            {"type": "kicked", "message": "Another user took over this robot"},
        ):
            with suppress(Exception):
                await asyncio.wait_for(
                    send_json(session["websocket"], message, session["send_lock"]),
                    1.0,
                )
        evict_session(key, CLOSE_KICKED, "Kicked off")


def find_resumable(token):
    """Return (active_key, session) for a resume token, or (None, None)."""
    if not token:
        return None, None
    for key, session in active_sessions.items():
        if session["token"] == token:
            return key, session
    session = recent_sessions.get(token)
    if session is None:
        return None, None
    in_use = {s["name"] for s in active_sessions.values()}
    if time.time() - session["left_at"] > RESUME_GRACE or session["name"] in in_use:
        return None, None
    return None, session


def prune_recent_sessions():
    now = time.time()
    for token, session in list(recent_sessions.items()):
        if now - session["left_at"] > RESUME_GRACE:
            del recent_sessions[token]


async def admit_client(websocket, send_lock):
    """Decide whether a client may hold the robot and register it if so.

    Must run under admission_lock(): everything from the busy/resume check
    to registration in active_sessions happens atomically with respect to
    other connecting clients. Returns the new session, or None if busy.
    """
    prune_recent_sessions()
    resume_key, resumable = find_resumable(query_param(websocket, "resume"))
    # Someone else holds the robot if any active session isn't the one resumed.
    others = [key for key in active_sessions if key != resume_key]
    if others and not wants_takeover(websocket):
        holder = active_sessions[others[0]]
        names = ", ".join(active_sessions[key]["name"] for key in others)
        with suppress(Exception):
            await asyncio.wait_for(
                send_json(
                    websocket,
                    {
                        "type": "busy",
                        "session": names,
                        "holder": holder["name"],
                        "since": holder["since"],
                    },
                    send_lock,
                ),
                1.0,
            )
        logging.info("Rejected client; robot is in use by %s", names)
        return None

    if resumable is not None:
        session_name = resumable["name"]
        token = resumable["token"]
        since = resumable["since"]
        recent_sessions.pop(token, None)
        if resume_key is not None:
            # The old socket is half-dead (e.g. Wi-Fi drop); replace it quietly.
            evict_session(resume_key, CLOSE_REPLACED, "replaced by resume")
    else:
        session_name = new_session_name(query_param(websocket, "name"))
        token = secrets.token_urlsafe(16)
        since = time.time()
    if active_sessions:
        await kick_all_sessions(session_name)

    session = {
        "name": session_name,
        "token": token,
        "since": since,
        "websocket": websocket,
        "send_lock": send_lock,
        "resumed_from": resumable,
    }
    active_sessions[id(websocket)] = session
    return session


async def handle_client(websocket, *ignored):
    send_lock = asyncio.Lock()
    async with admission_lock():
        session = await admit_client(websocket, send_lock)
    if session is None:
        # Close outside the lock so a slow peer can't hold up admission.
        await close_later(websocket, CLOSE_BUSY, "Robot is in use")
        return
    session_name = session["name"]
    token = session["token"]
    since = session["since"]
    resumable = session.pop("resumed_from", None)
    if resumable is not None:
        logging.info("%s resumed", session_name)
    else:
        logging.info("Control client connected as %s", session_name)
    tasks = [
        asyncio.create_task(send_video(websocket)),
        asyncio.create_task(send_telemetry(websocket, send_lock)),
        asyncio.create_task(motor_watchdog()),
    ]
    try:
        config = current_video_config()
        await send_json(
            websocket,
            {
                "type": "hello",
                "session": session_name,
                "resume": token,
                "robot": socket.gethostname(),
                "resumed": resumable is not None,
                "video": {"format": "jpeg", **config},
            },
            send_lock,
        )
        async for raw_message in websocket:
            if session.get("evicted"):
                break  # Taken over or replaced; ignore late commands.
            if not isinstance(raw_message, str):
                continue
            try:
                message = json.loads(raw_message)
                if not isinstance(message, dict):
                    raise ValueError("command must be a JSON object")
                if message.get("type") == "video_config":
                    reply = await asyncio.to_thread(configure_video, message)
                else:
                    reply = handle_command(message)
            except (
                KeyError,
                TypeError,
                ValueError,
                OverflowError,
                json.JSONDecodeError,
            ) as error:
                reply = {"type": "error", "message": str(error)}
            await send_json(websocket, reply, send_lock)
    except ConnectionClosed:
        pass  # Normal for a Wi-Fi drop or takeover; logged below.
    finally:
        if active_sessions.get(id(websocket)) is session:
            del active_sessions[id(websocket)]
        if not session.get("evicted"):
            # Dropped rather than replaced: keep it resumable for a while.
            recent_sessions[token] = {
                "name": session_name,
                "token": token,
                "since": since,
                "left_at": time.time(),
            }
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if not active_sessions:
            stop_robot()
        logging.info("Session %s disconnected", session_name)


async def main(host=HOST, port=PORT, fake=False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    setup_hardware(fake)
    try:
        async with serve(
            handle_client,
            host,
            port,
            max_size=2**22,
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_TIMEOUT,
        ):
            logging.info(
                "Listening on ws://%s:%s%s", host, port, " (fake robot)" if fake else ""
            )
            await asyncio.Future()
    finally:
        stop_robot()
        with suppress(Exception):
            camera.stop()
        with suppress(Exception):
            camera.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default=HOST, help="address to listen on")
    parser.add_argument("--port", type=int, default=PORT, help="port to listen on")
    parser.add_argument(
        "--fake",
        action="store_true",
        help="no hardware: synthetic camera and sensors, motors/LEDs only logged",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(args.host, args.port, args.fake))
    except KeyboardInterrupt:
        pass
