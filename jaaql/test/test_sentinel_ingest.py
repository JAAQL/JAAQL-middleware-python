"""
Sentinel's ingest route (POST /sentinel/reporting/error) stores every report a browser or cloud reporter can send, whatever BATON it runs:
a body the route accepted before is stored exactly as before, anything else is made to fit Sentinel's error table with each change noted
after the stacktrace (a body over the former 2 MB cap keeps the start and end of its stacktrace), and only a body holding no JSON object or
an object with none of the report keys (400) or one over the route's 16 MiB (413) is refused. Never 500.

    python -m unittest jaaql.test.test_sentinel_ingest

TestReadReport and TestTheRoute need only the package's requirements (the route's INSERT is captured, not run). TestIngestAgainstPostgres
posts every shape through the real route, JAAQLModel.submit (PREVENT_ARBITRARY_QUERIES on) and the interpreter into Sentinel's own error
table, domains, alert tables and error.process_alert on a scratch Postgres with the jaaql extension; it runs only when
JAAQL_TEST_POSTGRES_URI is set to postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database
jaaql_test_ingest and the role jaaql_test_ingest_user. All report bodies here are synthetic, shaped as the reporters send them
"""
import contextlib
import io
import json
import os
import time
import unittest
from unittest import mock

import psycopg

from jaaql.constants import ENDPOINT__report_sentinel_error, ENVIRON__sentinel_url, KEY__database
from jaaql.db import db_utils_no_circ
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_interface import DBInterface
from jaaql.documentation.documentation_internal import DOCUMENTATION__report_sentinel_error
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.mvc.base_controller import BaseJAAQLController
from jaaql.mvc.controller import JAAQLController
from jaaql.mvc.exception_queries import QUERY__fetch_application_schemas, KEY__is_default
from jaaql.mvc.generated_queries import KG__application_schema__name, KG__application__is_live
from jaaql.mvc.model import JAAQLModel
from jaaql.openapi.swagger_documentation import SwaggerFlatResponse, RESPONSE__200_ok
from jaaql.utilities import sentinel_ingest
from jaaql.utilities.crypt_utils import decrypt_raw
from jaaql.test.test_slow_queries import StubModel, StubVault, CRYPT_KEY

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_ingest"
TEST_ROLE = "jaaql_test_ingest_user"
CT = "application/json; charset=utf-8"
NINE = set(sentinel_ingest.REPORT_KEYS)

# A report of today's browser reporter (BATON f6eb175 and later)
BASE = {
    "location": "https://app.example.test/week__planning.html?week=12",
    "source_file": "https://app.example.test/libs/BATON/BATON.browser.33e375.js",
    "error_condensed": "Uncaught TypeError: Cannot read properties of null (reading 'x')",
    "file_line_number": 1234,
    "file_col_number": 56,
    "version": "v0.6.30",
    "source_system": "lesbij",
    "stacktrace": "Throw site:\n\tTypeError: Cannot read properties of null (reading 'x')\n\t    at f (https://app.example.test/libs/BATON/"
                  "BATON.browser.33e375.js:1234:56)",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 "
                  "Safari/604.1",
}
WEBKIT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15"


def variant(**changes):
    body = dict(BASE)
    for key, value in changes.items():
        if value is KeyError:
            body.pop(key, None)
        else:
            body[key] = value
    return body


def encoded(body) -> bytes:
    return json.dumps(body, ensure_ascii=True).encode("utf-8")


def no_stack(message, file, line, col):
    return "No stack available. %s\n\tat %s:%s:%s" % (message, file, line, col)


# The shapes of the refusals in prod's logs (18 Jun - 8 Oct 2026), as synthetic bodies
PROD_REFUSED = {
    # R1, 40 x 422 in Jun/Jul: every report in that window, whatever its shape (the INSERT was refused by PREVENT_ARBITRARY_QUERIES, fixed
    # in 99834d0); the reporter then was BATON f9edf50 (and 713e3cc): a stacktrace of evt.error.stack, null for an error without a stack
    "R1 f9edf50 reporter": dict(BASE, stacktrace="TypeError: Cannot read properties of null (reading 'x')\n    at f (https://app.example.test/"
                                                 "libs/BATON/BATON.browser.33e375.js:1234:56)"),
    "R1 f9edf50 reporter, error without a stack": dict(BASE, error_condensed="Uncaught x", stacktrace=None),
    # R2, 4 x 422 column_number_check since September, iOS Safari 26 on the current reporter: WebKit gives column 0 for every SyntaxError in
    # a loaded script; Script error., the ResizeObserver loop error and a synthetic ErrorEvent give 0:0 in every engine
    "R2 WebKit SyntaxError 1:0": dict(BASE, source_file="https://app.example.test/libs/BATON/BATON.browser.33e375.js",
                                      error_condensed="SyntaxError: Unexpected token ';'", file_line_number=1, file_col_number=0,
                                      stacktrace=no_stack("SyntaxError: Unexpected token ';'",
                                                          "https://app.example.test/libs/BATON/BATON.browser.33e375.js", 1, 0),
                                      user_agent=WEBKIT),
    "R2 WebKit truncated script 4:0": dict(BASE, source_file="https://app.example.test/index.7684cd.js",
                                           error_condensed="SyntaxError: Unexpected end of script", file_line_number=4, file_col_number=0,
                                           stacktrace=no_stack("SyntaxError: Unexpected end of script",
                                                               "https://app.example.test/index.7684cd.js", 4, 0), user_agent=WEBKIT),
    "R2 Script error. 0:0": dict(BASE, source_file="", error_condensed="Script error.", file_line_number=0, file_col_number=0,
                                 stacktrace=no_stack("Script error.", "unknown file", 0, 0)),
    "R2 ResizeObserver loop 0:0": dict(BASE, source_file="", error_condensed="ResizeObserver loop completed with undelivered notifications.",
                                       file_line_number=0, file_col_number=0,
                                       stacktrace=no_stack("ResizeObserver loop completed with undelivered notifications.", "unknown file",
                                                           0, 0)),
    # R3, 1 x 400 (a manual curl test): no location
    "R3 no location": variant(location=KeyError),
}

