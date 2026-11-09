import app as blockly_app
import pytest


@pytest.fixture()
def client():
    return blockly_app.app.test_client()


def test_index(client):
    assert client.get("/").status_code == 200


def test_python_reference_serves_the_docs_markdown(client):
    response = client.get("/api/docs/python-reference")
    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    assert response.get_data(as_text=True) == blockly_app.PYTHON_REFERENCE.read_text(
        encoding="utf-8"
    )
    assert blockly_app.PYTHON_REFERENCE.parent.name == "docs"
    assert "## Moving" in response.get_data(as_text=True)


def test_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)


def test_generate_python(client):
    program = {
        "blocks": {
            "blocks": [{"type": "robot_stop"}],
        }
    }
    response = client.post("/api/python/generate", json={"program": program})
    assert response.status_code == 200
    assert "stop()" in response.get_json()["code"]


def test_generate_reports_unknown_block_to_student(client):
    program = {"blocks": {"blocks": [{"type": "not_a_real_block"}]}}
    response = client.post("/api/python/generate", json={"program": program})
    assert response.status_code == 400
    assert "not_a_real_block" in response.get_json()["error"]


def test_start_reports_unknown_block_to_student(client):
    program = {"blocks": {"blocks": [{"type": "not_a_real_block"}]}}
    response = client.post("/api/program/start", json={"program": program})
    assert response.status_code == 400
    assert "not_a_real_block" in response.get_json()["error"]


def test_camera_reset_clears_the_preview_and_restores_default_settings(client):
    import numpy as np
    from robot_config import DEFAULT_VIDEO_CONFIG

    session = blockly_app.session
    session.set_camera_overlay(np.zeros((10, 10, 3), np.uint8))
    session.set_camera_marks([([(0, 0), (5, 0), (5, 5), (0, 5)], "x", (0, 0, 0))])
    blockly_app.runner.camera_view = "OpenCV preview (10×10)"
    response = client.post("/api/camera/reset")
    assert response.status_code == 200
    data = response.get_json()
    assert data["video"] == DEFAULT_VIDEO_CONFIG
    assert "connect" in data["message"]  # not connected: used on the next connect
    assert session.camera_overlay is None and session.camera_marks == []
    assert blockly_app.runner.camera_view is None


def test_websocket_example_download(client):
    response = client.get("/api/downloads/websocket_example.py")
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert b"ws://" in response.data
