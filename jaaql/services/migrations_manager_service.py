import os
import subprocess

from jaaql.utilities.utils import load_config, get_base_url, await_jaaql_installation, await_jaaql_bootup
from jaaql.constants import ENDPOINT__install, VAULT_KEY__super_local_access_key, ENDPOINT__execute_migrations, \
    PORT__mms, ENVIRON__JAAQL__SUPER_BYPASS_KEY, VAULT_KEY__super_db_password, VAULT_KEY__jaaql_password
from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.utilities.bootstrap_secrets import get_or_seed_vault_secret
from monitor.main import HEADER__security_bypass, initialise as monitor_initialise, MARKER__bypass
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


def _truthy_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().upper() in ("1", "TRUE", "YES", "Y", "ON")


def _resolve_autorun_path(pattern: str) -> str:
    pattern = pattern.strip()
    if pattern.startswith("/"):
        return pattern
    return join("/slurp-in", pattern)


def _read_built_timestamp_from_slurp() -> int | None:
    built_ts_path = "/slurp-in/built_timestamp"
    if not exists(built_ts_path):
        return None
    try:
        return int(open(built_ts_path, "r").read().strip())
    except Exception:
        return None


def _autorun_once_marker_path() -> str:
    return join(DIR__vault, "autorun_pattern.completed")


def _autorun_force_marker_path() -> str:
    return join(DIR__vault, "autorun_pattern.force")


def _has_autorun_completed() -> bool:
    return exists(_autorun_once_marker_path())


def _has_autorun_force_marker() -> bool:
    return exists(_autorun_force_marker_path())


def _clear_autorun_force_marker() -> None:
    marker_path = _autorun_force_marker_path()
    if not exists(marker_path):
        return
    try:
        os.unlink(marker_path)
    except Exception as ex:
        raise RuntimeError(f"Failed removing autorun force marker at {marker_path}: {ex}")


def _write_autorun_completed_marker(pattern: str, built_time: int | None) -> None:
    marker_path = _autorun_once_marker_path()
    try:
        with open(marker_path, "w") as marker_file:
            marker_file.write(f"pattern={pattern}\n")
            if built_time is not None:
                marker_file.write(f"built_timestamp={built_time}\n")
            marker_file.write(f"completed_at={int(time.time())}\n")
    except Exception as ex:
        raise RuntimeError(f"Failed writing autorun completion marker at {marker_path}: {ex}")


def _post_build_time(base_url: str, bypass_header: dict, built_time: int) -> None:
    res = requests.post(base_url + "/build-time", json={"last_successful_build_time": built_time}, headers=bypass_header, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"Could not update build time, status={res.status_code}, body={res.text}")


def _post_set_web_config_if_present(base_url: str, bypass_header: dict) -> None:
    if not (exists("/nginx-mount/nginx.config") or exists("/nginx-mount/nginx.test.config")):
        return
    res = requests.post(base_url + "/internal/set-web-config", headers=bypass_header, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"Could not apply web config, status={res.status_code}, body={res.text}")


def _run_psql_file(file_path: str, username: str, database: str) -> None:
    # Postgres local trust is configured in the container startup flow, so no password is needed.
    result = subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-U", username, "-d", database, "-f", file_path],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql failed for {file_path}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def _run_psql_procedures_from_slurp(autorun_pattern: str) -> None:
    procedures_dir = "/slurp-in/procedures"
    if not exists(procedures_dir):
        return

    file_names = sorted(
        [
            name for name in os.listdir(procedures_dir)
            if os.path.isfile(join(procedures_dir, name))
        ]
    )

    test_files = [f for f in file_names if (".test" in f or ".error" in f)]
    normal_files = [f for f in file_names if f not in test_files]

    is_empty = ".empty.jaaql" in autorun_pattern
    skip_db_tests = _truthy_env("AUTORUN_SKIP_DB_TESTS", default=False) or is_empty or exists("/slurp-in/skip_proc_tests")
    if skip_db_tests:
        test_files = []

    app_database = os.environ.get("AUTORUN_DATABASE", "database")
    jaaql_database = os.environ.get("AUTORUN_JAAQL_DATABASE", "jaaql")

    for file_name in [*normal_files, *test_files]:
        username = "dba" if file_name.endswith("dba") else "jaaql"
        database = app_database if username == "dba" else jaaql_database
        _run_psql_file(join(procedures_dir, file_name), username, database)


