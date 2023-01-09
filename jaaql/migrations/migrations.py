from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils import time_delta_ms, get_jaaql_root, loc, get_base_url, get_external_url
from datetime import datetime
import hashlib
from os.path import join, isdir
from os import listdir, environ
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.db.db_utils import create_interface
from jaaql.utilities.crypt_utils import encrypt_raw
import re
from jaaql.utilities.crypt_utils import AES__iv_length

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

REGEX__migration_replacement = r'{{JAAQL__[A-Z_]+}}'
REGEX__migration_replacement_and_encrypt = r'#{{JAAQL__[A-Z_]+}}'


def load_config_file(location: str) -> (str, str, str):
    ret_role = None
    ret_databases = None
    try:
        the_content = open(location, "r").read()

        if "ROLE=" in the_content:
            ret_role = the_content.split("ROLE=")[1].split("\r")[0].split("\n")[0].strip()
        if "DATABASES=" in the_content:
            ret_databases = the_content.split("DATABASES=")[1].split("\r")[0].split("\n")[0].strip()
    except:
        pass

    return ret_role, ret_databases


def get_config(role: str, folder_role: str, file_role: str, databases: str,
               folder_databases: str, file_databases: str):
    ret_role = "jaaql"
    ret_databases = ["jaaql"]

    if role is not None:
        ret_role = role
    if folder_role is not None:
        ret_role = folder_role
    if file_role is not None:
        ret_role = file_role

    if databases is not None:
        ret_databases = databases.split(",")
    if folder_databases is not None:
        ret_databases = folder_databases.split(",")
    if file_databases is not None:
        ret_databases = file_databases.split(",")

    return ret_role, ret_databases


def create_interface_for_db(config, super_credentials: str, database: str, sub_role: str):
    address, port, _, username, password = DBInterface.fracture_uri(super_credentials)

    return create_interface(config, address, port, database, username, password=password, sub_role=sub_role)


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


def run_migrations(db_interface: DBInterface, is_deployed: bool, project_name: str = None, migration_folder: str = None, config=None,
                   super_credentials: str = None, options: dict = None, key: bytes = None):
    if migration_folder is None:
        migration_folder = join(get_jaaql_root(), PATH_MIGRATIONS)

    base_override_role, base_override_databases = load_config_file(join(migration_folder, "config"))

    if project_name is None:
        project_name = PROJECT_JAAQL

    ij = InterpretJAAQL(db_interface)

    migration_history = None
    conn = db_interface.get_conn()

    statement_load_table = {"query": QUERY_LOAD_TABLE, "parameters": {ATTR_PROJECT_NAME: project_name}}

    dbs = {}

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
        folder_override_role, folder_override_databases = load_config_file(join(migration_folder, version_folder, "config"))

        script_files = sorted([script_file for script_file in listdir(join(migration_folder, version_folder)) if
                               script_file.endswith(EXTENSION_SQL)])
        for script_file in script_files:
            config_file_name = join(migration_folder, version_folder, script_file.split(EXTENSION_SQL)[0] + ".config")
            script_override_role, script_override_databases = load_config_file(config_file_name)
            full_name = version_folder + "/" + script_file
            content = open(join(migration_folder, version_folder, script_file), "r").read()
            cur_role, cur_databases = get_config(base_override_role, folder_override_role, script_override_role,
                                                             base_override_databases, folder_override_databases, script_override_databases)
            content_for_hash = replace_options_environment_variables(content, options, key, is_deployed, config,
                                                                     fixed_salt=True)
            content = replace_options_environment_variables(content, options, key, is_deployed, config,
                                                            fixed_salt=False)

            hash_content = content_for_hash + cur_role + str(cur_databases)
            checksum = hashlib.md5(hash_content.encode("UTF-8")).digest()
            checksum = int.from_bytes(checksum[0:3], byteorder="little")
            if full_name not in installed_scripts:
                start_time = datetime.now()

                for db in cur_databases:
                    if db not in dbs:
                        dbs[db] = create_interface_for_db(config, super_credentials, db, cur_role)
                    update_db_interface = dbs[db]
                    if not hasattr(update_db_interface, "attached_conns"):
                        update_db_interface.attached_conns = {}
                    update_db_interface.sub_role = cur_role
                    if cur_role not in update_db_interface.attached_conns:
                        update_db_interface.attached_conns[cur_role] = update_db_interface.get_conn()
                    update_db_interface.execute_script_file(update_db_interface.attached_conns[cur_role], as_content=content)
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

    for cur_db in dbs.values():
        for cur_conn in cur_db.attached_conns.values():
            cur_db.put_conn(cur_conn)
        cur_db.close()

    db_interface.put_conn(conn)
