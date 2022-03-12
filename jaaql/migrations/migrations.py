from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils import time_delta_ms, get_jaaql_root, loc
from datetime import datetime
import hashlib
from os.path import join, isdir
from os import listdir
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.exceptions.http_status_exception import HttpStatusException

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
SCRIPT_MIGRATION_HISTORY = "migration_history.sql"
EXTENSION_SQL = ".sql"

VERSION_SPLIT = "__"
WORD_SPLIT = "_"

PROJECT_JAAQL = "JAAQL"


def run_migrations(db_interface: DBInterface, project_name: str = None, migration_folder: str = None,
                   update_db_interface: DBInterface = None):
    if migration_folder is None:
        migration_folder = join(get_jaaql_root(), PATH_MIGRATIONS)

    if update_db_interface is None:
        update_db_interface = db_interface

    if project_name is None:
        project_name = PROJECT_JAAQL

    ij = InterpretJAAQL(db_interface)

    migration_history = None
    conn = db_interface.get_conn()

    statement_load_table = {"query": QUERY_LOAD_TABLE, "parameters": {ATTR_PROJECT_NAME: project_name}}

    try:
        migration_history = db_interface.objectify(ij.transform(statement_load_table, conn=conn))
    except HttpStatusException:
        print("Migration history table does not exist. Creating")
        db_interface.execute_script_file(conn, join(get_jaaql_root(), PATH_MIGRATIONS, SCRIPT_MIGRATION_HISTORY))
        migration_history = db_interface.objectify(ij.transform(statement_load_table, conn=conn))

    installed_scripts = [cur[ATTR_SCRIPT] for cur in migration_history]
    cur_installed_rank = ([-1] + sorted([cur[ATTR_INSTALLED_RANK] for cur in migration_history]))[-1]

    version_folders = sorted([version_folder for version_folder in listdir(migration_folder) if
                              isdir(join(migration_folder, version_folder)) and '.' in version_folder])
    for version_folder in version_folders:
        script_files = sorted([script_file for script_file in listdir(join(migration_folder, version_folder)) if
                               script_file.endswith(EXTENSION_SQL)])
        for script_file in script_files:
            full_name = version_folder + "/" + script_file
            content = open(join(migration_folder, version_folder, script_file), "r").read()
            checksum = hashlib.md5(content.encode("UTF-8")).digest()
            checksum = int.from_bytes(checksum[0:3], byteorder="little")
            if full_name not in installed_scripts:
                start_time = datetime.now()
                update_db_interface.execute_script_file(conn, join(migration_folder, version_folder, script_file))
                execution_time = time_delta_ms(start_time, datetime.now())
                version = script_file.split("__")[0][1:]
                description = " ".join(script_file.split(VERSION_SPLIT)[1].split(EXTENSION_SQL)[0].split(WORD_SPLIT))
                ij.transform({
                    "query": QUERY_INS_TABLE,
                    "parameters": {
                        ATTR_PROJECT_NAME: project_name,
                        ATTR_INSTALLED_RANK: cur_installed_rank + 1,
                        ATTR_VERSION: version,
                        ATTR_DESCRIPTION: description,
                        ATTR_SCRIPT: full_name,
                        ATTR_CHECKSUM: checksum,
                        ATTR_EXECUTION_TIME: execution_time
                    }
                }, conn=conn)
                cur_installed_rank += 1
            else:
                existing_checksum = loc(migration_history, ATTR_SCRIPT, full_name)
                existing_checksum = loc(existing_checksum, ATTR_PROJECT_NAME, project_name)[0][ATTR_CHECKSUM]
                if checksum != existing_checksum:
                    raise Exception("Migration mismatch for " + script_file + ". Locally calculated checksum " + str(
                        checksum) + " yet in db table found " + str(existing_checksum))

    db_interface.put_conn(conn)
