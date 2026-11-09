"""scan_robot_qr() finds robot QR codes and draws labelled boxes on the camera."""

import cv2
import numpy as np
from program_runner import QR_OTHER_COLOUR, QR_ROBOT_COLOUR, ProgramRunner
from robot_session import RobotSession, _draw_camera_marks


def _qr(text, size=200):
    code = cv2.QRCodeEncoder.create().encode(text)
    code = cv2.resize(code, (size, size), interpolation=cv2.INTER_NEAREST)
    return cv2.cvtColor(code, cv2.COLOR_GRAY2BGR)


def _frame(*codes):
    frame = np.full((480, 640, 3), 255, np.uint8)
    for (x, y), image in codes:
        frame[y : y + image.shape[0], x : x + image.shape[1]] = image
    return frame


def _runner_with_frame(frame):
    session = RobotSession()
    session.latest_frame = frame
    return ProgramRunner(session), session


def test_robot_code_is_found_and_boxed_with_its_name():
    runner, session = _runner_with_frame(
        _frame(((60, 140), _qr("https://lcastor.lincoln.ac.uk/#trilo-07")))
    )
    assert runner._scan_robot_qr() == "trilo-07"
    [(points, label, colour)] = session.camera_marks
    assert (label, colour) == ("trilo-07", QR_ROBOT_COLOUR)
    corners = np.asarray(points).reshape(-1, 2)
    assert corners[:, 0].min() >= 50 and corners[:, 0].max() <= 270


def test_other_codes_are_boxed_but_not_returned():
    runner, session = _runner_with_frame(
        _frame(
            ((20, 140), _qr("https://lcastor.lincoln.ac.uk/#trilo-03")),
            ((380, 140), _qr("hello there")),
        )
    )
    assert runner._scan_robot_qr() == "trilo-03"
    marks = {label: colour for _, label, colour in session.camera_marks}
    assert marks == {"trilo-03": QR_ROBOT_COLOUR, "hello there": QR_OTHER_COLOUR}


def test_no_code_clears_old_boxes():
    runner, session = _runner_with_frame(_frame())
    session.camera_marks = [([(0, 0), (9, 0), (9, 9), (0, 9)], "old", (0, 0, 0))]
    assert runner._scan_robot_qr() == ""
    assert session.camera_marks == []


def test_marks_are_drawn_with_a_label_inside_the_picture():
    image = np.zeros((480, 640, 3), np.uint8)
    corners = [(0, 0), (120, 0), (120, 120), (0, 120)]  # no room above: label below
    _draw_camera_marks(image, [(corners, "trilo-07", QR_ROBOT_COLOUR)])
    assert (image == QR_ROBOT_COLOUR).all(axis=2).sum() > 500
    assert (image == 255).all(axis=2).any()  # white label text


def test_streamed_frame_shows_the_boxes_but_frame_copy_stays_clean():
    session = RobotSession()
    frame = _frame()
    session.set_camera_marks(
        [([(100, 100), (200, 100), (200, 200), (100, 200)], "x", QR_ROBOT_COLOUR)]
    )
    session._store_frame(frame)
    assert (session.frame_copy() == 255).all()  # programs see the plain picture
    shown = cv2.imdecode(np.frombuffer(session.latest_jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert np.abs(shown.astype(int) - (255, 255, 255)).sum(axis=2).max() > 100
