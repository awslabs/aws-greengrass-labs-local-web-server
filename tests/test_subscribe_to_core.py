import pytest
from flask import Flask
from flask_socketio import SocketIO, send
from artifacts.backend.app import subscribe_to_core


def test_subscribe_to_core(mocker, monkeypatch):
    """Subscribe to AWS IoT Core for relaying to Socket.IO"""

    monkeypatch.setenv("AWS_IOT_THING_NAME", "TestDevice")
    ipc_connect = mocker.patch("awsiot.greengrasscoreipc.connect")

    app = Flask(__name__)
    socket_io = SocketIO(app, cors_allowed_origins="*")

    subscribe_to_core(socket_io)

    ipc_connect.assert_called_once()
