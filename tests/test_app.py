import app as blockly_app
import pytest


@pytest.fixture()
def client():
    return blockly_app.app.test_client()


def test_index(client):
    assert client.get("/").status_code == 200


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
