#!/usr/bin/env python3
"""ROS 2-style keyboard teleoperation and live video for a remote Trilobot.

Run this on the control/lab PC. The client.py file must be in the same folder.
"""

import argparse
import asyncio
import time

import cv2
import numpy as np

from client import RobotClient


# Matches the standard ROS 2 teleop_twist_keyboard layout:
#
#   u   i   o       forward-left, forward, forward-right
#   j   k   l       turn-left, stop, turn-right
#   m   ,   .       reverse-left, reverse, reverse-right
#
# Each value is (linear direction, angular direction).
ROS_MOVEMENT_KEYS = {
    ord("u"): (1.0, 1.0),
    ord("i"): (1.0, 0.0),
    ord("o"): (1.0, -1.0),
    ord("j"): (0.0, 1.0),
    ord("k"): (0.0, 0.0),
    ord("l"): (0.0, -1.0),
    ord("m"): (-1.0, 1.0),
    ord(","): (-1.0, 0.0),
    ord("."): (-1.0, -1.0),
}

# Uppercase keys avoid conflicts with the ROS movement and speed keys.
BUTTON_LED_KEYS = {
    ord("B"): "A",
    ord("N"): "B",
    ord("M"): "X",
    ord("Y"): "Y",
}

UNDERLIGHT_COLORS = {
    ord("1"): (255, 0, 0),
    ord("2"): (0, 255, 0),
    ord("3"): (0, 0, 255),
    ord("4"): (255, 255, 0),
    ord("0"): (0, 0, 0),
}


def wheel_speeds(linear_direction, angular_direction, linear_speed, turn_speed):
    """Convert ROS-style linear/angular commands to differential-drive speeds."""
    left = (linear_direction * linear_speed) - (angular_direction * turn_speed)
    right = (linear_direction * linear_speed) + (angular_direction * turn_speed)

    # Preserve the steering ratio if a diagonal command exceeds 1.0.
    scale = max(1.0, abs(left), abs(right))
    return left / scale, right / scale


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


def fit_frame_to_window(frame, window_name):
    """Scale a frame into the current window without changing its aspect ratio."""
    frame_height, frame_width = frame.shape[:2]

    try:
        _, _, window_width, window_height = cv2.getWindowImageRect(window_name)
    except cv2.error:
        window_width, window_height = frame_width, frame_height

    if window_width <= 0 or window_height <= 0:
        return frame

    scale = min(window_width / frame_width, window_height / frame_height)
    output_width = max(1, round(frame_width * scale))
    output_height = max(1, round(frame_height * scale))

    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    resized = cv2.resize(
        frame,
        (output_width, output_height),
        interpolation=interpolation,
    )

    canvas = np.zeros(
        (window_height, window_width, 3),
        dtype=frame.dtype,
    )
    offset_x = (window_width - output_width) // 2
    offset_y = (window_height - output_height) // 2
    canvas[
        offset_y:offset_y + output_height,
        offset_x:offset_x + output_width,
    ] = resized
    return canvas


def add_overlay(frame, client, linear_speed, turn_speed, left, right):
    telemetry = client.telemetry
    distance = telemetry.get("distance_cm", "--")
    buttons = telemetry.get("buttons", {})
    button_text = " ".join(
        f"{name}:{'ON' if buttons.get(name) else '--'}"
        for name in ("A", "B", "X", "Y")
    )

    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, 78), (0, 0, 0), -1)
    cv2.putText(
        frame,
        "u i o / j k l / m , .   |   space/k stop   |   ESC quit",
        (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        frame,
        f"q/z overall  w/x linear  e/c turn   "
        f"linear {linear_speed:.1f} turn {turn_speed:.1f}",
        (10, 43),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        frame,
        f"drive {left:+.1f},{right:+.1f}  distance {distance} cm  {button_text}",
        (10, 66),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 255, 255),
        1,
    )
    return frame


async def run(args):
    linear_speed = 0.5
    turn_speed = 0.5
    linear_direction = 0.0
    angular_direction = 0.0
    last_drive_sent = 0.0
    latest_frame = None
    button_led_values = {"A": 0.0, "B": 0.0, "X": 0.0, "Y": 0.0}

    print(f"Connecting to {args.url}")
    async with RobotClient(args.url) as client:
        cv2.namedWindow("Trilobot Pacman", cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        print(
            "ROS 2 keys: u i o / j k l / m , . | "
            "q/z overall | w/x linear | e/c turn | space/k stop | ESC quit"
        )
        try:
            while client.connected:
                key = cv2.waitKey(1)

                if key in ROS_MOVEMENT_KEYS:
                    linear_direction, angular_direction = ROS_MOVEMENT_KEYS[key]
                elif key in (ord("k"), ord(" ")):
                    linear_direction = angular_direction = 0.0
                elif key == ord("q"):
                    linear_speed = min(1.0, round(linear_speed + 0.1, 1))
                    turn_speed = min(1.0, round(turn_speed + 0.1, 1))
                elif key == ord("z"):
                    linear_speed = max(0.0, round(linear_speed - 0.1, 1))
                    turn_speed = max(0.0, round(turn_speed - 0.1, 1))
                elif key == ord("w"):
                    linear_speed = min(1.0, round(linear_speed + 0.1, 1))
                elif key == ord("x"):
                    linear_speed = max(0.0, round(linear_speed - 0.1, 1))
                elif key == ord("e"):
                    turn_speed = min(1.0, round(turn_speed + 0.1, 1))
                elif key == ord("c"):
                    turn_speed = max(0.0, round(turn_speed - 0.1, 1))
                elif key in UNDERLIGHT_COLORS:
                    await client.set_underlights(UNDERLIGHT_COLORS[key])
                elif key in BUTTON_LED_KEYS:
                    button = BUTTON_LED_KEYS[key]
                    button_led_values[button] = 1.0 - button_led_values[button]
                    await client.set_button_led(button, button_led_values[button])
                elif key == ord("R"):
                    await client.request_distance()
                elif key in (ord("Q"), 27):
                    break
                elif key != -1:
                    linear_direction = angular_direction = 0.0

                left, right = wheel_speeds(
                    linear_direction,
                    angular_direction,
                    linear_speed,
                    turn_speed,
                )

                # Refreshing the drive command keeps the sender watchdog happy.
                now = time.monotonic()
                if now - last_drive_sent >= 0.1:
                    await client.drive(left, right)
                    last_drive_sent = now

                new_frame = client.take_frame()
                if new_frame is not None:
                    latest_frame = new_frame
                frame = latest_frame if latest_frame is not None else make_placeholder()
                frame = add_overlay(
                    frame,
                    client,
                    linear_speed,
                    turn_speed,
                    left,
                    right,
                )
                display_frame = fit_frame_to_window(frame, "Trilobot Pacman")
                cv2.imshow("Trilobot Pacman", display_frame)
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
