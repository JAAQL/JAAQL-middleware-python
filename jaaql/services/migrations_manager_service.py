import os

from jaaql.utilities.utils import load_config, get_base_url, await_jaaql_installation, await_jaaql_bootup
from jaaql.constants import ENDPOINT__install, VAULT_KEY__super_local_access_key, ENDPOINT__execute_migrations, \
    PORT__mms, ENVIRON__JAAQL__SUPER_BYPASS_KEY
from jaaql.utilities.vault import Vault, DIR__vault
from monitor.main import HEADER__security_bypass
from os.path import join, exists, dirname
import requests
import time
import sys
from flask import Flask, jsonify


def create_app():

    app = Flask(__name__, instance_relative_config=True)

    @app.route("/", methods=["GET"])
    def is_alive():
        return jsonify("OK")

    return app


def bootup(vault_key, is_gunicorn: bool = False, install_on_bootup: bool = True):
    config = load_config(is_gunicorn)
    install_status = await_jaaql_bootup(config, is_gunicorn)
    base_url = get_base_url(config, is_gunicorn)
    if install_on_bootup and install_status != 200:
        install_key_file = join(dirname(dirname(dirname(__file__))), "install_key")
        while not exists(install_key_file):
            time.sleep(0.1)
        time.sleep(0.5)
        with open(install_key_file, "r") as install_key_file:
            install_key = install_key_file.read().strip()
        json_data = {
            "super_db_password": os.environ.get("SUPER_PASSWORD", "passw0rd"),
            "jaaql_password": os.environ.get("JAAQL_PASSWORD", "pa55word"),
            "install_key": install_key,
            "allow_uninstall": True
        }
        if not is_gunicorn:
            json_data["db_connection_string"] = "postgresql://postgres:123456@localhost:5434/"
        requests.post(base_url + ENDPOINT__install, json=json_data)

    await_jaaql_installation(config, is_gunicorn)
    vault = Vault(vault_key, DIR__vault)
    bypass_header = {HEADER__security_bypass: os.environ.get(ENVIRON__JAAQL__SUPER_BYPASS_KEY,
                     vault.get_obj(VAULT_KEY__super_local_access_key) if is_gunicorn else "00000-00000")}
    res = requests.post(base_url + ENDPOINT__execute_migrations, headers=bypass_header)

    if res.status_code == 200:
        flask_app = create_app()
        print("Created migration manager app host, running flask", file=sys.stderr)
        flask_app.run(port=PORT__mms, host="0.0.0.0", threaded=True)
