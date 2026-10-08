"""
Slow-query reports to Sentinel: a JAAQL query request whose statements and COMMIT take longer than SENTINEL_SLOW_QUERY_SECONDS is printed as
one line and posted to Sentinel's ingest route with exactly the keys that route binds; the request itself never waits for Sentinel, never
answers differently and never fails because of it. Sentinel's own ingest route, deploy and tooling routes, jaaql-monitor traffic however it
logged in and anything outside a request are never reported, and each process reports a query at most once an hour and makes at most 10
reports an hour, at most 3 of them for one account.

    python -m unittest jaaql.test.test_slow_queries

The unit tests need only the package's requirements: their statements run on a stand-in database interface that runs no SQL and says each
statement took the seconds its parameter t names, and Sentinel is a stub HTTP server on 127.0.0.1. TestSlowQueriesAgainstPostgres drives the
real request paths (the routes, submit, DBPGInterface, the jaaql extension, COMMIT) with pg_sleep against a scratch Postgres that has the jaaql
extension available; it runs only when JAAQL_TEST_POSTGRES_URI is set to postgresql://<superuser>:<password>@<host>:<port>/<database> and
creates, then drops, the database jaaql_test_slowq and the role jaaql_test_slowq_user
"""
import contextlib
import io
import json
import os
import queue
import re
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest import mock

import psycopg
from werkzeug.exceptions import InternalServerError

from jaaql.constants import ENDPOINT__report_sentinel_error, VERSION, ENVIRON__sentinel_url, KEY__database
from jaaql.db import db_utils_no_circ
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface_for_db, execute_supplied_statement
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.mvc import model
from jaaql.mvc.controller import JAAQLController
from jaaql.mvc.exception_queries import QUERY__fetch_application_schemas, KEY__is_default
from jaaql.mvc.generated_queries import KG__application_schema__name, KG__application__is_live
from jaaql.mvc.model import JAAQLModel
from jaaql.documentation.documentation_internal import DOCUMENTATION__report_sentinel_error
from jaaql.openapi.swagger_documentation import SwaggerFlatResponse, RESPONSE__200_ok
from jaaql.utilities import sentinel, slow_queries
from monitor.main import HEADER__security_bypass, HEADER__security

CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}
ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"

SUPER_KEY = "test-super-bypass-key"
PUBLIC_URL = "https://lesbij.example.test"
HOST = "lesbij.example.test"
APPLICATION = "LesBij_Test App"
SOURCE_SYSTEM = "lesbij-test-app"
CRYPT_KEY = b"k" * 32
REPORT_KEYS = {"location", "source_file", "error_condensed", "file_line_number", "file_col_number", "version", "source_system", "stacktrace",
               "user_agent"}
SLOW = 3.1
FAST = 0.1


class StubSentinel:
    """
    Sentinel's ingest route: records every POST (path, json body) and answers with status (an int), or "hang": holds the answer until
    released, so the sender's read timeout fires
    """

    def __init__(self):
        self.reports = []
        self.status = 200
        self.release = threading.Event()
        self.received = threading.Condition()
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                status = stub.status
                with stub.received:
                    stub.reports.append((self.path, body))
                    stub.received.notify_all()
                if status == "hang":
                    stub.release.wait(10)
                    status = 200
                try:
                    self.send_response(status)
                    self.send_header("Content-Length", "2")
                    self.end_headers()
                    self.wfile.write(b"ok")
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def wait_for(self, count, timeout=10):
        with self.received:
            return self.received.wait_for(lambda: len(self.reports) >= count, timeout)

    def bodies(self):
        return [body for _, body in self.reports]

    def reset(self):
        self.release.set()
        self.status = 200
        assert sentinel.wait_idle(15), "the sender did not finish"
        self.reports.clear()
        self.release.clear()

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()


def closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TimedInterface(DBInterface):
    """
    Runs no SQL: each statement says it took the seconds its parameter t names (never sleeping), and a statement whose text holds "fail"
    raises after that. timings keeps what each statement was given as capture_timing
    """

    def __init__(self):
        super().__init__(CONFIG, "localhost", "user")
        self.db_name = "timed_db"
        self.timings = []

    def get_conn(self):
        return SimpleNamespace(autocommit=False, closed=False)

    def put_conn(self, conn):
        pass

    def commit(self, conn):
        pass

    def rollback(self, conn):
        pass

    def check_dba(self, conn, wait_hook=None):
        pass

    def statement_may_end_transaction(self, query):
        return False

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        self.timings.append(capture_timing)
        seconds = float((parameters or {}).get("t", 0))
        if capture_timing is not None:
            capture_timing.append(seconds)
        if "fail" in query:
            # Quoting the other parameters' values, as a database error can quote the value it refused
            raise psycopg.errors.RaiseException("it failed after %s s" % seconds + "".join(
                " refusing " + str(value) for key, value in sorted((parameters or {}).items()) if key != "t"))
        return ["slept"], [0], [[seconds]]

    def handle_db_error(self, err, echo):
        return HttpStatusException(str(err))

    def close(self):
        pass


def run(query, parameters=None, application=APPLICATION, label=None, interface=None):
    operation = {"query": query, "parameters": parameters or {}}
    if application is not None:
        operation["application"] = application
    return InterpretJAAQL(interface or TimedInterface()).transform(operation, encryption_key=CRYPT_KEY, slow_query_label=label)


class StubModel:
    """
    What the routes need of a model, with the real JAAQLModel methods for the routes that run queries
    """

    def __init__(self, vault=None, account="account-1"):
        self.is_container = True
        self.has_installed = True
        self.use_easyauth = False
        self.local_super_access_key = SUPER_KEY
        self.local_jaaql_access_key = "test-jaaql-bypass-key"
        self.url = PUBLIC_URL
        self.vault = vault
        self.config = CONFIG
        self.jaaql_lookup_connection = None
        self.cached_canned_query_service = None
        self.prevent_arbitrary_queries = False
        self.account = account
        self.query_caches = {"application": APPLICATION, "queries": {"slow": ["SELECT slow(:t) AS slept"] * 4}}
        self.db_cache = {"default": {KG__application_schema__name: "default", KEY__database: "unused", KEY__is_default: True,
                                     KG__application__is_live: True}}
        self.prepared = []

    def get_bypass_user(self, username, ip_address):
        return self.account, None

    def verify_auth_token_threaded(self, auth_token, ip_address, complete):
        # The token of a password login, as jaaql-monitor gets one on a box from /oauth/token: no bypass key
        complete.put((True, None, None))
        return self.account, "dba", None, False, False

    def get_db_crypt_key(self):
        return CRYPT_KEY

    def query_cache_is_stale(self):
        return False

    def call_proc(self, inputs, account_id, verification_hook=None):
        return JAAQLModel.call_proc(self, inputs, account_id, verification_hook=verification_hook)

    def execute(self, inputs, account_id, verification_hook=None):
        return JAAQLModel.execute(self, inputs, account_id, verification_hook=verification_hook)

    def _lookup_cached_query(self, trimmed, requested=True):
        return JAAQLModel._lookup_cached_query(self, trimmed, requested)

    def submit(self, inputs, account_id, verification_hook=None, ip_address=None, **kwargs):
        return JAAQLModel.submit(self, inputs, account_id, verification_hook=verification_hook, ip_address=ip_address, **kwargs)

    def prepare_queries(self, inputs, account_id):
        self.prepared.append(inputs)
        return run("SELECT slow(:t)", {"t": SLOW})


class SlowQueryCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.stub = StubSentinel()
        # As create_app's produce_all_documentation leaves it at boot: a method that declares no 200 answers 200 OK
        for method in DOCUMENTATION__report_sentinel_error.methods:
            if not any(response.code == 200 for response in method.responses):
                method.responses.append(SwaggerFlatResponse(RESPONSE__200_ok))

    @classmethod
    def tearDownClass(cls):
        sentinel.configure(None, None)
        slow_queries.configure(None, False)
        cls.stub.close()

    def setUp(self):
        self.threshold = mock.patch.object(slow_queries, "THRESHOLD_SECONDS", 3.0)
        self.threshold.start()
        slow_queries.reset_throttle()
        self.stub.reset()
        self.controller = self.make_controller(self.make_model())

    def tearDown(self):
        self.threshold.stop()
        self.stub.reset()
        slow_queries.reset_throttle()

    def make_model(self):
        return StubModel()

    def make_controller(self, stub_model, sentinel_url=None):
        with mock.patch.dict(os.environ, {ENVIRON__sentinel_url: sentinel_url or self.stub.url}):
            controller = JAAQLController(stub_model, True, "http+unix://%2Ftmp%2Fjaaql.sock")
        controller.create_app()
        self.client = controller.app.test_client()
        return controller

    def post(self, route, body, application=APPLICATION, user_agent="Mozilla/5.0 (Test)", bypass=True):
        # With the super bypass key, as the microcompiler's jaaql-monitor and a cloud procedure log in, or else with a password login's token
        if application is not None:
            body = dict(body, application=application)
        headers = {"User-Agent": user_agent}
        if bypass:
            headers[HEADER__security_bypass] = SUPER_KEY
        else:
            headers[HEADER__security] = "a.token.from-oauth-token"
        return self.client.post(route, json=body, headers=headers)

    def assertNoReport(self):
        self.assertTrue(sentinel.wait_idle(10))
        self.assertEqual([], self.stub.reports)

    def report(self, count=1):
        self.assertTrue(self.stub.wait_for(count), "Sentinel received %d of %d reports" % (len(self.stub.reports), count))
        self.assertTrue(sentinel.wait_idle(10))
        self.assertEqual(count, len(self.stub.reports), [body["source_file"] for body in self.stub.bodies()])
        return self.stub.bodies()[-1]

    def assertContract(self, body):
        self.assertEqual(REPORT_KEYS, set(body))
        self.assertRegex(body["source_system"], r"^[a-z0-9-]{1,63}$")
        self.assertLessEqual(len(body["source_file"]), 255)
        self.assertLessEqual(len(body["location"]), 512)
        self.assertLessEqual(len(body["version"]), 40)
        self.assertLessEqual(len(body["error_condensed"]), 200)
        self.assertIsNone(body["file_line_number"])
        self.assertIsNone(body["file_col_number"])
        self.assertIsInstance(body["stacktrace"], str)
        self.assertNotEqual("", body["stacktrace"])
        self.assertTrue(body["user_agent"].isascii() and len(body["user_agent"]) <= 512)


