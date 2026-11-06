"""Values shared by the Python server and the browser page.

This module is the single source of truth. ``app.py`` and ``blocks_python.py``
import from it, and the ``/`` route embeds ``browser_config()`` in the page as
JSON for ``app.js`` to read. ``tests/test_consistency.py`` checks for drift.
"""

from __future__ import annotations

import json
from pathlib import Path

# Underlight colours, in the order the dropdowns show them: name -> robot hex.
LED_COLOURS = (
    ("red", "#ff0000"),
    ("green", "#00ff00"),
    ("blue", "#0000ff"),
    ("yellow", "#ffff00"),
    ("white", "#ffffff"),
    ("purple", "#ff00ff"),
)

VIDEO_SIZES = (
    (640, 480),
    (1640, 1232),
    (1920, 1080),
    (3280, 2464),
)
VIDEO_FPS_CHOICES = (5, 10, 15, 20, 25, 30)
VIDEO_QUALITY_CHOICES = (10, 20, 30, 40, 50, 60, 70, 80, 90)
DEFAULT_VIDEO_CONFIG = {
    "width": 640,
    "height": 480,
    "fps": 20.0,
    "jpeg_quality": 60,
}

# Robot directory: how recently a robot pinged decides its green/orange/red dot.
ROBOT_PING_GREEN_SECONDS = 10 * 60
ROBOT_PING_ORANGE_SECONDS = 30 * 60

# Placeholder used in static/blocks.json for a dropdown of LED_COLOURS.
LED_COLOUR_OPTIONS_PLACEHOLDER = "@led_colours"
BLOCKS_JSON = Path(__file__).resolve().parent / "static" / "blocks.json"


def browser_config():
    """Return the JSON-safe settings the page needs before it builds anything."""
    return {
        "led_colours": [list(item) for item in LED_COLOURS],
        "led_colour_placeholder": LED_COLOUR_OPTIONS_PLACEHOLDER,
        "video": {
            "sizes": [list(size) for size in VIDEO_SIZES],
            "fps_choices": list(VIDEO_FPS_CHOICES),
            "quality_choices": list(VIDEO_QUALITY_CHOICES),
            "default": dict(DEFAULT_VIDEO_CONFIG),
        },
        "robot_ping": {
            "green_seconds": ROBOT_PING_GREEN_SECONDS,
            "orange_seconds": ROBOT_PING_ORANGE_SECONDS,
        },
    }


def block_definitions():
    """Return the Blockly JSON block definitions from static/blocks.json."""
    return json.loads(BLOCKS_JSON.read_text(encoding="utf-8"))