# Every other way CLASSIFY.md found a browser report refused, by reporter family, as the reporters shape it
BROWSER_REFUSED = {
    "column past 999999 (minified bundle)": variant(file_line_number=1, file_col_number=1000017),
    "line past 999999": variant(file_line_number=1000006, file_col_number=7),
    "location over 512": variant(location="https://app.example.test/index.html?code=" + "c" * 600 + "#state=" + "s" * 50),
    "source_file over 255 with a query": variant(source_file="https://app.example.test/x.js?sig=" + "q" * 300),
    "source_file over 255 without a query": variant(source_file="https://app.example.test/" + "d/" * 150 + "x.js"),
    "version over 40": variant(version="v0.3.27-acceptance-1abc290bb59cd28a1e15c804771defbac7ff4858"),
    "alias with _ and .": variant(source_system="Cloud_Sheet.eu"),
    "alias over 63": variant(source_system="a" * 70),
    "NUL in the message and stack": variant(error_condensed="Uncaught Error: a\u0000b", stacktrace="Throw site:\n\tError: a\u0000b"),
    "NUL in a parameter value": variant(stacktrace="Parameters supplied:\n\t{\n\t\t\"name\": \"a\u0000b\"\n\t}"),
    "lone surrogate in the message": variant(error_condensed="Uncaught Error: \ud83d", stacktrace="Throw site:\n\tError: \ud83d x"),
    "low half alone in the stack": variant(stacktrace="a\ude42b"),
    "non-ASCII user agent": variant(user_agent="Mozilla/5.0 (Linux; Android 14) Chrome/141.0 Mobile Safari/537.36 Bibliothe\u0301que/2.1 \U0001F642"),
    "plain Event(\"error\")": {"location": BASE["location"], "version": "v0.6.30", "source_system": "lesbij",
                               "stacktrace": no_stack("Unknown error", "unknown file", "undefined", "undefined"), "user_agent": BASE["user_agent"]},
    "appVersion undefined": variant(version=KeyError),
    "appVersion a number": variant(version=1.2),
    "unhandled rejection (current reporter)": variant(source_file="(unhandled promise rejection)", file_line_number=0, file_col_number=1,
                                                      error_condensed="Unhandled promise rejection: x"),
}

# The route's own refusals (CLASSIFY.md section 6) that no reporter is known to send, all stored now
ROUTE_REFUSED = {
    "unknown key": variant(foo="bar"),
    "ip_address in the body": variant(ip_address="198.51.100.7"),
    "line as a list": variant(file_line_number=[1]),
    "line as true": variant(file_line_number=True),
    "line as 12.0": variant(file_line_number=12.0),
    "line as 12.5": variant(file_line_number=12.5),
    "line as ' 12'": variant(file_line_number=" 12"),
    "line as 'abc'": variant(file_line_number="abc"),
    "line -1": variant(file_line_number=-1),
    "line 2147483648": variant(file_line_number=2147483648),
    "line 10**21": variant(file_line_number=10 ** 21),
    "column -1": variant(file_col_number=-1),
    "location a number": variant(location=5),
    "source_file false": variant(source_file=False),
    "error_condensed a list": variant(error_condensed=["Uncaught"]),
    "stacktrace an object": variant(stacktrace={"a": 1}),
    "version an object": variant(version={"v": 1}),
    "source_system a number": variant(source_system=7),
    "user_agent a number": variant(user_agent=5),
    "source_system non-ASCII": variant(source_system="l\u00e9sbij"),
    "source_system with a space": variant(source_system="les bij"),
    "null source_system": variant(source_system=None),
    "null stacktrace": variant(stacktrace=None),
    "null location": variant(location=None),
    "missing error_condensed": variant(error_condensed=KeyError),
    "missing source_file": variant(source_file=KeyError),
    "lone surrogate in every string": {key: (value + "\ud83d" if isinstance(value, str) else value) for key, value in BASE.items()},
    "NUL in every string": {key: (value[:5] + "\u0000" + value[5:] if isinstance(value, str) else value) for key, value in BASE.items()},
}

# Bodies the route accepted before; each must be stored exactly as before
ACCEPTED_BEFORE = {
    "baseline": BASE,
    "line and column as digit strings": variant(file_line_number="12", file_col_number="7"),
    "no line, column or user agent": variant(file_line_number=KeyError, file_col_number=KeyError, user_agent=KeyError),
    "null line, column and user agent": variant(file_line_number=None, file_col_number=None, user_agent=None),
    "line 0, column 1 (a rejection)": variant(file_line_number=0, file_col_number=1),
    "line and column at 999999": variant(file_line_number=999999, file_col_number=999999),
    "empty strings": variant(location="", source_file="", error_condensed="", stacktrace="", version="", source_system=""),
    "padded strings": variant(location="  " + BASE["location"] + "\n", source_system="  lesbij  ", stacktrace="\n" + BASE["stacktrace"] + "\n"),
    "mixed-case alias": variant(source_system="LesBij"),
    "lengths at each limit": variant(location="x" * 512, source_file="x" * 255, version="x" * 40, source_system="a" * 63),
    "message over 200": variant(error_condensed="m" * 5000),
    "emoji everywhere": {key: (value + " \U0001F642" if isinstance(value, str) and key not in ("source_system", "user_agent") else value)
                         for key, value in BASE.items()},
    "other control characters": variant(stacktrace="a\u0001\u0008\u001b\u007f\u0085\u2028 b"),
    "NUL in the user agent (ASCII)": variant(user_agent="Mozilla/5.0 a\u0000b"),
    "a long stacktrace": variant(stacktrace="s" * 1000000),
}


# An ObjectError report of BATON ca62c63 to f6eb175 (LesBij v0.6.7 to v0.6.30): whole parameter values, then the stack sections. Over the
# former 2 MB cap; nginx in front of the route caps it at 1 MiB until its location for the route is raised
FORMER_CAP = 2 * 1024 * 1024
OLD_OBJECT_ERROR = variant(
    error_condensed="Uncaught ObjectError: value too long for type character varying(255)", source_file="https://app.example.test/libs/BATON/"
    "BATON.jaaql.5c1e2a.js",
    stacktrace="Failing query:\n\tSELECT \"document.persist\"(:name, :content)\n\nParameters supplied:\n\t{\n\t\t\"name\": \"scan.pdf\",\n\t\t"
               "\"content\": \"" + "QUJD" * 800000 + "\"\n\t}\n\nError code: 1004\n\nOriginating call:\n\tError\n\t    at save (https://app.example.test/"
               "document__edit.frame.js:88:12)\n\nThrow site:\n\tObjectError: value too long\n\t    at XMLHttpRequest.onload (https://app.example.test/"
               "libs/BATON/BATON.jaaql.5c1e2a.js:743:19)")


def former_inputs(body: dict, args: dict = None) -> dict:
    """
    The values the route bound before, for a body it accepted: get_input_as_dictionary's merge and validate_data
    """
    data = {**(args or {}), **body}
    BaseJAAQLController.validate_data(DOCUMENTATION__report_sentinel_error.methods[0], data, True)
    return data


def ensure_200_documented():
    # As create_app's produce_all_documentation leaves it at boot: a method that declares no 200 answers 200 OK
    for method in DOCUMENTATION__report_sentinel_error.methods:
        if not any(response.code == 200 for response in method.responses):
            method.responses.append(SwaggerFlatResponse(RESPONSE__200_ok))


