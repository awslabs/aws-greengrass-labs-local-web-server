import pytest
import json
from artifacts.backend.app import app, socket_io, get_secret

SECRET_USERNAME = "secret-user"
SECRET_PASSWORD = "secret-password"


def load_secret(mocker, username=SECRET_USERNAME, password=SECRET_PASSWORD):
    """Run get_secret() against a mocked Greengrass IPC client returning these credentials."""
    ipc_connect = mocker.patch("awsiot.greengrasscoreipc.connect")
    response = (
        ipc_connect.return_value.new_get_secret_value.return_value.get_response.return_value.result.return_value
    )
    response.secret_value.secret_string = json.dumps(
        {"username": username, "password": password}
    )
    get_secret()
    return ipc_connect


def test_api_endpoints(mocker, monkeypatch):
    """Test Flask API endpoints"""

    load_secret(mocker)

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
        "/api/login", json={"username": SECRET_USERNAME, "password": SECRET_PASSWORD}
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

    load_secret(mocker)

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
        "/api/login", json={"username": SECRET_USERNAME, "password": SECRET_PASSWORD}
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


def test_get_secret_replaces_default_credentials(mocker):
    """Only the Secrets Manager credential authenticates; test/test is rejected."""

    load_secret(mocker)
    flask_test_client = app.test_client()

    r = flask_test_client.post(
        "/api/login", json={"username": "test", "password": "test"}
    )
    assert json.loads(r.data.decode())["authenticated"] == False

    r = flask_test_client.post(
        "/api/login", json={"username": SECRET_USERNAME, "password": SECRET_PASSWORD}
    )
    assert json.loads(r.data.decode())["authenticated"] == True


def test_app_config_is_hardened():
    """No shipped session signing key and no debug mode."""

    assert app.config["SECRET_KEY"] != "greengrass-v2-example"
    assert len(app.config["SECRET_KEY"]) >= 32
    assert app.config["DEBUG"] == False
