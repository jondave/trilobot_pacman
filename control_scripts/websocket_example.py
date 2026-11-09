#!/usr/bin/env python3
"""Talk to a Trilobot directly over its WebSocket (no Blockly app needed).

Setup (once):
    pip install websockets

Run:
    python websocket_example.py ROBOT_IP_ADDRESS

The robot listens on port 8765. It sends JSON text messages (hello, telemetry,
ack, error) and camera pictures as binary JPEG messages. You send JSON
commands. Only one student can drive a robot at a time.
"""

import asyncio
import json
import sys

from websockets.asyncio.client import connect

PORT = 8765
NAME = "myown-script"  # your session name: word-word, lowercase, such as "blue-fox"


async def listen(websocket):
    """Print what the robot sends. Binary messages are camera frames (JPEG)."""
    async for message in websocket:
        if isinstance(message, bytes):
            continue  # a camera picture; save or decode it if you want it
        data = json.loads(message)
        if data.get("type") == "telemetry":
            print("distance:", data["distance_cm"], "cm  buttons:", data["buttons"])
        elif data.get("type") in ("hello", "error", "busy", "taken_over"):
            print("robot says:", data)


async def send(websocket, command):
    await websocket.send(json.dumps(command))


async def main(address):
    url = f"ws://{address}:{PORT}/?name={NAME}"
    async with connect(url, max_size=2**22) as websocket:
        listener = asyncio.create_task(listen(websocket))
        try:
            await send(websocket, {"type": "underlights", "color": [0, 255, 0]})

            # The robot stops by itself if it hears no "drive" for about half a
            # second, so keep sending it for as long as you want it to move.
            # Wheel speeds go from -1.0 (backwards) to 1.0 (forwards).
            for _ in range(20):  # about 2 seconds
                await send(websocket, {"type": "drive", "left": 0.5, "right": 0.5})
                await asyncio.sleep(0.1)

            await send(websocket, {"type": "stop"})
            await send(websocket, {"type": "underlights", "color": [0, 0, 0]})
            await asyncio.sleep(0.5)
        finally:
            await send(websocket, {"type": "stop"})
            listener.cancel()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python websocket_example.py ROBOT_IP_ADDRESS")
    asyncio.run(main(sys.argv[1]))
