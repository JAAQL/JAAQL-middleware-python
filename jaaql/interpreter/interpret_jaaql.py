from jaaql.exceptions.http_status_exception import *
from datetime import datetime
import re
from jaaql.db.db_interface import DBInterface, ECHO__none

ERR_malformed_statement = "Malformed query, expecting string or dictionary"
ERR_unknown_assert = "Unknown assert type '%s'. Please use one of %s"
ERR_malformed_parameters = "Malformed parameters! Please send as dictionary"
ERR_missing_parameter = "Missing parameter! Expected to find '%s'"
ERR_missing_query = "Missing query key from input dictionary"
ERR_unused_parameter = "Unused parameter! Supplied with '%s' but was never used"
ERR_polluted_input = "Input polluted. If passing query, only pass parameters as well"
ERR_malformed_query = "Value of 'query' key malformed. Please use a string if you are passing a value to 'query'"
ERR_mistyped_parameter = "Type '%s', for parameter '%s' unexpected. Please provide either a string, float or integer"
ERR_malformed_operation_type = "Operation malformed. Expecting either a list, string or dictionary input"
ERR_assert_expecting = "Assert expecting %s row(s) but received %d row(s)!"
ERR_malformed_join = "Joins only allowed as list or string input at the moment!"

KEY_parameters = "parameters"
KEY_select = "select"
KEY_where = "where"
KEY_echo = "echo"
KEY_query = "query"
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

REGEX_query_argument = r':([a-zA-Z0-9_\-])+(?=[^\']*(?:\'[^\']*\'[^\']*)*$)'  # Match all :blah not in quotes

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


class InterpretJAAQL:

    def __init__(self, db_interface: DBInterface):
        self.db_interface = db_interface

    def transform(self, operation, conn=None):
        if (not isinstance(operation, list)) and (not isinstance(operation, dict)) and (not isinstance(operation, str)):
            raise HttpStatusException(ERR_malformed_operation_type, HTTPStatus.BAD_REQUEST)

        was_conn_none = False
        if conn is None:
            conn = self.db_interface.get_conn()
            was_conn_none = True

        is_str_operation = isinstance(operation, str)
        is_dict_operation = isinstance(operation, dict)

        err = None
        ret = []

        last_query = None

        last_echo = ECHO__none

        try:
            ret_as_arr = False
            if is_str_operation:
                query_list = [operation]
                parameters_list = [{}]
                echo_list = [ECHO__none]
                assert_list = [ASSERT_none]
            else:
                if is_dict_operation:
                    operation = [operation]
                else:
                    ret_as_arr = True
                query_list = []
                parameters_list = []
                echo_list = []
                assert_list = []
                for op in operation:
                    query, parameters, echo, ret_assert = self.render_cur_operation(op)
                    query_list.append(query)
                    parameters_list.append(parameters)
                    echo_list.append(echo)
                    assert_list.append(ret_assert)

            past_parameters = {}

            for query, parameters, echo, cur_assert in zip(query_list, parameters_list, echo_list, assert_list):
                last_echo = echo
                last_query = query

                last_query, found_parameter_dictionary = self.pre_prepare_statement(query,
                                                                                    {**parameters, **past_parameters},
                                                                                    parameters)
                res = self.db_interface.execute_query_fetching_results(conn, last_query, found_parameter_dictionary,
                                                                       echo)

                if len(res['rows']) == 1:
                    for column, row in zip(res['columns'], res['rows'][0]):
                        past_parameters[column] = row

                if ret_as_arr:
                    ret.append(res)
                else:
                    ret = res

                if cur_assert != ASSERT_none:
                    if cur_assert == ASSERT_zero and len(res) != ASSERT_zero:
                        raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_zero), len(res)),
                                                  HTTPStatus.BAD_REQUEST)
                    elif cur_assert == ASSERT_one and len(res) != ASSERT_one:
                        raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_one), len(res)),
                                                  HTTPStatus.BAD_REQUEST)
                    elif cur_assert == ASSERT_one_plus and len(res) < ASSERT_one_plus_minimum_allowed:
                        raise HttpStatusException(ERR_assert_expecting % (str(ASSERT_one_plus_message), len(res)),
                                                  HTTPStatus.BAD_REQUEST)
        except Exception as ex:
            err = ex

        if was_conn_none:
            self.db_interface.put_conn_handle_error(conn, err, last_query if last_echo else STATEMENT_empty)
        else:
            self.db_interface.handle_error(conn, err, last_query if last_echo else STATEMENT_empty)

        return ret

    def render_cur_operation(self, operation):
        if isinstance(operation, dict):
            echo = ECHO__none
            assert_ = ASSERT_none
            parameters = {}

            if KEY_query not in operation:
                raise HttpStatusException(ERR_missing_query % KEY_query, HTTPStatus.BAD_REQUEST)

            if KEY_parameters in operation:
                if not isinstance(operation[KEY_parameters], dict):
                    raise HttpStatusException(ERR_malformed_parameters, HTTPStatus.BAD_REQUEST)
                parameters = operation[KEY_parameters]

            if KEY_assert in operation:
                assert_ = operation[KEY_assert]
                if KEY_assert not in ASSERT_allowed:
                    raise HttpStatusException(ERR_unknown_assert % (assert_, ", ".join(ASSERT_allowed)),
                                              HTTPStatus.BAD_REQUEST)

            if KEY_echo in operation:
                echo = operation[KEY_echo]

            query = self.render_dict_operation(operation[KEY_query])
            return query, parameters, echo, assert_
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

    def pre_prepare_statement(self, query, parameters, cur_parameters):
        """
        Replaces unquoted instances of :blah in query with correctly ordered pyformat equivalent
        :param query:
        :param parameters:
        :return:
        """
        prepared = ""
        last_index = 0
        found_parameters = []
        found_parameter_dictionary = {}

        for match in re.finditer(REGEX_query_argument, query):
            start_pos = match.regs[0][0]
            if start_pos != 0:
                if query[start_pos - 1] == ':':
                    continue
            end_pos = match.regs[0][1]
            match_str = query[start_pos + 1:end_pos]

            prepared += query[last_index:start_pos]
            last_index = end_pos

            if match_str not in found_parameters:
                if match_str not in parameters:
                    raise HttpStatusException(ERR_missing_parameter % match_str, HTTPStatus.BAD_REQUEST)
                found_parameters.append(match_str)
                found_parameter_dictionary[match_str] = parameters[match_str]

            if parameters[match_str] is None:
                prepared += STATEMENT_null
            else:
                type = self.get_format_type(match_str, parameters[match_str])
                prepared += STATEMENT_argument_begin + STATEMENT_paren_open + match_str + STATEMENT_paren_close + type

        prepared += query[last_index:]

        for match_str, _ in parameters.items():
            if match_str not in found_parameters and match_str in cur_parameters:
                raise HttpStatusException(ERR_unused_parameter % match_str, HTTPStatus.BAD_REQUEST)

        return prepared, found_parameter_dictionary
