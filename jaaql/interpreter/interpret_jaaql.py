import string
import traceback
import random

from decimal import Decimal
from jaaql.exceptions.http_status_exception import *
from datetime import datetime
import re
from jaaql.utilities.crypt_utils import encrypt_raw, decrypt_raw_ex
import uuid
import queue
import subprocess
import json
from jaaql.db.db_interface import DBInterface, ECHO__none
from psycopg.errors import OperationalError, Error
from jaaql.constants import KEY__position, KEY__file, KEY__application, KEY__error, KEY__error_row_number, KEY__error_query, \
    KEY__error_set, KEY__error_index, SQLStateJaaql, KEY__restrictions, REGEX__dmbs_object_name
from jaaql.exceptions.jaaql_interpretable_handled_errors import DatabaseOperationalError, HandledProcedureError, UnhandledQueryError, UnhandledProcedureError, \
    SingletonExpected
from typing import Union


ERR_malformed_statement = "Malformed query, expecting string or dictionary"
ERR_unknown_assert = "Unknown assert type '%s'. Please use one of %s"
ERR_malformed_parameters = "Malformed parameters! Please send as dictionary"
ERR_malformed_decrypt = "Malformed decryption request! Please send as a list of columns"
ERR_missing_parameter = "Missing parameter! Expected to find '%s'"
ERR_missing_query = "Missing query key from input dictionary"
ERR_unused_parameter = "Unused parameter! Supplied with '%s' but was never used"
ERR_polluted_input = "Input polluted. If passing query, only pass parameters as well"
ERR_malformed_query = "Value of 'query' key malformed. Please use a string if you are passing a value to 'query'"
ERR_mistyped_parameter = "Type '%s', for parameter '%s' unexpected. Please provide either a date, string, float, list, Decimal or integer"
ERR_malformed_operation_type = "Operation malformed. Expecting either a list, string or dictionary input"
ERR_assert_expecting = "Assert expecting %s row(s) but received %d row(s)!"
ERR_malformed_join = "Joins only allowed as list or string input at the moment!"
ERR__missing_decrypt_column = "Decrypted column '%s' not found in the result set"
ERR_missing_store = "Missing parameter for store operation '%s'"
ERR_store_parameter_malformatted = "Parameter '%s' for store operation should be a list"

KEY_parameters = "parameters"
KEY_decrypt = "decrypt"
KEY_select = "select"
KEY_where = "where"
KEY_echo = "echo"
KEY_query = "query"
KEY_autocommit = "autocommit"
KEY_order_by = "order by"
KEY_group_by = "group by"
KEY_assert = "assert"
KEY_join = "join"
KEY_join_left = "left join"
KEY_join_cross = "cross join"
KEY_join_inner = "inner join"
KEY_join_right = "right join"
KEY_join_full = "full join"
KEY_join_lateral = "lateral join"
KEY_store = "store"
KEY__state = "_state"
KEY_state = "state"
KEY__row_number = "_rowNumber"

STATEMENT_as = "as"
STATEMENT_argument_begin = "%"
STATEMENT_paren_open = "("
STATEMENT_paren_close = ")"
STATEMENT_space = " "
STATEMENT_empty = ""
STATEMENT_comma = ","
STATEMENT_new_line = "\r\n"
STATEMENT_null = "NULL"

ASSERT_none = None
ASSERT_zero = 0
ASSERT_one = 1
ASSERT_one_plus = "1+"
ASSERT_one_plus_minimum_allowed = 2
ASSERT_one_plus_message = "more than 1"
ASSERT_allowed = [ASSERT_zero, ASSERT_one, ASSERT_one_plus]

REGEX_query_argument = r':([a-zA-Z0-9_.\-])+(?=[^\']*(?:\'[^\']*\'[^\']*)*$)'  # Match all :blah not in quotes
REGEX_enc_query_argument = r'#([a-zA-Z0-9_.\-])+(?=[^\']*(?:\'[^\']*\'[^\']*)*$)'  # Match all #blah not in quotes
REGEX_enc_literals = r'#\'(([^\']*)(\'\')*)+\''

PYFORMAT_str = "s"

