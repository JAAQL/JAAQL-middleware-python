import os

from jaaql.constants import ENDPOINT__get_shared_var, ENDPOINT__set_shared_var, PORT__shared_var_service
import sys
from flask import Flask, jsonify, request

ARG__variable = "variable"
ARG__value = "value"

SHARED_VAR__frozen = "frozen"

STATE = {
    SHARED_VAR__frozen: os.environ.get("IS_FROZEN", "False").lower() == "true"
}


def create_app():

    app = Flask(__name__, instance_relative_config=True)

    @app.route("/", methods=["GET"])
    def is_alive():
        return jsonify("OK")

    @app.route(ENDPOINT__get_shared_var, methods=["POST"])
    def get_shared_var():
        global STATE

        return jsonify({ARG__value: STATE[request.json[ARG__variable]]})

    @app.route(ENDPOINT__set_shared_var, methods=["POST"])
    def set_shared_var():
        global STATE

        STATE[request.json[ARG__variable]] = request.json[ARG__value]

        return jsonify("OK")

    return app


def bootup():
    flask_app = create_app()
    print("Created shared var app host, running flask", file=sys.stderr)
    flask_app.run(port=PORT__shared_var_service, host="0.0.0.0", threaded=True)
