from datetime import datetime
import os
from jaaql.constants import ENVIRON__install_path, ARTIFACTS_DEFAULT_DIRECTORY
from os.path import join
from jaaql.exceptions.http_status_exception import HttpStatusException
import requests
from typing import Union
import re

ALLOWABLE_FILE_PATH = r'^[a-z0-9_\-\/]+(\.[a-zA-Z0-9]+)?$'


def objectify(data, singleton: bool = False):
    if singleton:
        return dict(zip(data['columns'], data['rows'][0]))
    else:
        return [dict(zip(data['columns'], row)) for row in data['rows']]


def time_delta_ms(start_time: datetime, end_time: datetime) -> int:
    return int(round((end_time - start_time).total_seconds() * 1000))


def load_artifact(is_container: bool, artifact_base_url: str, app_relative_path: str):
    if app_relative_path is None:
        return None

    if artifact_base_url is None:
        artifact_base_url = ARTIFACTS_DEFAULT_DIRECTORY

    if check_allowable_file_path(app_relative_path):
        raise Exception("Database has been tampered with! Cannot send email")
    if not artifact_base_url.startswith("https://") and not artifact_base_url.startswith("http://"):
        if is_container:
            if check_allowable_file_path(artifact_base_url):
                print(artifact_base_url)
                raise Exception("Illegal artifact source directory")
        if artifact_base_url.startswith("file:///"):
            return open(join(artifact_base_url.split("file:///")[1].replace("%20", " "), app_relative_path), "r").read()
        else:
            base_path = os.environ.get(ENVIRON__install_path)
            if base_path is None:
                base_path = ""
            template_path = join(base_path, "www", artifact_base_url, app_relative_path)
            try:
                return open(template_path.replace("\\", "/"), "r").read()
            except FileNotFoundError:
                raise HttpStatusException("Could not find template at path '%s'. Are you sure the template is accessible to JAAQL?" % template_path)
    else:
        splitter = "" if artifact_base_url.endswith("/") else "/"
        return requests.get(artifact_base_url + splitter + app_relative_path).text


def check_allowable_file_path(uri):
    return re.match(ALLOWABLE_FILE_PATH, uri) is None


def pull_from_dict(self, inputs: dict, keys: Union[list, str, dict]):
    if not isinstance(keys, list) and not isinstance(keys, dict):
        keys = [keys]
    if isinstance(keys, list):
        return {key: inputs[key] for key in keys}
    else:
        return {map_to: inputs[map_from if map_from is not None else map_to] for map_from, map_to in keys.items()}
