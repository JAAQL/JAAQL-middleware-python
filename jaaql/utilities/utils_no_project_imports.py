from datetime import datetime
import os
from jaaql.constants import ENVIRON__install_path
from os.path import join
import requests
from typing import Union


def time_delta_ms(start_time: datetime, end_time: datetime) -> int:
    return int(round((end_time - start_time).total_seconds() * 1000))


def load_artifact(is_container: bool, artifact_base_uri: str, app_relative_path: str):
    if app_relative_path is None:
        return None

    if check_allowable_file_path(app_relative_path):
        raise Exception("Database has been tampered with! Cannot send email")
    if not app_relative_path.endswith(".html"):
        app_relative_path = app_relative_path + ".html"
    if not artifact_base_uri.startswith("https://") and not artifact_base_uri.startswith("http://"):
        if is_container:
            if check_allowable_file_path(artifact_base_uri):
                print(artifact_base_uri)
                raise Exception("Illegal artifact base url")
        if artifact_base_uri.startswith("file:///"):
            return open(join(artifact_base_uri.split("file:///")[1].replace("%20", " "), app_relative_path), "r").read()
        else:
            return open(join(os.environ[ENVIRON__install_path], "www", artifact_base_uri, app_relative_path), "r").read()
    else:
        splitter = "" if artifact_base_uri.endswith("/") else "/"
        return requests.get(artifact_base_uri + splitter + app_relative_path).text


def check_allowable_file_path(uri):
    return not isinstance(uri, str) or any([not letter.isalnum() and letter not in ['-', '_', '/'] for letter in uri])


def pull_from_dict(self, inputs: dict, keys: Union[list, str, dict]):
    if not isinstance(keys, list) and not isinstance(keys, dict):
        keys = [keys]
    if isinstance(keys, list):
        return {key: inputs[key] for key in keys}
    else:
        return {map_to: inputs[map_from if map_from is not None else map_to] for map_from, map_to in keys.items()}
