"""A tiny stand-in for robot_sender.py's websocket protocol, for tests."""

import asyncio
import json
import secrets
import socket
import threading
import time
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
from client import CLOSE_BUSY, CLOSE_TAKEN_OVER
from websockets.asyncio.server import serve


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _jpeg():
    ok, encoded = cv2.imencode(".jpg", np.zeros((48, 64, 3), dtype=np.uint8))
    assert ok
    return encoded.tobytes()


class FakeRobot:
    """Run a stub robot server in a background thread."""

    def __init__(self, *, telemetry_interval=0.05, frame_interval=0.05):
        self.port = free_port()
        self.url = f"ws://127.0.0.1:{self.port}"
        self.telemetry_interval = telemetry_interval
        self.frame_interval = frame_interval
        self.busy_holder = None  # set to a name to refuse every client
        self.send_telemetry = True
        self.requests = []  # query dict of every connection attempt
        self.received = []  # every JSON command from any client
        self.sessions = {}  # token -> name
        self.active = None
        self._counter = 0
        self._loop = None
        self._ready = threading.Event()
        self._stop = None
        self._thread = threading.Thread(target=self._main, daemon=True)
        self._thread.start()
        assert self._ready.wait(5), "fake robot did not start"

    # -- control from the test thread -------------------------------------

    def _run(self, coroutine, timeout=5):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(timeout)

    def take_over(self, by):
        self._run(self._take_over(by))

    def drop(self):
        """Kill the active connection without a closing handshake."""
        self._run(self._drop())

    def commands(self, kind=None):
        return [m for m in list(self.received) if kind is None or m["type"] == kind]

    def close(self):
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        self._thread.join(5)

    # -- server side ------------------------------------------------------

    def _main(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._serve())
        self._loop.close()

    async def _serve(self):
        self._stop = asyncio.Event()
        async with serve(self._handle, "127.0.0.1", self.port):
            self._ready.set()
            await self._stop.wait()

    async def _take_over(self, by):
        websocket = self.active
        await websocket.send(
            json.dumps({"type": "taken_over", "by": by, "at": time.time()})
        )
        await websocket.close(CLOSE_TAKEN_OVER, "Kicked off")

    async def _drop(self):
        self.active.transport.abort()

    async def _handle(self, websocket):
        query = {
            k: v[0] for k, v in parse_qs(urlparse(websocket.request.path).query).items()
        }
        self.requests.append(query)
        if self.busy_holder:
            await websocket.send(
                json.dumps(
                    {
                        "type": "busy",
                        "session": self.busy_holder,
                        "holder": self.busy_holder,
                        "since": time.time() - 120,
                    }
                )
            )
            await websocket.close(CLOSE_BUSY, "Robot is in use")
            return
        token = query.get("resume")
        resumed = token in self.sessions
        if not resumed:
            self._counter += 1
            token = secrets.token_hex(4)
            self.sessions[token] = f"Fake-{self._counter}"
        name = self.sessions[token]
        self.active = websocket
        await websocket.send(
            json.dumps(
                {
                    "type": "hello",
                    "session": name,
                    "resume": token,
                    "robot": "fake-trilo",
                    "resumed": resumed,
                }
            )
        )
        tasks = [asyncio.create_task(self._stream(websocket))]
        try:
            async for raw in websocket:
                self.received.append(json.loads(raw))
        except Exception:
            pass
        finally:
            for task in tasks:
                task.cancel()

    async def _stream(self, websocket):
        jpeg = _jpeg()
        next_telemetry = 0.0
        while True:
            now = time.monotonic()
            if self.send_telemetry and now >= next_telemetry:
                next_telemetry = now + self.telemetry_interval
                await websocket.send(json.dumps({"type": "telemetry", "buttons": {}}))
            await websocket.send(jpeg)
            await asyncio.sleep(self.frame_interval)