def _run_autorun_pattern(base_url: str, bypass_header: dict) -> None:
    pattern = os.environ.get("AUTORUN_PATTERN", "").strip()
    if not pattern:
        return

    autorun_path = _resolve_autorun_path(pattern)
    if not exists(autorun_path):
        raise RuntimeError(f"AUTORUN_PATTERN resolved to missing file: {autorun_path}")

    built_time = _read_built_timestamp_from_slurp()
    force_autorun = _has_autorun_force_marker()
    if (not force_autorun) and _has_autorun_completed():
        print("AUTORUN_PATTERN skipped (completion marker exists)", file=sys.stderr)
        _post_set_web_config_if_present(base_url, bypass_header)
        return
    if force_autorun:
        print("AUTORUN_PATTERN force marker detected", file=sys.stderr)

    print(f"Running AUTORUN_PATTERN={pattern}", file=sys.stderr)

    # AUTORUN bootstrap is intentionally local-only.
    if not (
        base_url.startswith("http+unix://")
        or base_url.startswith("http://127.0.0.1")
        or base_url.startswith("http://localhost")
    ):
        raise RuntimeError(f"AUTORUN_PATTERN refused for non-local base_url: {base_url}")

    bypass_token = bypass_header.get(HEADER__security_bypass)
    if not bypass_token:
        raise RuntimeError("AUTORUN_PATTERN requires a local super bypass token")
    bypass_password = f"{MARKER__bypass}{bypass_token}"

    encoded_configs = [
        ["default", "http://localhost", "super_db", bypass_password, os.environ.get("AUTORUN_DATABASE", "database")],
        ["dba", "http://localhost", "dba", bypass_password, None],
        ["dba_db", "http://localhost", "dba", bypass_password, os.environ.get("AUTORUN_DATABASE", "database")],
        ["jaaql", "http://localhost", "jaaql", bypass_password, os.environ.get("AUTORUN_JAAQL_DATABASE", "jaaql")],
    ]

    additional_args = ["-i", autorun_path]

    param_pairs = [
        ("APPLICATION_BASE_URL", os.environ.get("APPLICATION_BASE_URL")),
        ("DISCOVERY_URL", os.environ.get("DISCOVERY_URL")),
        ("CLIENT_ID", os.environ.get("CLIENT_ID")),
        ("CLIENT_SECRET", os.environ.get("CLIENT_SECRET")),
    ]
    for key, value in param_pairs:
        if value is None or len(value.strip()) == 0:
            continue
        additional_args.extend(["-p", key, value])

    user_federation_file = "/slurp-in/user-federation.jqli"
    if exists(user_federation_file):
        additional_args.extend(["-i", user_federation_file])

    # We avoid process-global env mutation here by passing monitor credentials that use
    # the built-in "bypass <token>" password marker.
    monitor_initialise(
        file_name=None,
        configs=[],
        encoded_configs=encoded_configs,
        override_url=base_url,
        additional_args=additional_args
    )

    _run_psql_procedures_from_slurp(pattern)

    if built_time is not None:
        _post_build_time(base_url, bypass_header, built_time)

    _post_set_web_config_if_present(base_url, bypass_header)
    _write_autorun_completed_marker(pattern, built_time)
    _clear_autorun_force_marker()


def bootup(vault_key, is_gunicorn: bool = False, install_on_bootup: bool = True):
    config = load_config(is_gunicorn)
    install_status = await_jaaql_bootup(config, is_gunicorn)
    base_url = get_base_url(config, is_gunicorn)
    vault = Vault(vault_key, DIR__vault)
    super_db_password = get_or_seed_vault_secret(
        vault, VAULT_KEY__super_db_password, "SUPER_PASSWORD", generate_if_missing=is_gunicorn
    ) or "passw0rd"
    jaaql_password = get_or_seed_vault_secret(
        vault, VAULT_KEY__jaaql_password, "JAAQL_PASSWORD", generate_if_missing=is_gunicorn
    ) or "pa55word"
    super_bypass_key = (get_or_seed_vault_secret(
        vault, VAULT_KEY__super_local_access_key, ENVIRON__JAAQL__SUPER_BYPASS_KEY, generate_if_missing=True
    ) if is_gunicorn else "00000-00000")

    if install_on_bootup and install_status != 200:
        install_key_file = join(dirname(dirname(dirname(__file__))), "install_key")
        while not exists(install_key_file):
            time.sleep(0.1)
        time.sleep(0.5)
        with open(install_key_file, "r") as install_key_file:
            install_key = install_key_file.read().strip()
        json_data = {
            "super_db_password": super_db_password,
            "jaaql_password": jaaql_password,
            "install_key": install_key,
            "allow_uninstall": True
        }
        if not is_gunicorn:
            json_data["db_connection_string"] = "postgresql://postgres:123456@localhost:5434/"
        requests.post(base_url + ENDPOINT__install, json=json_data)

    await_jaaql_installation(config, is_gunicorn)
    bypass_header = {HEADER__security_bypass: super_bypass_key}
    res = requests.post(base_url + ENDPOINT__execute_migrations, headers=bypass_header)

    if res.status_code == 200:
        _run_autorun_pattern(base_url, bypass_header)
        flask_app = create_app()
        print("Created migration manager app host, running flask", file=sys.stderr)
        flask_app.run(port=PORT__mms, host="0.0.0.0", threaded=True)
