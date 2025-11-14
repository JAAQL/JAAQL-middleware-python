from datetime import datetime
import os
from jaaql.constants import ENVIRON__install_path, TEMPLATES_DEFAULT_DIRECTORY
from os.path import join
from jaaql.exceptions.http_status_exception import HttpStatusException, HttpSingletonStatusException
import requests
from typing import Union
import re

ALLOWABLE_FILE_PATH = r'^[a-zA-Z0-9_\-\/]+(\.[a-zA-Z0-9]+)?$'


def objectify(data, singleton: bool = False):
    if singleton:
        if len(data['rows']) != 1:
            raise HttpSingletonStatusException("Did not return singleton!")
        return dict(zip(data['columns'], data['rows'][0]))
    else:
        return [dict(zip(data['columns'], row)) for row in data['rows']]


def time_delta_ms(start_time: datetime, end_time: datetime) -> int:
    return int(round((end_time - start_time).total_seconds() * 1000))


def load_template(is_container: bool, template_base_url: str, app_relative_path: str):
    if template_base_url is None:
        return None

    if template_base_url is None:
        template_base_url = TEMPLATES_DEFAULT_DIRECTORY

    if check_allowable_file_path(template_base_url):
        raise Exception("Database has been tampered with! Cannot send email")
    if not template_base_url.startswith("https://") and not template_base_url.startswith("http://"):
        if is_container:
            if check_allowable_file_path(template_base_url):
                print(template_base_url)
                raise Exception("Illegal template source directory")
        if template_base_url.startswith("file:///"):
            return open(join(template_base_url.split("file:///")[1].replace("%20", " "), app_relative_path), "r").read()
        else:
            base_path = os.environ.get(ENVIRON__install_path)
            if base_path is None:
                base_path = ""
            template_path = join(base_path, "www", template_base_url, app_relative_path)
            try:
                return open(template_path.replace("\\", "/"), "r").read()
            except FileNotFoundError:
                try:
                    template_path = join(base_path, template_base_url, app_relative_path)
                    return open(template_path.replace("\\", "/"), "r").read()
                except FileNotFoundError:
                    raise HttpStatusException("Could not find template at path '%s'. Are you sure the template is accessible to JAAQL?" % template_path)
    else:
        splitter = "" if template_base_url.endswith("/") else "/"
        return requests.get(template_base_url + splitter + app_relative_path).text


def check_allowable_file_path(uri):
    return re.match(ALLOWABLE_FILE_PATH, uri) is None


def pull_from_dict(self, inputs: dict, keys: Union[list, str, dict]):
    if not isinstance(keys, list) and not isinstance(keys, dict):
        keys = [keys]
    if isinstance(keys, list):
        return {key: inputs[key] for key in keys}
    else:
        return {map_to: inputs[map_from if map_from is not None else map_to] for map_from, map_to in keys.items()}


COOKIE_JAAQL_AUTH = "jaaql_auth"
COOKIE_LOGIN_MARKER = "jaaql_successful_auth"
COOKIE_OIDC = "oidc"
COOKIE_FLAG_HTTP_ONLY = "HttpOnly"
COOKIE_FLAG_SECURE = "Secure"
COOKIE_ATTR_SAME_SITE = "SameSite"
COOKIE_ATTR_EXPIRES = "Expires"
COOKIE_ATTR_MAX_AGE = "Max-Age"
COOKIE_VAL_LAX = "Lax"
COOKIE_VAL_INACTIVITY_15_MINUTES = "900"
COOKIE_EXPIRY_90_DAYS = 90
COOKIE_ATTR_PATH = "Path"

from wsgiref.handlers import format_date_time
from time import mktime
from datetime import timedelta


def get_cookie_attrs(vigilant_sessions: bool, remember_me: bool, is_gunicorn: bool):
    cookie_attrs = {COOKIE_ATTR_SAME_SITE: COOKIE_VAL_LAX}
    cookie_attrs[COOKIE_ATTR_PATH] = "/api" if is_gunicorn else "/"

    if vigilant_sessions:
        cookie_attrs[COOKIE_ATTR_MAX_AGE] = COOKIE_VAL_INACTIVITY_15_MINUTES
    elif remember_me:
        cookie_attrs[COOKIE_ATTR_EXPIRES] = format_date_time(mktime((datetime.now() + timedelta(days=COOKIE_EXPIRY_90_DAYS)).timetuple()))

    return cookie_attrs


def get_sloppy_cookie_attrs():
    cookie_attrs = {}
    cookie_attrs[COOKIE_ATTR_PATH] = "/"

    cookie_attrs[COOKIE_ATTR_EXPIRES] = format_date_time(mktime((datetime.now() + timedelta(minutes=15)).timetuple()))

    return cookie_attrs


def format_cookie(name, value, attributes, is_https: bool):
    cookie_flags = [COOKIE_FLAG_HTTP_ONLY]
    if name == COOKIE_LOGIN_MARKER:
        cookie_flags = []
    if is_https:
        cookie_flags.append(COOKIE_FLAG_SECURE)

    return "; ".join([name + "=" + value] + cookie_flags + [key + "=" + val for key, val in attributes.items()])