OPERATOR_none = None
OPERATOR_separators = {
    KEY_select: STATEMENT_comma,
    KEY_where: STATEMENT_space,
    KEY_order_by: STATEMENT_comma,
    KEY_group_by: STATEMENT_comma
}
OPERATOR_joins = [
    KEY_join,
    KEY_join_left,
    KEY_join_cross,
    KEY_join_inner,
    KEY_join_right,
    KEY_join_full,
    KEY_join_lateral
]
SEPARATOR_none = ""
SEPARATOR_space = " "
SEPARATOR_spaces_per_tab = 4

MARKER_DEFAULT = "default"
MARKERS = [MARKER_DEFAULT]


class MarkerPrepare:
    def __init__(self, count):
        self.count = count


class InterpretJAAQL:

    def __init__(self, db_interface: DBInterface, jaaql_db_interface: DBInterface = None):
        self.db_interface = db_interface
        self.jaaql_db_interface = jaaql_db_interface

    def transform(self, operation: Union[dict, str], conn=None, skip_commit: bool = False, wait_hook: queue.Queue = None,
                  encryption_key: bytes = None, autocommit: bool = False, canned_query_service=None, prevent_unused_parameters: bool = True,
                  do_prepare_only: str = False, and_return_connection_mid_transaction: bool = False, attempt_fetch_domain_types: bool = False,
                  psql: list = None, pre_psql: str = None):
        if (not isinstance(operation, dict)) and (not isinstance(operation, str)):
            raise HttpStatusException(ERR_malformed_operation_type, HTTPStatus.BAD_REQUEST)

        was_conn_none = False
        if conn is None:
            conn = self.db_interface.get_conn()
            was_conn_none = True

        is_dict_operation = isinstance(operation, dict)
        query = {"query": {KEY_query: operation, KEY_assert: None, KEY_decrypt: None, KEY_parameters: {}}}
        is_dict_query = False
        parameters = {}
        past_parameters = {}
        restrictions = {}
        skip_as_restricted = []
        checked_roles_permit = set()
        checked_roles_restrict = set()
        check_required = True
        ret = {}
        err = None
        query_key = None

        if autocommit:
            conn.autocommit = autocommit

        if is_dict_operation:
            restrictions = operation.get(KEY__restrictions, {})
            if not isinstance(restrictions, dict):
                raise HttpStatusException("Malformatted restriction dictionary", HTTPStatus.BAD_REQUEST)
            else:
                for key, val in restrictions.items():
                    if not isinstance(key, str) or not isinstance(val, str) or not re.match(REGEX__dmbs_object_name, val):
                        raise HttpStatusException("Malformatted restriction dictionary around " + key, HTTPStatus.BAD_REQUEST)

            if len(restrictions) != 0 and do_prepare_only:
                raise HttpStatusException("Supplying restrictions makes no sense when preparing! Choose one or the other")

            if len(restrictions) != 0 and self.jaaql_db_interface is None:
                raise Exception("You must provide the jaaql db interface if you plan to check for restrictions")

            query = operation.get(KEY_query)
            if KEY_autocommit in operation:
                if conn.autocommit != operation[KEY_autocommit]:
                    conn.commit()
                conn.autocommit = operation[KEY_autocommit]

            if query is None:
                canned_query = canned_query_service.get_canned_query(operation[KEY__application],
                                                                     operation[KEY__file], operation[KEY__position])
                query = {"query": {KEY_query: canned_query, KEY_assert: operation.get(KEY_assert), KEY_decrypt: operation.get(KEY_decrypt),
                                   KEY_parameters: {}}}
                check_required = False
            else:
                is_dict_query = isinstance(query, dict)
                if not is_dict_query:
                    query = {"query": {"query": query, KEY_assert: operation.get(KEY_assert), KEY_decrypt: operation.get(KEY_decrypt),
                                       KEY_parameters: {}}}
                else:
                    all_replaced = True
                    for key, val in query.items():
                        if isinstance(val, str):
                            all_replaced = False
                            query[key] = {KEY_query: val, KEY_assert: None, KEY_decrypt: None, KEY_parameters: {}}
                        else:
                            if KEY_store in val:
                                for sub_key, sub_val in val.items():
                                    if sub_key in [KEY_parameters, KEY_decrypt, KEY_store]:
                                        continue
                                    if isinstance(sub_val, str):
                                        all_replaced = False
                                    else:
                                        canned_query = canned_query_service.get_canned_query(operation[KEY__application],
                                                                                             sub_val[KEY__file], sub_val[KEY__position])
                                        val[sub_key] = canned_query
                                if KEY_parameters not in val:
                                    val[KEY_parameters] = {}
                                if KEY_decrypt not in val:
                                    val[KEY_decrypt] = None
                            else:
                                fetched_query = None
                                if isinstance(val[KEY_query], str):
                                    all_replaced = False
                                    fetched_query = val[KEY_query]
                                else:
                                    fetched_query = canned_query_service.get_canned_query(operation[KEY__application],
                                                                                          val[KEY_query][KEY__file], val[KEY_query][KEY__position])
                                query[key] = {KEY_query: fetched_query, KEY_assert: val.get(KEY_assert), KEY_decrypt: val.get(KEY_decrypt),
                                              KEY_parameters: val.get(KEY_parameters, {})}
                    check_required = not all_replaced

            parameters = operation.get(KEY_parameters, {})

        unused_orig_parameters = set(parameters.keys())

        was_store = None
        exc_query_key = None
        exc_row_idx = None
        exc_parameters = None
        exc_query = None
        exc_row_number = None
        exc_state = None

        try:
            if prevent_unused_parameters:
                check_unused = unused_orig_parameters.copy()

                for query_key, query_obj in query.items():
                    was_store = is_dict_query and KEY_store in query_obj
                    if was_store:
                        check_unused -= {query_obj[KEY_store]}
                    else:
                        cur_query = query_obj[KEY_query]

                        last_query, found_parameter_dictionary = self.pre_prepare_statement(cur_query, parameters, require_presence=False)
                        enc_parameter_dictionary = {}
                        encrypt_parameters = {key: val for key, val in parameters.items() if key not in found_parameter_dictionary}
                        if len(encrypt_parameters) != 0:
                            last_query, enc_parameter_dictionary = self.pre_prepare_statement(last_query, encrypt_parameters,
                                                                                              match_regex=REGEX_enc_query_argument,
                                                                                              encryption_key=encryption_key,
                                                                                              require_presence=False)

                        found_params = {**found_parameter_dictionary, **enc_parameter_dictionary}
                        check_unused -= set(found_params.keys())

                if len(check_unused):
                    raise HttpStatusException(ERR_unused_parameter % list(check_unused)[0], HTTPStatus.BAD_REQUEST)

            for query_key, query_obj in query.items():
                exc_query_key = query_key
                replacement_parameters = {**past_parameters, **parameters, **query_obj[KEY_parameters]}

                to_exec = []
                states = []
                was_store = is_dict_query and KEY_store in query_obj
                if was_store:
                    if query_obj[KEY_store] not in replacement_parameters:
                        raise HttpStatusException(ERR_missing_store % query_obj[KEY_store])
                    if not isinstance(replacement_parameters[query_obj[KEY_store]], list):
                        raise HttpStatusException(ERR_store_parameter_malformatted % query_obj[KEY_store])
                    unused_orig_parameters -= {query_obj[KEY_store]}
                    to_exec = [query_obj[obj[KEY__state]] for obj in replacement_parameters[query_obj[KEY_store]]]
                    states = [obj[KEY__state] for obj in replacement_parameters[query_obj[KEY_store]]]
                    iterate_params = replacement_parameters.pop(query_obj[KEY_store])
                    replacement_parameters = [{**replacement_parameters, **{query_obj[KEY_store] + "." + key: val for key, val in cur.items()}}
                                              for cur in iterate_params]
                else:
                    to_exec = [query_obj[KEY_query]]
                    replacement_parameters = [replacement_parameters]
                    states = [None] * len(to_exec)

                if was_store:
                    ret[query_key] = []

                if query_key in restrictions:
                    the_role = restrictions[query_key]
                    if the_role in checked_roles_permit:
                        pass  # We allow!
                    elif the_role in checked_roles_restrict:
                        skip_as_restricted.append(query_key)
                    else:
                        check_query = "SELECT T.has_role FROM check_user_role(%(test_role)s, %(interface_role)s) T;"
                        check_parameters = {
                            "test_role": the_role,
                            "interface_role": self.db_interface.role
                        }
                        check_conn = self.jaaql_db_interface.get_conn()
                        try:
                            permitted = self.jaaql_db_interface.execute_query_fetching_results(check_conn, check_query, check_parameters)["rows"][0][0]
                            if permitted:
                                checked_roles_permit.add(the_role)
                            else:
                                checked_roles_restrict.add(the_role)
                                skip_as_restricted.append(query_key)
                            self.jaaql_db_interface.put_conn(check_conn)
                        except Exception as ex:
                            try:
                                self.jaaql_db_interface.put_conn(check_conn)
                            except:
                                pass
                            raise ex

                skipped_singletons = []

                for cur_query, cur_parameters, cur_row_idx, cur_state in zip(to_exec, replacement_parameters, range(len(to_exec)), states):
                    exc_query = cur_query
                    exc_state = cur_state
                    exc_row_idx = cur_row_idx
                    exc_parameters = cur_parameters
                    exc_row_number = cur_parameters.get(KEY__row_number)
                    last_query, found_parameter_dictionary = self.pre_prepare_statement(
                        cur_query, cur_parameters, for_prepare=do_prepare_only is not False and do_prepare_only is not None,
                        skipped_singletons=skipped_singletons, replace_with_nulls=attempt_fetch_domain_types)

                    enc_parameter_dictionary = {}

                    encrypt_parameters = {key: val for key, val in cur_parameters.items() if key not in found_parameter_dictionary}

                    if len(encrypt_parameters) != 0:
                        last_query, enc_parameter_dictionary = self.pre_prepare_statement(
                            last_query, encrypt_parameters, match_regex=REGEX_enc_query_argument,
                            encryption_key=encryption_key, for_prepare=do_prepare_only is not False and do_prepare_only is not None,
                            skipped_singletons=skipped_singletons, replace_with_nulls=attempt_fetch_domain_types)

                    last_query = self.encrypt_literals(last_query, encryption_key)
                    found_params = {**found_parameter_dictionary, **enc_parameter_dictionary}

                    if attempt_fetch_domain_types:
                        temp_view_name = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                        last_query = "CREATE TEMP VIEW \"temp_view__" + temp_view_name + "\" AS (" + last_query + ")"
                        self.db_interface.execute_query_fetching_results(conn, last_query, found_params, wait_hook=wait_hook,
                                                                         requires_dba_check=check_required and canned_query_service is not None)
                        last_query = """
WITH RECURSIVE column_hierarchy AS (
    -- Base case: Select columns from 'managed_service'
    SELECT
        C.column_name, C.data_type, C.udt_name, C.domain_name,
        VC.table_catalog, VC.table_schema, VC.table_name,
        true as is_nullable,
        1 as level
    FROM information_schema.columns C
    LEFT JOIN information_schema.view_column_usage VC on VC.view_name = C.table_name AND VC.column_name = C.column_name
    WHERE C.table_name = 'temp_view__""" + temp_view_name + """'

    UNION ALL

    SELECT
        C.column_name, C.data_type, C.udt_name, C.domain_name,
        VC.table_catalog, VC.table_schema, VC.table_name,
        CASE WHEN C.is_nullable = 'NO' then false else true end as is_nullable,
        CH.level + 1 as level
    FROM information_schema.columns C
    JOIN column_hierarchy CH ON C.column_name = CH.column_name
    LEFT JOIN information_schema.view_column_usage VC on VC.view_name = C.table_name AND VC.column_name = C.column_name
    WHERE C.table_name = CH.table_name AND C.table_schema = CH.table_schema AND C.table_catalog = CH.table_catalog
)SELECT
    MAX(CH.column_name) as column_name,
    MAX(CH.data_type) as data_type,
    MAX(CH.udt_name) as udt_name,
    MAX(CH.domain_name) as domain_name,
    NOT(bool_or(NOT(CH.is_nullable))) as is_nullable
FROM column_hierarchy CH
GROUP BY CH.column_name, CH.data_type, CH.udt_name, CH.domain_name;"""
                        found_params = {}
                    elif do_prepare_only and not psql:
                        arg_open = "(" if len(found_params) != 0 else ""
                        arg_close = ")" if len(found_params) != 0 else ""
                        last_query = "PREPARE _jaaql_query_check_" + do_prepare_only + arg_open + ", ".join(
                            ["unknown" for _ in found_params.keys()]) + arg_close + " as " + last_query
                        last_query = last_query + "; SET plan_cache_mode = force_generic_plan; "
                        self.db_interface.execute_query_fetching_results(conn, last_query, found_params, wait_hook=wait_hook,
                                                                         requires_dba_check=check_required and canned_query_service is not None)
                        last_query = "EXPLAIN EXECUTE _jaaql_query_check_" + do_prepare_only + arg_open + ", ".join(
                            ["NULL" for _ in found_params.keys()]) + arg_close
                        found_params = {}

                    cur_assert = query_obj.get(KEY_assert)

                    if query_key in skip_as_restricted:
                        res = {
                            "columns": [],
                            "rows": [],
                            "type_codes": []
                        }
                        if cur_assert == ASSERT_one:
                            skipped_singletons.append(query_key)

                    elif psql is not None:
                        result = subprocess.run(
                            psql,
                            input=f"{pre_psql}\n{last_query}\n\\gdesc\n",
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=True
                        )
                        res = {
                            "columns": ["result"],
                            "rows": [result.stdout],
                            "type_codes": [""]
                        }
                    else:
                        res = self.db_interface.execute_query_fetching_results(conn, last_query, found_params, wait_hook=wait_hook,
                                                                               requires_dba_check=check_required and canned_query_service is not None)

                    if do_prepare_only and not attempt_fetch_domain_types and not psql:
                        self.db_interface.execute_query_fetching_results(conn, "DEALLOCATE _jaaql_query_check_" + do_prepare_only, found_params,
                                                                         wait_hook=wait_hook,
                                                                         requires_dba_check=check_required and canned_query_service is not None)
                    elif attempt_fetch_domain_types:
                        self.db_interface.execute_query_fetching_results(conn, "DROP VIEW IF EXISTS \"temp_view__" + temp_view_name + "\"", found_params,
                                                                         wait_hook=wait_hook,
                                                                         requires_dba_check=check_required and canned_query_service is not None)

                    wait_hook = None  # We've already checked authentication, we don't need to do it again
                    check_required = False  # We've done the first check, if we have reached here without an exception, user does not need a DBA check

                    if len(res['rows']) == 1 and not was_store:
                        for column, row in zip(res['columns'], res['rows'][0]):
                            past_parameters[query_key + "." + column] = row

                    if is_dict_query:
                        if was_store:
                            ret[query_key].append(res)
                        else:
                            ret[query_key] = res
                    else:
                        ret = res

                    if cur_assert != ASSERT_none and query_key not in skip_as_restricted:
                        if cur_assert == ASSERT_zero and len(res["rows"]) != ASSERT_zero:
                            raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_zero), len(res["rows"])), HTTPStatus.BAD_REQUEST)
                        elif cur_assert == ASSERT_one and len(res["rows"]) != ASSERT_one:
                            raise SingletonExpected(exc_query_key, descriptor={
                                "row_count": len(res["rows"]),
                                "columns": res["rows"],
                                "rows": res["columns"],
                                "type_codes": res["type_codes"]
                            })
                        elif cur_assert == ASSERT_one_plus and len(res["rows"]) < ASSERT_one_plus_minimum_allowed:
                            raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_one_plus_message), len(res["rows"])), HTTPStatus.BAD_REQUEST)

                    if query_obj[KEY_decrypt] is not None and query_key not in skip_as_restricted:
                        missing = [param for param in query_obj[KEY_decrypt] if param not in res["columns"]]
                        if len(missing) != 0:
                            raise HttpStatusException(ERR__missing_decrypt_column % missing)

                        if len(query_obj[KEY_decrypt]) != 0:
                            res["rows"] = [
                                [decrypt_raw_ex(encryption_key, val) if col in query_obj[KEY_decrypt] and val is not None else val for val, col in
                                 zip(row, res["columns"])] for row in res["rows"]]
        except Exception as ex:
            traceback.print_exc()
            if isinstance(ex, OperationalError):
                err = DatabaseOperationalError(
                    message=str(ex),
                    descriptor={
                        "class": ex.diag.sqlstate[0:2],
                        "constraint_name": ex.diag.constraint_name,
                        "context": ex.diag.context,
                        "datatype_name": ex.diag.datatype_name,
                        "message_detail": ex.diag.message_detail,
                        "message_primary": ex.diag.message_primary,
                        "message_hint": ex.diag.message_hint,
                        "schema_name": ex.diag.schema_name,
                        "severity": ex.diag.severity,
                        "sqlstate": ex.diag.sqlstate
                    }
                )
            elif isinstance(ex, Error):
                if ex.diag.sqlstate == SQLStateJaaql:
                    err = HandledProcedureError(message=None, index=None, table_name=None, descriptor=json.loads(ex.diag.message_primary))
                elif query_key == "_jaaql_procedure":
                    err = UnhandledProcedureError(
                        message=str(ex),
                        table_name=ex.diag.table_name,
                        column_name=ex.diag.column_name,
                        descriptor={
                            "class": ex.diag.sqlstate[0:2],
                            "constraint_name": ex.diag.constraint_name,
                            "context": ex.diag.context,
                            "datatype_name": ex.diag.datatype_name,
                            "message_detail": ex.diag.message_detail,
                            "message_primary": ex.diag.message_primary,
                            "message_hint": ex.diag.message_hint,
                            "schema_name": ex.diag.schema_name,
                            "severity": ex.diag.severity,
                            "sqlstate": ex.diag.sqlstate
                        }
                    )
                else:
                    err = UnhandledQueryError(
                        message=str(ex),
                        _set=query_key,
                        table_name=ex.diag.table_name,
                        column_name=ex.diag.column_name,
                        descriptor={
                            "class": ex.diag.sqlstate[0:2],
                            "constraint_name": ex.diag.constraint_name,
                            "context": ex.diag.context,
                            "datatype_name": ex.diag.datatype_name,
                            "message_detail": ex.diag.message_detail,
                            "message_primary": ex.diag.message_primary,
                            "message_hint": ex.diag.message_hint,
                            "schema_name": ex.diag.schema_name,
                            "severity": ex.diag.severity,
                            "sqlstate": ex.diag.sqlstate
                        }
                    )
            elif is_dict_query:
                if isinstance(ex, JaaqlInterpretableHandledError):
                    err = ex
                    err.set = exc_query_key
                else:
                    new_ex = HttpStatusException(str(ex))
                    if isinstance(ex, HttpStatusException):
                        new_ex.response_code = ex.response_code
                    ex = new_ex

                    ex.message = {
                        KEY__error: ex.message,
                        KEY__error_set: exc_query_key,
                        KEY__error_query: exc_query,
                        KEY_parameters: exc_parameters
                    }
                    if was_store:
                        ex.message[KEY__error_row_number] = exc_row_number
                        ex.message[KEY__error_index] = exc_row_idx
                        ex.message[KEY_state] = exc_state

                    err = ex
            else:
                err = ex

        #
        # and_return_connection_mid_transaction
        # err

        if was_conn_none:
            self.db_interface.put_conn_handle_error(conn, err, skip_rollback_commit=skip_commit)
        elif not and_return_connection_mid_transaction:
            self.db_interface.handle_error(conn, err)
        elif err is not None:
            raise err

        if is_dict_query:
            ret["_restrictions"] = skip_as_restricted

        return ret

    def render_cur_operation(self, operation):
        if isinstance(operation, dict):
            echo = ECHO__none
            assert_ = ASSERT_none
            parameters = {}
            decrypt_columns = {}

            if KEY_query not in operation:
                raise HttpStatusException(ERR_missing_query, HTTPStatus.BAD_REQUEST)

            if KEY_parameters in operation:
                if not isinstance(operation[KEY_parameters], dict):
                    raise HttpStatusException(ERR_malformed_parameters, HTTPStatus.BAD_REQUEST)
                parameters = operation[KEY_parameters]

            if KEY_decrypt in operation:
                if not isinstance(operation[KEY_decrypt], list):
                    raise HttpStatusException(ERR_malformed_parameters, HTTPStatus.BAD_REQUEST)
                decrypt_columns = operation[KEY_decrypt]

            if KEY_assert in operation:
                assert_ = operation[KEY_assert]
                if KEY_assert not in ASSERT_allowed:
                    raise HttpStatusException(ERR_unknown_assert % (assert_, ", ".join(ASSERT_allowed)),
                                              HTTPStatus.BAD_REQUEST)

            if KEY_echo in operation:
                echo = operation[KEY_echo]

            query = self.render_dict_operation(operation[KEY_query])
            return query, parameters, decrypt_columns, echo, assert_
        elif isinstance(operation, str):
            return operation, {}, ECHO__none, ASSERT_none
        else:
            raise HttpStatusException(ERR_malformed_statement, HTTPStatus.BAD_REQUEST)

    def render_dict_operation(self, query):
        if isinstance(query, dict):
            return self.render_statement_from_dict(query)
        elif isinstance(query, str):
            return query
        else:
            raise HttpStatusException(ERR_malformed_statement, HTTPStatus.BAD_REQUEST)

    def get_format_type(self, key, value):
        # There is not an error below. psycopg2 _requires_ that the format is always string
        if isinstance(value, str):
            return PYFORMAT_str
        elif isinstance(value, bytes):
            return PYFORMAT_str
        elif isinstance(value, int):
            return PYFORMAT_str
        elif isinstance(value, float):
            return PYFORMAT_str
        elif isinstance(value, datetime):
            return PYFORMAT_str
        elif isinstance(value, uuid.UUID):
            return PYFORMAT_str
        elif isinstance(value, list):
            return PYFORMAT_str
        elif type(value).__name__ == "date":
            return PYFORMAT_str
        elif isinstance(value, Decimal):
            return PYFORMAT_str
        else:
            raise HttpStatusException(ERR_mistyped_parameter % (type(value).__name__, key), HTTPStatus.BAD_REQUEST)

    def render_statement(self, statement):
        parameters = {}

        if isinstance(statement, str):
            query = statement
        elif isinstance(statement, dict):
            query, parameters = self.render_statement_from_dict(statement)
        else:
            raise HttpStatusException(ERR_malformed_statement, HTTPStatus.BAD_REQUEST)

        return query, parameters

    def render_statement_from_dict(self, statement, depth=0):
        query = ""

        custom_operators = {
            KEY_select: self.render_select
        }

        i = 0
        for key, val in statement.items():
            trans_key = key.lower()

            if i != 0:
                query += STATEMENT_new_line

            query += trans_key.upper()

            render_function = custom_operators.get(trans_key, self.render_element)
            if trans_key in OPERATOR_joins:
                render_function = self.render_join

            unjoined = render_function(val, trans_key, depth)
            query += self.join_line_with_separator(trans_key, 1, unjoined, trans_key in OPERATOR_joins)

            i += 1

        return query

    def get_spaces_depth(self, depth):
        spaces = [SEPARATOR_space] * depth * SEPARATOR_spaces_per_tab
        return SEPARATOR_none.join(spaces)

    def join_line_with_separator(self, operator, depth, elements, is_join=False):
        spaces = self.get_spaces_depth(depth)

        joiner = OPERATOR_separators.get(operator, SEPARATOR_none) + STATEMENT_new_line
        if not is_join:
            joiner += spaces
        joined = joiner.join([str(element) for element in elements])

        return STATEMENT_new_line + spaces + joined

    def render_join(self, element, operator, depth=0, do_join=False):
        spaces = self.get_spaces_depth(depth + 1)

        if isinstance(element, str):
            return element
        elif isinstance(element, list):
            return [cur if ix == 0 else operator.upper() + STATEMENT_new_line + spaces + cur for ix, cur in zip(
                range(len(element)), element)]
        else:
            raise HttpStatusException(ERR_malformed_join, HTTPStatus.BAD_REQUEST)

    def render_select(self, element, operator, depth=0, do_join=False):
        if isinstance(element, dict):
            return [
                self.join_line_with_separator(KEY_select, depth, self.render_element(val, OPERATOR_none, depth))
                + " " + STATEMENT_as + " \"" + key + "\"" for key, val in element.items()]
        else:
            return self.render_element(element, KEY_select, depth)

    def render_element(self, element, operator, depth=0, do_join=False):
        if isinstance(element, list):
            unjoined = [
                self.render_element(sub_element, operator, depth + 1)
                if isinstance(sub_element, list) or isinstance(sub_element, dict) else sub_element
                for sub_element in element
            ]
            return unjoined
        elif isinstance(element, dict):
            opener = STATEMENT_paren_open if depth != 0 else ""
            closer = STATEMENT_paren_close if depth != 0 else ""
            unjoined = [
                opener + self.render_element(operands, " " + new_operator + " ", depth + 1) + closer
                for new_operator, operands in element.items()
            ]
            return unjoined
        else:
            return [element]

    def encrypt_literals(self, query, encryption_key: bytes = None, match_regex: str = REGEX_enc_literals):
        new_query = ""
        last_end_match = 0

        for match in re.finditer(match_regex, query):
            start_pos = match.regs[0][0]
            end_pos = match.regs[0][1]
            match_str = query[start_pos + 2:end_pos - 1]
            new_query += query[last_end_match:start_pos] + "'" + encrypt_raw(encryption_key, match_str) + "'"
            last_end_match = end_pos

        return new_query + query[last_end_match:]

    def pre_prepare_statement(self, query, parameters, match_regex: str = REGEX_query_argument, encryption_key: bytes = None,
                              require_presence: bool = True, for_prepare: bool = False, skipped_singletons: list[str] = None,
                              replace_with_nulls: bool = False):
        prepared = ""
        last_index = 0
        found_parameters = []
        found_parameter_dictionary = {}

        for match in re.finditer(match_regex, query):
            is_skipped_default = False
            start_pos = match.regs[0][0]
            if start_pos != 0:
                if query[start_pos - 1] == REGEX_query_argument[0]:
                    continue
            end_pos = match.regs[0][1]
            match_str = query[start_pos + 1:end_pos]

            prepared += query[last_index:start_pos]
            last_index = end_pos

            if match_str not in parameters and for_prepare:
                parameters[match_str] = MarkerPrepare(len(parameters))

            if match_str not in found_parameters:
                if match_str not in parameters and match_str not in MARKERS:
                    if require_presence:
                        missing_str = ERR_missing_parameter % match_str
                        if skipped_singletons is not None and len(skipped_singletons) != 0:
                            missing_str += ". Is it possible the parameter exists in one of the following restricted singletons: " + ", ".join(
                                missing_str) + "?"
                        raise HttpStatusException(missing_str, HTTPStatus.BAD_REQUEST)
                    else:
                        continue
                elif match_str not in parameters and match_str in MARKERS:
                    is_skipped_default = True
                else:
                    found_parameters.append(match_str)
                    param = parameters[match_str]
                    if encryption_key is not None:
                        param = encrypt_raw(encryption_key, param)
                    found_parameter_dictionary[match_str] = param

            if parameters[match_str] is None and not isinstance(parameters[match_str], MarkerPrepare):
                prepared += STATEMENT_null
            else:
                if isinstance(parameters[match_str], MarkerPrepare):
                    if replace_with_nulls:
                        prepared += "NULL"
                    else:
                        prepared += "$" + str(int(parameters[match_str].count) + 1)
                else:
                    the_type = self.get_format_type(match_str, parameters[match_str])
                    if is_skipped_default:
                        prepared += MARKER_DEFAULT
                    else:
                        prepared += STATEMENT_argument_begin + STATEMENT_paren_open + match_str + STATEMENT_paren_close + the_type

        prepared += query[last_index:]

        return prepared, found_parameter_dictionary
