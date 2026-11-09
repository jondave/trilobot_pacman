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
