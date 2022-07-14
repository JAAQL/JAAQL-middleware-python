from jaaql.utilities.utils import load_config, await_ems_startup, get_base_url, await_jaaql_bootup
from jaaql.constants import HEADER__security_bypass, VAULT_KEY__jaaql_local_access_key, ENDPOINT__install
from jaaql.utilities.vault import Vault, DIR__vault
import os
from os.path import join, exists, dirname
from os import listdir
import requests
import json
import time

DIR__install_scripts = "install_scripts"


def process_script(script: str, base_url: str, bypass_header: dict):
    script = script.replace("\r\n", "\n")
    commands = script.split("\n\n")
    if len(commands[0]) == 0:
        print("Script is empty")
    for command in commands:
        action = command.split("\n")[0].strip()
        method = action.split(" ")[0]
        endpoint = action.split(" ")[1]

        loaded_json = None
        if len(command.split("\n")) > 1:
            loaded_json = json.loads("\n".join(command.split("\n")[1:]).strip())

        requests.request(method, base_url + endpoint, headers=bypass_header, json=loaded_json)


def bootup(vault_key, is_gunicorn: bool = False, install_on_bootup: bool = False):
    config = load_config(is_gunicorn)
    install_status = await_jaaql_bootup(config, is_gunicorn)
    base_url = get_base_url(config, is_gunicorn)
    if install_on_bootup and install_status != 200:
        install_key_file = join(dirname(dirname(dirname(__file__))), "install_key")
        while not exists(install_key_file):
            time.sleep(0.1)
        time.sleep(0.5)
        install_key = None
        with open(install_key_file, "r") as install_key_file:
            install_key = install_key_file.read().strip()
        json_data = {
            "password": "pa55word",
            "use_mfa": False,
            "install_key": install_key,
            "superjaaql_password": "passw0rd",
            "allow_uninstall": False
        }
        if not is_gunicorn:
            json_data["db_connection_string"] = "postgresql://postgres:123456@localhost:5432/jaaql"
        requests.post(base_url + ENDPOINT__install, json=json_data)

    await_ems_startup()
    vault = Vault(vault_key, DIR__vault)

    bypass_header = {HEADER__security_bypass: vault.get_obj(VAULT_KEY__jaaql_local_access_key)}
    if "INSTALL_PATH" in os.environ:
        did_script_install_marker = join(os.environ["INSTALL_PATH"], "vault", "did_script_install")
    else:
        did_script_install_marker = join("vault", "did_script_install")
    try:
        os.makedirs(did_script_install_marker)
    except FileExistsError:
        pass
    script_root = join(os.getcwd(), DIR__install_scripts)
    try:
        i = 0
        for script in listdir(script_root):
            cur_script_marker = join(did_script_install_marker, script)
            if not exists(cur_script_marker):
                if i != 0:
                    print()

                with open(join(script_root, script), "r") as script_file:
                    print("Processing script " + script)
                    process_script(script_file.read(), base_url, bypass_header)
                i += 1
            open(cur_script_marker, "w").close()
    except FileNotFoundError:
        print("Skipping installation as no files found in install scripts")
