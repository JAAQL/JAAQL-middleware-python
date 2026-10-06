"""
The SQL that /call-proc and a security event's procedure call build from the request: names, parameter keys and explicit types.

    python -m unittest jaaql.test.test_call_proc

Needs only the package's requirements: submit is replaced, so no database is reached
"""
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.mvc import model
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

    def call_proc(self, inputs):
        with mock.patch.object(model, "submit", return_value="submitted") as submitted:
            result = JAAQLModel.call_proc(stub_model(), inputs, "account")
        return result, submitted

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
