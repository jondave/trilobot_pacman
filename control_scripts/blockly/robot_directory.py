"""Fetch and clean the LCAS robot directory for the robot picker."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import threading
import time
import urllib.request
from datetime import datetime, timezone

from robot_config import ROBOT_PING_GREEN_SECONDS, ROBOT_PING_ORANGE_SECONDS

LOG = logging.getLogger("trilobot_blockly")

ROBOT_DIRECTORY_URL = os.environ.get(
    "TRILOBOT_ROBOT_DIRECTORY_URL",
    "https://findmyrobot.services.lcas.group/api/robots?filter=trilo",
)
ROBOT_DIRECTORY_TIMEOUT = 2
# How long a directory answer counts as fresh, and how long the very first
# request (with nothing cached yet) waits for the directory before giving up.
ROBOT_DIRECTORY_TTL = 60
ROBOT_DIRECTORY_FIRST_WAIT = 2.0
# After a failed refresh, wait this long before trying the directory again.
ROBOT_DIRECTORY_RETRY = 10
UNAVAILABLE_MESSAGE = "Robot list unavailable; enter an address manually."
STALE_MESSAGE = "Robot list may be out of date; enter an address manually if needed."

# Errors fetch_robot_directory() may raise; the route turns them into a 502.
RobotDirectoryError = (OSError, ValueError, json.JSONDecodeError)


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
        headers={"Accept": "application/json", "User-Agent": "Trilobot Blockly"},
    )
    with urllib.request.urlopen(request, timeout=ROBOT_DIRECTORY_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _robot_directory_entries(payload)


class RobotDirectoryCache:
    """Serve the robot directory from memory and refresh it in the background.

    A fresh answer (younger than ``ttl``) is served as it is. A stale one is
    still served at once, and starts one background refresh. If a refresh
    fails the last good list keeps being served, marked ``stale``. Only the
    very first request, with nothing cached, waits for the directory, and
    then at most ``first_wait`` seconds.
    """

    def __init__(
        self,
        fetch=None,
        ttl=ROBOT_DIRECTORY_TTL,
        first_wait=ROBOT_DIRECTORY_FIRST_WAIT,
        retry=ROBOT_DIRECTORY_RETRY,
        clock=time.monotonic,
    ):
        # Looked up on each refresh so tests can patch fetch_robot_directory.
        self._fetch = fetch or (lambda: fetch_robot_directory())
        self.ttl = ttl
        self.first_wait = first_wait
        self.retry = retry
        self._clock = clock
        self._lock = threading.Lock()
        self._robots = None
        self._fetched_at = None
        self._failed_at = None
        self._error = ""
        self._refresh_done = None  # threading.Event while a refresh runs

    def _start_refresh_locked(self):
        if self._refresh_done is not None:
            return self._refresh_done
        done = threading.Event()
        self._refresh_done = done
        threading.Thread(
            target=self._refresh, args=(done,), name="robot-directory", daemon=True
        ).start()
        return done

    def _refresh(self, done):
        try:
            robots = self._fetch()
        except Exception as error:  # noqa: BLE001 - any failure keeps the cache
            LOG.warning("Could not load robot directory: %s", error)
            with self._lock:
                self._failed_at = self._clock()
                self._error = str(error) or type(error).__name__
        else:
            with self._lock:
                self._robots = robots
                self._fetched_at = self._clock()
                self._failed_at = None
                self._error = ""
        finally:
            with self._lock:
                self._refresh_done = None
            done.set()

    def _answer_locked(self):
        now = self._clock()
        if self._robots is None:
            return {"robots": [], "stale": True, "error": UNAVAILABLE_MESSAGE}
        age = now - self._fetched_at
        answer = {
            "robots": list(self._robots),
            "stale": bool(self._error) or age >= self.ttl,
            "age_seconds": round(age, 1),
        }
        if self._error:
            answer["error"] = STALE_MESSAGE
        return answer

    def get(self):
        """Return {"robots": [...], "stale": bool, ...}; "error" when it failed."""
        with self._lock:
            now = self._clock()
            fresh = self._robots is not None and now - self._fetched_at < self.ttl
            backing_off = (
                self._failed_at is not None and now - self._failed_at < self.retry
            )
            done = None
            if not fresh and not backing_off:
                done = self._start_refresh_locked()
            # Only wait when nothing has ever been fetched or has failed.
            first_load = self._robots is None and self._failed_at is None
            if not first_load:
                return self._answer_locked()
            done = done or self._refresh_done
        if done is not None:
            done.wait(self.first_wait)
        with self._lock:
            return self._answer_locked()
