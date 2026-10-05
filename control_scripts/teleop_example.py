#!/usr/bin/env python3
"""ROS 2-style keyboard teleoperation and live video for a remote Trilobot."""

import argparse
import asyncio
import time

import cv2
import numpy as np

from client import RobotClient

WINDOW_NAME = "Trilobot Teleop"
VIDEO_SIZE_CHOICES = (
    "640x480",
    "1640x1232",
    "1920x1080",
    "3280x2464",
)

# Standard ROS 2 teleop_twist_keyboard layout:
#
#   u   i   o       forward-left, forward, forward-right
#   j   k   l       turn-left, stop, turn-right
#   m   ,   .       reverse-left, reverse, reverse-right
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
    left = (linear_direction * linear_speed) - (angular_direction * turn_speed)
    right = (linear_direction * linear_speed) + (angular_direction * turn_speed)
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
        cv2.LINE_AA,
    )
    return frame


def window_size(window_name, fallback_width, fallback_height):
    try:
        _, _, width, height = cv2.getWindowImageRect(window_name)
    except cv2.error:
        width, height = fallback_width, fallback_height
    if width <= 0 or height <= 0:
        return fallback_width, fallback_height
    return width, height


def make_display_frame(
    frame,
    client,
    linear_speed,
    turn_speed,
    left,
    right,
    video_size,
    video_fps,
    jpeg_quality,
    show_crosshair,
):
    """Build a sharp UI canvas and letterbox the camera image into it."""
    frame_height, frame_width = frame.shape[:2]
    window_width, window_height = window_size(WINDOW_NAME, frame_width, frame_height)

    # Keep a dedicated control panel so its text is rendered at screen size.
    panel_height = max(138, round(window_height * 0.24))
    video_area_height = max(1, window_height - panel_height)
    scale = min(
        window_width / frame_width,
        video_area_height / frame_height,
    )
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
        dtype=np.uint8,
    )
    offset_x = (window_width - output_width) // 2
    offset_y = (video_area_height - output_height) // 2
    canvas[
        offset_y : offset_y + output_height,
        offset_x : offset_x + output_width,
    ] = resized

    if show_crosshair:
        centre_x = offset_x + output_width // 2
        centre_y = offset_y + output_height // 2
        arm = max(12, round(min(output_width, output_height) * 0.035))
        # Black outline keeps the crosshair visible on both light and dark scenes.
        cv2.line(
            canvas,
            (centre_x - arm, centre_y),
            (centre_x + arm, centre_y),
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.line(
            canvas,
            (centre_x, centre_y - arm),
            (centre_x, centre_y + arm),
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.line(
            canvas,
            (centre_x - arm, centre_y),
            (centre_x + arm, centre_y),
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.line(
            canvas,
            (centre_x, centre_y - arm),
            (centre_x, centre_y + arm),
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

    panel_top = video_area_height
    cv2.rectangle(
        canvas,
        (0, panel_top),
        (window_width, window_height),
        (18, 18, 18),
        cv2.FILLED,
    )
    cv2.line(
        canvas,
        (0, panel_top),
        (window_width, panel_top),
        (0, 190, 255),
        2,
    )

    font_scale = max(0.42, min(0.78, window_width / 1050.0))
    thickness = 2 if font_scale >= 0.62 else 1
    line_type = cv2.LINE_AA
    key_size = max(28, min(44, round(panel_height * 0.22)))
    key_gap = max(4, round(key_size * 0.14))
    grid_x = 12
    grid_y = panel_top + 10

    def draw_text(value, x, y, color=(235, 235, 235), scale=font_scale):
        cv2.putText(
            canvas,
            value,
            (x, y),
            cv2.FONT_HERSHEY_DUPLEX,
            scale,
            color,
            thickness,
            line_type,
        )

    # Direction keys are shown as actual square buttons in arrow formation.
    for row, keys in enumerate((("u", "i", "o"), ("j", "k", "l"), ("m", ",", "."))):
        for column, key_name in enumerate(keys):
            x = grid_x + column * (key_size + key_gap)
            y = grid_y + row * (key_size + key_gap)
            cv2.rectangle(
                canvas,
                (x, y),
                (x + key_size, y + key_size),
                (48, 48, 48),
                cv2.FILLED,
            )
            cv2.rectangle(
                canvas,
                (x, y),
                (x + key_size, y + key_size),
                (0, 210, 255),
                1,
            )
            text_size, _ = cv2.getTextSize(
                key_name,
                cv2.FONT_HERSHEY_DUPLEX,
                max(0.45, font_scale),
                thickness,
            )
            text_x = x + (key_size - text_size[0]) // 2
            text_y = y + (key_size + text_size[1]) // 2
            draw_text(key_name, text_x, text_y, (255, 255, 255), max(0.45, font_scale))

    info_x = grid_x + 3 * key_size + 2 * key_gap + 16
    draw_text("TRILOBOT TELEOP", info_x, panel_top + 24, (0, 220, 255))
    draw_text(f"TARGET  {client.url}", info_x, panel_top + 47)
    draw_text("H/h crosshair   Q/Z all   W/X drive   E/C turn", info_x, panel_top + 70)
    draw_text(
        "K/SPACE stop   ESC quit   0-4 lights   R distance", info_x, panel_top + 93
    )

    telemetry = client.telemetry
    distance = telemetry.get("distance_cm", "--")
    buttons = telemetry.get("buttons", {})
    button_text = " ".join(
        f"{name}:{'ON' if buttons.get(name) else '--'}" for name in ("A", "B", "X", "Y")
    )
    width, height = video_size
    status = (
        f"L {left:+.1f}  R {right:+.1f}   "
        f"DIST {distance} cm   {button_text}   "
        f"{width}x{height} {video_fps:g}fps Q{jpeg_quality}   "
        f"CROSSHAIR {'ON' if show_crosshair else 'OFF'}"
    )
    draw_text(status, 12, window_height - 10, (0, 255, 180))

    return canvas


async def run(args):
    linear_speed = 0.5
    turn_speed = 0.5
    linear_direction = 0.0
    angular_direction = 0.0
    last_drive_sent = 0.0
    latest_frame = None
    show_crosshair = False
    button_led_values = {"A": 0.0, "B": 0.0, "X": 0.0, "Y": 0.0}

    print(f"Connecting to {args.url}")
    async with RobotClient(args.url) as client:
        await client.configure_video(
            args.video_width,
            args.video_height,
            args.fps,
            args.jpeg_quality,
        )
        cv2.namedWindow(
            WINDOW_NAME,
            cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO,
        )
        print(
            "ROS 2 keys: u i o / j k l / m , . | "
            "H/h crosshair | q/z overall | w/x drive | e/c turn | "
            "space/k stop | ESC quit"
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
                elif key in (ord("h"), ord("H")):
                    show_crosshair = not show_crosshair
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

                now = time.monotonic()
                if now - last_drive_sent >= 0.1:
                    await client.drive(left, right)
                    last_drive_sent = now

                new_frame = client.take_frame()
                if new_frame is not None:
                    latest_frame = new_frame
                frame = latest_frame if latest_frame is not None else make_placeholder()
                display_frame = make_display_frame(
                    frame,
                    client,
                    linear_speed,
                    turn_speed,
                    left,
                    right,
                    (args.video_width, args.video_height),
                    args.fps,
                    args.jpeg_quality,
                    show_crosshair,
                )
                cv2.imshow(WINDOW_NAME, display_frame)
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
    parser.add_argument(
        "--video-size",
        choices=VIDEO_SIZE_CHOICES,
        default="1640x1232",
        help="camera output size sent by the robot",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=15.0,
        help="camera JPEG/WebSocket rate, from 1 to 30",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=75,
        help="JPEG quality, from 10 to 100",
    )
    args = parser.parse_args()

    if not 1.0 <= args.fps <= 30.0:
        parser.error("--fps must be between 1 and 30")
    if not 10 <= args.jpeg_quality <= 100:
        parser.error("--jpeg-quality must be between 10 and 100")

    args.video_width, args.video_height = (
        int(value) for value in args.video_size.split("x")
    )
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
