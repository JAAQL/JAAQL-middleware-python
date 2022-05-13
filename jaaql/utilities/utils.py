from datetime import datetime
import requests
from os.path import join, exists, dirname
import glob
from jaaql.constants import DIR__config, FILE__config, CONFIG_KEY__server, CONFIG_KEY_SERVER__port
import configparser

PATH__migrations = "migrations"


def time_delta_ms(start_time: datetime, end_time: datetime) -> int:
    return int(round((end_time - start_time).total_seconds() * 1000))


def get_jaaql_root() -> str:
    return dirname(dirname(__file__))


def load_config(is_gunicorn):
    config_root = get_jaaql_root()
    if is_gunicorn:
        config_root = "/JAAQL-middleware-python/jaaql"

    config = configparser.ConfigParser()
    config.sections()
    config_path = join(config_root, DIR__config, FILE__config)
    if not exists(config_path):
        raise Exception("Could not find config. Please check working directory has access to '" + config_path + "'")
    config.read(config_path)
    return {s: dict(config.items(s)) for s in config.sections()}


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
        return "http://127.0.0.1/api"
    else:
        return "http://127.0.0.1:" + str(int(config[CONFIG_KEY__server][CONFIG_KEY_SERVER__port]))

def await_jaaql_installation(config, is_gunicorn: bool):
    base_url = get_base_url(config, is_gunicorn)
    while True:
        try:
            if requests.get(base_url + "/internal/is_installed").status_code == 200:
                break
        except:
            pass
        time.sleep(5)