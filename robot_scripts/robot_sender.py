#!/usr/bin/env python3
"""Simple configurable WebSocket server for a Trilobot.

Run this file on the Raspberry Pi. It receives JSON commands and sends
binary JPEG camera frames plus JSON telemetry to the connected control PC.
"""

import asyncio
import json
import logging
import math
import random
import time
from contextlib import suppress
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from threading import Lock

from PIL import Image
from picamera2 import Picamera2
from trilobot import BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y, Trilobot

try:
    from websockets.asyncio.server import serve
except ImportError:
    from websockets.server import serve


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

SESSION_WORDS = json.loads(
    (Path(__file__).with_name("session_words.json")).read_text(encoding="utf-8")
)
CLOSE_BUSY = 4001
CLOSE_KICKED = 4002

BUTTONS = {
    "A": BUTTON_A,
    "B": BUTTON_B,
    "X": BUTTON_X,
    "Y": BUTTON_Y,
}

tbot = Trilobot()
hardware_lock = Lock()
camera_lock = Lock()
camera = Picamera2()

video_size = DEFAULT_VIDEO_SIZE
video_fps = DEFAULT_VIDEO_FPS
jpeg_quality = DEFAULT_JPEG_QUALITY

camera.configure(
    camera.create_preview_configuration(main={"format": "BGR888", "size": video_size})
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

last_drive_command = time.monotonic()


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
    return {
        "type": "telemetry",
        "distance_cm": round(float(distance), 1),
        "buttons": buttons,
    }


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
    buffer = BytesIO()
    # Keep the camera byte order unchanged for this camera setup.
    Image.fromarray(image).save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def capture_jpeg():
    with camera_lock:
        image = camera.capture_array()
        current_fps = video_fps
        current_quality = jpeg_quality
        jpeg = encode_jpeg(image, current_quality)
    return jpeg, current_fps


async def send_json(websocket, message, send_lock):
    async with send_lock:
        await websocket.send(json.dumps(message))


async def send_video(websocket, send_lock):
    while True:
        started = time.monotonic()
        jpeg, current_fps = await asyncio.to_thread(capture_jpeg)
        async with send_lock:
            await websocket.send(jpeg)
        remaining = (1.0 / current_fps) - (time.monotonic() - started)
        if remaining > 0:
            await asyncio.sleep(remaining)


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


def new_session_name():
    taken = {session["name"] for session in active_sessions.values()}
    while True:
        name = "-".join(word.capitalize() for word in random.sample(SESSION_WORDS, 2))
        if name not in taken:
            return name


def wants_takeover(websocket):
    request = getattr(websocket, "request", None)
    path = getattr(request, "path", None) or getattr(websocket, "path", "") or ""
    return parse_qs(urlparse(path).query).get("force", ["0"])[0] in ("1", "true")


async def kick_all_sessions():
    """Close every active session so a new client can take over the robot."""
    for session in list(active_sessions.values()):
        with suppress(Exception):
            await send_json(
                session["websocket"],
                {"type": "kicked", "message": "Another user took over this robot"},
                session["send_lock"],
            )
        with suppress(Exception):
            await session["websocket"].close(CLOSE_KICKED, "Kicked off")
    for _ in range(50):
        if not active_sessions:
            break
        await asyncio.sleep(0.1)


async def handle_client(websocket, *ignored):
    send_lock = asyncio.Lock()
    if active_sessions:
        if not wants_takeover(websocket):
            names = ", ".join(s["name"] for s in active_sessions.values())
            with suppress(Exception):
                await send_json(
                    websocket,
                    {"type": "busy", "session": names},
                    send_lock,
                )
                await websocket.close(CLOSE_BUSY, "Robot is in use")
            logging.info("Rejected client; robot is in use by %s", names)
            return
        await kick_all_sessions()
    session_name = new_session_name()
    active_sessions[id(websocket)] = {
        "name": session_name,
        "websocket": websocket,
        "send_lock": send_lock,
    }
    logging.info("Control client connected as %s", session_name)
    send_lock = asyncio.Lock()
    tasks = [
        asyncio.create_task(send_video(websocket, send_lock)),
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
                "video": {"format": "jpeg", **config},
            },
            send_lock,
        )
        async for raw_message in websocket:
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
    finally:
        active_sessions.pop(id(websocket), None)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if not active_sessions:
            stop_robot()
        logging.info("Session %s disconnected", session_name)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        async with serve(
            handle_client,
            HOST,
            PORT,
            max_size=2**22,
            ping_interval=20,
            ping_timeout=20,
        ):
            logging.info("Listening on ws://%s:%s", HOST, PORT)
            await asyncio.Future()
    finally:
        stop_robot()
        with suppress(Exception):
            camera.stop()
        with suppress(Exception):
            camera.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