class TestReadReport(unittest.TestCase):

    def read(self, body, content_type=CT, args=None):
        return sentinel_ingest.read_report(body if isinstance(body, bytes) else encoded(body), content_type, args)

    def notes(self, report):
        heading = "\n" + sentinel_ingest.NOTES__heading + "\n"
        return report["stacktrace"].split(heading, 1)[1].split("\n") if heading in "\n" + report["stacktrace"] else []

    def test_a_body_accepted_before_is_read_exactly_as_before(self):
        for name, body in ACCEPTED_BEFORE.items():
            with self.subTest(name):
                self.assertEqual(former_inputs(dict(body)), self.read(body))

    def test_content_types_accepted_before_are_read_as_before(self):
        for content_type in ["application/json", "application/json;charset=UTF-8", "application/json; charset=UTF-8",
                             "application/json; charset=utf-8; foo=bar"]:
            with self.subTest(content_type):
                self.assertEqual(former_inputs(dict(BASE)), self.read(BASE, content_type))

    def test_the_query_string_fills_a_missing_key_as_before(self):
        body = variant(version=KeyError)
        self.assertEqual(former_inputs(dict(body), {"version": "v9"}), self.read(body, args={"version": "v9"}))
        self.assertEqual(12, self.read(variant(file_line_number=KeyError), args={"file_line_number": "12"})["file_line_number"])

    def test_the_result_has_exactly_the_nine_keys(self):
        for name, body in {**PROD_REFUSED, **BROWSER_REFUSED, **ROUTE_REFUSED, **ACCEPTED_BEFORE}.items():
            with self.subTest(name):
                self.assertEqual(NINE, set(self.read(body)))

    def test_column_zero_is_stored_as_null(self):
        for name in ["R2 WebKit SyntaxError 1:0", "R2 WebKit truncated script 4:0", "R2 Script error. 0:0", "R2 ResizeObserver loop 0:0"]:
            with self.subTest(name):
                body = PROD_REFUSED[name]
                report = self.read(body)
                self.assertIsNone(report["file_col_number"])
                self.assertEqual(body["file_line_number"], report["file_line_number"])
                self.assertEqual(body["stacktrace"] + "\n\nIngest adjustments:\n\t- file_col_number: 0 is not a column number within 1..999999, "
                                                      "stored as NULL", report["stacktrace"])
                self.assertEqual({key: body[key] for key in NINE - {"file_col_number", "stacktrace"}},
                                 {key: report[key] for key in NINE - {"file_col_number", "stacktrace"}})

    def test_a_null_stacktrace_gets_the_text_newer_reporters_send(self):
        report = self.read(PROD_REFUSED["R1 f9edf50 reporter, error without a stack"])
        self.assertEqual(no_stack("Uncaught x", BASE["source_file"], 1234, 56) + "\n\nIngest adjustments:\n\t- stacktrace: null, stored as the "
                         "browser reporters' text for an error without a stack", report["stacktrace"])
        report = self.read(variant(stacktrace=KeyError, error_condensed=KeyError, source_file=KeyError, file_line_number=KeyError))
        self.assertTrue(report["stacktrace"].startswith(no_stack("Unknown error", "unknown file", "undefined", 56) + "\n\nIngest adjustments:"))

    def test_missing_values_get_defaults(self):
        report = self.read(BROWSER_REFUSED["plain Event(\"error\")"])
        self.assertEqual(("", "Unknown error", None, None), (report["source_file"], report["error_condensed"], report["file_line_number"],
                                                              report["file_col_number"]))
        self.assertEqual(["\t- source_file: missing, stored as \"\"", "\t- error_condensed: missing, stored as \"Unknown error\""],
                         self.notes(report))
        self.assertEqual(("", ["\t- location: missing, stored as \"\""]), (self.read(PROD_REFUSED["R3 no location"])["location"],
                                                                           self.notes(self.read(PROD_REFUSED["R3 no location"]))))
        self.assertEqual("", self.read(variant(version=KeyError))["version"])
        self.assertEqual("baton-generator", self.read(variant(source_system=None))["source_system"])

    def test_positions_out_of_the_domains_are_null_with_the_value_noted(self):
        cases = [("file_col_number", 1000017, None, "1000017 is not a column number within 1..999999"),
                 ("file_line_number", 1000006, None, "1000006 is not a line number within 0..999999"),
                 ("file_line_number", -1, None, "-1 is not a line number"), ("file_line_number", 2147483648, None, "2147483648 is not"),
                 ("file_line_number", 10 ** 21, None, "1000000000000000000000 is not"), ("file_line_number", [1], None, "[1] is not"),
                 ("file_line_number", True, None, "true is not"), ("file_line_number", 12.5, None, "12.5 is not"),
                 ("file_line_number", "abc", None, "\"abc\" is not"), ("file_line_number", "1" * 30, None, "is not"),
                 ("file_line_number", "-5", None, "\"-5\" is not"), ("file_col_number", -1, None, "-1 is not a column"),
                 ("file_line_number", 12.0, 12, "12.0 stored as 12"), ("file_line_number", " 12", 12, "\" 12\" stored as 12"),
                 ("file_line_number", "012", 12, "\"012\" stored as 12"), ("file_col_number", 1e+3, 1000, "1000.0 stored as 1000")]
        for key, value, stored, note in cases:
            with self.subTest(key=key, value=value):
                report = self.read(variant(**{key: value}))
                self.assertEqual(stored, report[key])
                self.assertEqual(1, len(self.notes(report)))
                self.assertIn(note, self.notes(report)[0])
        report = self.read(encoded(BASE).replace(b"1234", b"NaN"))
        self.assertEqual((None, ["\t- file_line_number: NaN is not a line number within 0..999999, stored as NULL"]),
                         (report["file_line_number"], self.notes(report)))

    def test_strings_are_cut_to_their_columns(self):
        report = self.read(BROWSER_REFUSED["location over 512"])
        self.assertEqual(BROWSER_REFUSED["location over 512"]["location"][:512], report["location"])
        self.assertEqual(["\t- location: %d characters, cut to the first 512" % len(BROWSER_REFUSED["location over 512"]["location"])],
                         self.notes(report))
        self.assertEqual("https://app.example.test/x.js", self.read(BROWSER_REFUSED["source_file over 255 with a query"])["source_file"])
        long_path = self.read(BROWSER_REFUSED["source_file over 255 without a query"])["source_file"]
        self.assertEqual((255, "..."), (len(long_path), long_path[:3]))
        self.assertTrue(long_path.endswith("/d/x.js"))
        self.assertEqual(BROWSER_REFUSED["version over 40"]["version"][:40], self.read(BROWSER_REFUSED["version over 40"])["version"])
        self.assertEqual("m" * 5000, self.read(variant(error_condensed="m" * 5000))["error_condensed"])

    def test_source_system_is_made_a_system_name(self):
        for sent, stored in [("Cloud_Sheet.eu", "cloud-sheet-eu"), ("a" * 70, "a" * 63), ("l\u00e9sbij", "l-sbij"), ("les bij", "les-bij"),
                             (7, "7"), ("\u00e9\u00e9", "-"), ("LesBij", "LesBij"), ("", ""), ("  lesbij  ", "lesbij")]:
            with self.subTest(sent):
                self.assertEqual(stored, self.read(variant(source_system=sent))["source_system"])

    def test_text_postgres_cannot_store_is_replaced_one_for_one(self):
        report = self.read(ROUTE_REFUSED["NUL in every string"])
        for key in ["location", "source_file", "error_condensed", "version"]:
            self.assertEqual(BASE[key][:5] + "\ufffd" + BASE[key][5:], report[key])
        self.assertEqual(BASE["user_agent"][:5] + "\u0000" + BASE["user_agent"][5:], report["user_agent"])
        self.assertTrue(report["stacktrace"].startswith(BASE["stacktrace"][:5] + "\ufffd" + BASE["stacktrace"][5:]))
        report = self.read(ROUTE_REFUSED["lone surrogate in every string"])
        self.assertEqual(BASE["location"] + "\ufffd", report["location"])
        self.assertEqual(BASE["user_agent"] + "\\ud83d", report["user_agent"])
        self.assertEqual("a\ufffdb\n\nIngest adjustments:\n\t- stacktrace: 1 character(s) Postgres cannot store (NUL, half a surrogate pair) "
                         "replaced by U+FFFD", self.read(BROWSER_REFUSED["low half alone in the stack"])["stacktrace"])
        self.assertEqual("x \U0001F642", self.read(variant(error_condensed="x \U0001F642"))["error_condensed"])

    def test_a_non_ascii_user_agent_is_escaped(self):
        report = self.read(BROWSER_REFUSED["non-ASCII user agent"])
        self.assertEqual("Mozilla/5.0 (Linux; Android 14) Chrome/141.0 Mobile Safari/537.36 Bibliothe\\u0301que/2.1 \\ud83d\\ude42",
                         report["user_agent"])
        self.assertEqual(["\t- user_agent: 2 non-ASCII character(s) stored as \\uXXXX escapes"], self.notes(report))
        self.assertTrue(report["user_agent"].isascii())
        self.assertNotIn("Bibliothe", report["stacktrace"])

    def test_non_strings_are_stored_as_their_json_text(self):
        for key, value, stored in [("location", 5, "5"), ("source_file", False, "false"), ("error_condensed", ["Uncaught"], "[\"Uncaught\"]"),
                                   ("stacktrace", {"a": 1}, "{\"a\": 1}"), ("version", 1.2, "1.2"), ("user_agent", 5, "5")]:
            with self.subTest(key):
                report = self.read(variant(**{key: value}))
                self.assertTrue(report[key].startswith(stored))
                self.assertIn("\t- %s: %s, stored as its JSON text" % (key, sentinel_ingest.type_name(value)), self.notes(report))

    def test_unknown_keys_are_ignored_and_noted(self):
        report = self.read(variant(foo="bar", error_id={"x": 1}))
        self.assertEqual(former_inputs(dict(BASE)), dict(report, stacktrace=BASE["stacktrace"]))
        self.assertEqual(["\t- unknown key \"foo\" ignored: \"bar\"", "\t- unknown key \"error_id\" ignored: {\"x\": 1}"], self.notes(report))
        report = self.read(variant(ip_address="198.51.100.7"))
        self.assertEqual(["\t- ip_address ignored: the address stored is the one the request came from"], self.notes(report))
        self.assertNotIn("198.51.100.7", report["stacktrace"])
        report = self.read(dict(BASE, **{"k%02d" % i: "v" * 2000 for i in range(30)}))
        self.assertEqual(21, len(self.notes(report)))
        self.assertEqual("\t- 10 more unknown keys ignored", self.notes(report)[-1])
        self.assertLess(len(report["stacktrace"]), len(BASE["stacktrace"]) + 20 * 1100)

    def test_the_query_string_never_loses_a_report(self):
        report = self.read(BASE, args={"x": "1", "version": "v9"})
        self.assertEqual("v0.6.30", report["version"])
        self.assertEqual(["\t- query string: \"x\" ignored", "\t- query string: version ignored, the body has it"], self.notes(report))
        report = self.read(BASE, args={"q%02d" % i: "v" for i in range(30)})
        self.assertEqual((21, "\t- query string: 10 more keys ignored"), (len(self.notes(report)), self.notes(report)[-1]))

    def test_any_content_type_is_read_as_json(self):
        for content_type in ["Application/JSON; charset=utf-8", "application/json ; charset=utf-8", "application/json; charset=utf8",
                             "application/json; charset=\"utf-8\"", "application/json; charset=iso-8859-1", "text/plain;charset=UTF-8",
                             "text/plain", "application/x-www-form-urlencoded", None]:
            with self.subTest(content_type):
                report = self.read(BASE, content_type)
                self.assertEqual(former_inputs(dict(BASE)), dict(report, stacktrace=BASE["stacktrace"]))
                self.assertEqual(1, len(self.notes(report)))

    def test_bodies_json_parsing_accepted_before_and_lenient_ones(self):
        self.assertEqual(former_inputs(dict(BASE)), self.read(b"\xef\xbb\xbf" + encoded(BASE)))
        self.assertEqual("v9", self.read(encoded(BASE)[:-1] + b", \"version\": \"v9\"}")["version"])
        report = self.read(encoded(BASE).replace(b"Uncaught", b"Unc\xffaught"))
        self.assertEqual("Unc\ufffdaught" + BASE["error_condensed"][8:], report["error_condensed"])
        self.assertIn("the body is not valid UTF-8", self.notes(report)[0])
        report = self.read(encoded(BASE).replace(b"Throw site:\\n", b"Throw site:\x01"))
        self.assertIn("the body is not strict JSON", self.notes(report)[0])

    def test_only_a_body_without_a_json_object_is_refused(self):
        for raw in [b"", b"null", b"\"x\"", b"123", b"[]", encoded([BASE]), encoded(BASE)[:-5], b"{", b"[" * 100000 + b"]" * 100000,
                    b"\xff\xfe"]:
            with self.subTest(raw[:20]):
                with self.assertRaises(HttpStatusException) as raised:
                    self.read(raw)
                self.assertEqual((400, "Expected a JSON object"), (raised.exception.response_code, raised.exception.message))

    def test_an_integer_too_long_for_python_is_read_as_its_digits(self):
        # JSON.stringify never writes one (it writes 1e+308), but an object holding one is a report all the same
        report = self.read(encoded(BASE).replace(b'"file_line_number": 1234', b'"file_line_number": ' + b"9" * 5000))
        self.assertIsNone(report["file_line_number"])
        self.assertIn("the body is not strict JSON", self.notes(report)[0])
        self.assertTrue(self.notes(report)[1].startswith("\t- file_line_number: \"9999"))
        self.assertTrue(self.notes(report)[1].endswith("... is not a line number within 0..999999, stored as NULL"))
        report = self.read(encoded(dict(BASE, extra=1)).replace(b'"extra": 1', b'"extra": ' + b"1" * 5000))
        self.assertEqual(former_inputs(dict(BASE)), dict(report, stacktrace=BASE["stacktrace"]))
        self.assertTrue(self.notes(report)[1].startswith("\t- unknown key \"extra\" ignored: \"1111"))

    def test_an_object_without_any_report_key_is_refused(self):
        # No reporter sends one; storing it would let any probe make a row and queue an alert
        for body in [{}, {"test": 1}, {"query": "{ __typename }"}, {"Location": "x", "STACKTRACE": "y"}, {"ip_address": "198.51.100.7"}]:
            with self.subTest(body):
                with self.assertRaises(HttpStatusException) as raised:
                    self.read(body)
                self.assertEqual((400, "Expected a report"), (raised.exception.response_code, raised.exception.message))
        # One of the nine is enough, in the body or in the query string (the route took the nine from the query string before)
        self.assertEqual("x", self.read({"error_condensed": "x"})["error_condensed"])
        self.assertEqual("https://a.test/", self.read({}, args={"location": "https://a.test/"})["location"])

    def test_a_long_user_agent_the_route_did_not_take_before_is_cut_before_it_is_escaped(self):
        agent = "Mozilla/5.0 " + "\u00e9" * (1024 * 1024)
        raw = json.dumps(variant(user_agent=agent), ensure_ascii=False).encode("utf-8")
        started = time.perf_counter()
        with mock.patch.object(sentinel_ingest, "ascii_escaped", side_effect=sentinel_ingest.ascii_escaped) as spy:
            report = self.read(raw)
        elapsed = time.perf_counter() - started
        self.assertEqual([2048], [len(call.args[0]) for call in spy.call_args_list])
        self.assertEqual("Mozilla/5.0 " + "\\u00e9" * 2036, report["user_agent"])
        self.assertEqual(["\t- user_agent: %d characters, cut to the first 2048" % len(agent),
                          "\t- user_agent: 2036 non-ASCII character(s) stored as \\uXXXX escapes"], self.notes(report))
        self.assertLess(elapsed, 0.1)
        self.assertEqual(2048 * 12, len(self.read(variant(user_agent="\U0001F642" * 5000))["user_agent"]))
        report = self.read(variant(user_agent=["x" * 3000]))
        self.assertEqual(('["' + "x" * 2046, ["\t- user_agent: a list, stored as its JSON text", "\t- user_agent: 3004 characters, cut to the first 2048"]),
                         (report["user_agent"], self.notes(report)))
        # An ASCII agent was taken before, whatever its length, and still is, as it was
        self.assertEqual(("a" * 1500000, []), (self.read(variant(user_agent="a" * 1500000))["user_agent"],
                                              self.notes(self.read(variant(user_agent="a" * 1500000)))))

    def test_a_personal_value_under_another_key_is_not_quoted(self):
        report = self.read(dict(BASE, userAgent="Mozilla/5.0 agent-x", ipAddress="198.51.100.7", ua="UA-1", IP="198.51.100.8",
                                remote_addr="198.51.100.9", user_agent_full="UA-2"))
        for value in ["agent-x", "198.51.100", "UA-1", "UA-2"]:
            self.assertNotIn(value, report["stacktrace"])
        self.assertEqual(["\t- unknown key \"%s\" ignored, its value not quoted: it may be personal data, which Sentinel stores encrypted" % key
                          for key in ["userAgent", "ipAddress", "ua", "IP", "remote_addr", "user_agent_full"]], self.notes(report))
        self.assertEqual(["\t- unknown key \"display\" ignored: \"wide\""], self.notes(self.read(dict(BASE, display="wide"))))

    def test_a_body_over_the_former_cap_keeps_the_start_and_end_of_its_stacktrace(self):
        raw = encoded(dict(OLD_OBJECT_ERROR, user_agent="Mozilla/5.0 " + "a" * 3000))
        self.assertGreater(len(raw), FORMER_CAP)
        report = sentinel_ingest.read_report(raw, CT, None, FORMER_CAP)
        stack, notes = report["stacktrace"].split("\n\nIngest adjustments:\n")
        sent = OLD_OBJECT_ERROR["stacktrace"]
        start = sentinel_ingest.LIMIT__stacktrace - sentinel_ingest.LIMIT__stacktrace_end - len("\n\n[... %d characters cut ...]\n\n" % (
            len(sent) - sentinel_ingest.LIMIT__stacktrace))
        self.assertEqual(sentinel_ingest.LIMIT__stacktrace, len(stack))
        self.assertEqual(sent[:start] + "\n\n[... %d characters cut ...]\n\n" % (len(sent) - sentinel_ingest.LIMIT__stacktrace) +
                         sent[-sentinel_ingest.LIMIT__stacktrace_end:], stack)
        for section in ["Failing query:", "Parameters supplied:", "Error code: 1004", "Originating call:", "Throw site:"]:
            self.assertIn(section, stack)
        self.assertEqual(["\t- the body is %d bytes, over the %d the route took before" % (len(raw), FORMER_CAP),
                          "\t- user_agent: 3012 characters, cut to the first 2048",
                          "\t- stacktrace: %d characters in a body over the former size cap, cut to its first %d and last 65536" % (len(sent), start)],
                         notes.split("\n"))
        self.assertEqual("Mozilla/5.0 " + "a" * 2036, report["user_agent"])
        self.assertEqual({key: OLD_OBJECT_ERROR[key] for key in NINE - {"stacktrace", "user_agent"}},
                         {key: report[key] for key in NINE - {"stacktrace", "user_agent"}})
        # Without a stack, the text made for one is cut the same way; under the cap nothing is cut
        report = sentinel_ingest.read_report(encoded(variant(stacktrace=None, error_condensed="m" * 2200000)), CT, None, FORMER_CAP)
        self.assertEqual(sentinel_ingest.LIMIT__stacktrace, len(report["stacktrace"].split("\n\nIngest adjustments:\n")[0]))
        self.assertEqual(former_inputs(variant(stacktrace="s" * 2000000)), sentinel_ingest.read_report(
            encoded(variant(stacktrace="s" * 2000000)), CT, None, FORMER_CAP))

    def test_a_fault_in_reading_falls_back_to_the_string_fields(self):
        with mock.patch.object(sentinel_ingest, "position", side_effect=ZeroDivisionError("bug")):
            report = self.read(dict(BASE, user_agent="u\u00e9", source_system="Bad_Name", location="\u0000" + "x" * 600))
        self.assertEqual(NINE, set(report))
        self.assertEqual(("\ufffd" + "x" * 511, BASE["source_file"], None, None, None, "baton-generator"),
                         (report["location"], report["source_file"], report["file_line_number"], report["file_col_number"],
                          report["user_agent"], report["source_system"]))
        self.assertEqual(BASE["stacktrace"] + "\n\nIngest adjustments:\n\t- the report could not be read in full (ZeroDivisionError), so only "
                                              "its string fields were stored", report["stacktrace"])


class RouteCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_200_documented()

    def make_client(self, model):
        env = {k: v for k, v in os.environ.items() if k != ENVIRON__sentinel_url}
        with mock.patch.dict(os.environ, env, clear=True):
            controller = JAAQLController(model, True, "http+unix://%2Ftmp%2Fjaaql.sock")
        controller.create_app()
        return controller.app.test_client()

    def post(self, raw, content_type=CT, path_suffix="", real_ip="203.0.113.5"):
        headers = {"X-Real-IP": real_ip}
        if content_type is not None:
            headers["Content-Type"] = content_type
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return self.client.post(ENDPOINT__report_sentinel_error + path_suffix, data=raw if isinstance(raw, bytes) else encoded(raw),
                                    headers=headers)


class TestTheRoute(RouteCase):
    """
    The route with its INSERT captured instead of run
    """

    def setUp(self):
        self.model = StubModel()
        self.inserted = []

        def submit(inputs, account_id, **kwargs):
            if inputs["query"].startswith("insert into error"):
                self.inserted.append(dict(inputs["parameters"]))
                return {"error_id": "e%d" % len(self.inserted)}
            return None
        self.model.submit = submit
        self.client = self.make_client(self.model)

    def test_every_report_shape_is_answered_200_and_inserted_with_the_nine_keys(self):
        for name, body in {**PROD_REFUSED, **BROWSER_REFUSED, **ROUTE_REFUSED, **ACCEPTED_BEFORE}.items():
            with self.subTest(name):
                self.inserted.clear()
                res = self.post(body)
                self.assertEqual(200, res.status_code, res.data)
                self.assertEqual(1, len(self.inserted))
                self.assertEqual(NINE | {"ip_address"}, set(self.inserted[0]))
                self.assertEqual("203.0.113.5", self.inserted[0]["ip_address"])

    def test_a_body_accepted_before_is_bound_exactly_as_before(self):
        for name, body in ACCEPTED_BEFORE.items():
            with self.subTest(name):
                self.inserted.clear()
                self.assertEqual(200, self.post(body).status_code)
                self.assertEqual(dict(former_inputs(dict(body)), ip_address="203.0.113.5"), self.inserted[0])

    def test_the_query_string_and_any_content_type(self):
        self.assertEqual(200, self.post(variant(version=KeyError), path_suffix="?version=v9&x=1").status_code)
        self.assertEqual("v9", self.inserted[-1]["version"])
        for content_type in ["text/plain;charset=UTF-8", "Application/JSON; charset=utf-8", "application/json; charset=utf8", None]:
            with self.subTest(content_type):
                self.assertEqual(200, self.post(BASE, content_type).status_code)
                self.assertEqual(BASE["location"], self.inserted[-1]["location"])

    def test_an_ip_address_in_the_body_never_replaces_the_requests(self):
        self.assertEqual(200, self.post(variant(ip_address="198.51.100.7")).status_code)
        self.assertEqual("203.0.113.5", self.inserted[-1]["ip_address"])

    def test_a_body_without_a_json_object_is_400_and_never_500(self):
        # null, a string and a number were 500 (UnhandledJaaqlServerError) before, and so was nesting too deep for the parser
        for raw in [b"", b"null", b"\"x\"", b"123", b"[]", encoded([BASE]), encoded(BASE)[:-5], b"[" * 100000 + b"]" * 100000]:
            with self.subTest(raw[:20]):
                res = self.post(raw)
                self.assertEqual((400, b"Expected a JSON object"), (res.status_code, res.data))
        for raw in [b"{}", b"{\"test\": 1}"]:
            with self.subTest(raw):
                res = self.post(raw)
                self.assertEqual((400, b"Expected a report"), (res.status_code, res.data))
        self.assertEqual([], self.inserted)

    def test_a_body_over_the_former_size_limit_is_stored_cut_and_one_over_the_routes_is_413(self):
        self.assertEqual(200, self.post(variant(stacktrace="s" * 1900000)).status_code)
        self.assertEqual("s" * 1900000, self.inserted[-1]["stacktrace"])
        res = self.post(OLD_OBJECT_ERROR)
        self.assertEqual(200, res.status_code, res.data)
        stack = self.inserted[-1]["stacktrace"].split("\n\nIngest adjustments:\n")[0]
        self.assertEqual((sentinel_ingest.LIMIT__stacktrace, True), (len(stack), stack.endswith(OLD_OBJECT_ERROR["stacktrace"][-65536:])))
        self.inserted.clear()
        res = self.post(variant(stacktrace="s" * sentinel_ingest.LIMIT__body))
        self.assertEqual(413, res.status_code)
        self.assertEqual([], self.inserted)

    def test_a_report_stored_is_answered_200_though_its_alert_fails(self):
        # The INSERT has committed: an error answer would only make the reporter send it again, as a second row
        def submit(inputs, account_id, **kwargs):
            if inputs["query"].startswith("insert into error"):
                self.inserted.append(dict(inputs["parameters"]))
                return {"error_id": "e1"}
            raise HttpStatusException("process_alert failed")
        self.model.submit = submit
        res = self.post(BASE)
        self.assertEqual(200, res.status_code, res.data)
        self.assertEqual(1, len(self.inserted))

    def test_a_fault_in_reading_is_stored_from_the_string_fields(self):
        with mock.patch.object(sentinel_ingest, "normalise", side_effect=ZeroDivisionError("bug")):
            res = self.post(BASE)
        self.assertEqual(200, res.status_code, res.data)
        self.assertIsNone(self.inserted[-1]["user_agent"])

    def test_a_fault_even_in_the_fallback_is_422_never_500(self):
        with mock.patch.object(sentinel_ingest, "normalise", side_effect=ZeroDivisionError("bug")), \
                mock.patch.object(sentinel_ingest, "fallback", side_effect=KeyError("worse")):
            res = self.post(BASE)
        self.assertEqual(422, res.status_code, res.data)
        self.assertEqual([], self.inserted)

    def test_a_database_failure_is_still_422(self):
        def failing(inputs, account_id, **kwargs):
            raise HttpStatusException("the database is down")
        self.model.submit = failing
        res = self.post(BASE)
        self.assertEqual((422, b"the database is down"), (res.status_code, res.data))

    def test_the_preflight_is_unchanged(self):
        res = self.client.options(ENDPOINT__report_sentinel_error)
        self.assertEqual(200, res.status_code)
        self.assertEqual("*", res.headers.get("Access-Control-Allow-Origin"))


