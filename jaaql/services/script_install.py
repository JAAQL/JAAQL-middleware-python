from jaaql.utilities.utils import load_config, await_ems_startup, get_base_url
from jaaql.constants import HEADER__security_bypass, VAULT_KEY__jaaql_local_access_key
from jaaql.utilities.vault import Vault, DIR__vault
import os
from os.path import join
from os import listdir
import requests
import json

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


def bootup(vault_key, is_gunicorn: bool = False):
    config = load_config(is_gunicorn)
    await_ems_startup()
    base_url = get_base_url(config, is_gunicorn)
    vault = Vault(vault_key, DIR__vault)

    bypass_header = {HEADER__security_bypass: vault.get_obj(VAULT_KEY__jaaql_local_access_key)}

    script_root = join(os.getcwd(), DIR__install_scripts)
    try:
        i = 0
        for script in listdir(script_root):
            if i != 0:
                print()

            with open(join(script_root, script), "r") as script_file:
                print("Processing script " + script)
                process_script(script_file.read(), base_url, bypass_header)
            i += 1

    except FileNotFoundError:
        print("Skipping installation as no files found in install scripts")
