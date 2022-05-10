from datetime import datetime
from os.path import dirname
import glob

PATH__migrations = "migrations"


def time_delta_ms(start_time: datetime, end_time: datetime) -> int:
    return int(round((end_time - start_time).total_seconds() * 1000))


def get_jaaql_root() -> str:
    return dirname(dirname(__file__))


def loc(data: [dict], key: str, val: str):
    return [row for row in data if row[key] == val]


def load_email_templates():
    templates_locs = glob.glob("templates/*.html")
    templates = {}
    for template in templates_locs:
        template = template.replace("\\", "/")
        with open(template, "r") as f:
            templates[".".join(template.split("templates/")[1].split(".")[:-1])] = f.read()
