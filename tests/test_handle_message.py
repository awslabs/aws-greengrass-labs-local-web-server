import pytest
import json
from artifacts.backend.app import app, socket_io, get_secret


def test_api_endpoints(mocker, monkeypatch):
    """Test Flask API endpoints"""

    # log the user in through Flask test client
    flask_test_client = app.test_client()

    # log in via HTTP
    r = flask_test_client.post(
        "/api/login", json={"username": "invalid", "password": "invalid"}
    )
    assert r.status_code == 200
    assert json.loads(r.data.decode())["authenticated"] == False

    # log in via HTTP
    r = flask_test_client.post(
        "/api/login", json={"username": "test", "password": "test"}
    )
    assert r.status_code == 200
    assert json.loads(r.data.decode())["authenticated"] == True

    # log in via HTTP
    r = flask_test_client.get("/api/authenticated")
    assert r.status_code == 200
    assert json.loads(r.data.decode())["authenticated"] == True

    # log in via HTTP
    r = flask_test_client.get("/api/logout")
    assert r.status_code == 200
    assert json.loads(r.data.decode())["authenticated"] == False


def test_handle_message(mocker, monkeypatch):
    """Test relaying message back to MQTT"""

    # log the user in through Flask test client
    flask_test_client = app.test_client()

    # connect to Socket.IO without being logged in
    socketio_test_client = socket_io.test_client(
        app, flask_test_client=flask_test_client
    )

    # make sure the server rejected the connection
    assert not socketio_test_client.is_connected()

    # log in via HTTP
    r = flask_test_client.post(
        "/api/login", json={"username": "test", "password": "test"}
    )
    assert r.status_code == 200
    assert json.loads(r.data.decode())["authenticated"] == True

    # connect to Socket.IO again, but now as a logged in user
    socketio_test_client = socket_io.test_client(
        app, flask_test_client=flask_test_client
    )

    # make sure the server accepted the connection
    r = socketio_test_client.get_received()
    assert len(r) == 1

    monkeypatch.setenv("AWS_IOT_THING_NAME", "TestDevice")
    ipc_connect = mocker.patch("awsiot.greengrasscoreipc.connect")

    socketio_test_client.emit("publish", "test")
    r = socketio_test_client.get_received()

    ipc_connect.assert_called_once()


def test_get_secret(mocker, monkeypatch):
    """Test get_secret from Secrets Manager"""

    monkeypatch.setenv("AWS_IOT_THING_NAME", "TestDevice")
    ipc_connect = mocker.patch("awsiot.greengrasscoreipc.connect")
    mocker.patch("json.loads", return_value={"username": "test", "password": "test"})

    get_secret()

    ipc_connect.assert_called_once()
