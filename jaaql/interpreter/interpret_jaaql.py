import traceback

from jaaql.exceptions.http_status_exception import *
from datetime import datetime
import re
from jaaql.utilities.crypt_utils import encrypt_raw, decrypt_raw_ex
import uuid
import queue
from jaaql.db.db_interface import DBInterface, ECHO__none
from jaaql.constants import KEY__position, KEY__file, KEY__application, KEY__configuration, KEY__error, KEY__error_row_number, KEY__error_query, \
    KEY__error_set, KEY__error_index
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
ERR_mistyped_parameter = "Type '%s', for parameter '%s' unexpected. Please provide either a string, float or integer"
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


class InterpretJAAQL:

    def __init__(self, db_interface: DBInterface):
        self.db_interface = db_interface

    def transform(self, operation: Union[dict, str], conn=None, skip_commit: bool = False, wait_hook: queue.Queue = None,
                  encryption_key: bytes = None, autocommit: bool = False, canned_query_service=None):
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
        check_required = True
        ret = {}
        err = None

        if autocommit:
            conn.autocommit = autocommit

        if is_dict_operation:
            query = operation.get(KEY_query)
            if KEY_autocommit in operation:
                if conn.autocommit != operation[KEY_autocommit]:
                    conn.commit()
                conn.autocommit = operation[KEY_autocommit]

            if query is None:
                canned_query = canned_query_service.get_canned_query(operation[KEY__application], operation[KEY__configuration],
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
                                                                                             operation[KEY__configuration],
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
                                                                                          operation[KEY__configuration],
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

                for cur_query, cur_parameters, cur_row_idx, cur_state in zip(to_exec, replacement_parameters, range(len(to_exec)), states):
                    exc_query = cur_query
                    exc_state = cur_state
                    exc_row_idx = cur_row_idx
                    exc_parameters = cur_parameters
                    exc_row_number = cur_parameters.get(KEY__row_number)
                    last_query, found_parameter_dictionary = self.pre_prepare_statement(cur_query, cur_parameters)

                    enc_parameter_dictionary = {}

                    encrypt_parameters = {key: val for key, val in cur_parameters.items() if key not in found_parameter_dictionary}

                    if len(encrypt_parameters) != 0:
                        last_query, enc_parameter_dictionary = self.pre_prepare_statement(last_query, encrypt_parameters,
                                                                                          match_regex=REGEX_enc_query_argument,
                                                                                          encryption_key=encryption_key)

                    last_query = self.encrypt_literals(last_query, encryption_key)
                    found_params = {**found_parameter_dictionary, **enc_parameter_dictionary}
                    unused_orig_parameters -= set(found_params.keys())

                    res = self.db_interface.execute_query_fetching_results(conn, last_query, found_params, wait_hook=wait_hook,
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

                    cur_assert = query_obj.get(KEY_assert)
                    if cur_assert != ASSERT_none:
                        if cur_assert == ASSERT_zero and len(res["rows"]) != ASSERT_zero:
                            raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_zero), len(res["rows"])), HTTPStatus.BAD_REQUEST)
                        elif cur_assert == ASSERT_one and len(res["rows"]) != ASSERT_one:
                            raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_one), len(res["rows"])), HTTPStatus.BAD_REQUEST)
                        elif cur_assert == ASSERT_one_plus and len(res["rows"]) < ASSERT_one_plus_minimum_allowed:
                            raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_one_plus_message), len(res["rows"])), HTTPStatus.BAD_REQUEST)

                    if query_obj[KEY_decrypt] is not None:
                        missing = [param for param in query_obj[KEY_decrypt] if param not in res["columns"]]
                        if len(missing) != 0:
                            raise HttpStatusException(ERR__missing_decrypt_column % missing)

                        if len(query_obj[KEY_decrypt]) != 0:
                            res["rows"] = [
                                [decrypt_raw_ex(encryption_key, val) if col in query_obj[KEY_decrypt] and val is not None else val for val, col in
                                 zip(row, res["columns"])] for row in res["rows"]]

            if len(unused_orig_parameters):
                raise HttpStatusException(ERR_unused_parameter % list(unused_orig_parameters)[0], HTTPStatus.BAD_REQUEST)
        except Exception as ex:
            if is_dict_query:
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

        if was_conn_none:
            self.db_interface.put_conn_handle_error(conn, err, STATEMENT_empty, skip_rollback_commit=skip_commit)
        else:
            self.db_interface.handle_error(conn, err, STATEMENT_empty)

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
        last_start_match = 0
        last_end_match = 0

        for match in re.finditer(match_regex, query):
            start_pos = match.regs[0][0]
            end_pos = match.regs[0][1]
            match_str = query[start_pos + 2:end_pos - 1]
            new_query += query[last_start_match:start_pos] + "'" + encrypt_raw(encryption_key, match_str) + "'"
            last_start_match = start_pos
            last_end_match = end_pos

        return new_query + query[last_end_match:]

    def pre_prepare_statement(self, query, parameters, match_regex: str = REGEX_query_argument, encryption_key: bytes = None):
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

            if match_str not in found_parameters:
                if match_str not in parameters and match_str not in MARKERS:
                    raise HttpStatusException(ERR_missing_parameter % match_str, HTTPStatus.BAD_REQUEST)
                elif match_str not in parameters and match_str in MARKERS:
                    is_skipped_default = True
                else:
                    found_parameters.append(match_str)
                    param = parameters[match_str]
                    if encryption_key is not None:
                        param = encrypt_raw(encryption_key, param)
                    found_parameter_dictionary[match_str] = param

            if parameters[match_str] is None:
                prepared += STATEMENT_null
            else:
                type = self.get_format_type(match_str, parameters[match_str])
                if is_skipped_default:
                    prepared += MARKER_DEFAULT
                else:
                    prepared += STATEMENT_argument_begin + STATEMENT_paren_open + match_str + STATEMENT_paren_close + type

        prepared += query[last_index:]

        return prepared, found_parameter_dictionary
