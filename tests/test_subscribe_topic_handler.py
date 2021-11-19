import pytest
import json
from flask import Flask
from flask_socketio import SocketIO, send
import awsiot.greengrasscoreipc.model as model
from artifacts.backend.app import SubscribeTopicHandler


def test_subscribe_topic_handler(mocker, monkeypatch):
    """Subscribe to AWS IoT Core for relaying to Socket.IO"""

    app = Flask(__name__)
    socket_io = SocketIO(app, cors_allowed_origins="*")

    stream_handler = SubscribeTopicHandler(socket_io)

    event = model.IoTCoreMessage(
        message=model.MQTTMessage(
            topic_name=None, payload=json.dumps({"test": "test"}).encode()
        )
    )

    stream_handler.on_stream_event(event)
