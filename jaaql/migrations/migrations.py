import os

from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils import time_delta_ms, get_jaaql_root, loc, get_base_url, get_external_url
from datetime import datetime
import hashlib
from os.path import join, isdir
from os import listdir, environ
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.utilities.crypt_utils import encrypt_raw, AES__iv_length
from jaaql.utilities.utils_no_project_imports import objectify
import re
from monitor.main import initialise, MARKER__bypass, MARKER__jaaql_bypass
from jaaql.constants import USERNAME__jaaql, USERNAME__super_db, DB__jaaql, DB__postgres, USERNAME__superuser


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
EXTENSION_JAAQL = ".jaaql"

VERSION_SPLIT = "__"
WORD_SPLIT = "_"

PROJECT_JAAQL = "JAAQL"

REGEX__migration_replacement = r'{{JAAQL__[A-Z_]+}}'
REGEX__migration_replacement_and_encrypt = r'#{{JAAQL__[A-Z_]+}}'


def replace_options_environment_variables(query: str, parsed_options: dict, crypt_key: bytes, is_deployed: bool, config, fixed_salt: bool):
    last_index = 0
    prepared = ""
    for match in re.finditer(REGEX__migration_replacement_and_encrypt, query):
        start_pos = match.regs[0][0]
        end_pos = match.regs[0][1]
        match_str = query[start_pos + 3 + len("JAAQL__"):end_pos - 2]
        prepared += query[last_index:start_pos]
        last_index = end_pos

        option_match_str = match_str.lower().replace("_", "-")
        if option_match_str in parsed_options:
            to_crypt = parsed_options[option_match_str]
        elif match_str in environ:
            to_crypt = environ[match_str]
        else:
            raise Exception("Missing parameter from migration scripts " + match_str)
        iv = None
        if fixed_salt:
            iv = b"\x00" * AES__iv_length
        prepared += encrypt_raw(crypt_key, to_crypt, iv=iv)

    prepared += query[last_index:]
    query = prepared

    last_index = 0
    prepared = ""
    for match in re.finditer(REGEX__migration_replacement, query):
        start_pos = match.regs[0][0]
        end_pos = match.regs[0][1]
        match_str = query[start_pos + 2 + len("JAAQL__"):end_pos - 2]
        is_quote = match_str.startswith("QUOTE_")
        if is_quote:
            match_str = match_str[len("QUOTE_"):]
        is_double_quote = match_str.startswith("QUOTE_")
        if is_double_quote:
            match_str = match_str[len("DOUBLE_QUOTE_"):]
        prepared += query[last_index:start_pos]
        last_index = end_pos

        option_match_str = match_str.lower().replace("_", "-")
        was_null = False
        if option_match_str in parsed_options:
            to_add = parsed_options[option_match_str]
        elif match_str in environ:
            to_add = environ[match_str]
        elif match_str == "BASE_URL":
            to_add = get_base_url(config, is_deployed)
        elif match_str == "EXTERNAL_URL":
            to_add = get_external_url(config)
        else:
            was_null = True
            to_add = "null"

        if not was_null and is_quote:
            prepared += "'"
        if not was_null and is_double_quote:
            prepared += '"'
        prepared += to_add
        if not was_null and is_quote:
            prepared += "'"
        if not was_null and is_double_quote:
            prepared += '"'

    prepared += query[last_index:]
    return prepared


def run_migrations(host: str, bypass_super: str, bypass_jaaql: str, db_interface: DBInterface, is_deployed: bool, project_name: str = None,
                   migration_folder: str = None, config=None, options: dict = None, key: bytes = None):
    if migration_folder is None:
        migration_folder = join(get_jaaql_root(), PATH_MIGRATIONS)

    if project_name is None:
        project_name = PROJECT_JAAQL

    ij = InterpretJAAQL(db_interface)

    migration_history = None
    conn = db_interface.get_conn()

    statement_load_table = {"query": QUERY_LOAD_TABLE, "parameters": {ATTR_PROJECT_NAME: project_name}}

    try:
        migration_history = objectify(ij.transform(statement_load_table, conn=conn))
    except HttpStatusException:
        print("Migration history table does not exist. Creating")
        db_interface.execute_script_file(conn, join(get_jaaql_root(), PATH_MIGRATIONS, SCRIPT_MIGRATION_HISTORY))
        migration_history = objectify(ij.transform(statement_load_table, conn=conn))

    installed_scripts = [cur[ATTR_SCRIPT] for cur in migration_history]
    cur_installed_rank = ([-1] + sorted([cur[ATTR_INSTALLED_RANK] for cur in migration_history]))[-1]

    version_folders = sorted([version_folder for version_folder in listdir(migration_folder) if
                              isdir(join(migration_folder, version_folder)) and '.' in version_folder])
    for version_folder in version_folders:
        script_files = sorted([script_file for script_file in listdir(join(migration_folder, version_folder)) if
                               script_file.endswith(EXTENSION_JAAQL)])
        for script_file in script_files:
            full_name = version_folder + "/" + script_file
            actual_file_name = join(migration_folder, version_folder, script_file)
            content = open(actual_file_name, "r").read()
            content_for_hash = replace_options_environment_variables(content, options, key, is_deployed, config,
                                                                     fixed_salt=True)
            content = replace_options_environment_variables(content, options, key, is_deployed, config,
                                                            fixed_salt=False)

            hash_content = content_for_hash
            checksum = hashlib.md5(hash_content.encode("UTF-8")).digest()
            checksum = int.from_bytes(checksum[0:3], byteorder="little")
            if full_name not in installed_scripts:
                config_loc = os.environ.get("JAAQL_CONFIG_LOC", "monitor_config")
                configs = []
                for fname in os.listdir(config_loc):
                    config_name = ".".join(fname.split(".")[0:-1])
                    configs.append([config_name, join(config_loc, fname)])

                encoded_configs = [[USERNAME__jaaql, host, USERNAME__jaaql, MARKER__jaaql_bypass + bypass_jaaql, DB__jaaql],
                                   [USERNAME__superuser, host, USERNAME__super_db, MARKER__bypass + bypass_super, DB__postgres]]

                start_time = datetime.now()

                initialise(actual_file_name, content, configs, encoded_configs)

                execution_time = time_delta_ms(start_time, datetime.now())
                version = script_file.split("__")[0][1:]
                description = " ".join(script_file.split(VERSION_SPLIT)[1].split(EXTENSION_JAAQL)[0].split(WORD_SPLIT))
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
