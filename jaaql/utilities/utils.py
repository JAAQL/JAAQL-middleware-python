import requests
from os.path import join, exists, dirname
from datetime import datetime
import os
import glob
from jaaql.constants import DIR__config, FILE__config, CONFIG_KEY__server, CONFIG_KEY_SERVER__port, ENVIRON__install_path, PORT__ems, PORT__mms, \
    VAULT_KEY__db_crypt_key
from jaaql.config_constants import *
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import create_interface
from jaaql.constants import VAULT_KEY__jaaql_lookup_connection
from jaaql.utilities.crypt_utils import ENCODING__ascii
import configparser
import time
import urllib.parse
from jaaql.utilities.utils_no_project_imports import time_delta_ms  # Do not delete, relied on by others

PATH__migrations = "migrations"


class Profiler:
    def __init__(self, profile_id, do_profiling: bool):
        self.profile_id = profile_id
        self.do_profiling = do_profiling
        self.cur_time = datetime.now()

    def perform_profile(self, description: str):
        if not self.do_profiling:
            return

        cur_time = str(time_delta_ms(self.cur_time, datetime.now()))
        print("PROFILING: " + str(self.profile_id) + " " + cur_time + " " + description)
        self.cur_time = datetime.now()

    def copy(self):
        return Profiler(self.profile_id, self.do_profiling)


def get_jaaql_root() -> str:
    return dirname(dirname(__file__))


def load_root_config(is_gunicorn):
    config_root = get_jaaql_root()
    if is_gunicorn:
        config_root = "/JAAQL-middleware-python/jaaql"

    config = configparser.ConfigParser()
    config.sections()
    config_path = join(config_root, DIR__config, FILE__config).replace("\\", "/")
    if not exists(config_path):
        raise Exception("Could not find config. Please check working directory has access to '" + config_path + "'")
    config.read(config_path)
    return {s: dict(config.items(s)) for s in config.sections()}


def load_config(is_gunicorn, config_path=None):
    config = load_root_config(is_gunicorn)
    if config_path is None:
        config_path = join(DIR__config, FILE__config)
    if exists(config_path):
        override_config = configparser.ConfigParser()
        override_config.sections()
        override_config.read(config_path)
        override_config = {s: dict(override_config.items(s)) for s in override_config.sections()}
        for each, _ in override_config.items():
            if each in config:
                for sub_each, val in override_config[each].items():
                    if sub_each in config[each]:
                        config[each][sub_each] = val
            else:
                config[each] = override_config[each]
    return config


def loc(data: [dict], key: str, val: str):
    return [row for row in data if row[key] == val]


def load_email_templates():
    templates_locs = glob.glob("templates/*.html")
    templates = {}
    for template in templates_locs:
        template = template.replace("\\", "/")
        with open(template, "r") as f:
            templates[".".join(template.split("templates/")[1].split(".")[:-1])] = f.read()
    return templates


def get_base_url(config, is_gunicorn: bool):
    if is_gunicorn:
        return "http+unix://" + urllib.parse.quote(os.environ.get(ENVIRON__install_path) + "/jaaql.sock", safe='')
    else:
        return "http://127.0.0.1:" + str(int(config[CONFIG_KEY__server][CONFIG_KEY_SERVER__port]))


def await_jaaql_bootup(config, is_gunicorn: bool):
    base_url = get_base_url(config, is_gunicorn)
    while True:
        try:
            return requests.get(base_url + "/internal/is_installed").status_code
        except:
            pass
        time.sleep(0.5)


def await_jaaql_installation(config, is_gunicorn: bool):
    base_url = get_base_url(config, is_gunicorn)
    while True:
        try:
            if requests.get(base_url + "/internal/is_installed").status_code == 200:
                break
        except:
            pass
        time.sleep(0.5)


def get_external_url(config):
    return config[CONFIG_KEY__swagger][CONFIG_KEY_SWAGGER__url]


def await_ems_startup():
    while True:
        try:
            if requests.get("http://127.0.0.1:" + str(PORT__ems) + "/").status_code == 200:
                break
        except:
            pass
        time.sleep(5)


def await_migrations_finished():
    while True:
        try:
            if requests.get("http://127.0.0.1:" + str(PORT__mms) + "/").status_code == 200:
                break
        except:
            pass
        time.sleep(5)


def get_jaaql_connection(config, vault):
    jaaql_uri = vault.get_obj(VAULT_KEY__jaaql_lookup_connection)
    address, port, db, username, password = DBInterface.fracture_uri(jaaql_uri)
    return create_interface(config, address, port, db, username, password)


def get_db_connection_as_jaaql(config, vault, db: str):
    jaaql_uri = vault.get_obj(VAULT_KEY__jaaql_lookup_connection)
    address, port, _, username, password = DBInterface.fracture_uri(jaaql_uri)
    return create_interface(config, address, port, db, username, password)


def get_db_crypt_key(vault):
    return vault.get_obj(VAULT_KEY__db_crypt_key).encode(ENCODING__ascii)
