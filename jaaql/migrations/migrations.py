import os

from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils import time_delta_ms, get_jaaql_root
from datetime import datetime
from os.path import join
from os import listdir
from monitor.main import initialise, MARKER__bypass, MARKER__jaaql_bypass, DEFAULT_CONNECTION
from jaaql.constants import USERNAME__jaaql, USERNAME__super_db, DB__jaaql, DB__postgres, USERNAME__superuser
from jaaql.mvc.generated_queries import jaaql__select, KG__jaaql__migration_version, jaaql__update


MIGRATION_HISTORY = "migration_history"


QUERY_LOAD_TABLE = "SELECT * FROM %s WHERE project_name = :project_name" % MIGRATION_HISTORY
ATTR_PROJECT_NAME = "project_name"
QUERY_INS_TABLE = "INSERT INTO %s (project_name, installed_rank, version, description, script, checksum, execution_time) VALUES (:project_name, :installed_rank, :version, :description, :script, :checksum, :execution_time)" % MIGRATION_HISTORY
ATTR_INSTALLED_RANK = "installed_rank"
ATTR_VERSION = "version"
ATTR_DESCRIPTION = "description"
ATTR_SCRIPT = "script"
ATTR_CHECKSUM = "checksum"
ATTR_EXECUTION_TIME = "execution_time"
PATH_MIGRATIONS = "migrations"
PATH_SCRIPTS = "scripts"
SCRIPT_MIGRATION_HISTORY = "migration_history.sql"
EXTENSION_JAAQL = ".jaaql"

VERSION_SPLIT = "__"
WORD_SPLIT = "_"


def compare_versions(version1, version2):
    # Split the version strings into major, minor, and patch
    v1_parts = [int(part) for part in version1.split('.')]
    v2_parts = [int(part) for part in version2.split('.')]

    # Pad the versions to ensure both have the same length (e.g., handle cases like '1.0' vs '1.0.0')
    while len(v1_parts) < len(v2_parts):
        v1_parts.append(0)
    while len(v2_parts) < len(v1_parts):
        v2_parts.append(0)

    # Compare major, minor, and patch versions
    for i in range(len(v1_parts)):
        if v1_parts[i] < v2_parts[i]:
            return -1
        elif v1_parts[i] > v2_parts[i]:
            return 1

    return 0


def run_migrations(host: str, bypass_super: str, bypass_jaaql: str, db_interface: DBInterface):
    migration_folder = join(get_jaaql_root(), PATH_MIGRATIONS, PATH_SCRIPTS)
    print("Launching migration manager on folder: " + migration_folder)

    if not os.path.exists(migration_folder):
        print("Couldn't find migrations, this may be okay")
        return

    jaaql_singleton = jaaql__select(db_interface)
    migration_from_version = "0.0.0"
    if KG__jaaql__migration_version in jaaql_singleton:
        migration_from_version = jaaql_singleton[KG__jaaql__migration_version]
        print("Detected migration from version " + migration_from_version)

    script_files = sorted([script_file for script_file in listdir(migration_folder) if
                           script_file.endswith(EXTENSION_JAAQL)])
    for script_file in script_files:
        script_file_version = ".".join(script_file.split(".")[:-1]).split("__")[0]
        if compare_versions(migration_from_version, script_file_version) >= 0:
            print("Migration " + script_file_version + " already installed")
            continue

        print("Installing migration " + script_file_version)

        actual_file_name = join(migration_folder, script_file)

        encoded_configs = [[DEFAULT_CONNECTION, host, USERNAME__jaaql, MARKER__jaaql_bypass + bypass_jaaql, DB__jaaql],
                           [USERNAME__jaaql, host, USERNAME__jaaql, MARKER__jaaql_bypass + bypass_jaaql, DB__jaaql],
                           ["dba", host, USERNAME__jaaql, MARKER__jaaql_bypass + bypass_jaaql, DB__jaaql],
                           ["dba_db", host, USERNAME__jaaql, MARKER__jaaql_bypass + bypass_jaaql, DB__jaaql],
                           [USERNAME__superuser, host, USERNAME__super_db, MARKER__bypass + bypass_super, DB__postgres]]

        start_time = datetime.now()
        initialise(None, configs=[], encoded_configs=encoded_configs, override_url=host,
                   additional_args=["-i", actual_file_name])

        execution_time = time_delta_ms(start_time, datetime.now())
        print("Executed migration " + script_file + " in " + str(execution_time) + "ms")
        jaaql__update(db_interface, migration_version=script_file_version)
