#!/usr/bin/env python3
"""Reusable WebSocket client for the Trilobot sender."""

import asyncio
import json
import logging

import cv2
import numpy as np

try:
    from websockets.asyncio.client import connect
except ImportError:
    from websockets import connect
from websockets.exceptions import ConnectionClosed

LOG = logging.getLogger("trilobot_client")

# Close codes used by the robot sender.
CLOSE_BUSY = 4001
CLOSE_TAKEN_OVER = 4002
CLOSE_REPLACED = 4003

# Matches the robot's own keepalive so a dead connection is noticed in ~10s.
PING_INTERVAL = 5
PING_TIMEOUT = 5


class RobotClient:
    def __init__(
        self,
        url,
        *,
        max_size=2**22,
        on_message=None,
        open_timeout=5,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT,
    ):
        self.url = url
        self.max_size = max_size
        self.on_message = on_message
        self.open_timeout = open_timeout
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.websocket = None
        self.receiver_task = None
        self._latest_jpeg = None
        self._frame_event = asyncio.Event()
        self._telemetry = {}
        self._send_lock = asyncio.Lock()
        self.connected = False
        self.error = None
        self.hello = None
        self.hello_event = asyncio.Event()
        self.closed_event = asyncio.Event()
        self.close_code = None
        self.close_reason = ""
        self.session_name = ""
        self.resume_token = ""
        self.robot_name = ""
        self.resumed = False
        self.busy_session = None
        self.busy_holder = None
        self.busy_since = None
        self.kicked = False
        self.taken_over_by = None
        self.taken_over_at = None

    async def open(self):
        """Open the WebSocket and start receiving. Raises on connect failure."""
        self.websocket = await connect(
            self.url,
            max_size=self.max_size,
            open_timeout=self.open_timeout,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            close_timeout=1,
        )
        self.connected = True
        self.receiver_task = asyncio.create_task(self._receive_loop())
        return self

    async def __aenter__(self):
        return await self.open()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def _handle_text(self, payload):
        message_type = payload.get("type")
        if message_type == "telemetry":
            self._telemetry = payload
        elif message_type == "distance":
            self._telemetry = {
                **self._telemetry,
                "distance_cm": payload.get("distance_cm", "--"),
            }
        elif message_type == "hello":
            self.hello = payload
            self.session_name = str(payload.get("session") or "")
            self.resume_token = str(payload.get("resume") or "")
            self.robot_name = str(payload.get("robot") or "")
            self.resumed = bool(payload.get("resumed"))
            self.hello_event.set()
        elif message_type == "busy":
            holder = payload.get("holder") or payload.get("session") or "another user"
            self.busy_session = str(payload.get("session") or holder)
            self.busy_holder = str(holder)
            self.busy_since = payload.get("since")
        elif message_type == "taken_over":
            self.kicked = True
            self.taken_over_by = str(payload.get("by") or "another user")
            self.taken_over_at = payload.get("at")
        elif message_type == "kicked":
            # Older robots only send this; newer ones send taken_over first.
            self.kicked = True
        elif message_type == "error":
            LOG.warning("Robot error: %s", payload.get("message"))
        else:
            LOG.debug("Robot message: %s", payload)

    async def _receive_loop(self):
        try:
            async for message in self.websocket:
                if isinstance(message, bytes):
                    # Keep only the newest frame to avoid display latency.
                    self._latest_jpeg = message
                    self._frame_event.set()
                    continue

                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    LOG.warning("Ignoring non-JSON text message")
                    continue
                if not isinstance(payload, dict):
                    LOG.warning("Ignoring non-object JSON message")
                    continue
                self._handle_text(payload)
                if self.on_message is not None:
                    try:
                        self.on_message(payload)
                    except Exception:
                        LOG.exception("on_message callback failed")
        except asyncio.CancelledError:
            raise
        except ConnectionClosed as error:
            self.error = error
            LOG.info("Robot connection closed abnormally: %s", error)
        except Exception as error:
            self.error = error
            LOG.warning("Robot receive loop failed: %s", error, exc_info=True)
        finally:
            self.connected = False
            if self.websocket is not None:
                self.close_code = self.websocket.close_code
                self.close_reason = self.websocket.close_reason or ""
            self.closed_event.set()
            # Wake anyone waiting for a frame so they notice the close.
            self._frame_event.set()

    async def send(self, message):
        if not self.websocket or not self.connected:
            return False
        async with self._send_lock:
            await self.websocket.send(json.dumps(message))
        return True

    async def configure_video(self, width, height, fps, jpeg_quality):
        """Request a new camera size, frame rate, and JPEG quality."""
        return await self.send(
            {
                "type": "video_config",
                "width": int(width),
                "height": int(height),
                "fps": float(fps),
                "jpeg_quality": int(jpeg_quality),
            }
        )

    async def drive(self, left, right):
        return await self.send({"type": "drive", "left": left, "right": right})

    async def stop(self):
        return await self.send({"type": "stop"})

    async def set_underlights(self, color):
        return await self.send({"type": "underlights", "color": list(color)})

    async def set_button_led(self, button, value):
        return await self.send({"type": "button_led", "button": button, "value": value})

    async def request_distance(self):
        return await self.send({"type": "distance_request"})

    @staticmethod
    def decode_frame(data):
        if not data:
            return None
        return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)

    def take_frame_bytes(self):
        """Return the newest JPEG bytes, or None if none arrived since last time."""
        data = self._latest_jpeg
        self._latest_jpeg = None
        self._frame_event.clear()
        return data

    async def next_frame_bytes(self):
        """Wait for a newer JPEG frame. Returns None once the connection closes."""
        while True:
            if self._latest_jpeg is not None:
                return self.take_frame_bytes()
            if not self.connected:
                return None
            await self._frame_event.wait()
            data = self.take_frame_bytes()
            if data is not None:
                return data
            if not self.connected:
                return None

    def take_frame(self):
        """Return the newest BGR OpenCV frame, or None if none has arrived."""
        return self.decode_frame(self.take_frame_bytes())

    @property
    def telemetry(self):
        return self._telemetry

    async def close(self, timeout=1.5):
        if self.websocket and self.connected:
            try:
                await asyncio.wait_for(self.stop(), 0.5)
            except (ConnectionClosed, TimeoutError, OSError) as error:
                LOG.debug("Could not send stop while closing: %s", error)
        if self.receiver_task:
            self.receiver_task.cancel()
            await asyncio.gather(self.receiver_task, return_exceptions=True)
            self.receiver_task = None
        if self.websocket:
            websocket = self.websocket
            try:
                await asyncio.wait_for(websocket.close(), timeout)
            except (TimeoutError, OSError) as error:
                LOG.debug("Closing robot socket timed out: %s", error)
                transport = getattr(websocket, "transport", None)
                if transport is not None:
                    transport.abort()
            if self.close_code is None:
                self.close_code = websocket.close_code
            self.websocket = None
        self.connected = False
        self.closed_event.set()
        self._frame_event.set()

    async def abort(self):
        """Drop the connection immediately (used when the link looks dead)."""
        websocket = self.websocket
        transport = getattr(websocket, "transport", None)
        if transport is not None:
            transport.abort()
        await self.close(timeout=0.5)
