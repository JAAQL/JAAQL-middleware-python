import sys

from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.db.db_interface import DBInterface
import jaaql.utilities.crypt_utils as crypt_utils
from jaaql.migrations.migrations import run_migrations
from jaaql.email.email_manager import EmailManager
from jaaql.db.db_utils import execute_supplied_statement, create_interface

from jaaql.constants import *
from jaaql.config_constants import *
from os.path import dirname

import uuid
import traceback
import subprocess
import json
import time
import os
from os.path import join

from jaaql.exceptions.http_status_exception import *
from typing import Union

CONFIG_KEY_security = "SECURITY"
CONFIG_KEY_SECURITY__mfa_label = "mfa_label"
CONFIG_KEY_SECURITY__mfa_issuer = "mfa_issuer"
CONFIG_KEY_SECURITY__do_audit = "do_audit"
CONFIG_KEY_SECURITY__token_expiry_ms = "token_expiry_ms"
CONFIG_KEY_SECURITY__token_refresh_expiry_ms = "token_refresh_expiry_ms"

DELETION_KEY__cooldown_removal = 0.1
DELETION_KEY__default_expiry_seconds = 30

ERR__expected_matcher = "'like' or '='"
ERR__expected_attribute = "attribute name"
ERR__expected_operand = "operand"
ERR__expected_logic = "'AND' or 'OR'"

ERR__expected_parser = "Expected %s in search parameter not '%s'"
ERR__deletion_invalid_key = "Deletion key invalid. Either didn't exist or expired"
ERR__deletion_key_expired = "Deletion key expired"
ERR__missing_page_size = "Cannot provide one or the other for page/size. Please provide both or neither"
ERR__unexpected_paren_close = "Cannot process ')' in search as no associated '('"
ERR__unexpected_parse_err = "Unexpected error whilst parsing search string. Please inspect"
ERR__unsupported_direction = "Sort direction should be ASC, DESC or left empty"
ERR__unsupported_column_names = "Please format sorts like 'colname ASC,othercol DESC'. Spaced columns not yet supported"
ERR__unexpected_quote = "Unexpected single quote. Only usable within the operand (after 'like' or '=')"

EXPECTING__attr = 0
EXPECTING__matcher = 1
EXPECTING__operand = 2
EXPECTING__logic = 3
EXPECTING__total = 4

WHERE__id = "where_query_"

KEY__db_crypt_key = "db_crypt_key"

VAULT_KEY__jwt_crypt_key = "jwt_crypt_key"
VAULT_KEY__jwt_obj_crypt_key = "jwt_obj_crypt_key"

FILE__was_installed = "was_installed"

JWT__data = "data"

WARNING__uninstall_allowed = "Due to installation parameters, the system can be uninstalled completely via the API. We do not recommend this being " \
                             "used in production systems (the super user db password is required to perform uninstallation so it is not 'open') "

DIR__apps = "apps"
SEPARATOR__dir = "/"


class JAAQLPivotData:
    def __init__(self, level_data: list, matching: list = None):
        self.matching = matching
        self.level_data = level_data
        self.matching = matching

        self.copy_from_idx = None
        self.copy_to_idx = None

        self.check_idxs = None


class JAAQLPivotInfo:
    def __init__(self, name, keys: [str], on: str):
        self.name = name
        self.keys = keys
        if isinstance(keys, str):
            self.keys = [keys]
        self.on = on
        if not self.on.startswith(self.name + "_"):
            self.on = self.name + "_" + self.on