class TestReports(SlowQueryCase):

    def test_a_slow_call_proc_is_reported_once_with_the_bound_keys(self):
        out = io.StringIO()
        with mock.patch.object(db_utils_no_circ, "get_required_db", return_value=TimedInterface()), \
                mock.patch.object(model, "is_federation_procedure", return_value=False), contextlib.redirect_stdout(out):
            res = self.post("/call-proc", {"query": "lesson.save", "parameters": {"t": SLOW, "note": "kept"}})
        self.assertEqual(200, res.status_code, res.data)
        body = self.report()
        self.assertContract(body)
        self.assertEqual("/api" + ENDPOINT__report_sentinel_error, self.stub.reports[0][0])
        self.assertEqual("slow-query:call-proc:lesson.save@" + HOST, body["source_file"])
        self.assertEqual("Slow query: 3.10 s call-proc:lesson.save", body["error_condensed"])
        self.assertEqual(PUBLIC_URL + "/api/call-proc", body["location"])
        self.assertEqual("JAAQL " + VERSION, body["version"])
        self.assertEqual(SOURCE_SYSTEM, body["source_system"])
        self.assertEqual("Mozilla/5.0 (Test)", body["user_agent"])
        trace = body["stacktrace"]
        self.assertTrue(trace.startswith("Slow query: 3.10 s, over the 3 s threshold\nQuery: call-proc:lesson.save\nOutcome: completed\n"), trace)
        self.assertIn("Route: POST /call-proc on " + PUBLIC_URL, trace)
        self.assertIn("Application: " + APPLICATION + " | database: timed_db | account: account-1\n", trace)
        self.assertNotIn("super_db", trace)
        self.assertIn("\n  (wall clock in this worker, to which its other requests add while they hold it; not counted: ", trace)
        self.assertIn("Database time: 3.10 s = statements 3.10 s + COMMIT 0.00 s", trace)
        self.assertIn("Statement 1 of 1 | query key _jaaql_procedure | 3.10 s\n\tSELECT * FROM \"lesson.save\"(\n\t\t", trace)
        self.assertIn("\t\tt => :t", trace)
        self.assertIn('\t\t"note": "kept"', trace)
        self.assertIn("SLOW QUERY 3.10 s call-proc:lesson.save (POST /call-proc, " + APPLICATION + ") - reported", out.getvalue())

    def test_a_fast_query_gives_no_report_and_no_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), slow_queries.request_scope("/submit", "POST", "/submit"):
            run("SELECT slow(:t)", {"t": FAST})
        self.assertNoReport()
        self.assertEqual("", out.getvalue())

    def test_the_threshold_is_strictly_exceeded(self):
        for seconds, reported in [(3.0, False), (3.0001, True)]:
            with self.subTest(seconds=seconds):
                slow_queries.reset_throttle()
                self.stub.reset()
                with slow_queries.request_scope("/submit", "POST", "/submit"):
                    measurement = slow_queries.start(None, {"application": APPLICATION}, TimedInterface())
                measurement.statement("query", "SELECT 1", {}, (), [seconds])
                with contextlib.redirect_stdout(io.StringIO()):
                    measurement.finish()
                if reported:
                    self.report()
                else:
                    self.assertNoReport()

    def test_the_contract_holds_for_long_and_odd_values(self):
        long_name = "p" * 63
        with mock.patch.object(db_utils_no_circ, "get_required_db", return_value=TimedInterface()), \
                mock.patch.object(model, "is_federation_procedure", return_value=False), mock.patch.object(slow_queries, "_host", "h" * 300), \
                contextlib.redirect_stdout(io.StringIO()):
            res = self.post("/call-proc", {"query": long_name, "parameters": {"t": SLOW}}, application="Ä pp.with/odd_CHARS " + "x" * 100,
                            user_agent="Mozilla/5.0 (Ünïcode)")
        self.assertEqual(200, res.status_code, res.data)
        body = self.report()
        self.assertContract(body)
        self.assertEqual("-pp-with-odd-chars-" + "x" * 44, body["source_system"])
        self.assertEqual("Mozilla/5.0 (?n?code)", body["user_agent"])
        self.assertEqual("snow ? man", slow_queries._ascii("snow ☃ man"))

    def test_a_long_label_is_cut_and_keeps_a_hash_of_the_whole(self):
        long_label = "x" * 400
        self.assertEqual(193, len(slow_queries.short_label(long_label)))
        self.assertNotEqual(slow_queries.short_label(long_label), slow_queries.short_label("x" * 399 + "y"))
        self.assertEqual("call-proc:lesson.save", slow_queries.short_label("call-proc:lesson.save"))

    def test_a_request_without_a_user_agent_names_jaaql(self):
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            run("SELECT slow(:t)", {"t": SLOW})
        self.assertEqual("JAAQL/" + VERSION, self.report()["user_agent"])

    def test_several_statements_are_one_report_listing_each(self):
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            InterpretJAAQL(TimedInterface()).transform({"query": {key: {"query": "SELECT slow(:t)", "parameters": {"t": 0.8}} for key in "abcd"},
                                                        "application": APPLICATION}, encryption_key=CRYPT_KEY)
        body = self.report()
        self.assertEqual("Slow query: 3.20 s sql:" + body["source_file"].split("sql:")[1].split("@")[0] + " SELECT slow(:t)", body["error_condensed"])
        for idx, key in enumerate("abcd"):
            self.assertIn("Statement %d of 4 | query key %s | 0.80 s" % (idx + 1, key), body["stacktrace"])

    def test_several_fast_statements_are_not_reported(self):
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            InterpretJAAQL(TimedInterface()).transform({"query": {key: {"query": "SELECT slow(:t)", "parameters": {"t": FAST}} for key in "abcd"},
                                                        "application": APPLICATION}, encryption_key=CRYPT_KEY)
        self.assertNoReport()

    def test_a_procedure_called_through_submit_is_named_by_the_procedure(self):
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            run('SELECT * FROM "slow.proc"(t => :t)', {"t": SLOW})
        self.assertEqual("slow-query:proc:slow.proc@" + HOST, self.report()["source_file"])

    def test_the_same_sql_is_one_identity_however_it_is_spaced(self):
        labels = []
        for query in ["SELECT slow(:t)", "SELECT  slow(:t)\n", "SELECT slow(:t) AS other"]:
            measurement = slow_queries.Measurement(slow_queries.Scope(), None, None, None)
            measurement.statement("query", query, {}, (), [SLOW])
            labels.append(slow_queries.label_of(measurement))
        self.assertEqual(labels[0], labels[1])
        self.assertNotEqual(labels[0], labels[2])
        self.assertRegex(labels[0], r"^sql:[0-9a-f]{12}$")

    def test_a_slow_failure_is_reported_as_failed_and_answers_as_before(self):
        answers = []
        for threshold in [3.0, 0]:
            with mock.patch.object(slow_queries, "THRESHOLD_SECONDS", threshold), \
                    mock.patch.object(db_utils_no_circ, "get_required_db", return_value=TimedInterface()), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                res = self.post("/submit", {"query": "SELECT fail(:t)", "parameters": {"t": SLOW}})
            answers.append((res.status_code, res.data))
        self.assertEqual(answers[0], answers[1])
        self.assertNotEqual(200, answers[0][0])
        body = self.report()
        self.assertIn("\nOutcome: failed - UnhandledQueryError: ", body["stacktrace"])

    def test_parameters_are_redacted_or_marked_encrypted(self):
        parameters = {"t": SLOW, "password": "p1", "client_secret": "s1", "refresh_token": "r1", "api_key": "a1", "Password2": "p2",
                      "email": "someone@example.com", "note": "kept", "essay": "e" * 2000}
        query = "SELECT slow(:t, :password, :client_secret, :refresh_token, :api_key, :Password2, #email, :note, :essay)"
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            run(query, parameters)
        trace = self.report()["stacktrace"]
        for key in ["password", "client_secret", "refresh_token", "api_key", "Password2"]:
            self.assertIn('"%s": "<redacted>"' % key, trace)
        for secret in ["p1", "s1", "r1", "a1", "p2", "someone@example.com"]:
            self.assertNotIn('"' + secret + '"', trace)
        self.assertIn('"email": "<encrypted>"', trace)
        self.assertIn('"note": "kept"', trace)
        self.assertIn('"essay": "' + "e" * 499 + "...", trace)
        self.assertNotIn("e" * 500, trace)

    def test_secrets_are_redacted_at_any_depth_and_under_more_names(self):
        parameters = {"t": SLOW, "apiKey": "SECRET-apikey", "pwd": "SECRET-pwd", "passwd": "SECRET-passwd", "authorization": "SECRET-bearer",
                      "document_id": "SECRET-document", "private_key": "SECRET-private", "credentials": "SECRET-credentials",
                      "settings": [{"smtp_password": "SECRET-smtp", "host": "mail.example", "nested": [{"token": "SECRET-nested"}, "kept"]}],
                      "json_text": json.dumps({"client_secret": "SECRET-json", "name": "kept-in-json"}), "plain_text": "[not json"}
        query = "SELECT slow(" + ", ".join(":" + key for key in parameters) + ")"
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            run(query, parameters)
        trace = self.report()["stacktrace"]
        self.assertNotIn("SECRET-", trace)
        for key in ["apiKey", "pwd", "passwd", "authorization", "document_id", "private_key", "credentials"]:
            self.assertIn('"%s": "<redacted>"' % key, trace)
        self.assertIn('"settings": [{"smtp_password": "<redacted>", "host": "mail.example", "nested": [{"token": "<redacted>"}, "kept"]}]', trace)
        self.assertIn('"json_text": "{\\"client_secret\\": \\"<redacted>\\", \\"name\\": \\"kept-in-json\\"}"', trace)
        self.assertIn('"plain_text": "[not json"', trace)

    def test_a_failure_quoting_a_redacted_value_does_not_repeat_it(self):
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(Exception):
            run("SELECT fail(:t, :password, :note)", {"t": SLOW, "password": "hunter2-secret", "note": "kept"})
        trace = self.report()["stacktrace"]
        self.assertNotIn("hunter2-secret", trace)
        self.assertRegex(trace, r"\nOutcome: failed - \w+: it failed after 3\.1 s refusing kept refusing <redacted>\n")

    def test_an_encrypted_literal_is_masked(self):
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()):
            run("SELECT slow(:t), #'literal-plaintext' AS x", {"t": SLOW})
        body = self.report()
        self.assertNotIn("literal-plaintext", json.dumps(body))
        self.assertIn("\tSELECT slow(:t), #'<encrypted>' AS x\n", body["stacktrace"])
        self.assertTrue(body["error_condensed"].endswith(" SELECT slow(:t), #'<encrypted>' AS x"), body["error_condensed"])
        self.assertEqual(self.label("SELECT slow(:t), #'one'"), self.label("SELECT slow(:t), #'other'"))

    @staticmethod
    def label(text="SELECT 1", label=None):
        measurement = slow_queries.Measurement(slow_queries.Scope(), label, None, None)
        measurement.statement("query", text, {}, (), [SLOW])
        return slow_queries.label_of(measurement)

    def test_a_label_is_one_line_whatever_a_request_names(self):
        self.assertEqual("proc:slow.proc", self.label('SELECT * FROM "slow.proc"(t => :t)'))
        self.assertRegex(self.label('SELECT * FROM "x\nFORGED: line"(t => :t)'), r"^sql:[0-9a-f]{12}$")
        self.assertEqual("email:app. FORGED?", self.label(label=slow_queries.Label("email", "app.\nFORGED\x1b")))
        with slow_queries.request_scope("/submit", "POST", "/submit"), contextlib.redirect_stdout(io.StringIO()) as out:
            run('SELECT * FROM "x\nFORGED: line"(t => :t)', {"t": SLOW})
        self.assertEqual(1, len(out.getvalue().splitlines()), out.getvalue())
        self.assertNotIn("FORGED", self.report()["source_file"])

    def test_execute_is_named_by_its_slowest_compiled_query(self):
        measurement = slow_queries.Measurement(slow_queries.Scope(route="/execute"),
                                               slow_queries.Label("execute", refs={"a": "week:0", "b": "week:1", "c": "week:2"}), APPLICATION, None)
        for key, seconds in [("a", 0.5), ("b", 2.8), ("c", 0.4)]:
            measurement.statement(key, "SELECT 1", {}, (), [seconds])
        self.assertEqual("execute:week:1", slow_queries.label_of(measurement))
        trace = slow_queries.stacktrace_of(measurement, 3.7, "execute:week:1", APPLICATION, None)
        self.assertIn("\nStatement 2 of 3 | query key b, compiled query week:1 | 2.80 s\n", trace)

    def test_the_500_reporter_still_reaches_sentinel(self):
        # Through the one sender, now with the keys Sentinel binds and once, by the Flask handlers' fallback for a route added to the app
        # directly (jaaql/utilities/server_errors.py)
        @self.controller.app.route("/test-internal-error")
        def internal_error():
            raise InternalServerError()

        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            res = self.client.get("/test-internal-error")
        self.assertEqual(500, res.status_code)
        self.assertEqual(REPORT_KEYS, set(self.report()))


