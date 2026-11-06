import asyncio

from client import RobotClient


def test_next_frame_bytes_drains_buffered_frame_after_disconnect():
    async def read_frames():
        robot = RobotClient("ws://localhost")
        robot._latest_jpeg = b"buffered frame"

        assert await asyncio.wait_for(robot.next_frame_bytes(), 0.1) == b"buffered frame"
        assert await asyncio.wait_for(robot.next_frame_bytes(), 0.1) is None
        assert await asyncio.wait_for(robot.next_frame_bytes(), 0.1) is None

    asyncio.run(read_frames())
