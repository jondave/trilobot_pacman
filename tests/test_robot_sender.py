"""Session, resume and takeover behaviour of robot_sender.py in --fake mode."""

import asyncio
import contextlib
import importlib.util
import json

import pytest
from robot_helpers import ROBOT_SENDER, fake_robot, free_port
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed


@pytest.fixture
def robot_url():
    with fake_robot() as url:
        yield url


async def next_json(ws, timeout=5.0):
    """Return the next JSON message, skipping binary video frames."""

    async def read():
        while True:
            message = await ws.recv()
            if isinstance(message, str):
                return json.loads(message)

    return await asyncio.wait_for(read(), timeout)


async def wait_for_type(ws, wanted, timeout=5.0):
    while True:
        message = await next_json(ws, timeout)
        if message["type"] == wanted:
            return message


async def json_until_closed(ws, timeout=5.0):
    """Collect JSON messages until the socket closes; return (messages, code)."""
    messages = []

    async def read():
        try:
            async for message in ws:
                if isinstance(message, str):
                    messages.append(json.loads(message))
        except ConnectionClosed:
            pass

    await asyncio.wait_for(read(), timeout)
    return messages, ws.close_code


def test_hello_has_session_resume_and_robot(robot_url):
    async def run():
        async with connect(robot_url) as ws:
            hello = await wait_for_type(ws, "hello")
            assert hello["session"]
            assert isinstance(hello["resume"], str) and len(hello["resume"]) >= 16
            assert hello["robot"]
            assert hello["resumed"] is False
            assert hello["video"]["format"] == "jpeg"
            frame = await asyncio.wait_for(ws.recv(), 5)
            while isinstance(frame, str):
                frame = await asyncio.wait_for(ws.recv(), 5)
            assert frame[:2] == b"\xff\xd8"  # JPEG start-of-image
            await ws.send(json.dumps({"type": "drive", "left": 0.5, "right": 0.5}))
            assert await wait_for_type(ws, "ack") == {"type": "ack", "command": "drive"}
            telemetry = await wait_for_type(ws, "telemetry")
            assert telemetry["buttons"] == {k: False for k in "ABXY"}

    asyncio.run(run())


def test_second_client_gets_busy_with_holder(robot_url):
    async def run():
        async with connect(robot_url) as first:
            hello = await wait_for_type(first, "hello")
            async with connect(robot_url) as second:
                messages, code = await json_until_closed(second)
        busy = messages[0]
        assert busy["type"] == "busy"
        assert busy["holder"] == hello["session"]
        assert busy["session"] == hello["session"]
        assert isinstance(busy["since"], float)
        assert code == 4001

    asyncio.run(run())


def test_force_sends_taken_over_then_4002(robot_url):
    async def run():
        async with connect(robot_url) as first:
            await wait_for_type(first, "hello")
            async with connect(robot_url + "/?force=1") as second:
                hello = await wait_for_type(second, "hello")
                messages, code = await json_until_closed(first)
                taken = [m for m in messages if m["type"] == "taken_over"]
                assert taken and taken[0]["by"] == hello["session"]
                assert isinstance(taken[0]["at"], float)
                assert code == 4002

    asyncio.run(run())


def test_resume_after_abrupt_drop_keeps_name(robot_url):
    async def run():
        first = await connect(robot_url)
        hello = await wait_for_type(first, "hello")
        first.transport.abort()  # Simulate a Wi-Fi drop: no close handshake.
        await asyncio.sleep(0.3)
        async with connect(f"{robot_url}/?resume={hello['resume']}") as second:
            again = await wait_for_type(second, "hello")
        assert again["session"] == hello["session"]
        assert again["resume"] == hello["resume"]
        assert again["resumed"] is True

    asyncio.run(run())