SENTINEL_DDL = r"""
CREATE DOMAIN encrypted__ip_address AS character varying(200);
CREATE DOMAIN system_name AS character varying(63) CHECK (VALUE ~* '^[a-z0-9\-]*$');
CREATE DOMAIN full_url_allowing_anchor_and_parameters AS character varying(512);
CREATE DOMAIN filename AS character varying(255);
CREATE DOMAIN error_condensed AS character varying(400);
CREATE DOMAIN line_number AS integer CHECK (VALUE between 0 and 999999);
CREATE DOMAIN column_number AS integer CHECK (VALUE between 1 and 999999);
CREATE DOMAIN version AS character varying(40);
CREATE DOMAIN alert_scope AS character varying(20);
CREATE DOMAIN scope_key AS character varying(255);
CREATE DOMAIN alert_template AS character varying(40);
create table error (
    id uuid not null default gen_random_uuid(),
    location full_url_allowing_anchor_and_parameters not null,
    source_file filename not null,
    user_agent text,
    ip_address encrypted__ip_address not null,
    error_condensed error_condensed not null,
    stacktrace text not null,
    file_line_number line_number,
    file_col_number column_number,
    version version not null,
    source_system system_name not null,
    created timestamptz not null default current_timestamp,
    primary key (id),
    check (file_line_number between 0 and 999999),
    check (file_col_number between 1 and 999999) );
create table alert_cooldown (
    scope alert_scope not null,
    scope_key scope_key not null,
    last_alerted timestamptz not null,
    primary key (scope, scope_key) );
create table alert_outbox (
    id uuid not null default gen_random_uuid(),
    template alert_template not null,
    error uuid,
    managed_service_check uuid,
    created timestamptz not null default current_timestamp,
    sent_at timestamptz,
    primary key (id) );
alter table alert_outbox add constraint alert_outbox__error foreign key (error) references error (id) ON DELETE RESTRICT ON UPDATE cascade;
create function "error.process_alert" (id uuid, raw_ip_address text) returns integer as
$$
    DECLARE
        source_system_ text;
        source_file_ text;
        file_line_number_ text;
        ip_key text;
        source_file_key text;
        line_number_key text;
        should_alert bool;
    BEGIN
        SELECT e.source_system, e.source_file, e.file_line_number::text
        INTO source_system_, source_file_, file_line_number_
        FROM error e
        WHERE e.id = "error.process_alert".id;
        ip_key = md5("error.process_alert".raw_ip_address);
        source_file_key = md5(source_system_ || ':' || source_file_);
        line_number_key = md5(source_system_ || ':' || source_file_ || ':' || coalesce(file_line_number_, ''));
        SELECT NOT EXISTS (
            SELECT 1 FROM alert_cooldown ac WHERE
                (ac.scope = 'ip'          AND ac.scope_key = ip_key          AND ac.last_alerted > current_timestamp - interval '3 hours') OR
                (ac.scope = 'source_file' AND ac.scope_key = source_file_key AND ac.last_alerted > current_timestamp - interval '6 hours') OR
                (ac.scope = 'line_number' AND ac.scope_key = line_number_key AND ac.last_alerted > current_timestamp - interval '3 hours')
        ) INTO should_alert;
        if should_alert then
            INSERT INTO alert_outbox (template, error)
            VALUES ('error_reported', "error.process_alert".id);
            INSERT INTO alert_cooldown (scope, scope_key, last_alerted) VALUES
                ('ip',          ip_key,          current_timestamp),
                ('source_file', source_file_key, current_timestamp),
                ('line_number', line_number_key, current_timestamp)
            ON CONFLICT (scope, scope_key) DO UPDATE SET last_alerted = excluded.last_alerted;
        end if;
        return 0;
    END
$$ language plpgsql security definer;
"""
COLUMNS = ["location", "source_file", "error_condensed", "file_line_number", "file_col_number", "version", "source_system", "stacktrace",
           "user_agent"]


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestIngestAgainstPostgres(RouteCase):
    """
    Sentinel's error table (domains.jsql, reset.structure.jsql, its alert tables and error.process_alert as generated), the route's real
    INSERT through JAAQLModel.submit with PREVENT_ARBITRARY_QUERIES on, as on every box
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
        cls.pool_user = DBInterface.fracture_uri(uri)[3]
        cls.test_uri = uri.rsplit("/", 1)[0] + "/" + TEST_DATABASE
        with psycopg.connect(uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("CREATE DATABASE " + TEST_DATABASE)
            admin.execute("DO $$ BEGIN CREATE ROLE " + TEST_ROLE + "; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
        with psycopg.connect(cls.test_uri, autocommit=True) as conn:
            try:
                conn.execute("CREATE SCHEMA jaaql_extension")
                conn.execute("GRANT USAGE ON SCHEMA jaaql_extension TO PUBLIC")
                conn.execute("CREATE EXTENSION jaaql")
            except psycopg.Error as ex:
                raise unittest.SkipTest("the jaaql extension is not available: " + str(ex))
            conn.execute(SENTINEL_DDL)
            conn.execute("GRANT SELECT, INSERT ON error TO " + TEST_ROLE + "; GRANT EXECUTE ON FUNCTION \"error.process_alert\"(uuid, text) TO "
                         + TEST_ROLE)
        cls.vault = StubVault(uri)

    @classmethod
    def tearDownClass(cls):
        pool = DBPGInterface.HOST_POOLS.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        DBPGInterface.HOST_POOLS_QUEUES.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        if pool is not None:
            pool.close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("DROP ROLE IF EXISTS " + TEST_ROLE)

    def setUp(self):
        real_lookup = db_utils_no_circ.execute_supplied_statement

        def lookup(connection, query, parameters=None, **kwargs):
            if query == QUERY__fetch_application_schemas:
                return [{KG__application_schema__name: "default", KEY__database: TEST_DATABASE, KEY__is_default: True,
                         KG__application__is_live: True}]
            return real_lookup(connection, query, parameters, **kwargs)

        self.lookup = mock.patch.object(db_utils_no_circ, "execute_supplied_statement", side_effect=lookup)
        self.lookup.start()
        self.model = StubModel(vault=self.vault, account=TEST_ROLE)
        self.model.prevent_arbitrary_queries = True
        self.model.db_cache = {"default": {KG__application_schema__name: "default", KEY__database: TEST_DATABASE, KEY__is_default: True,
                                           KG__application__is_live: True}}
        self.queries = []

        def submit(inputs, account_id, **kwargs):
            self.queries.append(inputs["query"])
            return JAAQLModel.submit(self.model, inputs, TEST_ROLE, **kwargs)
        self.model.submit = submit
        self.client = self.make_client(self.model)
        self.admin("DELETE FROM alert_outbox; DELETE FROM alert_cooldown; DELETE FROM error")

    def tearDown(self):
        self.lookup.stop()

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def rows(self):
        rows = self.admin("SELECT " + ", ".join(COLUMNS) + ", length(ip_address) > 0 FROM error ORDER BY created, id")
        return [dict(zip(COLUMNS, row[:-1]), user_agent=decrypt_raw(CRYPT_KEY, row[-2]) if row[-2] is not None else None,
                     ip_address_stored=row[-1]) for row in rows]

    def stored(self, raw, content_type=CT, path_suffix=""):
        self.admin("DELETE FROM alert_outbox; DELETE FROM alert_cooldown; DELETE FROM error")
        res = self.post(raw, content_type, path_suffix)
        rows = self.rows()
        self.assertEqual((200, 1), (res.status_code, len(rows)), res.data)
        self.assertEqual(1, self.admin("SELECT count(*) FROM alert_outbox")[0][0])
        return rows[0]

    def expected(self, report):
        return dict(report, error_condensed=report["error_condensed"][:200], ip_address_stored=True)

    def test_every_shape_refused_before_is_stored_as_read(self):
        for name, body in {**PROD_REFUSED, **BROWSER_REFUSED, **ROUTE_REFUSED}.items():
            with self.subTest(name):
                self.assertEqual(self.expected(sentinel_ingest.read_report(encoded(body), CT)), self.stored(body))

    def test_the_prod_refusals_are_stored(self):
        for name in ["R2 WebKit SyntaxError 1:0", "R2 WebKit truncated script 4:0", "R2 Script error. 0:0", "R2 ResizeObserver loop 0:0"]:
            with self.subTest(name):
                row = self.stored(PROD_REFUSED[name])
                self.assertEqual((PROD_REFUSED[name]["file_line_number"], None), (row["file_line_number"], row["file_col_number"]))
        row = self.stored(PROD_REFUSED["R1 f9edf50 reporter"])
        self.assertEqual(PROD_REFUSED["R1 f9edf50 reporter"], {key: row[key] for key in NINE})
        row = self.stored(PROD_REFUSED["R1 f9edf50 reporter, error without a stack"])
        self.assertTrue(row["stacktrace"].startswith(no_stack("Uncaught x", BASE["source_file"], 1234, 56)))
        self.assertEqual("", self.stored(PROD_REFUSED["R3 no location"])["location"])

    def test_a_body_accepted_before_is_stored_exactly_as_before(self):
        # The former route: get_input_as_dictionary's validation, then the same INSERT and process_alert
        self.stored(BASE)
        insert, alert = self.queries[-2:]
        for name, body in ACCEPTED_BEFORE.items():
            with self.subTest(name):
                now = self.stored(body)
                self.admin("DELETE FROM alert_outbox; DELETE FROM alert_cooldown; DELETE FROM error")
                parameters = dict(former_inputs(dict(body)), ip_address="203.0.113.5")
                error_id = self.model.submit({"query": insert, "parameters": parameters, "application": "sentinel"}, "dba", as_objects=True,
                                             singleton=True, server_authored_query=True)["error_id"]
                self.model.submit({"query": alert, "parameters": {"id": error_id, "raw_ip_address": "203.0.113.5"}, "application": "sentinel"},
                                  "dba", server_authored_query=True)
                self.assertEqual(self.rows(), [now])

    def test_the_route_answers_without_a_row_only_when_it_refuses(self):
        for raw, status in [(b"null", 400), (b"[]", 400), (b"{", 400), (b"{}", 400), (b"{\"test\": 1}", 400),
                            (encoded(variant(stacktrace="s" * sentinel_ingest.LIMIT__body)), 413)]:
            with self.subTest(raw[:10]):
                self.assertEqual(status, self.post(raw).status_code)
        self.assertEqual([], self.rows())
        self.assertEqual(0, self.admin("SELECT count(*) FROM alert_outbox")[0][0])

    def test_a_body_over_the_former_cap_is_stored_with_its_stack_sections(self):
        row = self.stored(OLD_OBJECT_ERROR)
        stack = row["stacktrace"].split("\n\nIngest adjustments:\n")[0]
        self.assertEqual(sentinel_ingest.LIMIT__stacktrace, len(stack))
        self.assertTrue(stack.endswith("Throw site:\n\tObjectError: value too long\n\t    at XMLHttpRequest.onload (https://app.example.test/libs/"
                                       "BATON/BATON.jaaql.5c1e2a.js:743:19)"))
        self.assertEqual(self.expected(sentinel_ingest.read_report(encoded(OLD_OBJECT_ERROR), CT, None, FORMER_CAP)), row)

    def test_a_report_is_stored_once_though_its_alert_fails(self):
        self.admin("REVOKE EXECUTE ON FUNCTION \"error.process_alert\"(uuid, text) FROM PUBLIC, " + TEST_ROLE)
        try:
            res = self.post(BASE)
        finally:
            self.admin("GRANT EXECUTE ON FUNCTION \"error.process_alert\"(uuid, text) TO " + TEST_ROLE)
        self.assertEqual(200, res.status_code, res.data)
        self.assertEqual((1, 0), (len(self.rows()), self.admin("SELECT count(*) FROM alert_outbox")[0][0]))

    def test_odd_requests_are_stored(self):
        row = self.stored(variant(version=KeyError), content_type="text/plain", path_suffix="?version=v9&x=1")
        self.assertEqual("v9", row["version"])
        self.assertTrue(row["stacktrace"].endswith("\n\nIngest adjustments:\n\t- Content-Type \"text/plain\" read as JSON\n\t- query string: \"x\" "
                                                   "ignored"))
        row = self.stored(encoded(BASE).replace(b"Uncaught", b"Unc\xffaught"))
        self.assertEqual("Unc\ufffdaught" + BASE["error_condensed"][8:], row["error_condensed"])
        row = self.stored(dict(BASE, **{"k%02d" % i: "\u0000\ud83d" * 1000 for i in range(30)}))
        self.assertEqual(BASE["location"], row["location"])


if __name__ == "__main__":
    unittest.main()
