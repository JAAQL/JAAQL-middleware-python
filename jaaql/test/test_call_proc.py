"""
The SQL that /call-proc and a security event's procedure call build from the request: names, parameter keys and explicit types;
and /call-proc's refusal of federation procedures.

    python -m unittest jaaql.test.test_call_proc

Needs only the package's requirements: submit and the federation procedure lookup are replaced, so no database is reached
"""
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.mvc import handmade_queries, model
from jaaql.mvc.model import JAAQLModel, _explicit_type

# Every explicit type found in the generated __dbms__.ts of 41 projects is a FIESTA realm name: a bare identifier
TYPES__generated = ["project_code", "_datetime", "_string", "boolean", "jsonb", "postgres_user_id", "position_", "value_",
                    "full_url_allowing_anchor_and_parameters", "kadastraal_registratienummer", "iso_weeknummer"]

TYPES__unsafe = [
    "text) , other => (SELECT 1",
    "text||(SELECT email FROM person LIMIT 1)::int",
    "int; DROP TABLE person",
    "text--",
    "text/**/",
    "text\n",
    " text",
    "text ",
    "character varying",
    "numeric(5,2)",
    "text[]",
    "public.text",
    "\"text\"",
    "1text",
    "x" * 64,
]


def stub_model():
    return SimpleNamespace(vault=None, config=None, get_db_crypt_key=lambda: b"key", jaaql_lookup_connection=None,
                           cached_canned_query_service=None)


class TestExplicitType(unittest.TestCase):

    def assertUnsafe(self, explicit_types, parameter_key="p"):
        with self.assertRaises(HttpStatusException) as caught:
            _explicit_type(explicit_types, parameter_key)
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, caught.exception.response_code)

    def test_generated_types_are_accepted_unchanged(self):
        for explicit_type in TYPES__generated:
            self.assertEqual(explicit_type, _explicit_type({"p": explicit_type}, "p"))

    def test_the_longest_postgres_identifier_is_accepted(self):
        self.assertEqual("x" * 63, _explicit_type({"p": "x" * 63}, "p"))

    def test_absent_types_give_none(self):
        self.assertIsNone(_explicit_type(None, "p"))
        self.assertIsNone(_explicit_type({}, "p"))
        self.assertIsNone(_explicit_type({"p": None}, "p"))
        self.assertIsNone(_explicit_type({"p": ""}, "p"))
        self.assertIsNone(_explicit_type({"q": "text) , x => (SELECT 1"}, "p"))

    def test_anything_but_one_bare_identifier_is_refused(self):
        for explicit_type in TYPES__unsafe:
            with self.subTest(explicit_type=explicit_type):
                self.assertUnsafe({"p": explicit_type})

    def test_values_that_are_not_strings_are_refused(self):
        for explicit_type in [1, ["text"], {"text": 1}, True]:
            with self.subTest(explicit_type=explicit_type):
                self.assertUnsafe({"p": explicit_type})

    def test_explicit_types_must_be_an_object(self):
        for explicit_types in [["text"], "text", 1]:
            with self.subTest(explicit_types=explicit_types):
                self.assertUnsafe(explicit_types)