def test_resume_while_old_socket_open_closes_it_with_4003(robot_url):
    async def run():
        async with connect(robot_url) as first:
            hello = await wait_for_type(first, "hello")
            async with connect(f"{robot_url}/?resume={hello['resume']}") as second:
                again = await wait_for_type(second, "hello")
                assert again["session"] == hello["session"]
                assert again["resumed"] is True
                messages, code = await json_until_closed(first)
                assert code == 4003
                assert not [m for m in messages if m["type"] == "taken_over"]

    asyncio.run(run())


def test_bogus_resume_token_gets_busy(robot_url):
    async def run():
        async with connect(robot_url) as first:
            hello = await wait_for_type(first, "hello")
            async with connect(robot_url + "/?resume=not-a-real-token") as second:
                messages, code = await json_until_closed(second)
        assert messages[0]["type"] == "busy"
        assert messages[0]["holder"] == hello["session"]
        assert code == 4001

    asyncio.run(run())


@pytest.fixture
def sender():
    """Import robot_sender in-process (fake hardware) so a test can patch it."""
    spec = importlib.util.spec_from_file_location("robot_sender_inproc", ROBOT_SENDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.setup_hardware(fake=True)
    return module


def slow_kicks(monkeypatch, sender, delay=0.5):
    """Make every takeover notice slow, as if the old holder's link stalled."""
    real_send_json = sender.send_json

    async def send_json(websocket, message, send_lock):
        if message.get("type") in ("taken_over", "kicked"):
            await asyncio.sleep(delay)
        await real_send_json(websocket, message, send_lock)

    monkeypatch.setattr(sender, "send_json", send_json)


async def _connect_hello(url):
    ws = await connect(url)
    return ws, await wait_for_type(ws, "hello")


async def _drain(ws):
    with contextlib.suppress(ConnectionClosed):
        async for _ in ws:
            pass


async def _open_count(sockets, settle=1.5):
    """How many sockets the robot has not closed after a settling period.

    Each socket is drained meanwhile, so a close frame queued behind video
    frames is actually seen.
    """
    drains = [asyncio.ensure_future(_drain(ws)) for ws in sockets]
    await asyncio.sleep(settle)
    for task in drains:
        task.cancel()
    await asyncio.gather(*drains, return_exceptions=True)
    return sum(1 for ws in sockets if ws.close_code is None)


async def _serve_inproc(sender):
    port = free_port()
    server = await serve(sender.handle_client, "127.0.0.1", port)
    return server, f"ws://127.0.0.1:{port}"


def test_concurrent_force_connects_leave_one_session(monkeypatch, sender):
    slow_kicks(monkeypatch, sender)

    async def run():
        server, url = await _serve_inproc(sender)
        sockets = []
        try:
            holder, _ = await _connect_hello(url)
            sockets.append(holder)
            results = await asyncio.gather(
                *(_connect_hello(url + "/?force=1") for _ in range(3)),
                return_exceptions=True,
            )
            sockets += [r[0] for r in results if not isinstance(r, BaseException)]
            assert await _open_count(sockets) <= 1
            assert len(sender.active_sessions) <= 1
        finally:
            for ws in sockets:
                await ws.close()
            server.close()
            await server.wait_closed()

    asyncio.run(run())


def test_force_connect_racing_resume_leaves_one_session(monkeypatch, sender):
    slow_kicks(monkeypatch, sender)

    async def run():
        server, url = await _serve_inproc(sender)
        sockets = []
        try:
            first, hello = await _connect_hello(url)
            sockets.append(first)
            results = await asyncio.gather(
                _connect_hello(url + "/?force=1"),
                _connect_hello(f"{url}/?resume={hello['resume']}"),
                return_exceptions=True,
            )
            sockets += [r[0] for r in results if not isinstance(r, BaseException)]
            assert await _open_count(sockets) <= 1
            assert len(sender.active_sessions) <= 1
        finally:
            for ws in sockets:
                await ws.close()
            server.close()
            await server.wait_closed()

    asyncio.run(run())
