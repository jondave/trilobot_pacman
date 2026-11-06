"""The simulated robot drawn by robot_sender.py --fake (kinematics, colour, protocol)."""

import asyncio
import importlib.util
import json
import math
import sys

import pytest
from robot_helpers import ROBOT_SENDER, fake_robot
from websockets.asyncio.client import connect


@pytest.fixture(scope="module")
def rs():
    spec = importlib.util.spec_from_file_location("robot_sender_sim", ROBOT_SENDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


@pytest.fixture
def sim(rs):
    clock = Clock()
    sim = rs.FakeRobotSim(aspect=4 / 3, clock=clock)
    sim.clock = clock
    return sim


def test_forward_moves_along_heading(sim):
    start = sim.snapshot()
    assert start["heading_deg"] == 90.0  # Starts facing up the frame.
    sim.set_speeds(1.0, 1.0)
    sim.clock.now += 0.5
    moved = sim.snapshot()
    assert moved["x"] == pytest.approx(start["x"])
    # 0.35 widths/s for 0.5 s is 0.175 widths, i.e. 0.233 heights at 4:3.
    assert start["y"] - moved["y"] == pytest.approx(0.175 * 4 / 3, abs=1e-3)
    sim.heading = 0.0  # Face right.
    sim.clock.now += 0.2
    assert sim.snapshot()["x"] - moved["x"] == pytest.approx(0.07, abs=1e-3)


def test_reverse_moves_backwards(sim):
    y = sim.snapshot()["y"]
    sim.set_speeds(-0.5, -0.5)
    sim.clock.now += 0.2
    assert sim.snapshot()["y"] > y


def test_spin_in_place_turns_without_moving(sim):
    start = sim.snapshot()
    sim.set_speeds(-1.0, 1.0)  # Right wheel forward: turn anticlockwise.
    sim.clock.now += 0.25
    spun = sim.snapshot()
    assert (spun["x"], spun["y"]) == pytest.approx((start["x"], start["y"]))
    assert spun["heading_deg"] == pytest.approx(135.0, abs=0.5)
    sim.set_speeds(1.0, -1.0)
    sim.clock.now += 0.5
    assert sim.snapshot()["heading_deg"] == pytest.approx(45.0, abs=0.5)


def test_clamped_to_frame_edges(sim):
    sim.set_speeds(1.0, 1.0)
    sim.clock.now += 10
    top = sim.snapshot()
    assert top["y"] == pytest.approx(sim.RADIUS)
    sim.heading = math.pi  # Face left.
    sim.clock.now += 10
    left = sim.snapshot()
    assert left["x"] == pytest.approx(sim.RADIUS / sim.aspect)
    assert left["y"] == pytest.approx(sim.RADIUS)


def test_stop_halts_movement(rs, sim):
    robot = rs.FakeTrilobot(sim)
    robot.set_motor_speeds(1.0, 1.0)
    sim.clock.now += 0.1
    robot.stop()  # What the motor watchdog calls.
    stopped = sim.snapshot()
    sim.clock.now += 5
    assert sim.snapshot() == stopped
    assert (stopped["left"], stopped["right"]) == (0.0, 0.0)


def test_watchdog_stops_the_robot(rs, monkeypatch):
    monkeypatch.setattr(rs, "WATCHDOG_SECONDS", 0.2)
    rs.setup_hardware(fake=True)
    rs.set_drive(1.0, 1.0)

    async def run():
        task = asyncio.ensure_future(rs.motor_watchdog())
        await asyncio.sleep(0.5)
        task.cancel()

    asyncio.run(run())
    stopped = rs.tbot.sim.snapshot()
    assert (stopped["left"], stopped["right"]) == (0.0, 0.0)
    asyncio.run(asyncio.sleep(0.2))
    assert rs.tbot.sim.snapshot() == stopped


def test_distance_to_facing_edge(rs, sim):
    # Facing up from y=0.75 of a 4:3 frame: 0.75 heights = 0.5625 widths,
    # less the robot radius (0.045 widths), times 200 cm per width.
    assert sim.distance_cm() == pytest.approx((0.5625 - 0.045) * 200, abs=0.1)
    sim.heading = 0.0  # Facing right from x=0.5.
    assert sim.distance_cm() == pytest.approx((0.5 - 0.045) * 200, abs=0.1)
    sim.set_speeds(1.0, 1.0)
    sim.clock.now += 10
    assert sim.distance_cm() == pytest.approx(0.0, abs=0.1)


def test_light_colour_rules(rs, sim):
    robot = rs.FakeTrilobot(sim)
    assert sim.colour() == (150, 150, 150)
    robot.fill_underlighting([255, 0, 0])
    assert sim.colour() == (255, 0, 0)
    robot.clear_underlighting()
    robot.set_underlight(0, (255, 0, 0))
    robot.set_underlight(1, (0, 0, 255))
    assert sim.colour() == (128, 0, 128)  # Mean of the lit LEDs only.
    robot.fill_underlighting(0, 0, 0)
    assert sim.colour() == (150, 150, 150)


def _centre_pixel_rgb(rs, camera, backend):
    jpeg = camera.capture_jpeg(95)
    state = camera.sim.snapshot()
    width, height = camera.size
    x, y = int(state["x"] * width), int(state["y"] * height)
    if backend == "cv2":
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        return tuple(int(c) for c in image[y, x][::-1])  # BGR -> RGB
    import io

    from PIL import Image

    return Image.open(io.BytesIO(jpeg)).convert("RGB").getpixel((x, y))


@pytest.mark.parametrize("backend", ["cv2", "pil"])
def test_rendered_robot_colour(rs, monkeypatch, backend):
    if backend == "pil":
        pytest.importorskip("PIL")
        monkeypatch.setitem(sys.modules, "cv2", None)  # Force the PIL path.
    else:
        pytest.importorskip("cv2")
    sim = rs.FakeRobotSim()
    robot = rs.FakeTrilobot(sim)
    camera = rs.FakeCamera(sim)
    camera.configure({"size": (640, 480)})

    def close(actual, expected):
        return all(abs(a - e) <= 12 for a, e in zip(actual, expected, strict=True))

    grey = _centre_pixel_rgb(rs, camera, backend)
    assert close(grey, (150, 150, 150)), grey
    robot.fill_underlighting([255, 0, 0])
    red = _centre_pixel_rgb(rs, camera, backend)
    assert close(red, (255, 0, 0)), red
    robot.fill_underlighting([0, 0, 255])
    blue = _centre_pixel_rgb(rs, camera, backend)
    assert close(blue, (0, 0, 255)), blue


def test_drive_over_protocol_moves_robot():
    async def telemetry(ws):
        while True:
            message = await asyncio.wait_for(ws.recv(), 5)
            if isinstance(message, str):
                message = json.loads(message)
                if message["type"] == "telemetry":
                    return message

    async def run(url):
        async with connect(url) as ws:
            start = (await telemetry(ws))["sim"]
            for _ in range(5):  # Keep the watchdog fed for about 0.5 s.
                await ws.send(json.dumps({"type": "drive", "left": 1, "right": 1}))
                await asyncio.sleep(0.1)
            await ws.send(json.dumps({"type": "stop"}))
            await ws.send(json.dumps({"type": "underlights", "color": [255, 0, 0]}))
            moved = await telemetry(ws)
            while moved["sim"]["colour"] != [255, 0, 0]:  # Skip older telemetry.
                moved = await telemetry(ws)
            distance = moved["distance_cm"]
            moved = moved["sim"]
            assert start["y"] - moved["y"] > 0.1
            assert moved["x"] == pytest.approx(start["x"])
            assert moved["colour"] == [255, 0, 0]
            assert distance < 100

    with fake_robot() as url:
        asyncio.run(run(url))
