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


LOG = logging.getLogger("trilobot_client")


class RobotClient:
    def __init__(self, url, *, max_size=2**22):
        self.url = url
        self.max_size = max_size
        self.websocket = None
        self.receiver_task = None
        self._latest_frame = None
        self._telemetry = {}
        self._send_lock = asyncio.Lock()
        self.connected = False
        self.error = None

    async def __aenter__(self):
        self.websocket = await connect(
            self.url,
            max_size=self.max_size,
            ping_interval=20,
            ping_timeout=20,
        )
        self.connected = True
        self.receiver_task = asyncio.create_task(self._receive_loop())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def _receive_loop(self):
        try:
            async for message in self.websocket:
                if isinstance(message, bytes):
                    array = np.frombuffer(message, dtype=np.uint8)
                    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
                    if frame is not None:
                        # Keep only the newest frame to avoid display latency.
                        self._latest_frame = frame
                    continue

                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    LOG.warning("Ignoring non-JSON text message")
                    continue

                message_type = payload.get("type")
                if message_type == "telemetry":
                    self._telemetry = payload
                elif message_type == "distance":
                    self._telemetry = {
                        **self._telemetry,
                        "distance_cm": payload.get("distance_cm", "--"),
                    }
                elif message_type == "error":
                    LOG.warning("Robot error: %s", payload.get("message"))
                else:
                    LOG.debug("Robot message: %s", payload)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.error = error
        finally:
            self.connected = False

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
        return await self.send(
            {"type": "button_led", "button": button, "value": value}
        )

    async def request_distance(self):
        return await self.send({"type": "distance_request"})

    def take_frame(self):
        """Return the newest BGR OpenCV frame, or None if none has arrived."""
        frame = self._latest_frame
        self._latest_frame = None
        return frame

    @property
    def telemetry(self):
        return self._telemetry

    async def close(self):
        if self.websocket and self.connected:
            try:
                await self.stop()
            except Exception:
                pass
        if self.receiver_task:
            self.receiver_task.cancel()
            await asyncio.gather(self.receiver_task, return_exceptions=True)
            self.receiver_task = None
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False