class TestCallProc(unittest.TestCase):

    def call_proc(self, inputs, federation_procedures=()):
        with mock.patch.object(model, "submit", return_value="submitted") as submitted, \
                mock.patch.object(model, "is_federation_procedure", side_effect=lambda _, name: name in federation_procedures) as looked_up:
            self.looked_up = looked_up
            result = JAAQLModel.call_proc(stub_model(), inputs, "account")
        return result, submitted

    def test_a_federation_procedure_is_refused(self):
        with mock.patch.object(model, "submit") as submitted, \
                mock.patch.object(model, "is_federation_procedure", return_value=True) as looked_up:
            with self.assertRaises(HttpStatusException) as caught:
                JAAQLModel.call_proc(stub_model(), {"query": "_system.federate", "parameters": {
                    "account_id": "attacker", "email": "victim@example.com"}}, "attacker")
        self.assertEqual(HTTPStatus.FORBIDDEN, caught.exception.response_code)
        looked_up.assert_called_once_with(None, "_system.federate")
        submitted.assert_not_called()

    def test_other_procedures_are_looked_up_by_their_exact_name_and_called(self):
        result, submitted = self.call_proc({"query": "project.federate_single_policy", "parameters": {"a": 1}},
                                           federation_procedures=("_system.federate",))
        self.assertEqual("submitted", result)
        self.looked_up.assert_called_once_with(None, "project.federate_single_policy")

    def test_a_bad_request_is_refused_before_the_lookup(self):
        with self.assertRaises(HttpStatusException):
            self.call_proc({"query": "_system.federate", "parameters": {"a": "1"}, "explicit_types": {"a": "text--"}},
                           federation_procedures=("_system.federate",))
        self.looked_up.assert_not_called()

    def test_a_generated_call_builds_the_same_sql_as_before(self):
        result, submitted = self.call_proc({
            "application": "app",
            "query": "person.update",
            "parameters": {"number": 1, "email": "a@b.nl", "note": None, "start": "2026-10-06T10:00:00"},
            "explicit_types": {"number": "person_number", "email": "_email", "note": "comment", "start": "_datetime"}
        })
        self.assertEqual("submitted", result)
        self.assertEqual({"_jaaql_procedure": "SELECT * FROM \"person.update\"("
                                              "\n\tnumber => :number::person_number,"
                                              "\n\temail => :email,"
                                              "\n\tnote => :note,"
                                              "\n\tstart => :start )"},
                         submitted.call_args.args[4]["query"])

    def test_a_call_without_explicit_types_is_unchanged(self):
        for inputs in [{"query": "x", "parameters": {"a": 1}}, {"query": "x", "parameters": {"a": 1}, "explicit_types": None}]:
            with self.subTest(inputs=inputs):
                _, submitted = self.call_proc(inputs)
                self.assertEqual({"_jaaql_procedure": "SELECT * FROM \"x\"(\n\ta => :a )"}, submitted.call_args.args[4]["query"])

    def test_an_unsafe_type_is_refused_before_anything_is_submitted(self):
        for explicit_type in TYPES__unsafe:
            with self.subTest(explicit_type=explicit_type):
                with self.assertRaises(HttpStatusException):
                    self.call_proc({"query": "x", "parameters": {"a": "1"}, "explicit_types": {"a": explicit_type}})

    def test_an_unsafe_type_is_refused_even_for_a_null_value(self):
        with self.assertRaises(HttpStatusException):
            self.call_proc({"query": "x", "parameters": {"a": None}, "explicit_types": {"a": "text) , b => (SELECT 1"}})


class TestIsFederationProcedure(unittest.TestCase):

    def test_the_registered_name_is_looked_up_exactly(self):
        for rows, expected in [([{"name": "_system.federate"}], True), ([], False)]:
            with self.subTest(rows=rows):
                with mock.patch.object(handmade_queries, "execute_supplied_statement", return_value=rows) as executed:
                    self.assertIs(expected, handmade_queries.is_federation_procedure("connection", "_system.federate"))
                executed.assert_called_once_with("connection", "SELECT name FROM federation_procedure WHERE name = :name",
                                                 {"name": "_system.federate"}, as_objects=True)


class TestSecurityEventProcedure(unittest.TestCase):

    def run_singleton(self, parameters, explicit_types):
        with mock.patch.object(model, "submit", return_value="submitted") as submitted:
            JAAQLModel._gate_run_singleton(stub_model(), {"application": "app", "parameters": parameters, "explicit_types": explicit_types},
                                           "account", {"database_procedure": "person.add_user"})
        return submitted.call_args.args[4]["query"]

    def test_a_generated_call_builds_the_same_sql_as_before(self):
        self.assertEqual("SELECT * FROM \"person.add_user\"(\n\temail => :email::email,\n\tname => :name\n)",
                         self.run_singleton({"email": "a@b.nl", "name": "A"}, {"email": "email", "name": "_string"}))

    def test_an_unsafe_type_is_refused(self):
        for explicit_type in TYPES__unsafe:
            with self.subTest(explicit_type=explicit_type):
                with self.assertRaises(HttpStatusException):
                    self.run_singleton({"email": "a@b.nl"}, {"email": explicit_type})


if __name__ == "__main__":
    unittest.main()
