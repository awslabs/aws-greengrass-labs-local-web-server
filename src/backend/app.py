import json
import logging
import os
import sys
from datetime import timedelta

import awsiot.greengrasscoreipc
import awsiot.greengrasscoreipc.client as client
import awsiot.greengrasscoreipc.model as model
from flask import Flask, jsonify, request
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user
from flask_socketio import SocketIO, disconnect, send

# Setup logging to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

app = Flask(__name__)
app.config.update(
    DEBUG=True,
    SECRET_KEY="greengrass-v2-example",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=15),
)
login_manager = LoginManager()
login_manager.init_app(app)
TIMEOUT = 10
socket_io = SocketIO(app, cors_allowed_origins="*")
users = [{"id": 46, "username": "test", "password": "test"}]


class User(UserMixin):
    pass


def get_user(user_id: int):
    for user in users:
        if int(user["id"]) == int(user_id):
            return user


@login_manager.user_loader
def user_loader(id: int):
    user = get_user(id)
    if user:
        user_model = User()
        user_model.id = user["id"]
        return user_model


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    for user in users:
        if user["username"] == username and user["password"] == password:
            user_model = User()
            user_model.id = user["id"]
            login_user(user_model)
            return jsonify({"authenticated": True})

    return jsonify({"authenticated": False})


@app.route("/api/logout", methods=["GET"])
def logout():
    logout_user()
    return jsonify({"authenticated": False})


@app.route("/api/authenticated", methods=["GET"])
def check_authenticated():
    return jsonify({"authenticated": current_user.is_authenticated})


class SubscribeTopicHandler(client.SubscribeToIoTCoreStreamHandler):
    """
    Event handler for SubscribeToTopicOperation

    Inherit from this class and override methods to handle
    stream events during a SubscribeToTopicOperation.
    """

    def __init__(self, socket_io_app):
        super().__init__()
        self.socket_io = socket_io_app

    def on_stream_event(self, event: model.IoTCoreMessage) -> None:
        """
        Invoked when a SubscriptionResponseMessage is received.
        """
        payload = {"payload": json.loads(event.message.payload.decode())}

        self.socket_io.emit("message", payload)
        logger.info("message sent from SubscribeTopicHandler!")


def subscribe_to_core(socket_io_app):
    ipc_client = awsiot.greengrasscoreipc.connect()

    subscribe_operation = ipc_client.new_subscribe_to_iot_core(
        stream_handler=SubscribeTopicHandler(socket_io_app)
    )
    subscribe_operation.activate(
        request=model.SubscribeToIoTCoreRequest(
            topic_name="{}/subscribe".format(os.environ["AWS_IOT_THING_NAME"]),
            qos=model.QOS.AT_LEAST_ONCE,
        )
    )


@socket_io.on("connect")
def connect_handler():
    if current_user.is_authenticated:
        socket_io.emit(
            "message", {"payload": "New socket has connected"}, broadcast=True,
        )
        logger.info("connect() - authenticated user!")
    else:
        return False


@socket_io.on("publish")
def handle_message(msg):

    if current_user.is_authenticated:

        ipc_client = awsiot.greengrasscoreipc.connect()

        topic = "{}/publish".format(os.environ["AWS_IOT_THING_NAME"])
        data = {"msg": msg}

        publish_operation = ipc_client.new_publish_to_iot_core()
        publish_operation.activate(
            request=model.PublishToIoTCoreRequest(
                topic_name=topic,
                qos=model.QOS.AT_MOST_ONCE,
                payload=json.dumps(data).encode(),
            )
        )


def get_secret():

    ipc_client = awsiot.greengrasscoreipc.connect()

    get_secret_value = ipc_client.new_get_secret_value()
    get_secret_value.activate(
        request=model.GetSecretValueRequest(secret_id="localwebserver_credentials")
    )
    secret_response = get_secret_value.get_response().result()
    secrets = json.loads(secret_response.secret_value.secret_string)
    get_secret_value.close()

    users = [
        {"id": 1, "username": secrets["username"], "password": secrets["password"]}
    ]


if __name__ == "__main__":  # pragma: no cover

    get_secret()
    subscribe_to_core(socket_io)
    socket_io.run(app, host="0.0.0.0", port=5000)
