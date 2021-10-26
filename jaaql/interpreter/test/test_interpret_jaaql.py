from jaaql.test.base_test import BaseTest


class TestInterpretJAAQL(BaseTest):

    def setUp(self) -> None:
        self.test_interface = DBTestInterface({KEY_CONFIG_system: {KEY_CONFIG_logging: False}})
        self.ij: InterpretJAAQL = InterpretJAAQL(self.test_interface)

    def test_transform(self):
        ret = self.ij.transform([
            {
                "query": "SELECT * FROM table WHERE :test = FALSE",
                "parameters": {"test": "val"}
            },
            {
                "select": ["a", "b", "c"],
                "from": "table t",
                "where": {"AND": ["a", "b"]}
            }
        ])
        self.run_test(1, self.test_interface.fetched_conn_count, "Match fetched connection count")
        self.run_test(1, self.test_interface.put_conn_count, "Match put connection count")
        self.run_test(1, self.test_interface.commit_count, "Match commit count")
        self.run_test(0, self.test_interface.rollback_count, "Match rollback count")
        self.run_test([], self.test_interface.errs, "Match errors")
        self.run_test(2, self.test_interface.execute_count, "Match execute count")
        self.run_test([1, 2], ret, "Match returned")
        self.run_test("SELECT * FROM table WHERE :(test) = FALSE", self.test_interface.executed_queries[0][0][0], "Match first query")
        self.run_test({"test": "val"}, self.test_interface.executed_queries[0][0][1], "Match first parameters")
        self.run_test('SELECT a, b, c FROM table t WHERE a AND b', self.test_interface.executed_queries[0][1][0], "Match second query")
        self.run_test({}, self.test_interface.executed_queries[0][1][1], "Match second parameters")

        self.test_interface.reset()

        caught = False
        try:
            self.ij.transform([{"query": ["SELECT * FROM table WHERE :test = FALSE"]}])
        except UnitException:
            caught = True
        self.run_test(True, caught, "Caught exception on failure")
        self.run_test(1, self.test_interface.rollback_count, "Match rollback count on failure")
        self.run_test(0, self.test_interface.commit_count, "Match commit count on failure")
        self.run_test(1, self.test_interface.put_conn_count, "Match put connection count on failure")

    def test_pre_prepare_statement(self):
        expected_statement = ":(test)"
        actual_statement = self.ij.pre_prepare_statement(":test", {"test": "val"})
        self.run_test(expected_statement, actual_statement, "Base statement match")

        expected_statement = "str"
        actual_statement = self.ij.pre_prepare_statement("str", {})
        self.run_test(expected_statement, actual_statement, "Unaltered statement match")

        expected_statement = "'Escaped'':query match'"
        actual_statement = self.ij.pre_prepare_statement("'Escaped'':query match'", {})
        self.run_test(expected_statement, actual_statement, "Escaped statement match")

        caught = False
        try:
            self.ij.pre_prepare_statement(":test", {})
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Match missing error response code")
            self.run_test(ERR_missing_parameter % "test", str(ex), "Match missing error message")
        self.run_test(True, caught, "Missing error exception thrown")

        caught = False
        try:
            self.ij.pre_prepare_statement(":test", {"test": "val", "extra": "val2"})
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Match unused error response code")
            self.run_test(ERR_unused_parameter % "extra", str(ex), "Match unused error message")
        self.run_test(True, caught, "Unused error exception thrown")

        caught = False
        try:
            self.ij.pre_prepare_statement(":test", {"extra": "val2"})
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Match both error response code")
            self.run_test(ERR_missing_parameter % "test", str(ex), "Match both error message")
        self.run_test(True, caught, "Both error exception thrown")

        expected_statement = "':test'"
        actual_statement = self.ij.pre_prepare_statement("':test'", {})
        self.run_test(expected_statement, actual_statement, "Quoted statement match")

        expected_statement = "':test':(test)"
        actual_statement = self.ij.pre_prepare_statement("':test':test", {"test": "val"})
        self.run_test(expected_statement, actual_statement, "Quoted with replacement statement match")

        expected_statement = ":(test):(extra):(test)"
        actual_statement =  self.ij.pre_prepare_statement(
            ":test:extra:test", {"test": "val", "extra": "val2"})
        self.run_test(expected_statement, actual_statement, "Multi replacement statement match")

        expected_statement = "WHERE t.a = ':test' AND t.b = :(test) AND t.c = 'end'"
        actual_statement = self.ij.pre_prepare_statement(
            "WHERE t.a = ':test' AND t.b = :test AND t.c = 'end'", {"test": "val"})
        self.run_test(expected_statement, actual_statement, "Realistic example statement match")

    def test_render_statement(self):
        expected_statement = "Test statement"
        expected_parameters = {}
        actual_statement, actual_parameters = self.ij.render_statement("Test statement")
        self.run_test(expected_statement, actual_statement, "")
        self.run_test(expected_parameters, actual_parameters, "")

        caught = False
        try:
            self.ij.render_statement(["list"])
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Malformed statement match response code")
            self.run_test(ERR_malformed_statement, str(ex), "Malformed statement match message")
        self.run_test(True, caught, "Malformed statement exception thrown")

    def test_render_statement_from_dict(self):
        expected = "SELECT col1, col2, col3 FROM table t WHERE a=b AND b=c AND d=f"
        actual_statement, actual_parameters = self.ij.render_statement_from_dict({
            "select": ["col1", "col2", "col3"],
            "from": "table t",
            "where": {"AND": ["a=b", "b=c", "d=f"]}
        })
        self.run_test(expected, actual_statement, "Render with no parameters, query")
        expected = {}
        self.run_test(expected, actual_parameters, "Render with no parameters, parameters")

        expected = "SELECT col1, col2, col3 FROM table t WHERE a=b AND b=c AND d=f"
        input_parameters = {"param1": 2}
        actual_statement, actual_parameters = self.ij.render_statement_from_dict({
            "select": "col1, col2, col3 FROM table t WHERE a=b AND b=c AND d=f",
            "parameters": input_parameters
        })
        self.run_test(expected, actual_statement, "Render with parameters, query")
        expected = input_parameters
        self.run_test(expected, actual_parameters, "Render with parameters, parameters")

        caught = False
        try:
            self.ij.render_statement_from_dict({
                "select": "",
                "parameters": "whoops"
            })
        except UnitException as ex:
            caught = True
            self.run_test(ERR_malformed_parameters, str(ex), "Match malformed parameters error message")
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Match malformed parameters response code")
        self.run_test(True, caught, "Malformed parameters exception thrown")

        expected = "SELECT * FROM table"
        actual_statement, actual_parameters = self.ij.render_statement_from_dict({
            "query": "SELECT * FROM table"
        })
        self.run_test(expected, actual_statement, "Render with query, query")
        expected = {}
        self.run_test(expected, actual_parameters, "Render with query, parameters")

        expected = "SELECT * FROM table"
        actual_statement, actual_parameters = self.ij.render_statement_from_dict({
            "query": "SELECT * FROM table",
            "parameters": input_parameters
        })
        self.run_test(expected, actual_statement, "Render with query and parameters, query")
        expected = input_parameters
        self.run_test(expected, actual_parameters, "Render with query and parameters, parameters")

        caught = False
        try:
            self.ij.render_statement_from_dict({
                "query": "SELECT * FROM table",
                "other": "val"
            })
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Polluted input match response code")
            self.run_test(ERR_polluted_input, str(ex), "Polluted input match message")
        self.run_test(True, caught, "Polluted input exception caught")

        caught = False
        try:
            self.ij.render_statement_from_dict({
                "query": ["SELECT * FROM table"]
            })
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Malformed query match response code")
            self.run_test(ERR_malformed_query, str(ex), "Malformed query match message")
        self.run_test(True, caught, "Malformed query exception caught")

        caught = False
        try:
            self.ij.render_statement_from_dict({
                "query": "SELECT * FROM table",
                "parameters": input_parameters,
                "other": "val"
            })
        except UnitException as ex:
            caught = True
            self.run_test(HTTPStatus.BAD_REQUEST, ex.response_code, "Polluted input w/ parameters match response code")
            self.run_test(ERR_polluted_input, str(ex), "Polluted input w/ parameters match message")
        self.run_test(True, caught, "Polluted input w/ parameters exception caught")

    def test_render_element(self):
        expected = "table t"
        actual = self.ij.render_element("table t")
        self.run_test(expected, actual, "Flat")

        expected = "table t, sub_table s"
        actual = self.ij.render_element(["table t", "sub_table s"])
        self.run_test(expected, actual, "List")

        expected = "a=1 AND b=2"
        actual = self.ij.render_element(["a=1", "b=2"], " AND ")
        self.run_test(expected, actual, "List operator")

        expected = "a=b AND b=c AND d=f"
        actual = self.ij.render_element({"AND": ["a=b", "b=c", "d=f"]})
        self.run_test(expected, actual, "Dictionary")

        expected = "a=b AND b=c AND ((d + e) * (f - g) * h)"
        actual = self.ij.render_element(
            {
                "AND": [
                    "a=b", "b=c",
                    {
                        "*": [
                            {
                                "+": ["d", "e"],
                                "-": ["f", "g"]
                            },
                            "h"
                        ]
                    }
                ]
            })
        self.run_test(expected, actual, "Dictionary complex")