class TestWhatIsNeverReported(SlowQueryCase):

    def test_the_ingest_route_never_reports_itself(self):
        self.controller.model.submit = lambda inputs, account_id, **kwargs: (run("SELECT slow(:t)", {"t": SLOW}), {"error_id": "e"})[1]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            res = self.client.post(ENDPOINT__report_sentinel_error, json={
                "location": "https://app/index.html", "source_file": "common.js", "error_condensed": "TypeError", "stacktrace": "at x",
                "version": "1", "source_system": "lesbij"})
        self.assertEqual(200, res.status_code, res.data)
        self.assertNoReport()
        self.assertEqual("", out.getvalue())

    def test_deploy_routes_are_not_reported(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            res = self.post("/prepare", {"queries": []})
        self.assertEqual(200, res.status_code, res.data)
        self.assertEqual(1, len(self.controller.model.prepared))
        self.assertNoReport()
        self.assertEqual("", out.getvalue())

    def test_monitor_traffic_is_not_reported_but_cloud_procedure_traffic_is(self):
        # jaaql-monitor names no application: in development it logs in with the bypass key, on a box with a password (deploy scripts and
        # migrate.sh), so the rule is the missing application, whatever the login
        with mock.patch.object(db_utils_no_circ, "get_required_db", return_value=TimedInterface()), contextlib.redirect_stdout(io.StringIO()):
            for bypass in [True, False]:
                self.assertEqual(200, self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": SLOW}}, application=None,
                                                bypass=bypass).status_code)
                self.assertNoReport()
            self.assertEqual(200, self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": SLOW}}).status_code)
            self.assertEqual(SOURCE_SYSTEM, self.report()["source_system"])
            self.stub.reset()
            slow_queries.reset_throttle()
            self.assertEqual(200, self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": SLOW}}, bypass=False).status_code)
        self.assertIn("| account: account-1\n", self.report()["stacktrace"])

    def test_tooling_is_a_request_naming_no_application_on_the_monitors_route_or_with_a_bypass_key(self):
        def tooling(route, application, bypass):
            scope = slow_queries.Scope(route=route)
            scope.application, scope.bypass = application, bypass
            return slow_queries.is_tooling(scope)

        self.assertEqual([True, True, True, False, False, False],
                         [tooling("/submit", None, False), tooling("/submit", None, True), tooling("/call-proc", None, True),
                          tooling("/call-proc", None, False), tooling("/submit", APPLICATION, False), tooling("/submit", APPLICATION, True)])
        self.assertFalse(slow_queries.is_tooling(slow_queries.Scope(route="/submit"), APPLICATION))
        self.assertFalse(slow_queries.is_tooling(slow_queries.Scope(background="auth-verification")))

    def test_nothing_outside_a_request_is_reported(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run("SELECT slow(:t)", {"t": SLOW})
        self.assertNoReport()
        self.assertEqual("", out.getvalue())


class TestThrottle(SlowQueryCase):

    def setUp(self):
        super().setUp()
        self.clock = [1000.0]
        self.now = mock.patch.object(slow_queries, "_now", lambda: self.clock[0])
        self.now.start()

    def tearDown(self):
        self.now.stop()
        super().tearDown()

    def slow(self, procedure, seconds=SLOW, account=None):
        with slow_queries.request_scope("/call-proc", "POST", "/call-proc"), contextlib.redirect_stdout(io.StringIO()) as out:
            if account is not None:
                slow_queries.note_caller(account, False)
            run('SELECT * FROM "' + procedure + '"(t => :t)', {"t": seconds}, label=slow_queries.Label("call-proc", procedure))
        return out.getvalue()

    def test_a_query_is_reported_once_an_hour_with_its_repeats(self):
        self.slow("a.proc")
        self.assertIn("- repeat, not reported", self.slow("a.proc", 5.0))
        self.report(1)
        self.clock[0] += 3599
        self.slow("a.proc")
        self.report(1)
        self.clock[0] += 2
        self.slow("a.proc")
        body = self.report(2)
        self.assertIn("\nRepeats: 2 more slow runs of this query in this worker since its last report, slowest 5.00 s\n", body["stacktrace"])
        self.clock[0] += 3601
        self.slow("a.proc")
        self.assertNotIn("Repeats:", self.report(3)["stacktrace"])

    def test_another_query_is_reported_on_its_own(self):
        self.slow("a.proc")
        self.slow("b.proc")
        self.report(2)
        self.assertEqual(["slow-query:call-proc:a.proc@" + HOST, "slow-query:call-proc:b.proc@" + HOST],
                         [body["source_file"] for body in self.stub.bodies()])

    def test_at_most_ten_reports_an_hour(self):
        for idx in range(10):
            self.slow("p%d.proc" % idx)
        self.assertIn("over 10 reports this hour, not reported", self.slow("p10.proc"))
        self.report(10)
        self.clock[0] += 3600
        self.slow("p10.proc")
        body = self.report(11)
        self.assertEqual("slow-query:call-proc:p10.proc@" + HOST, body["source_file"])
        self.assertIn("Repeats: 1 more slow run of", body["stacktrace"])

    def test_at_most_three_reports_an_hour_for_one_account(self):
        for idx in range(3):
            self.slow("a%d.proc" % idx, account="account-a")
        self.assertIn("- over 3 reports this hour for this account, not reported", self.slow("a3.proc", account="account-a"))
        self.assertIn("- reported", self.slow("b0.proc", account="account-b"))
        self.report(4)
        self.clock[0] += 3600
        self.slow("a3.proc", account="account-a")
        body = self.report(5)
        self.assertEqual("slow-query:call-proc:a3.proc@" + HOST, body["source_file"])
        self.assertIn("Repeats: 1 more slow run of", body["stacktrace"])

    def test_the_queries_kept_track_of_are_bounded(self):
        with mock.patch.object(slow_queries, "SLOW_QUERY__max_tracked_queries", 20):
            for idx in range(10):
                self.assertEqual(slow_queries.DECISION__report, slow_queries._throttle("reported-%d" % idx, SLOW)[0])
            for idx in range(1000):
                self.assertEqual(slow_queries.DECISION__capped, slow_queries._throttle("capped-%d" % idx, SLOW)[0])
            self.assertEqual(20, len(slow_queries._identities))
            # Those reported in the last hour are kept, or they would be reported again
            for idx in range(10):
                self.assertEqual(slow_queries.DECISION__repeat, slow_queries._throttle("reported-%d" % idx, SLOW)[0])
            self.clock[0] += slow_queries.FORGET__seconds
            slow_queries._throttle("later", SLOW)
            self.assertEqual(["later"], list(slow_queries._identities))


class TestConfiguration(SlowQueryCase):

    def test_zero_turns_reports_off_and_times_nothing(self):
        interface = TimedInterface()
        with mock.patch.object(slow_queries, "THRESHOLD_SECONDS", 0), \
                mock.patch.object(db_utils_no_circ, "get_required_db", return_value=interface), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(200, self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": SLOW}}).status_code)
            with slow_queries.request_scope("/submit", "POST", "/submit"):
                run("SELECT slow(:t)", {"t": SLOW}, interface=interface)
        self.assertEqual([None, None], interface.timings)
        self.assertNoReport()
        self.assertEqual("", out.getvalue())

    def test_a_lower_threshold_reports_sooner(self):
        with mock.patch.object(slow_queries, "THRESHOLD_SECONDS", 0.5), slow_queries.request_scope("/submit", "POST", "/submit"), \
                contextlib.redirect_stdout(io.StringIO()):
            run("SELECT slow(:t)", {"t": 0.6})
        self.assertIn("over the 0.5 s threshold", self.report()["stacktrace"])

    def test_the_setting_is_parsed(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(3.0, slow_queries.parse_threshold("abc"))
            self.assertEqual(3.0, slow_queries.parse_threshold("nan"))
        self.assertIn("SENTINEL_SLOW_QUERY_SECONDS='abc' is not a number of seconds, using 3", out.getvalue())
        self.assertEqual([3.0, 3.0, 0.5, 0.0, -1.0], [slow_queries.parse_threshold(raw) for raw in [None, " ", "0.5", "0", "-1"]])

    def test_without_sentinel_a_slow_query_is_only_printed(self):
        sentinel.configure(None, None)
        try:
            with mock.patch.object(sentinel, "_ensure_sender") as started, slow_queries.request_scope("/call-proc", "POST", "/call-proc"), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                run('SELECT * FROM "a.proc"(t => :t)', {"t": SLOW}, label=slow_queries.Label("call-proc", "a.proc"))
            started.assert_not_called()
            self.assertEqual("SLOW QUERY 3.10 s call-proc:a.proc (POST /call-proc, " + APPLICATION + ")\n", out.getvalue())
        finally:
            sentinel.configure(self.stub.url, None)
        self.assertNoReport()

    def test_the_sentinel_url_is_normalised_as_before(self):
        for configured, expected in [("sentinel.relay-systems.com", "https://sentinel.relay-systems.com/api/sentinel/reporting/error"),
                                     ("https://sentinel.relay-systems.com", "https://sentinel.relay-systems.com/api/sentinel/reporting/error"),
                                     ("http://x:8443/api", "http://x:8443/api/sentinel/reporting/error"),
                                     ("http://x/api/sentinel/reporting/error", "http://x/api/sentinel/reporting/error")]:
            self.assertEqual((expected, False), sentinel.normalise_url(configured, "http+unix://sock"))
        self.assertEqual(("http+unix://sock/sentinel/reporting/error", True), sentinel.normalise_url("_", "http+unix://sock"))
        self.assertEqual((None, False), sentinel.normalise_url(None, "http+unix://sock"))
        self.assertEqual(("lesbij.relay-systems.com", "relay-systems.example"),
                         (self.configured_host("https://lesbij.relay-systems.com"), self.configured_host(None, "relay-systems.example")))

    def configured_host(self, public_url, hostname="unused"):
        saved = (slow_queries._public_url, slow_queries._api_prefix, slow_queries._host)
        try:
            with mock.patch.object(slow_queries.socket, "gethostname", return_value=hostname):
                slow_queries.configure(public_url, True)
            return slow_queries._host
        finally:
            slow_queries._public_url, slow_queries._api_prefix, slow_queries._host = saved


class TestSentinelDown(SlowQueryCase):

    def slow_request(self):
        started = time.monotonic()
        with mock.patch.object(db_utils_no_circ, "get_required_db", return_value=TimedInterface()), contextlib.redirect_stdout(io.StringIO()):
            res = self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": SLOW}})
        self.assertEqual(200, res.status_code, res.data)
        self.assertEqual([[SLOW]], res.json["rows"])
        return time.monotonic() - started

    def test_requests_never_wait_for_sentinel(self):
        for status in ["refused", "hang", 500, 422]:
            with self.subTest(status=status), mock.patch.object(sentinel, "SENTINEL__read_timeout", 1), contextlib.redirect_stdout(io.StringIO()):
                slow_queries.reset_throttle()
                if status == "refused":
                    sentinel.configure("http://127.0.0.1:%d" % closed_port(), None)
                else:
                    self.stub.status = status
                try:
                    self.assertLess(self.slow_request(), 1)
                    self.assertTrue(sentinel.wait_idle(10))
                finally:
                    sentinel.configure(self.stub.url, None)
                    self.stub.reset()
                slow_queries.reset_throttle()
                self.slow_request()
                self.assertEqual("slow-query:sql:", self.report()["source_file"][:15])
                self.stub.reset()

    def test_a_full_queue_drops_without_raising(self):
        self.stub.status = "hang"
        with contextlib.redirect_stdout(io.StringIO()) as out:
            sent = [sentinel.send({"n": idx}) for idx in range(60)]
        self.assertFalse(all(sent))
        self.assertGreaterEqual(sent.count(True), 50)
        self.assertIn("Sentinel queue full", out.getvalue())

    def test_a_forked_process_starts_its_own_daemon_sender(self):
        sentinel.send({"n": 0})
        self.assertTrue(self.stub.wait_for(1))
        first = sentinel._sender
        with mock.patch.object(sentinel, "os", SimpleNamespace(getpid=lambda: os.getpid() + 100000)):
            sentinel.send({"n": 1})
            self.assertTrue(self.stub.wait_for(2))
            self.assertIsNot(first, sentinel._sender)
            self.assertTrue(sentinel._sender.daemon)
            self.assertTrue(sentinel._sender.is_alive())
        self.assertTrue(first.daemon)


class StubVault:
    def __init__(self, uri):
        self.uri = uri

    def get_obj(self, key):
        return self.uri


TEST_DATABASE = "jaaql_test_slowq"
TEST_ROLE = "jaaql_test_slowq_user"
SENTINEL_DDL = """
    CREATE DOMAIN encrypted__ip_address AS character varying(200);
    CREATE DOMAIN system_name AS character varying(63) CHECK (VALUE ~* '^[a-z0-9\\-]*$');
    CREATE DOMAIN full_url_allowing_anchor_and_parameters AS character varying(512);
    CREATE DOMAIN filename AS character varying(255);
    CREATE DOMAIN error_condensed AS character varying(400);
    CREATE DOMAIN line_number AS integer CHECK (VALUE between 0 and 999999);
    CREATE DOMAIN column_number AS integer CHECK (VALUE between 1 and 999999);
    CREATE DOMAIN version AS character varying(40);
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
    CREATE FUNCTION "error.process_alert"(id uuid, raw_ip_address text) RETURNS void LANGUAGE sql AS $f$ SELECT $f$;
"""


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestSlowQueriesAgainstPostgres(SlowQueryCase):
    """
    The real request paths with pg_sleep. Most run at a threshold of 0.5 s with 0.6 s sleeps to keep the suite quick; the first runs at
    the default 3 s with a 3.1 s sleep
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
            conn.execute("""
                CREATE FUNCTION slow(t float8) RETURNS float8 LANGUAGE plpgsql AS $f$ BEGIN PERFORM pg_sleep(t); RETURN t; END $f$;
                CREATE FUNCTION slow_fail(t float8) RETURNS float8 LANGUAGE plpgsql AS $f$
                BEGIN PERFORM pg_sleep(t); RAISE EXCEPTION 'slow and then failed'; END $f$;
                CREATE FUNCTION "slow.proc"(t float8, note text, password text) RETURNS TABLE (slept float8, noted text) LANGUAGE plpgsql AS $f$
                BEGIN PERFORM pg_sleep(t); RETURN QUERY SELECT t, note; END $f$;
                CREATE FUNCTION "slow.federate"(tenant text, application text, account_id text, provider text, email text, sub text)
                    RETURNS TABLE (federated text) LANGUAGE plpgsql AS $f$ BEGIN PERFORM pg_sleep(0.6); RETURN QUERY SELECT email; END $f$;
                CREATE VIEW slow_view AS SELECT v.t, slow(v.t) AS slept FROM (VALUES (0.6::float8)) v(t);
                CREATE TABLE slow_commit (t float8);
                CREATE FUNCTION slow_commit_check() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN PERFORM pg_sleep(NEW.t); RETURN NULL; END $f$;
                CREATE CONSTRAINT TRIGGER slow_commit_deferred AFTER INSERT ON slow_commit DEFERRABLE INITIALLY DEFERRED
                    FOR EACH ROW EXECUTE FUNCTION slow_commit_check();
            """ + SENTINEL_DDL + """
                GRANT SELECT, INSERT ON slow_commit, error TO """ + TEST_ROLE + """;
                GRANT SELECT ON slow_view TO """ + TEST_ROLE + """;
            """)
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
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.threshold.stop()
        self.threshold = mock.patch.object(slow_queries, "THRESHOLD_SECONDS", 0.5)
        self.threshold.start()
        real_lookup = db_utils_no_circ.execute_supplied_statement

        def lookup(connection, query, parameters=None, **kwargs):
            # The application's schemas, as the jaaql database would answer: one schema, in the test database
            if query == QUERY__fetch_application_schemas:
                return [{KG__application_schema__name: "default", KEY__database: TEST_DATABASE, KEY__is_default: True,
                         KG__application__is_live: True}]
            return real_lookup(connection, query, parameters, **kwargs)

        self.lookup = mock.patch.object(db_utils_no_circ, "execute_supplied_statement", side_effect=lookup)
        self.lookup.start()
        self.out = contextlib.redirect_stdout(io.StringIO())
        self.out.__enter__()

    def tearDown(self):
        self.out.__exit__(None, None, None)
        self.lookup.stop()
        super().tearDown()

    def make_model(self):
        stub_model = StubModel(vault=self.vault, account=TEST_ROLE)
        stub_model.db_cache = {"default": {KG__application_schema__name: "default", KEY__database: TEST_DATABASE, KEY__is_default: True,
                                           KG__application__is_live: True}}
        return stub_model

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def call_proc(self, t, note="kept"):
        with mock.patch.object(model, "is_federation_procedure", return_value=False):
            return self.post("/call-proc", {"query": "slow.proc", "parameters": {"t": t, "note": note, "password": "hunter2"},
                                            "explicit_types": {"t": "float8"}})

    def test_call_proc_at_the_default_threshold(self):
        with mock.patch.object(slow_queries, "THRESHOLD_SECONDS", 3.0):
            res = self.call_proc(FAST)
            self.assertEqual(200, res.status_code, res.data)
            self.assertNoReport()
            res = self.call_proc(SLOW)
        self.assertEqual(200, res.status_code, res.data)
        self.assertEqual([[SLOW, "kept"]], res.json["_jaaql_procedure"]["rows"])
        body = self.report()
        self.assertContract(body)
        self.assertEqual("slow-query:call-proc:slow.proc@" + HOST, body["source_file"])
        # pg_sleep(3.1) plus the session authorization pipelined with the first statement on a pooled connection, ~0.1 s on a cold backend
        seconds = float(re.fullmatch(r"Slow query: (\d+\.\d\d) s call-proc:slow\.proc", body["error_condensed"]).group(1))
        self.assertGreaterEqual(seconds, SLOW)
        self.assertLess(seconds, 4.0)
        trace = body["stacktrace"]
        self.assertIn("over the 3 s threshold", trace)
        self.assertIn("| database: " + TEST_DATABASE + " | account: " + TEST_ROLE + "\n", trace)
        self.assertIn('"password": "<redacted>"', trace)
        self.assertNotIn("hunter2", trace)
        self.assertIn("\tSELECT * FROM \"slow.proc\"(\n\t\t", trace)
        self.assertIn("\t\tt => :t::float8", trace)

    def test_execute_adds_up_its_compiled_queries_and_is_named_by_the_slowest(self):
        sleeps = {"a": 0.1, "b": 0.25, "c": 0.1, "d": 0.1}
        res = self.post("/execute", {"query": {key: {"query": "slow:%d" % idx, "parameters": {"t": sleeps[key]}} for idx, key in enumerate("abcd")}})
        self.assertEqual(200, res.status_code, res.data)
        body = self.report()
        self.assertEqual("slow-query:execute:slow:1@" + HOST, body["source_file"])
        self.assertEqual(PUBLIC_URL + "/api/execute", body["location"])
        for idx, key in enumerate("abcd"):
            self.assertRegex(body["stacktrace"], r"Statement %d of 4 \| query key %s, compiled query slow:%d \| %s\d s\n\tSELECT slow\(:t\) AS slept\n" % (
                idx + 1, key, idx, re.escape("%.1f" % sleeps[key])))
        self.stub.reset()
        res = self.post("/execute", {"query": {key: {"query": "slow:%d" % idx, "parameters": {"t": 0.05}} for idx, key in enumerate("abcd")}})
        self.assertEqual(200, res.status_code, res.data)
        self.assertNoReport()

    def test_submit_from_a_cloud_procedure_is_reported_and_from_the_monitor_is_not(self):
        for bypass in [True, False]:
            res = self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": 0.6}, "database": TEST_DATABASE}, application=None,
                            bypass=bypass)
            self.assertEqual(200, res.status_code, res.data)
            self.assertNoReport()
        res = self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": 0.6}})
        self.assertEqual(200, res.status_code, res.data)
        body = self.report()
        self.assertContract(body)
        self.assertRegex(body["source_file"], r"^slow-query:sql:[0-9a-f]{12}@" + re.escape(HOST) + "$")
        self.assertIn(" SELECT slow(:t)", body["error_condensed"])

    def test_a_slow_commit_counts(self):
        res = self.post("/submit", {"query": "INSERT INTO slow_commit VALUES (:t)", "parameters": {"t": 0.6}})
        self.assertEqual(200, res.status_code, res.data)
        trace = self.report()["stacktrace"]
        statements, commit = re.search(r"= statements (\d+\.\d\d) s \+ COMMIT (\d+\.\d\d) s", trace).groups()
        self.assertLess(float(statements), 0.3, trace)
        self.assertGreaterEqual(float(commit), 0.6, trace)

    def test_a_slow_failure_is_reported_and_answers_as_before(self):
        answers = []
        for threshold in [0.5, 0]:
            with mock.patch.object(slow_queries, "THRESHOLD_SECONDS", threshold), contextlib.redirect_stderr(io.StringIO()):
                res = self.post("/submit", {"query": "SELECT slow_fail(:t)", "parameters": {"t": 0.6}})
            answers.append((res.status_code, res.data))
        self.assertEqual(answers[0], answers[1])
        self.assertEqual(422, answers[0][0], answers[0][1])
        trace = self.report()["stacktrace"]
        self.assertIn("\nOutcome: failed - UnhandledQueryError: ", trace)
        self.assertIn("+ ROLLBACK ", trace)

    def test_the_security_event_procedure(self):
        with slow_queries.request_scope("/security-event", "POST", "/security-event"):
            row = JAAQLModel._gate_run_singleton(self.controller.model, {"application": APPLICATION, "parameters": {
                "t": 0.6, "note": "n", "password": "p"}}, TEST_ROLE, {"database_procedure": "slow.proc"})
        self.assertEqual("n", row["noted"])
        self.assertEqual("slow-query:security-event:slow.proc@" + HOST, self.report()["source_file"])

    def test_the_federation_procedure(self):
        with slow_queries.request_scope("/exchange-auth-code", "GET", "/exchange-auth-code"), \
                mock.patch.object(model, "fetch_parameters_for_federation_procedure", return_value=[]), \
                mock.patch.object(model, "ROLE__jaaql", TEST_ROLE):
            JAAQLModel._run_federation_procedure(self.controller.model, {model.KG__database_user_registry__federation_procedure: "slow.federate"},
                                                 APPLICATION, "default", TEST_ROLE, "Relay Systems", "default", "a@example.com", "sub-1", {})
        self.assertEqual("slow-query:federation:slow.federate@" + HOST, self.report()["source_file"])

    def test_the_email_data_view(self):
        stub_model = self.controller.model
        stub_model.replace_default_app_url = lambda url: url
        stub_model.email_manager = SimpleNamespace(construct_and_send_email=mock.Mock())
        stub_model.is_container = False
        template = {model.KG__email_template__can_be_sent_anonymously: False, model.KG__email_template__fixed_address: None,
                    model.KG__email_template__validation_schema: "default", model.KG__email_template__data_view: "slow_view",
                    model.KG__email_template__dispatcher: "dispatcher"}
        with slow_queries.request_scope("/email", "POST", "/email"), \
                mock.patch.object(model, "application__select", return_value={model.KG__application__base_url: PUBLIC_URL,
                                                                               model.KG__application__name: "app",
                                                                               model.KG__application__templates_source: "templates"}), \
                mock.patch.object(model, "email_template__select", return_value=template), \
                mock.patch.object(model, "fetch_document_templates_for_email_template", return_value=[]):
            JAAQLModel.send_email(stub_model, False, TEST_ROLE, {"application": APPLICATION, "template": "slow_mail", "parameters": {"t": 0.6}},
                                  "someone@example.com", None)
        stub_model.email_manager.construct_and_send_email.assert_called_once()
        self.assertEqual("slow-query:email:" + APPLICATION + ".slow_mail@" + HOST, self.report()["source_file"])

    def test_the_auth_verifier(self):
        interface = create_interface_for_db(self.vault, CONFIG, TEST_ROLE, TEST_DATABASE)
        verdict = queue.Queue()

        class Stop(Exception):
            pass

        class OneRequest:
            def __init__(self):
                self.items = [("token", "127.0.0.1", verdict)]

            def get(self):
                if not self.items:
                    raise Stop()
                return self.items.pop()

        stub_model = SimpleNamespace(verify_auth_token=lambda token, ip_address: execute_supplied_statement(interface, "SELECT slow(0.6)"))
        with self.assertRaises(Stop):
            JAAQLModel.verification_thread(stub_model, OneRequest())
        self.assertEqual((True, None, None), verdict.get_nowait())
        body = self.report()
        self.assertEqual(PUBLIC_URL + " (auth-verification)", body["location"])
        self.assertEqual("jaaql", body["source_system"])
        self.assertIn("\nBackground: auth-verification on " + PUBLIC_URL + "\n", body["stacktrace"])

    def test_the_wait_for_the_verifiers_verdict_is_not_counted(self):
        # The verdict comes 0.8 s after the statement is ready to go; the statement then sleeps 0.2 s. Counting the wait would report ~1 s
        interface = create_interface_for_db(self.vault, CONFIG, TEST_ROLE, TEST_DATABASE)
        hook = queue.Queue()
        verdict = threading.Timer(0.8, hook.put, args=[(True, None, None)])
        with mock.patch.object(slow_queries, "THRESHOLD_SECONDS", 0.15), slow_queries.request_scope("/call-proc", "POST", "/call-proc"):
            started = time.perf_counter()
            verdict.start()
            InterpretJAAQL(interface).transform({"query": "SELECT pg_sleep(0.2)", "application": APPLICATION}, wait_hook=hook)
            wall = time.perf_counter() - started
        verdict.join()
        self.assertGreaterEqual(wall, 0.8 + 0.2)
        seconds = float(re.match(r"Slow query: (\d+\.\d\d) s sql:", self.report()["error_condensed"]).group(1))
        self.assertGreaterEqual(seconds, 0.2)
        self.assertLess(seconds, 0.7)

    def test_nothing_outside_a_request_is_timed(self):
        interface = create_interface_for_db(self.vault, CONFIG, TEST_ROLE, TEST_DATABASE)
        with mock.patch.object(interface, "execute_query", wraps=interface.execute_query) as executed:
            execute_supplied_statement(interface, "SELECT slow(0.6)")
        self.assertIsNone(executed.call_args.kwargs["capture_timing"])
        self.assertNoReport()

    def test_a_report_is_accepted_by_sentinels_ingest_sql(self):
        res = self.post("/submit", {"query": "SELECT slow(:t)", "parameters": {"t": 0.6}}, user_agent="Mozilla/5.0 (Ünïcode)")
        self.assertEqual(200, res.status_code, res.data)
        payload = self.report()
        self.assertEqual("Mozilla/5.0 (?n?code)", payload["user_agent"])
        self.stub.reset()

        # The ingest route of this JAAQL, with its INSERT run as the test role against Sentinel's table and domains
        stub_model = self.controller.model
        stub_model.submit = lambda inputs, account_id, **kwargs: JAAQLModel.submit(stub_model, inputs, TEST_ROLE, **kwargs)
        with contextlib.redirect_stderr(io.StringIO()):
            accepted = self.client.post(ENDPOINT__report_sentinel_error, json=payload)
            extra_key = self.client.post(ENDPOINT__report_sentinel_error, json=dict(payload, source_file="extra", extra="x"))
            raw_agent = self.client.post(ENDPOINT__report_sentinel_error, json=dict(payload, source_file="raw", user_agent="Mozilla/5.0 (Ünïcode)"))
        self.assertEqual(200, accepted.status_code, accepted.data)
        self.assertEqual([(payload["source_file"], payload["source_system"], payload["error_condensed"], payload["stacktrace"])],
                         self.admin("SELECT source_file, source_system, error_condensed, stacktrace FROM error"))
        self.assertNotEqual(200, extra_key.status_code)
        self.assertEqual(422, raw_agent.status_code, raw_agent.data)
        self.assertEqual(1, self.admin("SELECT count(*) FROM error")[0][0])
        self.assertNoReport()


if __name__ == "__main__":
    unittest.main()
