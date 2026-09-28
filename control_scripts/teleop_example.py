#!/usr/bin/env python3
"""Basic keyboard teleoperation and live video for a remote Trilobot.

Run this on the student's lab machine, not on the Raspberry Pi. The client
and this file should be in the same directory.
"""

import argparse
import asyncio
import time

import cv2
import numpy as np

from client import RobotClient


MOVEMENT_KEYS = {
    ord("w"): (1.0, 1.0),
    ord("s"): (-1.0, -1.0),
    ord("a"): (-1.0, 1.0),
    ord("d"): (1.0, -1.0),
    2490368: (1.0, 1.0),  # up arrow on Linux OpenCV
    2621440: (-1.0, -1.0),  # down arrow
    2424832: (-1.0, 1.0),  # left arrow
    2555904: (1.0, -1.0),  # right arrow
}

LED_COLORS = {
    ord("1"): (255, 0, 0),
    ord("2"): (0, 255, 0),
    ord("3"): (0, 0, 255),
    ord("4"): (255, 255, 0),
    ord("0"): (0, 0, 0),
}

BUTTON_LED_KEYS = {
    ord("b"): "A",
    ord("n"): "B",
    ord("m"): "X",
    ord(","): "Y",
}


def make_placeholder():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        "Waiting for camera...",
        (170, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )
    return frame


def add_overlay(frame, client, speed, left, right):
    telemetry = client.telemetry
    distance = telemetry.get("distance_cm", "--")
    buttons = telemetry.get("buttons", {})
    button_text = " ".join(
        f"{name}:{'ON' if buttons.get(name) else '--'}"
        for name in ("A", "B", "X", "Y")
    )
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, 60), (0, 0, 0), -1)
    cv2.putText(
        frame,
        f"WASD/arrows  X/space stop  Q quit  speed {speed:.1f}",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        frame,
        f"drive {left:+.1f},{right:+.1f}  distance {distance} cm  {button_text}",
        (10, 46),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 255),
        1,
    )
    return frame


async def run(args):
    speed = 0.5
    left = right = 0.0
    last_drive_sent = 0.0
    button_led_values = {"A": 0.0, "B": 0.0, "X": 0.0, "Y": 0.0}

    print(f"Connecting to {args.url}")
    async with RobotClient(args.url) as client:
        cv2.namedWindow("Trilobot Pacman", cv2.WINDOW_NORMAL)
        print(
            "WASD/arrows move | X or space stops | 1-4/0 underlights | "
            "B/N/M/, toggle button LEDs | R distance | Q quits"
        )
        try:
            while client.connected:
                key = cv2.waitKey(1)

                if key in MOVEMENT_KEYS:
                    direction_left, direction_right = MOVEMENT_KEYS[key]
                    left = direction_left * speed
                    right = direction_right * speed
                elif key in (ord("x"), ord(" ")):
                    left = right = 0.0
                    await client.stop()
                elif key in (ord("+"), ord("=")):
                    speed = min(1.0, round(speed + 0.1, 1))
                elif key in (ord("-"), ord("_")):
                    speed = max(0.0, round(speed - 0.1, 1))
                elif key in LED_COLORS:
                    await client.set_underlights(LED_COLORS[key])
                elif key in BUTTON_LED_KEYS:
                    button = BUTTON_LED_KEYS[key]
                    button_led_values[button] = 1.0 - button_led_values[button]
                    await client.set_button_led(button, button_led_values[button])
                elif key == ord("r"):
                    await client.request_distance()
                elif key in (ord("q"), 27):
                    break

                # Refreshing the drive command keeps the sender's safety watchdog happy.
                now = time.monotonic()
                if now - last_drive_sent >= 0.1:
                    await client.drive(left, right)
                    last_drive_sent = now

                frame = client.take_frame()
                if frame is None:
                    frame = make_placeholder()
                frame = add_overlay(frame, client, speed, left, right)
                cv2.imshow("Trilobot Pacman", frame)
                await asyncio.sleep(0.01)
        finally:
            await client.stop()
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "url",
        help="robot WebSocket URL, for example ws://trilobot.local:8765",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
