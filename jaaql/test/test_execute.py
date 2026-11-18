"""
/execute runs only the application's compiled queries, in the application's databases: the query a request names is replaced by its
compiled text, and a store query, whose other keys would be run as SQL text, is refused.

    python -m unittest jaaql.test.test_execute

Needs only the package's requirements: submit and the query cache are replaced, so no database is reached
"""
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel

COMPILED = {"frame:0": "SELECT number FROM person WHERE number = :number"}


def stub_model():
    return SimpleNamespace(query_caches={"application": "app"}, db_cache={}, vault=None, config=None, get_db_crypt_key=lambda: b"key",
                           jaaql_lookup_connection=None, cached_canned_query_service=None,
                           _lookup_cached_query=mock.Mock(side_effect=lambda name: COMPILED[name]))


class TestExecute(unittest.TestCase):

    def execute(self, inputs):
        stub = stub_model()
        with mock.patch.object(model, "submit", return_value="submitted") as submitted:
            result = JAAQLModel.execute(stub, inputs, "account")
        return result, submitted, stub

    def test_a_compiled_query_is_run_by_its_compiled_text(self):
        for query in ["frame:0", {"query": "frame:0", "parameters": {"number": 1}}]:
            with self.subTest(query=query):
                result, submitted, _ = self.execute({"application": "app", "query": {"person": query}})
                self.assertEqual("submitted", result)
                sent = submitted.call_args.args[4]["query"]["person"]
                self.assertEqual(COMPILED["frame:0"], sent if isinstance(sent, str) else sent["query"])

    def test_the_queries_run_in_the_configured_application_whatever_the_request_names(self):
        for extra in [{}, {"database": "jaaql"}, {"application": "other", "database": "postgres"}]:
            with self.subTest(extra=extra):
                _, submitted, _ = self.execute({"query": {"person": "frame:0"}, **extra})
                self.assertEqual("app", submitted.call_args.args[4]["application"])

    def test_a_store_query_is_refused_before_anything_is_submitted(self):
        stub = stub_model()
        with mock.patch.object(model, "submit") as submitted:
            with self.assertRaises(HttpStatusException) as caught:
                JAAQLModel.execute(stub, {"application": "app", "query": {"rows": {
                    "query": "frame:0", "store": "rows", "own_sql": "SELECT email FROM person"}},
                    "parameters": {"rows": [{"_state": "own_sql"}]}}, "account")
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, caught.exception.response_code)
        submitted.assert_not_called()

    def test_a_compiled_query_is_found_whatever_its_file_holds(self):
        # The file a compiled query names is a key of queries.json, the frame's path in the application's source (the microcompiler writes
        # "<path>:<index>"), which may hold a space: it is found as any other, as it was before 5f6ac4e checked the reference's form
        compiled = {"Application/My Frames/x.frame.ts": ["SELECT 1", "SELECT 2"], "FDS Exports/export_.frame.ts": ["SELECT 3"]}
        stub = stub_model()
        stub.query_caches["queries"] = compiled
        stub.query_cache_is_stale = mock.Mock(return_value=False)
        stub._lookup_cached_query = lambda trimmed: JAAQLModel._lookup_cached_query(stub, trimmed)
        for reference, sql in [("Application/My Frames/x.frame.ts:1", "SELECT 2"), ("FDS Exports/export_.frame.ts:0", "SELECT 3")]:
            with self.subTest(reference=reference):
                self.assertEqual(sql, stub._lookup_cached_query(reference))
        with mock.patch.object(model, "submit", return_value="submitted") as submitted:
            JAAQLModel.execute(stub, {"query": {"a": " Application/My Frames/x.frame.ts:0 ", "b": {"query": "FDS Exports/export_.frame.ts:0 "}}},
                               "account")
        self.assertEqual({"a": "SELECT 1", "b": {"query": "SELECT 3"}}, submitted.call_args.args[4]["query"])
        # A colon still ends the file, and a file the application lacks is still the client's 400
        for reference, message in [("Application/My Frames/x.frame.ts", "Expected a compiled query as '<file>:<index>'"),
                                   ("Application/My Frames/x.frame.ts:0:1", "Expected a compiled query as '<file>:<index>'"),
                                   ("Application/My Frames/y.frame.ts:0", "The application has no compiled query")]:
            with self.subTest(reference=reference):
                with self.assertRaises(HttpStatusException) as caught:
                    stub._lookup_cached_query(reference)
                self.assertEqual(HTTPStatus.BAD_REQUEST, caught.exception.response_code)
                self.assertTrue(caught.exception.message.startswith(message), caught.exception.message)


if __name__ == "__main__":
    unittest.main()
