import os
import re
import subprocess

from jaaql.utilities.utils import load_config, get_base_url, await_jaaql_installation, await_jaaql_bootup
from jaaql.constants import ENDPOINT__install, VAULT_KEY__super_local_access_key, ENDPOINT__execute_migrations, \
    PORT__mms, ENVIRON__JAAQL__SUPER_BYPASS_KEY, VAULT_KEY__super_db_password, VAULT_KEY__jaaql_password, \
    USERNAME__superuser, USERNAME__super_db, DB__postgres
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
    # Always connect as postgres — JAAQL roles are typically NOLOGIN and may
    # lack schema privileges.  We run inside the container as root so this is safe.
    result = subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-f", file_path],
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


def _build_encoded_configs(bypass_header: dict) -> list:
    bypass_token = bypass_header.get(HEADER__security_bypass)
    if not bypass_token:
        raise RuntimeError("Requires a local super bypass token")
    bypass_password = f"{MARKER__bypass}{bypass_token}"

    configs = [
        ["default", "http://localhost", "super_db", bypass_password, os.environ.get("AUTORUN_DATABASE", "database")],
        ["dba", "http://localhost", "dba", bypass_password, None],
        ["dba_db", "http://localhost", "dba", bypass_password, os.environ.get("AUTORUN_DATABASE", "database")],
        ["jaaql", "http://localhost", "jaaql", bypass_password, os.environ.get("AUTORUN_JAAQL_DATABASE", "jaaql")],
        [USERNAME__superuser, "http://localhost", USERNAME__super_db, bypass_password, DB__postgres],
        ["user", "http://localhost", "user", bypass_password, None],
    ]

    dispatcher_host = os.environ.get("AUTORUN_DISPATCHER_HOST", "").strip()
    if dispatcher_host:
        configs.append([
            "dispatcher",
            dispatcher_host,
            os.environ.get("AUTORUN_DISPATCHER_USERNAME", ""),
            os.environ.get("AUTORUN_DISPATCHER_PASSWORD", ""),
            None,
        ])

    return configs


def _build_param_args() -> list:
    args = []
    param_pairs = [
        ("APPLICATION_BASE_URL", os.environ.get("APPLICATION_BASE_URL")),
        ("DISCOVERY_URL", os.environ.get("DISCOVERY_URL")),
        ("CLIENT_ID", os.environ.get("CLIENT_ID")),
        ("CLIENT_SECRET", os.environ.get("CLIENT_SECRET")),
    ]
    for key, value in param_pairs:
        if value is None or len(value.strip()) == 0:
            continue
        args.extend(["-p", key, value])
    return args


