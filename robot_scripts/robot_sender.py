#!/usr/bin/env python3
"""Simple WebSocket server for a Trilobot.

Run this file on the Raspberry Pi. It receives JSON commands and sends
binary JPEG camera frames plus JSON telemetry to the connected control PC.
"""

import asyncio
import json
import logging
from io import BytesIO
import math
import time
from contextlib import suppress
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
VIDEO_SIZE = (640, 480)
VIDEO_FPS = 15
JPEG_QUALITY = 75
WATCHDOG_SECONDS = 0.6

BUTTONS = {
    "A": BUTTON_A,
    "B": BUTTON_B,
    "X": BUTTON_X,
    "Y": BUTTON_Y,
}

tbot = Trilobot()
hardware_lock = Lock()
camera = Picamera2()
camera.configure(
    camera.create_preview_configuration(
        main={"format": "RGB888", "size": VIDEO_SIZE}
    )
)
camera.start()

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
            name: bool(tbot.read_button(button))
            for name, button in BUTTONS.items()
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


async def send_json(websocket, message, send_lock):
    async with send_lock:
        await websocket.send(json.dumps(message))


def encode_jpeg(image):
    buffer = BytesIO()
    Image.fromarray(image).save(buffer, format="JPEG", quality=JPEG_QUALITY)
    return buffer.getvalue()


async def send_video(websocket, send_lock):
    delay = 1.0 / VIDEO_FPS
    while True:
        started = time.monotonic()
        image = await asyncio.to_thread(camera.capture_array)
        jpeg = await asyncio.to_thread(encode_jpeg, image)
        async with send_lock:
            await websocket.send(jpeg)
        remaining = delay - (time.monotonic() - started)
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


async def handle_client(websocket, *ignored):
    logging.info("Control client connected")
    send_lock = asyncio.Lock()
    tasks = [
        asyncio.create_task(send_video(websocket, send_lock)),
        asyncio.create_task(send_telemetry(websocket, send_lock)),
        asyncio.create_task(motor_watchdog()),
    ]
    try:
        await send_json(
            websocket,
            {
                "type": "hello",
                "video": {
                    "format": "jpeg",
                    "width": VIDEO_SIZE[0],
                    "height": VIDEO_SIZE[1],
                },
            },
            send_lock,
        )
        async for raw_message in websocket:
            if not isinstance(raw_message, str):
                continue
            try:
                reply = handle_command(json.loads(raw_message))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                reply = {"type": "error", "message": str(error)}
            await send_json(websocket, reply, send_lock)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        stop_robot()
        logging.info("Control client disconnected; motors stopped")


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
