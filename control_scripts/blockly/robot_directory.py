"""Fetch and clean the LCAS robot directory for the robot picker."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone

from robot_config import ROBOT_PING_GREEN_SECONDS, ROBOT_PING_ORANGE_SECONDS

LOG = logging.getLogger("trilobot_blockly")

ROBOT_DIRECTORY_URL = os.environ.get(
    "TRILOBOT_ROBOT_DIRECTORY_URL",
    "https://findmyrobot.services.lcas.group/api/robots?filter=trilo",
)
# Every request goes to the directory (nothing is cached), so keep the wait
# short: a slow or unreachable directory must never hold up the page.
ROBOT_DIRECTORY_TIMEOUT = 2
UNAVAILABLE_MESSAGE = "Robot list unavailable; enter an address manually."


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


def fetch_robot_directory():
    """Download the robot directory and return its safe entries."""
    request = urllib.request.Request(
        ROBOT_DIRECTORY_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "Trilobot Blockly",
            # Ask any proxy on the way for a fresh answer too.
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=ROBOT_DIRECTORY_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _robot_directory_entries(payload)


def robot_directory_answer():
    """Fetch the directory now for /api/robots; never raises.

    Returns {"robots": [...]} or, when the directory fails or times out,
    {"robots": [], "error": "..."}.
    """
    try:
        return {"robots": fetch_robot_directory()}
    except Exception as error:  # noqa: BLE001 - any failure means "unavailable"
        LOG.warning("Could not load robot directory: %s", error)
        return {"robots": [], "error": UNAVAILABLE_MESSAGE}