class BaseJAAQLModel:

    def splice_into(self, x: [dict], y: [dict]):
        for i in range(len(x)):
            missing_dict_fields = [key for key in y[i].keys() if key not in x[i]]
            matching_dict_fields = [key for key in y[i].keys() if key in x[i]]
            for missing in missing_dict_fields:
                x[i][missing] = y[i][missing]
            for matching in matching_dict_fields:
                if isinstance(x[i][matching], list):
                    self.splice_into(x[i][matching], y[i][matching])

    def exit_jaaql(self):
        """
        Will terminate the worker forcefully which fires a hook in gunicorn_config.py
        This hook reloads all workers if the file exists in vault
        :return:
        """
        if self.is_container:
            open(join(DIR__vault, FILE__was_installed), 'a').close()
        if os.environ.get(ENVIRON__install_path, "").strip() == "/component-test-project":
            pid = open("app.pid", "r").read()
            subprocess.call("kill -HUP " + pid, shell=True)  # Kill gunicorn so coverage report is generated
        else:
            time.sleep(1)
            os._exit(0)

    def pivot(self, data: [dict], pivot_info: [JAAQLPivotInfo]):
        if len(data) == 0:
            return data
        if not isinstance(pivot_info, list):
            pivot_info = [pivot_info]

        ret = []
        stack = [JAAQLPivotData(ret)]
        cols = list(data[0].keys())

        for row in data:
            copy_from_idx = 0
            last_pivot_length = -1
            for pivot, pivot_idx in zip(pivot_info, range(len(pivot_info))):
                copy_to_idx = cols.index(pivot.on)

                level_data = {key[last_pivot_length + 1:]: val for key, val in row.items() if copy_from_idx <=
                              cols.index(key) < copy_to_idx}
                matching = [level_data[key[last_pivot_length + 1:]] for key in pivot.keys]
                is_empty = len([match for match in matching if match is not None]) == 0

                cur = stack[pivot_idx]
                sub_list = cur.level_data
                if cur.matching != matching:
                    if not is_empty:
                        sub_list.append(level_data)
                    cur.matching = matching
                    stack = stack[0:pivot_idx + 1]

                    new_data = []
                    level_data[pivot.name] = new_data
                    stack.append(JAAQLPivotData(new_data))

                copy_from_idx = copy_to_idx
                last_pivot_length = len(pivot.name)

            cur = stack[-1]
            final_data = {key[last_pivot_length + 1:]: val for key, val in row.items() if copy_from_idx <=
                          cols.index(key)}
            is_empty = len([key for key in final_data if final_data[key] is not None]) == 0
            if not is_empty:
                cur.level_data.append(final_data)

        return ret

    def set_jaaql_lookup_connection(self):
        if self.vault.has_obj(VAULT_KEY__jaaql_lookup_connection):
            jaaql_uri = self.vault.get_obj(VAULT_KEY__jaaql_lookup_connection)
            address, port, db, username, password = DBInterface.fracture_uri(jaaql_uri)
            self.jaaql_lookup_connection = create_interface(self.config, address, port, db, username, password, is_jaaql_user=True)

    def __init__(self, config, vault_key: str, migration_db_interface=None, migration_project_name: str = None,
                 migration_folder: str = None, is_container: bool = False, url: str = None):
        self.config = config
        self.migration_db_interface = migration_db_interface
        self.migration_project_name = migration_project_name
        self.migration_folder = migration_folder
        self.is_container = is_container

        self.url = url
        self.has_installed = False

        self.force_mfa = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__force_mfa]
        self.do_audit = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__do_audit]
        self.invite_only = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__invite_only]

        self.vault = Vault(vault_key, DIR__vault)
        self.jaaql_lookup_connection = None
        self.email_manager = None

        self.token_expiry_ms = int(config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__token_expiry_ms])
        self.refresh_expiry_ms = int(config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__token_refresh_expiry_ms])

        if not self.vault.has_obj(VAULT_KEY__db_repeatable_salt):
            self.vault.insert_obj(VAULT_KEY__db_repeatable_salt, crypt_utils.fetch_random_readable_salt().decode(crypt_utils.ENCODING__ascii))

        if not self.vault.has_obj(VAULT_KEY__db_crypt_key):
            _, db_crypt_key = crypt_utils.key_stretcher(str(uuid.uuid4()), length=crypt_utils.AES__key_length)
            self.vault.insert_obj(VAULT_KEY__db_crypt_key, db_crypt_key.decode(crypt_utils.ENCODING__ascii))

        if not self.vault.has_obj(VAULT_KEY__jwt_crypt_key):
            _, jwt_crypt_key = crypt_utils.key_stretcher(str(uuid.uuid4()))
            self.vault.insert_obj(VAULT_KEY__jwt_crypt_key, jwt_crypt_key.decode(crypt_utils.ENCODING__ascii))

        if not self.vault.has_obj(VAULT_KEY__jwt_obj_crypt_key):
            _, jwt_obj_crypt_key = crypt_utils.key_stretcher(str(uuid.uuid4()))
            self.vault.insert_obj(VAULT_KEY__jwt_obj_crypt_key, jwt_obj_crypt_key.decode(crypt_utils.ENCODING__ascii))

        if self.vault.has_obj(VAULT_KEY__jaaql_lookup_connection):
            if self.vault.has_obj(VAULT_KEY__allow_jaaql_uninstall):
                self.uninstall_key = str(uuid.uuid4())
                print(WARNING__uninstall_allowed, file=sys.stderr)
                print("UNINSTALL KEY: " + self.uninstall_key)
            else:
                self.install_key = None
            self.has_installed = True

        self.set_jaaql_lookup_connection()
        if self.vault.has_obj(VAULT_KEY__jaaql_lookup_connection):
            run_migrations(self.jaaql_lookup_connection)

            if self.migration_db_interface is None:
                self.migration_db_interface = self.jaaql_lookup_connection

            run_migrations(self.jaaql_lookup_connection, migration_project_name, migration_folder=migration_folder,
                           update_db_interface=self.migration_db_interface)

            if self.is_container:
                self.jaaql_lookup_connection.close(force=True)  # Each individual class will have one

            self.email_manager = EmailManager()
        else:
            self.install_key = str(uuid.uuid4())
            with open(os.path.join(dirname(dirname(dirname(__file__))), "install_key"), "w") as install_key_file:
                install_key_file.write(self.install_key)
            print("INSTALL KEY: " + self.install_key)

        if not self.vault.has_obj(VAULT_KEY__jaaql_local_access_key):
            self.vault.insert_obj(VAULT_KEY__jaaql_local_access_key, str(uuid.uuid4()))

        self.local_access_key = self.vault.get_obj(VAULT_KEY__jaaql_local_access_key)

    def get_db_crypt_key(self):
        return self.vault.get_obj(VAULT_KEY__db_crypt_key).encode(crypt_utils.ENCODING__ascii)

    def get_repeatable_salt(self):
        return self.vault.get_obj(VAULT_KEY__db_repeatable_salt).encode(crypt_utils.ENCODING__ascii)

    def setup_paging_parameters(self, inputs: dict, has_deleted: bool = True):
        inputs_no_del = inputs.copy()
        if KEY__show_deleted in inputs_no_del:
            inputs_no_del.pop(KEY__show_deleted)
        paging_dict, parameters = self.format_paging_request(inputs_no_del)

        if has_deleted:
            show_deleted = inputs.get(KEY__show_deleted, False)
            deleted_condition = ATTR__deleted + SEPARATOR__space + SQL__is_null
            if paging_dict[SQL__where] is None and not show_deleted:
                paging_dict[SQL__where] = deleted_condition
            elif paging_dict[SQL__where] is not None and not show_deleted:
                existing = SQL__paren_open + paging_dict[SQL__where] + SQL__paren_close
                paging_dict[SQL__where] = existing + SEPARATOR__space + SQL__and + SEPARATOR__space + deleted_condition

        return paging_dict, parameters

    def get_default_app_url(self):
        return self.url + SEPARATOR__dir + DIR__apps

    def replace_default_app_url(self, url_with_default: str):
        if url_with_default is None:
            return None
        return url_with_default.replace("{{DEFAULT}}", self.get_default_app_url())

    def execute_paging_query(self, jaaql_connection: DBInterface, full_query: str, count_query: str, parameters: dict,
                             where_query: str, where_parameters: dict, decrypt_columns: list = None,
                             encryption_key: bytes = None):
        data = execute_supplied_statement(jaaql_connection, full_query, parameters=parameters,
                                          as_objects=True, decrypt_columns=decrypt_columns,
                                          encryption_key=encryption_key)
        total = execute_supplied_statement(jaaql_connection, count_query, as_objects=True)
        total = total[0]["count"]
        total_filtered = execute_supplied_statement(jaaql_connection, count_query + where_query,
                                                    parameters=where_parameters,
                                                    as_objects=True)[0]["count"]
        return self.paged_collection(total, total_filtered, data)

    @staticmethod
    def paged_collection(total: int, filtered: int, data: list):
        return {
            KEY__records_total: total,
            KEY__records_filtered: filtered,
            KEY__data: data
        }

    @staticmethod
    def construct_paging_queries(http_inputs: dict) -> (str, str, dict, dict):
        formatted, parameters = BaseJAAQLModel.format_paging_request(http_inputs)
        qa, qaw, wp = BaseJAAQLModel.construct_formatted_paging_queries(formatted, parameters)
        return qa, qaw, wp, parameters

    @staticmethod
    def construct_formatted_paging_queries(paging_input: dict, paging_parameters: dict) -> (str, str, dict):
        query_addition = ""
        query_addition_where = ""

        if paging_input[SQL__where] is not None:
            query_addition += SEPARATOR__space + SQL__where + SEPARATOR__space + paging_input[SQL__where]
            query_addition_where = query_addition
        if paging_input[SQL__order_by] is not None:
            query_addition += SEPARATOR__space + SQL__order_by + SEPARATOR__space + paging_input[SQL__order_by]
        if paging_input[SQL__limit] is not None:
            query_addition += SEPARATOR__space + SQL__limit + SEPARATOR__space + str(paging_input[SQL__limit])
        if paging_input[SQL__offset] is not None:
            query_addition += SEPARATOR__space + SQL__offset + SEPARATOR__space + str(paging_input[SQL__offset])

        where_params = {}
        for param in paging_parameters.keys():
            if param.startswith(WHERE__id):
                where_params[param] = paging_parameters[param]

        return query_addition, query_addition_where, where_params

    @staticmethod
    def format_paging_request(http_inputs: dict) -> (dict, dict):
        sort_input = http_inputs.get(KEY__sort, "")
        if sort_input is None:
            sort_input = ""
        sort_broken = sort_input.replace(SEPARATOR__comma_space, SEPARATOR__comma).split(SEPARATOR__comma)
        all_parameters = {}
        order_query = []

        for cur_sort in sort_broken:
            cur_broken = cur_sort.split(SEPARATOR__space)
            if len(cur_broken) == 1:
                direction = SQL__asc
            elif len(cur_broken) > 2:
                raise HttpStatusException(ERR__unsupported_column_names)
            else:
                direction = cur_broken[1]

            direction = direction.upper()
            if direction not in [SQL__asc, SQL__desc]:
                raise HttpStatusException(ERR__unsupported_direction)

            column = cur_broken[0]
            order_query.append(SQL__double_quote + column + SQL__double_quote + SEPARATOR__space + direction)

        built_order = SEPARATOR__comma_space.join(order_query)
        if len(sort_input) == 0:
            order_query = []

        if KEY__size not in http_inputs or http_inputs[KEY__size] is None:
            size = None
        else:
            # Int not strictly needed as type checking is already done at the documentation level. This is merely
            # defensive as this method could be abused by an extension
            size = int(http_inputs[KEY__size])

        if KEY__page not in http_inputs or http_inputs[KEY__page] is None:
            page = None
        else:
            page = int(http_inputs[KEY__page])

        if (page is None and size is not None) or (page is not None and size is None):
            raise HttpStatusException(ERR__missing_page_size)

        offset = None
        if page is not None:
            offset = page * size

        try:
            where_str = BaseJAAQLModel.parse_where(http_inputs.get(KEY__search, ""), all_parameters)
        except HttpStatusException as err:
            raise err
        except Exception as err:
            traceback.print_tb(err.__traceback__)
            raise HttpStatusException(ERR__unexpected_parse_err)

        if KEY__db_crypt_key in http_inputs:
            all_parameters[KEY__db_crypt_key] = http_inputs[KEY__db_crypt_key]

        return {
                   SQL__where: where_str,
                   SQL__order_by: None if len(order_query) == 0 else built_order,
                   SQL__limit: size,
                   SQL__offset: offset
               }, all_parameters

    @staticmethod
    def check_parse_state(cur_token: str, expected_state: Union[int, list], actual_state: int):
        if isinstance(expected_state, int):
            expected_state = [expected_state]

        if actual_state in expected_state:
            return

        expected_err = []
        for expected in expected_state:
            if expected == EXPECTING__logic:
                expected_err.append(ERR__expected_logic)
            elif expected == EXPECTING__operand:
                expected_err.append(ERR__expected_operand)
            elif expected == EXPECTING__attr:
                expected_err.append(ERR__expected_attribute)
            else:
                expected_err.append(ERR__expected_matcher)

        spaced_or = SEPARATOR__space + SQL__or + SEPARATOR__space

        raise HttpStatusException(ERR__expected_parser % (spaced_or.join(expected_err), cur_token))

    @staticmethod
    def parse_where_token(parse_parameters: dict, parameters: dict):
        and_separated = SEPARATOR__space + SQL__and + SEPARATOR__space
        or_separated = SEPARATOR__space + SQL__or + SEPARATOR__space

        if parse_parameters["cur_token"].upper() == SQL__and:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], EXPECTING__logic, parse_parameters["state"])
            parse_parameters["cur_search"] += and_separated
        elif parse_parameters["cur_token"].upper() == SQL__or:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], EXPECTING__logic, parse_parameters["state"])
            parse_parameters["cur_search"] += or_separated
        elif parse_parameters["cur_token"] == SQL__paren_open:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], EXPECTING__attr, parse_parameters["state"])
            parse_parameters["paren_depth"] += 1
            parse_parameters["cur_search"] += "("
        elif parse_parameters["cur_token"] == SQL__paren_close:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], EXPECTING__logic, parse_parameters["state"])
            if parse_parameters["paren_depth"] == 0:
                raise HttpStatusException(ERR__unexpected_paren_close)
            parse_parameters["paren_depth"] -= 1
            parse_parameters["cur_search"] += ")"
        elif parse_parameters["cur_token"].upper() == SQL__like:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], EXPECTING__matcher,
                                             parse_parameters["state"])
            parse_parameters["cur_search"] += SEPARATOR__space + SQL__like + SEPARATOR__space
        elif parse_parameters["cur_token"] == SQL__eq:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], EXPECTING__matcher,
                                             parse_parameters["state"])
            parse_parameters["cur_search"] += SEPARATOR__space + SQL__eq + SEPARATOR__space
        else:
            BaseJAAQLModel.check_parse_state(parse_parameters["cur_token"], [EXPECTING__attr, EXPECTING__operand],
                                             parse_parameters["state"])

            if parse_parameters["state"] == EXPECTING__operand:
                where_id = WHERE__id + str(parse_parameters["param_num"])
                parameters[where_id] = parse_parameters["cur_token"]

                arg_marker = JAAQL__arg_marker + where_id
                as_attr_operand = SQL__lower + SQL__paren_open + arg_marker + SQL__paren_close + SQL__varchar_cast
                parse_parameters["param_num"] += 1
                parse_parameters["cur_search"] += as_attr_operand
            else:
                # TODO potential SQL injection issue. Is the user able to pass spaces in that don't look like spaces
                # TODO can we bind column names
                quoted = SQL__double_quote + parse_parameters["cur_token"] + SQL__double_quote + SQL__varchar_cast
                parse_parameters["cur_search"] += SQL__lower + SQL__paren_open + quoted + SQL__paren_close

        parse_parameters["state"] += 1
        parse_parameters["state"] %= EXPECTING__total

        parse_parameters["cur_token"] = ""

    @staticmethod
    def parse_where(search_str: str, parameters: dict):
        parse_parameters = {
            "cur_search": "",
            "cur_token": "",
            "state": EXPECTING__attr,
            "paren_depth": 0,
            "quote_char": None,
            "param_num": 0
        }

        if search_str is None:
            return None

        for i in range(len(search_str)):
            cur_char = search_str[i]
            if cur_char == SEPARATOR__space and parse_parameters["quote_char"] is None:
                BaseJAAQLModel.parse_where_token(parse_parameters, parameters)
            elif cur_char in [SQL__eq, SQL__paren_open, SQL__paren_close] and parse_parameters["quote_char"] is None:
                BaseJAAQLModel.parse_where_token(parse_parameters, parameters)
                parse_parameters["cur_token"] = cur_char
                BaseJAAQLModel.parse_where_token(parse_parameters, parameters)
            elif cur_char == SQL__single_quote and parse_parameters["quote_char"] is None:
                if parse_parameters["state"] != EXPECTING__operand or len(parse_parameters["cur_token"]) != 0:
                    raise HttpStatusException(ERR__unexpected_quote)
                parse_parameters["quote_char"] = SQL__single_quote
            elif cur_char == SQL__single_quote and parse_parameters["quote_char"] is SQL__single_quote:
                parse_parameters["quote_char"] = None
            else:
                parse_parameters["cur_token"] += cur_char

        if len(parse_parameters["cur_token"]) != 0:
            BaseJAAQLModel.parse_where_token(parse_parameters, parameters)

        return parse_parameters["cur_search"] if len(parse_parameters["cur_search"]) != 0 else None

    def request_deletion_key(self, purpose: str, input_args: dict,
                             expiry_seconds: int = DELETION_KEY__default_expiry_seconds):
        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_crypt_key)

        decoded = {
            JWT__data: crypt_utils.encrypt(jwt_obj_key, json.dumps(input_args))
        }

        return crypt_utils.jwt_encode(jwt_key, decoded, purpose, expiry_ms=expiry_seconds * 1000)

    def validate_deletion_key(self, key: str, purpose: str) -> dict:
        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_crypt_key)

        key = crypt_utils.jwt_decode(jwt_key, key, purpose)
        if not key:
            raise HttpStatusException(ERR__deletion_invalid_key)

        data = json.loads(crypt_utils.decrypt(jwt_obj_key, key[JWT__data]))
        return data