def _execute_monitor_jaaql(base_url: str, bypass_header: dict, jaaql_files: list) -> None:
    """Run one or more .jaaql files through the monitor CLI with bypass credentials."""
    encoded_configs = _build_encoded_configs(bypass_header)
    import tempfile
    import monitor.main as monitor_mod
    slurp_tmp = tempfile.mkdtemp(prefix="jaaql-slurp-")

    # The monitor's \psql command uses `sudo docker exec` to run psql, which
    # doesn't work inside the container.  Monkey-patch it to call psql directly
    # and point at the actual slurp temp directory (not the hardcoded /slurp-in/).
    _orig_construct = monitor_mod.construct_docker_command

    def _local_psql(_container, sql_path, database):
        actual_path = sql_path.replace("/slurp-in/", slurp_tmp + "/")
        # Strip SET SESSION AUTHORIZATION — we run as postgres directly inside
        # the container, and the named user may lack CREATE on public schema
        # (PostgreSQL 15+ revoked default CREATE from PUBLIC on template0).
        with open(actual_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        with open(actual_path, "w", encoding="utf-8") as fh:
            for line in lines:
                if not line.strip().upper().startswith("SET SESSION AUTHORIZATION"):
                    fh.write(line)
        return ["psql", "-U", "postgres", "-d", database, "-f", actual_path]

    monitor_mod.construct_docker_command = _local_psql

    additional_args = ["--jaaql-slurp-in-location", slurp_tmp]
    for f in jaaql_files:
        additional_args.extend(["-i", f])
    additional_args.extend(_build_param_args())
    try:
        monitor_initialise(
            file_name=None,
            configs=[],
            encoded_configs=encoded_configs,
            override_url=base_url,
            additional_args=additional_args,
        )
    finally:
        monitor_mod.construct_docker_command = _orig_construct


def _discover_handwritten_files(phase: str) -> list:
    """Discover compiled handwritten files for a given phase ('before' or 'after')."""
    handwritten_dir = f"/slurp-in/handwritten/{phase}"
    if not exists(handwritten_dir):
        return []
    return sorted(
        join(handwritten_dir, name)
        for name in os.listdir(handwritten_dir)
        if os.path.isfile(join(handwritten_dir, name))
    )


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

    jaaql_files = [autorun_path]
    user_federation_file = "/slurp-in/user-federation.jqli"
    user_federation_tmp = "/tmp/jaaql-user-federation.jqli"
    if exists(user_federation_file):
        import shutil
        shutil.copy2(user_federation_file, user_federation_tmp)

    _execute_monitor_jaaql(base_url, bypass_header, jaaql_files)

    before_hw = _discover_handwritten_files("before")
    if before_hw:
        print(f"Running {len(before_hw)} handwritten before-procedure files", file=sys.stderr)
        _execute_monitor_jaaql(base_url, bypass_header, before_hw)

    _run_psql_procedures_from_slurp(pattern)

    after_hw = _discover_handwritten_files("after")
    if after_hw:
        print(f"Running {len(after_hw)} handwritten after-procedure files", file=sys.stderr)
        _execute_monitor_jaaql(base_url, bypass_header, after_hw)

    if built_time is not None:
        _post_build_time(base_url, bypass_header, built_time)

    _post_set_web_config_if_present(base_url, bypass_header)
    _write_autorun_completed_marker(pattern, built_time)
    _clear_autorun_force_marker()


DIR__migrations = "/migrations"
MIGRATION_EXTENSIONS = {".sql", ".dba", ".jaaql"}


def _natural_sort_key(filename: str):
    """Sort key that compares numeric parts as integers so 1.10 sorts after 1.9."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", filename)]


def _run_psql_query(query: str, username: str, database: str) -> str:
    # Always connect as postgres — JAAQL roles are typically NOLOGIN and may
    # lack schema privileges.  We run inside the container as root so this is safe.
    result = subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-tAc", query],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql query failed\nQuery: {query}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result.stdout.strip()


def _resolve_migration_jaaql_paths() -> tuple:
    """Derive the migration pt1 and pt2 .jaaql paths from AUTORUN_PATTERN.

    Returns (pt1_path, pt2_path) or (None, None) if AUTORUN_PATTERN is not set.
    """
    pattern = os.environ.get("AUTORUN_PATTERN", "").strip()
    if not pattern:
        return None, None

    autorun_path = _resolve_autorun_path(pattern)
    if autorun_path.endswith(".jaaql"):
        pt1 = autorun_path.replace(".jaaql", ".migration.pt1.jaaql")
    else:
        pt1 = autorun_path + ".migration.pt1.jaaql"
    pt2 = join(dirname(autorun_path), "reset.migration.pt2.jaaql")
    return pt1, pt2


def _run_folder_migration(folder_path: str, folder_name: str,
                          base_url: str, bypass_header: dict,
                          app_database: str) -> None:
    """Execute a full schema-rebuild migration from a folder.

    Required folder contents:
      01.pre-wipe.dba       — backup data into migration schema
      02.post-structure.dba  — restore data after schema rebuild

    Any additional files (03.*.dba, 04.*.sql, etc.) are executed after
    post-structure but before the migration pt2 finalize step, sorted
    naturally.  The same .dba/.sql/.jaaql user rules apply.
    """
    pre_wipe = join(folder_path, "01.pre-wipe.dba")
    post_structure = join(folder_path, "02.post-structure.dba")

    if not exists(pre_wipe):
        raise RuntimeError(f"Folder migration {folder_name}: missing {pre_wipe}")
    if not exists(post_structure):
        raise RuntimeError(f"Folder migration {folder_name}: missing {post_structure}")

    pt1, pt2 = _resolve_migration_jaaql_paths()
    if pt1 is None:
        raise RuntimeError(f"Folder migration {folder_name}: AUTORUN_PATTERN not set, cannot derive migration .jaaql files")
    if not exists(pt1):
        raise RuntimeError(f"Folder migration {folder_name}: migration pt1 not found at {pt1}")
    if not exists(pt2):
        raise RuntimeError(f"Folder migration {folder_name}: migration pt2 not found at {pt2}")

    autorun_pattern = os.environ.get("AUTORUN_PATTERN", "").strip()
    jaaql_database = os.environ.get("AUTORUN_JAAQL_DATABASE", "jaaql")

    # Collect extra files (anything beyond the two required ones).
    reserved = {"01.pre-wipe.dba", "02.post-structure.dba"}
    extra_files = sorted(
        [
            f for f in os.listdir(folder_path)
            if f not in reserved
            and os.path.isfile(join(folder_path, f))
            and os.path.splitext(f)[1].lower() in MIGRATION_EXTENSIONS
        ],
        key=_natural_sort_key,
    )

    # Step 1: Create migration schema.
    print(f"  Creating migration schema", file=sys.stderr)
    _run_psql_query("DROP SCHEMA IF EXISTS migration CASCADE; CREATE SCHEMA migration;",
                    "postgres", app_database)

    # Step 2: Backup data (pre-wipe).
    print(f"  Running pre-wipe: {pre_wipe}", file=sys.stderr)
    _run_psql_file(pre_wipe, "dba", app_database)

    # Step 3: Wipe public schema.
    print(f"  Wiping public schema", file=sys.stderr)
    _run_psql_query(
        "SET search_path = public, pg_catalog; "
        "DROP EXTENSION IF EXISTS plpgsql_check; "
        "DROP SCHEMA IF EXISTS public CASCADE; "
        "CREATE SCHEMA public; "
        "GRANT USAGE, CREATE ON SCHEMA public TO PUBLIC; "
        "CREATE EXTENSION IF NOT EXISTS plpgsql_check SCHEMA public;",
        "postgres", app_database,
    )

    # Step 4: Rebuild schema from data model (migration pt1).
    print(f"  Rebuilding schema via migration pt1: {pt1}", file=sys.stderr)
    _execute_monitor_jaaql(base_url, bypass_header, [pt1])

    # Step 5: Re-install procedures.
    print(f"  Re-installing procedures", file=sys.stderr)
    _run_psql_procedures_from_slurp(autorun_pattern)

    # Step 6: Restore data (post-structure).
    print(f"  Running post-structure: {post_structure}", file=sys.stderr)
    _run_psql_file(post_structure, "dba", app_database)

    # Step 7: Run any extra files in the folder.
    for extra in extra_files:
        ext = os.path.splitext(extra)[1].lower()
        if ext in (".sql", ".dba"):
            username = "dba"
            database = app_database
        else:
            username = "jaaql"
            database = jaaql_database
        print(f"  Running extra migration file: {extra} (user={username}, db={database})", file=sys.stderr)
        _run_psql_file(join(folder_path, extra), username, database)

    # Step 8: Finalize (migration pt2 — references + vacuum).
    print(f"  Finalizing via migration pt2: {pt2}", file=sys.stderr)
    _execute_monitor_jaaql(base_url, bypass_header, [pt2])

    # Step 9: Drop migration schema.
    print(f"  Dropping migration schema", file=sys.stderr)
    _run_psql_query("DROP SCHEMA IF EXISTS migration CASCADE;", "postgres", app_database)


def _run_app_migrations(base_url: str, bypass_header: dict) -> None:
    if not exists(DIR__migrations):
        return

    app_database = os.environ.get("AUTORUN_DATABASE", "database")
    jaaql_database = os.environ.get("AUTORUN_JAAQL_DATABASE", "jaaql")

    # Discover top-level entries: files with supported extensions, and non-underscore folders.
    all_entries = os.listdir(DIR__migrations)
    migration_entries = []
    for name in all_entries:
        full_path = join(DIR__migrations, name)
        if os.path.isfile(full_path) and os.path.splitext(name)[1].lower() in MIGRATION_EXTENSIONS:
            migration_entries.append(("file", name))
        elif os.path.isdir(full_path) and not name.startswith("_"):
            migration_entries.append(("folder", name))

    migration_entries.sort(key=lambda e: _natural_sort_key(e[1]))

    if not migration_entries:
        return

    print(f"App migrations: found {len(migration_entries)} entry/entries in {DIR__migrations}", file=sys.stderr)

    # Ensure tracking table exists (idempotent).
    _run_psql_query(
        "CREATE TABLE IF NOT EXISTS migration_history ("
        "script TEXT PRIMARY KEY, "
        "executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
        ");",
        "dba",
        app_database,
    )

    # Load already-executed migrations.
    raw = _run_psql_query("SELECT script FROM migration_history;", "dba", app_database)
    executed = set(raw.splitlines()) if raw else set()

    for entry_type, name in migration_entries:
        if name in executed:
            print(f"App migration already applied: {name}", file=sys.stderr)
            continue

        if entry_type == "file":
            ext = os.path.splitext(name)[1].lower()
            if ext in (".sql", ".dba"):
                username = "dba"
                database = app_database
            else:
                username = "jaaql"
                database = jaaql_database

            print(f"Applying file migration: {name} (user={username}, db={database})", file=sys.stderr)
            _run_psql_file(join(DIR__migrations, name), username, database)
        else:
            print(f"Applying folder migration: {name} (full schema rebuild)", file=sys.stderr)
            _run_folder_migration(join(DIR__migrations, name), name, base_url, bypass_header, app_database)

        # Record successful execution.
        safe_name = name.replace("'", "''")
        _run_psql_query(
            f"INSERT INTO migration_history (script) VALUES ('{safe_name}');",
            "dba",
            app_database,
        )
        print(f"App migration applied: {name}", file=sys.stderr)

    print("App migrations complete", file=sys.stderr)


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
        _run_app_migrations(base_url, bypass_header)
        flask_app = create_app()
        print("Created migration manager app host, running flask", file=sys.stderr)
        flask_app.run(port=PORT__mms, host="0.0.0.0", threaded=True)
