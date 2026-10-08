"""
Server-error reports to Sentinel: a request that fails because of JAAQL or its infrastructure (an exception JAAQL did not expect, a 5xx,
JAAQL's own SQL failing or the database server failing under any SQL though the request is answered 4xx) is printed as one line and posted to
Sentinel's ingest route with exactly the keys that route binds, once; a request that fails because of what the client sent (its SQL, whatever
it raises short of the server failing under it, a malformed body, any 4xx, a client gone) never is. A report shows the values of a query
route's inputs only, and never an email address, an authorization code or an encrypted literal.
The answer is the same byte for byte whether the report is made, Sentinel is not configured or the reporting is off, and never waits for
Sentinel.

    python -m unittest jaaql.test.test_server_errors

The unit tests need only the package's requirements: statements run on stand-in database interfaces that raise the error a test names, and
Sentinel and Keycloak are stub HTTP servers on 127.0.0.1. TestServerErrorsAgainstPostgres drives the real request paths against a scratch
Postgres with the jaaql extension available; it runs only when JAAQL_TEST_POSTGRES_URI is set to
postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database jaaql_test_err500 and the role
jaaql_test_err500_user
"""
import contextlib
import inspect
import io
import json
import os
import queue
import sys
import threading
import time
import unittest
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest import mock

import greenlet
import jwt
import psycopg
import psycopg.errors as pg
import requests
from jwcrypto import jwe, jwk
from psycopg_pool import PoolTimeout
from werkzeug.exceptions import InternalServerError, ClientDisconnected

from jaaql.constants import ENDPOINT__report_sentinel_error, ENDPOINT__oidc_get_token, VERSION, KEY__database, ROLE__jaaql
from jaaql.db import db_utils_no_circ, db_pg_interface
from jaaql.mvc import base_controller
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface, execute_supplied_statement
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.exceptions.jaaql_interpretable_handled_errors import UserUnauthorized
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.mvc import model, handmade_queries, exception_queries
from jaaql.mvc.exception_queries import QUERY__fetch_application_schemas, KEY__is_default, KG__application_schema__application
from jaaql.mvc.generated_queries import KG__application_schema__name, KG__application__is_live
from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_slow_queries import StubModel, StubVault, TimedInterface, SlowQueryCase, CONFIG, SUPER_KEY, PUBLIC_URL, \
    APPLICATION, SOURCE_SYSTEM, REPORT_KEYS, SENTINEL_DDL, ENVIRON__test_postgres_uri, closed_port
from jaaql.utilities import sentinel, slow_queries, server_errors
from jaaql.utilities.utils_no_project_imports import COOKIE_OIDC, COOKIE_OIDC_RETURN
from monitor.main import HEADER__security_bypass, HEADER__security

ACCOUNT = "account-1"
RETURN_PAGE = PUBLIC_URL + "/lesson__browse.html"


def raiser(make):
    # A function raising a fresh exception on every call, as a request's code would
    def raise_it(*args, **kwargs):
        raise make()
    return raise_it


def line_of(function, text: str) -> int:
    # The line of a JAAQL function whose source holds text, which a report must name
    lines, first = inspect.getsourcelines(function)
    return next(first + idx for idx, line in enumerate(lines) if text in line)


class RaisingInterface(TimedInterface):
    """
    Runs no SQL: waits for the verifier's verdict as DBPGInterface does, then every statement raises what make() builds (or, with make None,
    answers as TimedInterface). role is the interface's role: None for JAAQL's lookup connection, an account for the requester's
    """

    def __init__(self, make=None, role=None, db_name="jaaql", rows=None):
        super().__init__()
        self.make = make
        self.role = role
        self.db_name = db_name
        self.rows = rows
        self.statements = []

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        self.statements.append(query)
        if wait_hook:
            db_pg_interface.await_verdict(wait_hook)
        if self.make is not None:
            raise self.make()
        if self.rows is not None:
            return [name for name in self.rows], [0] * len(self.rows), [list(self.rows.values())]
        return super().execute_query(conn, query, parameters, wait_hook, prepare, capture_provenance, capture_timing)


class LosingConnection(TimedInterface):
    """
    Every connection it hands out dies under the statement (a database restart), until lost runs out; then statements succeed, answering
    no rows when empty
    """

    def __init__(self, lost: int, empty: bool = False):
        super().__init__()
        self.lost = lost
        self.empty = empty
        self.attempts = 0

    def get_conn(self):
        self.attempts += 1
        return SimpleNamespace(autocommit=False, closed=self.attempts <= self.lost)

    def is_connection_closed(self, conn):
        return conn.closed

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        if conn.closed:
            raise psycopg.OperationalError("server closed the connection unexpectedly")
        if self.empty:
            return ["name"], [0], []
        return super().execute_query(conn, query, parameters, wait_hook, prepare, capture_provenance, capture_timing)


class PoolTimingOut(TimedInterface):
    # DBPGInterface.get_conn over a pool that has no connection to give
    get_conn = DBPGInterface.get_conn

    def _get_conn(self):
        raise PoolTimeout("couldn't get a connection after 2.50 sec")


class RefusingCommit(TimedInterface):
    # Statements succeed; the COMMIT is refused with what make() builds, and translated as DBPGInterface translates it
    translate_commit_error = DBPGInterface.translate_commit_error

    def __init__(self, make, role=None):
        super().__init__()
        self.make = make
        self.role = role

    def commit(self, conn):
        raise self.make()


class CommittingThenLost(LosingConnection):
    # Its statements may end their transaction (a COMMIT of the request's own); the connection dies under them
    def statement_may_end_transaction(self, query):
        return True


class ClosedBeforeCommit(TimedInterface):
    # Its statement may end its transaction and succeeds; the connection is gone before JAAQL's COMMIT
    def statement_may_end_transaction(self, query):
        return True

    def is_connection_closed(self, conn):
        return True


class LostCommit(RefusingCommit):
    # The COMMIT is lost in flight: the connection closes under it, so it may have committed
    def __init__(self, role=None):
        super().__init__(lambda: psycopg.OperationalError("server closed the connection unexpectedly"), role=role)

    def commit(self, conn):
        conn.closed = True
        super().commit(conn)


# The database server failing rather than refusing the SQL: the server's whoever wrote the SQL
SERVER_FAILURES = [
    lambda: pg.DiskFull("could not extend file: No space left on device"),
    lambda: pg.OutOfMemory("out of memory"),
    lambda: pg.TooManyConnections("sorry, too many clients already"),
    lambda: pg.InternalError_("could not read block 0 in file"),
    lambda: pg.DataCorrupted("invalid page in block 7 of relation base/16384/16385"),
    lambda: pg.IndexCorrupted("index contains unexpected zero page"),
    lambda: pg.IoError("could not fsync file"),
    lambda: pg.AdminShutdown("terminating connection due to administrator command"),
    lambda: pg.CannotConnectNow("the database system is starting up"),
    lambda: pg.ConfigFileError("configuration file contains errors"),
    lambda: pg.ConnectionFailure("connection to the server was lost"),
]


class Vault:
    def __init__(self, uri="postgresql://postgres:unused@localhost:5432/postgres"):
        self.uri = uri

    def get_obj(self, key):
        return self.uri

    def has_obj(self, key):
        return False


class ErrorStubModel(StubModel):
    """
    StubModel, with the real JAAQLModel methods of the routes and calls these tests drive
    """
    resend_verification_email = JAAQLModel.resend_verification_email
    _kc_get_token = JAAQLModel._kc_get_token
    _kc_find_user_id_by_username = JAAQLModel._kc_find_user_id_by_username
    _kc_send_verify_email = JAAQLModel._kc_send_verify_email
    handle_procedure = JAAQLModel.handle_procedure
    exchange_auth_code = JAAQLModel.exchange_auth_code
    _gate_run_singleton = JAAQLModel._gate_run_singleton
    _run_federation_procedure = JAAQLModel._run_federation_procedure
    send_email = JAAQLModel.send_email
    verify_auth_token = JAAQLModel.verify_auth_token

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vault = self.vault or Vault()
        self.verdict = (True, None, None)
        self.use_oidc_basic = True
        self.use_fapi_advanced = False
        self.is_https = False
        self.idp_session = None

    def verify_auth_token_threaded(self, auth_token, ip_address, complete):
        # The parallel verifier's verdict on a token login; None: it never gives one
        if self.verdict is not None:
            complete.put(self.verdict)
        return self.account, "someone@example.com", None, False, False

    def fetch_discovery_content(self, *args):
        return {"issuer": PUBLIC_URL + "/realms/r", "token_endpoint": PUBLIC_URL + "/realms/r/protocol/openid-connect/token",
                "id_token_signing_alg_values_supported": ["RS256"]}

    def fetch_jwks_client(self, *args):
        return SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key="unused"))

    def replace_default_app_url(self, url):
        return url


class StubKeycloak:
    """
    Keycloak's token and admin routes: the token route answers a token, every other route answers status
    """

    def __init__(self, status=401):
        self.status = status
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def answer(self, status, body):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.answer(200, b'{"access_token": "admin-token"}')

            def do_GET(self):
                self.answer(stub.status, b'{"error": "unauthorized"}')

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class ServerErrorCase(SlowQueryCase):

    def setUp(self):
        super().setUp()
        server_errors.reset_throttle()
        self.printed = io.StringIO()
        self.quiet = contextlib.ExitStack()
        self.quiet.enter_context(contextlib.redirect_stdout(self.printed))
        self.quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        self.quiet.enter_context(mock.patch.object(model, "is_federation_procedure", return_value=False))

    def tearDown(self):
        self.quiet.close()
        server_errors.reset_throttle()
        super().tearDown()

    def make_model(self):
        return ErrorStubModel()

    @property
    def model(self):
        return self.controller.model

    def lines(self):
        return [line for line in self.printed.getvalue().splitlines() if line.startswith("SERVER ERROR")]

    def answers(self, make_request):
        """
        The answer to make_request() with server-error reports on, with Sentinel not configured, and with the reporting code off, which are
        the same byte for byte, and the reports Sentinel received with them on
        """
        def answer(res):
            return res.status_code, sorted(res.headers.items()), res.get_data()

        server_errors.reset_throttle()
        reporting = answer(make_request())
        self.assertTrue(sentinel.wait_idle(10))
        reports = self.stub.bodies()
        self.stub.reset()
        server_errors.reset_throttle()
        sentinel.configure(None, None)
        try:
            unconfigured = answer(make_request())
        finally:
            sentinel.configure(self.stub.url, None)
        with mock.patch.object(server_errors, "request_failed"), mock.patch.object(server_errors, "unrouted_failure"):
            off = answer(make_request())
        self.assertNoReport()
        server_errors.reset_throttle()
        self.assertEqual(reporting, unconfigured)
        self.assertEqual(reporting, off)
        return reporting, reports

    def assertServerContract(self, body):
        self.assertEqual(REPORT_KEYS, set(body))
        self.assertRegex(body["source_system"], r"^[a-z0-9-]{1,63}$")
        self.assertLessEqual(len(body["source_file"]), 255)
        self.assertLessEqual(len(body["location"]), 512)
        self.assertLessEqual(len(body["version"]), 40)
        self.assertLessEqual(len(body["error_condensed"]), 200)
        self.assertTrue(body["file_line_number"] is None or isinstance(body["file_line_number"], int) and 0 <= body["file_line_number"] <= 999999)
        self.assertTrue(body["file_col_number"] is None or isinstance(body["file_col_number"], int) and 1 <= body["file_col_number"] <= 999999)
        self.assertEqual("JAAQL " + VERSION, body["version"])
        self.assertIsInstance(body["stacktrace"], str)
        self.assertNotEqual("", body["stacktrace"])
        self.assertFalse(body["stacktrace"].endswith("\n"))
        self.assertTrue(body["user_agent"].isascii() and len(body["user_agent"]) <= 512)

    def call_proc(self, parameters=None, **kwargs):
        return self.post("/call-proc", {"query": "lesson.save", "parameters": parameters or {"lesson": 1}}, **kwargs)

    def submit(self, query="SELECT 1", parameters=None, **kwargs):
        return self.post("/submit", {"query": query, "parameters": parameters or {}}, **kwargs)

    def interface(self, interface):
        return mock.patch.object(db_utils_no_circ, "get_required_db", return_value=interface)


class TestWhatIsReported(ServerErrorCase):

    def test_an_unexpected_exception_is_reported_once_with_the_bound_keys_and_answers_as_before(self):
        with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("federation_procedure"))):
            (status, headers, data), reports = self.answers(self.call_proc)
        self.assertEqual(500, status)
        self.assertEqual({"error_code": 1099, "message": "An unhandled exception has occurred with JAAQL.", "column_name": None,
                          "descriptor": None, "index": None, "set": None, "table_name": None}, json.loads(data))
        self.assertEqual(1, len(reports))
        body = reports[0]
        self.assertServerContract(body)
        line = line_of(JAAQLModel.call_proc, "if is_federation_procedure(")
        self.assertEqual("jaaql/mvc/model.py", body["source_file"])
        self.assertEqual(line, body["file_line_number"])
        self.assertIsInstance(body["file_col_number"], int)
        self.assertEqual("KeyError: 'federation_procedure'", body["error_condensed"])
        self.assertEqual(PUBLIC_URL + "/api/call-proc", body["location"])
        self.assertEqual(SOURCE_SYSTEM, body["source_system"])
        self.assertEqual("Mozilla/5.0 (Test)", body["user_agent"])
        trace = body["stacktrace"]
        self.assertTrue(trace.startswith("Server error: KeyError: 'federation_procedure'\nAnswered: 500 (error_code 1099)\n"
                                         "Where: jaaql/mvc/model.py:%d in call_proc\nRoute: POST /call-proc on %s\n" % (line, PUBLIC_URL)), trace)
        self.assertIn("\nApplication: " + APPLICATION + " | database: - | account: " + ACCOUNT + "\n", trace)
        self.assertIn('\nRequest inputs:\n\t{"application": "' + APPLICATION + '", "parameters": {"lesson": 1}, "query": "lesson.save"}\n', trace)
        self.assertIn('\nTraceback (most recent call last):\n  File "jaaql/mvc/base_controller.py", line ', trace)
        self.assertTrue(trace.endswith("KeyError: 'federation_procedure'"), trace[-200:])
        self.assertNotIn("super_db", trace)
        self.assertEqual(["SERVER ERROR KeyError at jaaql/mvc/model.py:%d (POST /call-proc, %s) answered 500 (error_code 1099) - reported" % (
            line, APPLICATION), "SERVER ERROR KeyError at jaaql/mvc/model.py:%d (POST /call-proc, %s) answered 500 (error_code 1099)" % (
            line, APPLICATION)], self.lines())

    def test_a_compiled_query_missing_from_a_cache_that_needed_reloading(self):
        # A queries.json newer than the cache, whose reload still lacks the query (a deploy half written, the 08 Jul incident): the
        # server's. With the cache as on disk the request named a query the application does not have (TestWhatIsNeverReported)
        reloads = []
        with mock.patch.object(self.model, "query_cache_is_stale", return_value=True), \
                mock.patch.object(self.model, "reload_cache", lambda: reloads.append(1), create=True):
            (status, _, data), reports = self.answers(lambda: self.post("/execute", {"query": {"a": "missing:0"}}))
        self.assertEqual((500, b"Compiled query 'missing' is not present in the query cache"), (status, data))
        self.assertEqual(3, len(reloads))
        self.assertServerContract(reports[0])
        self.assertEqual(["jaaql/mvc/model.py", line_of(JAAQLModel._lookup_cached_query, "raise missing")],
                         [reports[0]["source_file"], reports[0]["file_line_number"]])
        self.assertEqual("HttpStatusException: Compiled query 'missing' is not present in the query cache", reports[0]["error_condensed"])
        self.assertIn("\nAnswered: 500\n", reports[0]["stacktrace"])

    def test_deep_health_missing_its_query_from_a_cache_as_on_disk(self):
        # JAAQL's own query, which the microcompiler puts in every queries.json: missing, the box cannot serve, whatever the cache
        with mock.patch.object(self.model, "deep_health", lambda: JAAQLModel.deep_health(self.model), create=True):
            (status, _, data), reports = self.answers(lambda: self.client.get("/internal/deep-health"))
        self.assertEqual((500, b"Compiled query '__health__' is not present in the query cache"), (status, data))
        self.assertEqual(1, len(reports))
        self.assertEqual("HttpStatusException: Compiled query '__health__' is not present in the query cache", reports[0]["error_condensed"])

    def test_a_connection_lost_on_every_attempt(self):
        interfaces = []

        def request():
            interfaces.append(LosingConnection(lost=99))
            with self.interface(interfaces[-1]):
                return self.submit()

        (status, _, data), reports = self.answers(request)
        self.assertEqual(500, status)
        self.assertTrue(data.startswith(b"Connection lost, transaction not persisted: "), data)
        self.assertEqual(3, interfaces[0].attempts)
        self.assertEqual(1, len(reports))
        self.assertEqual("ConnectionLostError: Connection lost, transaction not persisted: server closed the connection unexpectedly",
                         reports[0]["error_condensed"])

    def test_a_connection_lost_once_and_retried_is_not_reported(self):
        interface = LosingConnection(lost=1)
        with self.interface(interface):
            self.assertEqual(200, self.submit().status_code)
        self.assertEqual(2, interface.attempts)
        # Nor is JAAQL's own query retried so, in a request that then fails because of the client
        self.model.jaaql_lookup_connection = LosingConnection(lost=1, empty=True)
        with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure), \
                self.interface(RaisingInterface(lambda: pg.UniqueViolation("duplicate key value violates unique constraint"))):
            self.assertEqual(422, self.call_proc().status_code)
        self.assertEqual(2, self.model.jaaql_lookup_connection.attempts)
        self.assertNoReport()
        self.assertEqual([], self.lines())

    def test_a_pool_with_no_connection_to_give(self):
        with self.interface(PoolTimingOut()):
            (status, _, data), reports = self.answers(self.submit)
        self.assertEqual((500, b"Could not create connection to database!"), (status, data))
        self.assertEqual(["jaaql/db/db_pg_interface.py", line_of(DBPGInterface.get_conn, "raise HttpStatusException(ERR__connect_db")],
                         [reports[0]["source_file"], reports[0]["file_line_number"]])

    def test_keycloak_unreachable_without_the_url_query_string(self):
        email = "someone" + "@example.com"
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": "http://127.0.0.1:%d" % closed_port(), "KEYCLOAK_REALM": "lesbij"}), \
                mock.patch.object(self.model, "call_proc", lambda inputs, account_id, verification_hook=None:
                                  self.model.resend_verification_email(email)):
            (status, _, _), reports = self.answers(self.call_proc)
        self.assertEqual(500, status)
        self.assertEqual(1, len(reports))
        self.assertServerContract(reports[0])
        self.assertTrue(reports[0]["error_condensed"].startswith("ConnectionError: "), reports[0]["error_condensed"])
        self.assertEqual("jaaql/mvc/model.py", reports[0]["source_file"])
        report = json.dumps(reports[0])
        self.assertNotIn("someone", report)
        self.assertNotIn("example.com", report)
        self.assertNotIn("exact=true", report)

    def test_keycloak_refusing_or_failing_is_not_reported(self):
        # Keycloak's own answer, a refusal of what the admin typed or a failure of its own, is never reported; the answer is unchanged
        for keycloak_status in (400, 401, 409, 500, 503):
            stub_keycloak = StubKeycloak(status=keycloak_status)
            try:
                with self.subTest(keycloak_status=keycloak_status), \
                        mock.patch.dict(os.environ, {"KEYCLOAK_URL": stub_keycloak.url, "KEYCLOAK_REALM": "lesbij"}), \
                        mock.patch.object(self.model, "call_proc", lambda inputs, account_id, verification_hook=None:
                                          self.model.resend_verification_email("someone" + "@example.com")):
                    (status, _, _), reports = self.answers(self.call_proc)
                    self.assertEqual(500, status)
                    self.assertEqual([], reports)
            finally:
                stub_keycloak.close()

    def test_a_result_json_cannot_serialise(self):
        # An interval column, say: a gap in JAAQL, answered 500
        with self.interface(RaisingInterface(rows={"gap": timedelta(days=1)})):
            (status, _, data), reports = self.answers(self.submit)
        self.assertEqual(500, status)
        self.assertEqual(1099, json.loads(data)["error_code"])
        self.assertTrue(reports[0]["error_condensed"].startswith(("TypeError: ", "JSONEncodeError: ")), reports[0]["error_condensed"])

    def test_an_undocumented_status_swapped_to_500(self):
        with mock.patch.object(self.model, "get_auth_token", raiser(lambda: HttpStatusException("conflict", 409)), create=True):
            (status, _, _), reports = self.answers(lambda: self.client.post("/oauth/token", json={"username": "u", "password": "p"}))
        self.assertEqual(500, status)
        self.assertEqual("Exception: Response with code '409' was not expected", reports[0]["error_condensed"])
        self.assertEqual("jaaql/mvc/base_controller.py", reports[0]["source_file"])

    def test_an_explicit_internal_server_error_is_reported_once_not_twice(self):
        with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(InternalServerError)):
            (status, _, data), reports = self.answers(self.call_proc)
        self.assertEqual((500, b"We have encountered an error whilst processing your request!"), (status, data))
        self.assertEqual(1, len(reports))
        self.assertTrue(reports[0]["error_condensed"].startswith("InternalServerError: 500 Internal Server Error"), reports[0]["error_condensed"])

    def test_a_route_added_to_the_app_directly_is_reported_by_the_handlers(self):
        @self.controller.app.route("/test-raw-route")
        def raw_route():
            raise KeyError("raw")

        @self.controller.app.route("/test-raw-internal-error")
        def raw_internal_error():
            raise InternalServerError()

        (status, _, data), reports = self.answers(lambda: self.client.get("/test-raw-route"))
        self.assertEqual(500, status)
        self.assertEqual(1, len(reports))
        self.assertServerContract(reports[0])
        self.assertEqual(["jaaql/test/test_server_errors.py", "KeyError: 'raw'", PUBLIC_URL + "/api/test-raw-route"],
                         [reports[0]["source_file"], reports[0]["error_condensed"], reports[0]["location"]])
        (status, _, _), reports = self.answers(lambda: self.client.get("/test-raw-internal-error"))
        self.assertEqual(500, status)
        self.assertEqual(1, len(reports))

    def test_a_cloud_procedure_that_crashes_is_reported_without_its_output(self):
        command = '"%s" -c "import sys; print(\'SECRET-STDOUT\'); sys.stderr.write(\'SECRET-STDERR\'); sys.exit(3)"' % sys.executable
        with mock.patch.object(model, "remote_procedure__select", return_value={"command": command, "access": model.RPC_ACCESS__private}):
            (status, _, data), reports = self.answers(lambda: self.client.post(
                "/remote_procedure", json={"application": APPLICATION, "name": "nightly", "args": {"note": "kept"}},
                headers={HEADER__security_bypass: SUPER_KEY, HEADER__security: "a.token", "User-Agent": "BATON"}))
        self.assertEqual(500, status)
        self.assertEqual(1023, json.loads(data)["error_code"])
        self.assertEqual(1, len(reports))
        body = reports[0]
        self.assertServerContract(body)
        self.assertEqual(("remote-procedure:" + APPLICATION + "/nightly", None, None),
                         (body["source_file"], body["file_line_number"], body["file_col_number"]))
        self.assertIn("\nDetail: the remote procedure exited with code 3, printing 14 characters to stdout and 13 to stderr (not shown)\n",
                      body["stacktrace"])
        self.assertNotIn("SECRET-", json.dumps(body))

    def test_a_cloud_procedure_printing_what_is_no_json_is_reported(self):
        command = '"%s" -c "print(\'SECRET-not-json\')"' % sys.executable
        with mock.patch.object(model, "remote_procedure__select", return_value={"command": command, "access": model.RPC_ACCESS__private}):
            (status, _, _), reports = self.answers(lambda: self.client.post(
                "/remote_procedure", json={"application": APPLICATION, "name": "nightly", "args": {}},
                headers={HEADER__security_bypass: SUPER_KEY, HEADER__security: "a.token"}))
        self.assertEqual(500, status)
        self.assertEqual("remote-procedure:" + APPLICATION + "/nightly", reports[0]["source_file"])
        self.assertNotIn("SECRET-", json.dumps(reports[0]))


class TestServerFaultsAnsweredAsClientErrors(ServerErrorCase):

    def test_jaaqls_own_query_failing_is_reported(self):
        self.model.jaaql_lookup_connection = RaisingInterface(lambda: pg.UndefinedTable('relation "federation_procedure" does not exist'))
        with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure):
            (status, _, data), reports = self.answers(lambda: self.call_proc({"lesson": 1, "secret_note": "hidden"}))
        self.assertEqual(422, status)
        self.assertEqual(1004, json.loads(data)["error_code"])
        self.assertEqual(1, len(reports))
        body = reports[0]
        self.assertServerContract(body)
        line = line_of(handmade_queries.is_federation_procedure, "return len(execute_supplied_statement(")
        self.assertEqual(["jaaql/mvc/handmade_queries.py", line], [body["source_file"], body["file_line_number"]])
        self.assertEqual('UndefinedTable 42P01: relation "federation_procedure" does not exist', body["error_condensed"])
        trace = body["stacktrace"]
        self.assertIn("\nAnswered: 422 (error_code 1004), a server-side failure JAAQL answers as a client error\n", trace)
        self.assertIn("\nWhere: jaaql/mvc/handmade_queries.py:%d in is_federation_procedure (JAAQL's own query)\n" % line, trace)
        self.assertIn("| database: jaaql | account: " + ACCOUNT + "\n", trace)
        self.assertIn("\nStatement (JAAQL's own, query key query):\n\t" + handmade_queries.QUERY__is_federation_procedure.strip().splitlines()[0],
                      trace)
        self.assertIn("\tParameters: name (values not shown)\n", trace)
        # The procedure's name is the value of JAAQL's own parameter: shown in the request's inputs, never with the statement
        statement = trace.split("\nStatement")[1].split("\nRequest inputs")[0]
        self.assertNotIn("lesson.save", statement)
        self.assertIn('"secret_note": "<redacted>"', trace)
        self.assertNotIn("hidden", trace)
        # From JAAQL's outermost frame down to the statement
        self.assertIn('\nTraceback (most recent call last):\n  File "jaaql/mvc/base_controller.py", line ', trace)
        self.assertIn('File "jaaql/interpreter/interpret_jaaql.py", line ', trace)
        self.assertNotIn("site-packages/flask", trace)

    def test_a_bug_in_the_interpreter_running_jaaqls_own_query_is_reported(self):
        self.model.jaaql_lookup_connection = RaisingInterface(lambda: KeyError("account"))
        with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure):
            (status, _, _), reports = self.answers(self.call_proc)
        self.assertEqual(422, status)
        self.assertEqual("KeyError: 'account'", reports[0]["error_condensed"])
        self.assertIn("(JAAQL's own code, running its own query)", reports[0]["stacktrace"])

    def test_the_verifiers_verdict_timing_out_is_reported_once(self):
        self.model.verdict = None
        with mock.patch.object(db_pg_interface, "WAIT_HOOK__timeout", 0.2), self.interface(RaisingInterface()):
            (status, _, data), reports = self.answers(lambda: self.submit(bypass=False))
            self.assertEqual((422, b"Authorization verification timed out"), (status, data))
            self.assertEqual(1, len(reports))
            self.assertEqual("VerificationTimedOut: Authorization verification timed out", reports[0]["error_condensed"])
            self.assertIn("(the wait for the authorization verifier's verdict)", reports[0]["stacktrace"])
            self.submit(bypass=False)
            self.submit(bypass=False)
        self.report(1)
        self.assertTrue(self.lines()[-1].endswith("- repeat, not reported"), self.lines())

    def test_a_pool_that_cannot_be_made_is_reported(self):
        refused = psycopg.OperationalError('connection failed: FATAL:  password authentication failed for user "postgres"')
        with mock.patch.object(db_pg_interface, "ConnectionPool", side_effect=raiser(lambda: refused)):
            (status, _, data), reports = self.answers(lambda: self.post("/submit", {"query": "SELECT 1", "database": "err500_refused"},
                                                                        application=None))
        self.assertEqual(422, status)
        self.assertIn(b"password authentication failed", data)
        self.assertEqual("OperationalError: connection failed: FATAL:  password authentication failed for user \"postgres\"",
                         reports[0]["error_condensed"])
        self.assertIn("(making the connection pool)", reports[0]["stacktrace"])
        self.assertIn("| database: err500_refused |", reports[0]["stacktrace"])

    def test_a_missing_database_is_not_reported(self):
        missing = PoolTimeout("couldn't get a connection after 2.50 sec")
        with mock.patch.object(db_pg_interface, "ConnectionPool", side_effect=raiser(lambda: missing)):
            (status, _, _), reports = self.answers(lambda: self.post("/submit", {"query": "SELECT 1", "database": "err500_missing"},
                                                                     application=None))
        self.assertEqual((460, []), (status, reports))

    def test_a_refused_commit_of_jaaqls_own_query(self):
        for make, reported in [(lambda: pg.SerializationFailure("could not serialize access"), True),
                               (lambda: pg.UniqueViolation("duplicate key value violates unique constraint"), False)]:
            with self.subTest(reported=reported):
                self.model.jaaql_lookup_connection = RefusingCommit(make)
                with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure):
                    (status, _, _), reports = self.answers(self.call_proc)
                self.assertEqual(422, status)
                self.assertEqual(1 if reported else 0, len(reports))
                if reported:
                    self.assertIn("(the COMMIT of JAAQL's own query)", reports[0]["stacktrace"])
                    self.assertEqual("SerializationFailure 40001: could not serialize access", reports[0]["error_condensed"])

    def test_jaaqls_own_query_refusing_the_clients_data_or_identity_is_not_reported(self):
        for make, role in [(lambda: pg.InvalidTextRepresentation('invalid input syntax for type uuid: "x"'), None),
                           (lambda: pg.UniqueViolation("duplicate key value violates unique constraint"), None),
                           (lambda: pg.RaiseException("a jaaql function refused it"), None),
                           (lambda: psycopg.DataError("PostgreSQL text fields cannot contain NUL (0x00) bytes"), None),
                           (lambda: pg.InsufficientPrivilege("permission denied for table account"), ACCOUNT)]:
            with self.subTest(error=type(make()).__name__):
                self.model.jaaql_lookup_connection = RaisingInterface(make, role=role)
                with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure):
                    (status, _, _), reports = self.answers(self.call_proc)
                self.assertEqual((422, []), (status, reports))
        # Refused as JAAQL itself, it is JAAQL's
        self.model.jaaql_lookup_connection = RaisingInterface(lambda: pg.InsufficientPrivilege("permission denied for table account"))
        with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure):
            (status, _, _), reports = self.answers(self.call_proc)
        self.assertEqual((422, 1), (status, len(reports)))

    def test_which_sqlstates_of_jaaqls_own_query_are_the_clients(self):
        requester = SimpleNamespace(role=ACCOUNT)
        lookup = SimpleNamespace(role=None)
        as_jaaql = SimpleNamespace(role=ROLE__jaaql)
        clients = [("22P02", lookup), ("22012", lookup), ("23505", lookup), ("23503", lookup), ("JQ000", lookup), ("P0001", lookup),
                   ("42501", requester)]
        servers = [("42P01", lookup), ("42703", lookup), ("42883", lookup), ("42601", lookup), ("42501", lookup), ("42501", as_jaaql),
                   ("08006", lookup), ("25P02", lookup), ("40001", lookup), ("40P01", lookup), ("53300", lookup), ("54000", lookup),
                   ("55P03", lookup), ("57014", lookup), ("57P01", lookup), ("58030", lookup), ("3D000", lookup), ("3F000", lookup),
                   ("F0000", lookup), ("XX000", lookup), ("P0002", lookup), ("P0004", lookup)]
        self.assertEqual([True] * len(clients), [server_errors.is_clients_sqlstate(state, interface) for state, interface in clients])
        self.assertEqual([False] * len(servers), [server_errors.is_clients_sqlstate(state, interface) for state, interface in servers])
        self.assertTrue(server_errors.is_clients_sqlstate(None, lookup, psycopg.DataError("NUL")))
        self.assertFalse(server_errors.is_clients_sqlstate(None, lookup, psycopg.OperationalError("server closed the connection")))
        self.assertFalse(server_errors.is_clients_sqlstate(None, lookup, psycopg.ProgrammingError("the query has 2 placeholders")))

    def test_the_database_server_failing_under_the_clients_sql_is_reported(self):
        # Disk full, out of memory, corruption, an I/O error, a shutdown under the app's INSERT: SQL text does not cause them
        self.model.query_caches["queries"]["kept"] = ["INSERT INTO kept VALUES (:id)"]
        routes = {
            "/submit": lambda: self.submit("INSERT INTO kept VALUES (:id)", {"id": 1}),
            "/execute": lambda: self.post("/execute", {"query": {"a": "kept:0"}, "parameters": {"id": 1}}),
            "/call-proc": lambda: self.call_proc({"id": 1}),
        }
        for route, request in routes.items():
            for make in SERVER_FAILURES:
                with self.subTest(route=route, error=type(make()).__name__), self.interface(RaisingInterface(make, role=ACCOUNT)):
                    (status, _, data), reports = self.answers(request)
                    self.assertEqual(422, status)
                    self.assertEqual(1, len(reports))
                    body = reports[0]
                    self.assertServerContract(body)
                    error = make()
                    self.assertEqual("%s %s: %s" % (type(error).__name__, error.sqlstate, error), body["error_condensed"])
                    self.assertEqual("jaaql/mvc/model.py", body["source_file"])
                    trace = body["stacktrace"]
                    self.assertIn(" (the database server, failing under the request's query)\n", trace)
                    self.assertIn("a server-side failure JAAQL answers as a client error\n", trace)
                    self.assertIn("\nStatement (the request's, query key ", trace)
                    self.assertIn("\tParameters: id (values not shown)\n", trace)

    def test_which_failures_are_the_database_server_failing(self):
        servers = [pg.ConnectionFailure, pg.DiskFull, pg.OutOfMemory, pg.TooManyConnections, pg.IoError, pg.UndefinedFile, pg.ConfigFileError,
                   pg.InternalError_, pg.DataCorrupted, pg.IndexCorrupted, pg.AdminShutdown, pg.CrashShutdown, pg.CannotConnectNow,
                   pg.DatabaseDropped, pg.IdleSessionTimeout]
        refusals = [pg.QueryCanceled, pg.ReadOnlySqlTransaction, pg.ProgramLimitExceeded, pg.SerializationFailure, pg.DeadlockDetected,
                    pg.LockNotAvailable, pg.InsufficientPrivilege, pg.DivisionByZero, pg.RaiseException, pg.UndefinedTable, pg.SyntaxError]
        self.assertEqual([True] * len(servers), [server_errors.is_servers_failure(error("x")) for error in servers])
        self.assertEqual([False] * len(refusals), [server_errors.is_servers_failure(error("x")) for error in refusals])
        self.assertFalse(server_errors.is_servers_failure(psycopg.OperationalError("server closed the connection")))

        # Unless the SQL raised it: a PL/pgSQL RAISE names any SQLSTATE (DO $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'disk_full'; END $$)
        class Raised(pg.DiskFull):
            diag = SimpleNamespace(sqlstate="53100", source_function="exec_stmt_raise")

        self.assertFalse(server_errors.is_servers_failure(Raised("x")))
        with self.interface(RaisingInterface(lambda: Raised("x"), role=ACCOUNT)):
            (status, _, _), reports = self.answers(lambda: self.submit("DO $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'disk_full'; END $$"))
        self.assertEqual((422, []), (status, reports))

    def test_a_connection_lost_after_the_clients_sql_may_have_committed_is_reported(self):
        # The outcome is unknown, so the request is not re-run and is answered 422: the connection went, whoever wrote the SQL
        cases = {
            "under a statement": lambda: CommittingThenLost(lost=99),
            "before the COMMIT": ClosedBeforeCommit,
            "with the COMMIT in flight": lambda: LostCommit(role=ACCOUNT),
        }
        for name, make in cases.items():
            interfaces = []

            def request():
                interfaces.append(make())
                with self.interface(interfaces[-1]):
                    return self.submit("INSERT INTO kept VALUES (1); COMMIT")

            with self.subTest(name):
                (status, _, data), reports = self.answers(request)
                self.assertEqual(422, status)
                self.assertEqual(1002, json.loads(data)["error_code"])
                self.assertEqual(1, len(reports))
                self.assertServerContract(reports[0])
                self.assertIn(" (the connection, lost after the request's query may have committed)\n", reports[0]["stacktrace"])
                if isinstance(interfaces[0], LosingConnection):
                    # Never re-run, which could apply it twice
                    self.assertEqual(1, interfaces[0].attempts)

    def test_the_database_server_failing_at_the_clients_commit(self):
        for make, reported in [(lambda: pg.DiskFull("could not extend file: No space left on device"), True),
                               (lambda: pg.IoError("could not fsync file"), True),
                               (lambda: pg.SerializationFailure("could not serialize access"), False),
                               (lambda: pg.UniqueViolation("duplicate key value violates unique constraint"), False)]:
            with self.subTest(error=type(make()).__name__), self.interface(RefusingCommit(make, role=ACCOUNT)):
                (status, _, _), reports = self.answers(lambda: self.submit("INSERT INTO kept VALUES (1)"))
                self.assertEqual(422, status)
                self.assertEqual(1 if reported else 0, len(reports))
                if reported:
                    self.assertIn(" (the database server, failing at the COMMIT of the request's query)\n", reports[0]["stacktrace"])


CLIENT_SQL_ERRORS = [
    lambda: pg.SyntaxError('syntax error at or near "SELEC"'),
    lambda: pg.InsufficientPrivilege("permission denied for table hidden"),
    lambda: pg.UniqueViolation('duplicate key value violates unique constraint "kept_pkey"'),
    lambda: pg.ForeignKeyViolation('insert or update on table "child" violates foreign key constraint'),
    lambda: pg.RaiseException("a business rule refused it"),
    lambda: psycopg.DatabaseError('[{"message": "a JQ000 business rule"}]'),
    lambda: pg.InvalidTextRepresentation('invalid input syntax for type integer: "x"'),
    lambda: pg.QueryCanceled("canceling statement due to statement timeout"),
    lambda: pg.LockNotAvailable('could not obtain lock on relation "kept"'),
    lambda: pg.DivisionByZero("division by zero"),
    lambda: pg.UndefinedFunction("function nope() does not exist"),
    lambda: pg.UndefinedColumn("column a.foo does not exist"),
    lambda: pg.DeadlockDetected("deadlock detected"),
]


class TestWhatIsNeverReported(ServerErrorCase):

    def test_the_clients_sql_whatever_it_raises(self):
        self.model.query_caches["queries"]["broken"] = ["SELEC 1"]
        routes = {
            "/submit": self.submit,
            "/execute": lambda: self.post("/execute", {"query": {"a": "broken:0"}}),
            "/call-proc": self.call_proc,
        }
        for route, request in routes.items():
            for make in CLIENT_SQL_ERRORS:
                with self.subTest(route=route, error=type(make()).__name__), self.interface(RaisingInterface(make, role=ACCOUNT)):
                    (status, _, _), reports = self.answers(request)
                    self.assertEqual((422, []), (status, reports))
        self.assertEqual([], self.lines())

    def run_in_request(self, route, call):
        # A model method run as routed_function runs a view: in a request scope, its failure seen before it is answered
        with slow_queries.request_scope(route, "POST", route):
            slow_queries.note_caller(ACCOUNT, False)
            try:
                return call()
            except Exception as ex:
                server_errors.request_failed(ex, route, True)
                return ex

    def test_the_security_event_and_email_procedures(self):
        stub_model = self.model
        template = {model.KG__email_template__can_be_sent_anonymously: False, model.KG__email_template__fixed_address: None,
                    model.KG__email_template__validation_schema: "default", model.KG__email_template__data_view: "lesson_mail",
                    model.KG__email_template__dispatcher: "dispatcher"}
        calls = {
            "/security-event": lambda: stub_model._gate_run_singleton({"application": APPLICATION, "parameters": {"lesson": 1}}, ACCOUNT,
                                                                      {"database_procedure": "lesson.reset"}),
            "/email": lambda: stub_model.send_email(False, ACCOUNT, {"application": APPLICATION, "template": "lesson_mail",
                                                                     "parameters": {"lesson": 1}}, "someone@example.com", None),
        }
        with mock.patch.object(model, "application__select", return_value={model.KG__application__base_url: PUBLIC_URL,
                                                                           model.KG__application__name: "app",
                                                                           model.KG__application__templates_source: "templates"}), \
                mock.patch.object(model, "email_template__select", return_value=template):
            for route, call in calls.items():
                with self.subTest(route=route), self.interface(RaisingInterface(lambda: pg.UndefinedFunction("function does not exist"),
                                                                                role=ACCOUNT)):
                    failed = self.run_in_request(route, call)
                    self.assertIsInstance(failed, Exception)
                    self.assertNoReport()
        self.assertEqual([], self.lines())

    def test_the_federation_procedure_is_jaaqls_own_sql(self):
        # The browser only follows a redirect: the procedure is the one the registry names, run as the jaaql role with the identity
        # provider's claims. An app migration that broke it is the server's; its refusal of the user's data or by a rule is the client's
        def federate():
            return self.model._run_federation_procedure({model.KG__database_user_registry__federation_procedure: "lesson.federate"},
                                                        APPLICATION, "default", ACCOUNT, "Relay Systems", "default", "a@example.com", "sub-1", {})

        class BusinessRule(psycopg.DatabaseError):
            # psycopg answers JQ000 with a plain DatabaseError, whose diagnostics carry the SQLSTATE
            sqlstate = "JQ000"

        with mock.patch.object(model, "fetch_parameters_for_federation_procedure", return_value=[]):
            for make, reported in [(lambda: pg.UndefinedFunction("function lesson.federate(...) does not exist"), True),
                                   (lambda: pg.RaiseException("no person with this email"), False),
                                   (lambda: BusinessRule('[{"message": "a JQ000 business rule"}]'), False),
                                   (lambda: pg.UniqueViolation("duplicate key value violates unique constraint"), False)]:
                self.stub.reset()
                server_errors.reset_throttle()
                with self.subTest(error=type(make()).__name__), self.interface(RaisingInterface(make, role=ROLE__jaaql)):
                    self.assertIsInstance(self.run_in_request(ENDPOINT__oidc_get_token, federate), Exception)
                    if reported:
                        body = self.report()
                        self.assertEqual("UndefinedFunction 42883: function lesson.federate(...) does not exist", body["error_condensed"])
                        self.assertIn("(JAAQL's own query)", body["stacktrace"])
                        self.assertIn('\nStatement (JAAQL\'s own, query key query):\n\tSELECT * FROM "lesson.federate"(', body["stacktrace"])
                    else:
                        self.assertNoReport()

    def raw(self, route, data, bypass=True):
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Test)"}
        if bypass:
            headers[HEADER__security_bypass] = SUPER_KEY
        else:
            headers[HEADER__security] = "a.token.of-the-anonymous-login"
        return self.client.post(route, data=data, headers=headers)

    def test_a_malformed_request_whoever_sends_it(self):
        # /submit, /execute and /call-proc take any body, and anyone can send one, logged in with a bypass key or with a token (the public
        # anonymous login has a published password): what reading it raises is answered 500 as ever, and never reported
        bodies = {
            "/call-proc": [{"query": 123, "parameters": {}}, {"query": "lesson.save"}, {"query": "lesson.save", "parameters": [1]},
                           {"query": None, "parameters": {}}, {"parameters": {}}],
            "/execute": [{"query": {"a": "slow"}}, {"query": {"a": "slow:x"}}, {"query": "SELECT 1"}, {"query": {"a": ["slow:0"]}},
                         {"query": {"a": {"query": 1}}}, {"query": {"a": {}}}, {"query": {"a": "slow:0"}, "parameters": [1]}, {},
                         # A query the application does not have, with its cache as on disk
                         {"query": {"a": "lesson__browse.frame:3"}}, {"query": {"a": "slow:99"}}],
            "/submit": [{"query": "SELECT 1", "parameters": [1]}, {"query": {"a": 1}}, {"query": {"a": {}}}, {"query": {"a": ["x"]}},
                        {"query": {"a": {"query": {"file": 1}}}}, {}],
        }
        requests_ = {"%s %s" % (route, json.dumps(body)): (lambda route=route, body=body, bypass=True: self.post(route, body, bypass=bypass))
                     for route, route_bodies in bodies.items() for body in route_bodies}
        for route in bodies:
            for raw in [b"1", b'"x"', b"null", b"true"] + ([b"[1]"] if route != "/submit" else []):
                requests_["%s body %s" % (route, raw.decode())] = (lambda route=route, raw=raw, bypass=True: self.raw(route, raw, bypass))
        for name, request in requests_.items():
            for bypass in [True, False]:
                with self.subTest(name, bypass=bypass), self.interface(RaisingInterface(role=ACCOUNT)):
                    (status, _, data), reports = self.answers(lambda: request(bypass=bypass))
                    self.assertEqual((500, []), (status, reports), data)
        self.assertEqual([], self.lines())

    def test_a_malformed_schema_role_or_application_whoever_sends_it(self):
        schemas = [{KG__application_schema__name: "default", KEY__database: "db", KEY__is_default: True, KG__application__is_live: True}]
        real_lookup = db_utils_no_circ.execute_supplied_statement

        def lookup(connection, query, parameters=None, **kwargs):
            # The application's schemas for its name; JAAQL's own query failing for any other value, as Postgres fails one of another type
            if query == QUERY__fetch_application_schemas and parameters[KG__application_schema__application] == APPLICATION:
                return schemas
            return real_lookup(connection, query, parameters, **kwargs)

        self.model.jaaql_lookup_connection = RaisingInterface(lambda: pg.UndefinedFunction("operator does not exist: character varying = smallint"))
        cases = {
            "an unknown schema": ({"schema": "nope"}, APPLICATION, 500),
            "a schema of another type": ({"schema": [1]}, APPLICATION, 500),
            "a role of another type": ({"role": 1}, APPLICATION, 500),
            "a role of another type, again": ({"role": [1]}, APPLICATION, 500),
            "an application of another type": ({}, 1, 422),
            "an application of another type, again": ({}, True, 422),
        }
        with mock.patch.object(db_utils_no_circ, "execute_supplied_statement", side_effect=lookup):
            for name, (extra, application, expected) in cases.items():
                for route, body in [("/submit", {"query": "SELECT 1"}), ("/call-proc", {"query": "lesson.save", "parameters": {}})]:
                    with self.subTest(name, route=route):
                        (status, _, data), reports = self.answers(lambda: self.post(route, dict(body, **extra), application=application))
                        self.assertEqual((expected, []), (status, reports), data)
            # JAAQL's own lookup failing so for an application that is a name is the server's
            (status, _, _), reports = self.answers(lambda: self.post("/submit", {"query": "SELECT 1"}, application="LesBij"))
        self.assertEqual((422, 1), (status, len(reports)))
        self.assertIn("(JAAQL's own query)", reports[0]["stacktrace"])

    def test_prepare_notes_no_fault_for_the_clients_statements(self):
        # Without gevent's pool, whose greenlets start with no request scope, so that a fault would be noted where one could be
        interface = RaisingInterface(lambda: pg.SyntaxError('syntax error at or near "SELEC"'), role=ACCOUNT)
        with slow_queries.request_scope("/prepare", "POST", "/prepare"), mock.patch.dict(sys.modules, {"gevent.pool": None}), \
                mock.patch.object(model, "create_interface_for_db", return_value=interface), \
                mock.patch.object(self.model, "is_dba", create=True):
            results = JAAQLModel.prepare_queries(self.model, {"database": "lesbij", "queries": [
                {"query": "SELEC 1", "file": "f", "line_number": 1, "name": "q"}], "sort_cost": False}, ACCOUNT)
            self.assertEqual([], slow_queries.current_scope().faults)
        self.assertIn("syntax error", results[0]["exception"])

    def test_client_errors_before_any_query(self):
        requests_ = {
            "bad JSON": lambda: self.client.post("/submit", data=b'{"query": ', headers={"Content-Type": "application/json",
                                                                                          HEADER__security_bypass: SUPER_KEY}),
            "an unknown argument": lambda: self.client.post("/oauth/token", json={"username": "u", "password": "p", "nonsense": 1}),
            "the wrong content type": lambda: self.client.post("/submit", data=b"query=SELECT 1", headers={HEADER__security_bypass: SUPER_KEY}),
            "a client gone mid-body": lambda: self.client.post("/submit", data=b'{"query": "SEL', headers={
                "Content-Type": "application/json", HEADER__security_bypass: SUPER_KEY}, environ_overrides={"CONTENT_LENGTH": "100"}),
            "a body too large": lambda: self.client.post("/submit", data=b"{}" + b" " * (2 * 1024 * 1024), headers={
                "Content-Type": "application/json", HEADER__security_bypass: SUPER_KEY}),
            "an unknown route": lambda: self.client.get("/nowhere"),
            "a method the route has not": lambda: self.client.delete("/submit"),
            "a wrong bypass key": lambda: self.client.post("/submit", json={"query": "SELECT 1"}, headers={HEADER__security_bypass: "wrong"}),
            "an unsafe procedure name": lambda: self.post("/call-proc", {"query": "x; DROP TABLE y", "parameters": {}}),
            "an unused parameter": lambda: self.submit("SELECT 1", {"unused": 1}),
        }
        statuses = {}
        with self.interface(RaisingInterface()):
            for name, request in requests_.items():
                with self.subTest(name):
                    (status, _, _), reports = self.answers(request)
                    self.assertEqual([], reports)
                    statuses[name] = status
        self.assertEqual({"bad JSON": 400, "an unknown argument": 400, "the wrong content type": 400, "a client gone mid-body": 400,
                          "a body too large": 413, "an unknown route": 404, "a method the route has not": 405, "a wrong bypass key": 401,
                          "an unsafe procedure name": 422, "an unused parameter": 400}, statuses)
        self.assertEqual([], self.lines())

    def test_a_refused_login_is_not_reported(self):
        self.model.verdict = (False, "Invalid token", 401)
        with self.interface(RaisingInterface()):
            (status, _, _), reports = self.answers(lambda: self.submit(bypass=False))
        self.assertEqual((401, []), (status, reports))

    def test_the_refusal_of_an_arbitrary_query_though_answered_500(self):
        self.model.prevent_arbitrary_queries = True
        with self.interface(RaisingInterface()):
            (status, _, data), reports = self.answers(lambda: self.client.post(
                "/submit", json={"query": "SELECT 1", "application": APPLICATION},
                headers={HEADER__security: "a.token", "X-Real-IP": "203.0.113.9"}))
        self.assertEqual((500, []), (status, reports))
        self.assertEqual("Not allowed to send queries to server!", json.loads(data)["descriptor"])

    def test_an_error_a_cloud_procedure_relays_though_answered_500(self):
        for code, status in [(1023, 500), (1004, 422)]:
            command = '"%s" -c "import json, sys; print(json.dumps(dict(error_code=%d, message=\'relayed\'))); sys.exit(1)"' % (
                sys.executable, code)
            with self.subTest(code=code), mock.patch.object(model, "remote_procedure__select", return_value={
                    "command": command, "access": model.RPC_ACCESS__private}):
                (answered, _, data), reports = self.answers(lambda: self.client.post(
                    "/remote_procedure", json={"application": APPLICATION, "name": "nightly", "args": {}},
                    headers={HEADER__security_bypass: SUPER_KEY, HEADER__security: "a.token"}))
                self.assertEqual((status, []), (answered, reports))
                self.assertEqual(code, json.loads(data)["error_code"])

    def test_a_client_gone_or_a_worker_shutting_down(self):
        for make in [ClientDisconnected, BrokenPipeError, ConnectionResetError]:
            with self.subTest(error=make.__name__), mock.patch.object(model, "is_federation_procedure", side_effect=raiser(make)):
                (status, _, _), reports = self.answers(self.call_proc)
                self.assertEqual([], reports)
        for make in [greenlet.GreenletExit, SystemExit]:
            with self.subTest(error=make.__name__), mock.patch.object(model, "is_federation_procedure", side_effect=raiser(make)):
                with self.assertRaises(make):
                    self.call_proc()
                self.assertNoReport()
        self.assertEqual([], self.lines())

    def test_requests_while_jaaql_is_not_installed(self):
        # /internal/is-alive at boot, with no lookup connection yet
        self.model.has_installed = False
        self.model.jaaql_lookup_connection = None
        with mock.patch.object(self.model, "is_alive", lambda: JAAQLModel.is_alive(self.model), create=True):
            (status, _, _), reports = self.answers(lambda: self.client.get("/internal/is-alive"))
        self.assertEqual((500, []), (status, reports))
        (status, _, _), reports = self.answers(self.call_proc)
        self.assertEqual((503, []), (status, reports))

    def test_the_ingest_route_never_reports_itself(self):
        # Even when Sentinel's own table is broken: its insert is JAAQL's own query, so the fault is noted, and the route is excluded
        interface = RaisingInterface(lambda: pg.UndefinedTable('relation "error" does not exist'))
        self.model.submit = lambda inputs, account_id, **kwargs: db_utils_no_circ.submit(None, CONFIG, b"k" * 32, None, inputs, account_id)
        report = {"location": "https://app/index.html", "source_file": "common.js", "error_condensed": "TypeError", "stacktrace": "at x",
                  "version": "1", "source_system": "lesbij", "file_line_number": 1, "file_col_number": 1, "user_agent": "u"}
        with self.interface(interface):
            (status, _, _), reports = self.answers(lambda: self.client.post(ENDPOINT__report_sentinel_error, json=report))
        self.assertEqual((422, []), (status, reports))
        self.model.submit = raiser(lambda: KeyError("error_id"))
        (status, _, _), reports = self.answers(lambda: self.client.post(ENDPOINT__report_sentinel_error, json=report))
        self.assertEqual((422, []), (status, reports))
        self.assertEqual([], self.lines())


class TestTheVerifier(ServerErrorCase):

    def verify(self, verify_auth_token, items=1):
        verdicts = [queue.Queue() for _ in range(items)]

        class Stop(Exception):
            pass

        class Requests:
            def __init__(self):
                self.items = [("token", "127.0.0.1", verdict) for verdict in verdicts]

            def get(self):
                if not self.items:
                    raise Stop()
                return self.items.pop(0)

        stub_model = SimpleNamespace(verify_auth_token=verify_auth_token)
        with self.assertRaises(Stop):
            JAAQLModel.verification_thread(stub_model, Requests())
        return [verdict.get_nowait() for verdict in verdicts]

    def test_a_failing_verifier_reports_itself_once_and_its_waiting_requests_do_not(self):
        lookup = RaisingInterface(lambda: pg.AdminShutdown("terminating connection due to administrator command"))
        self.model.jaaql_lookup_connection = lookup
        decoded = {"account_id": ACCOUNT, "username": "someone@example.com", "ip_address": "127.0.0.1", "password": None, "remember_me": False}
        with mock.patch.object(model.crypt_utils, "jwt_decode", return_value=decoded):
            verdicts = self.verify(lambda token, ip_address: self.model.verify_auth_token(token, ip_address))
        self.assertEqual(False, verdicts[0][0])
        self.assertEqual(500, verdicts[0][2])
        body = self.report()
        self.assertServerContract(body)
        self.assertEqual(PUBLIC_URL + " (auth-verification)", body["location"])
        self.assertEqual(SOURCE_SYSTEM, body["source_system"])
        self.assertEqual("JAAQL/" + VERSION, body["user_agent"])
        line = line_of(exception_queries.fetch_account_from_id, "execute_supplied_statement")
        self.assertEqual(["jaaql/mvc/exception_queries.py", line], [body["source_file"], body["file_line_number"]])
        trace = body["stacktrace"]
        self.assertIn("\nAnswered: 422 to the request waiting for this verification\n", trace)
        self.assertIn("\nBackground: auth-verification on " + PUBLIC_URL + "\n", trace)
        self.assertNotIn("someone@example.com", trace)
        self.stub.reset()

        # The requests that were waiting for that verdict answer 422 as before and report nothing of their own
        self.model.verdict = verdicts[0]
        with self.interface(RaisingInterface()):
            for _ in range(3):
                (status, _, data), reports = self.answers(lambda: self.submit(bypass=False))
                self.assertEqual((422, []), (status, reports))
                self.assertEqual(verdicts[0][1].encode(), data)

    def test_each_verification_notes_faults_of_its_own(self):
        # The second verification fails with no fault of its own: its report is its failure, never the first one's fault again
        failures = [lambda: execute_supplied_statement(RaisingInterface(lambda: pg.AdminShutdown("terminating connection")), "SELECT 1"),
                    raiser(lambda: RuntimeError("the second verification"))]
        verdicts = self.verify(lambda token, ip_address: failures.pop(0)(), items=2)
        self.assertEqual([500, 500], [verdict[2] for verdict in verdicts])
        self.report(2)
        self.assertEqual(["AdminShutdown 57P01: terminating connection", "RuntimeError: the second verification"],
                         [body["error_condensed"] for body in self.stub.bodies()])

    def test_a_failed_verdict_is_no_fault_of_the_query_waiting_for_it(self):
        # Even JAAQL's own query: the verifier reports its failure itself, once
        for verdict in [(False, "the verifier failed", 500), (False, "Invalid token", 401)]:
            hook = queue.Queue()
            hook.put(verdict)
            with self.subTest(verdict=verdict), slow_queries.request_scope("/submit", "POST", "/submit"):
                with self.assertRaises(Exception):
                    InterpretJAAQL(RaisingInterface()).transform({"query": "SELECT 1"}, wait_hook=hook)
                self.assertEqual([], slow_queries.current_scope().faults)

    def test_a_refused_login_in_the_verifier_is_not_reported(self):
        verdicts = self.verify(raiser(lambda: UserUnauthorized()))
        self.assertEqual(401, verdicts[0][2])
        self.assertNoReport()


class TestTheCodeExchange(ServerErrorCase):

    def exchange(self, post=None, state="s1"):
        self.model.idp_session = SimpleNamespace(post=post)
        oidc_state = {"application": APPLICATION, "provider": "Relay Systems", "tenant": "default", "database": "db", "code_verifier": "v" * 50,
                      "state": "s1", "nonce": "n1", "redirect_uri": RETURN_PAGE, "schema": "default"}
        # Every one of the requests answers() makes brings the cookies, which the first answer would otherwise expire in a cookie jar
        client = self.controller.app.test_client(use_cookies=False)
        cookies = {"Cookie": "%s=oidc-cookie; %s=%s" % (COOKIE_OIDC, COOKIE_OIDC_RETURN, RETURN_PAGE)}
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": "http://127.0.0.1:%d" % closed_port(), "OIDC_ISSUER": ""}), \
                mock.patch.object(model.crypt_utils, "jwt_decode", return_value=oidc_state), \
                mock.patch.object(model, "jaaql__decrypt", side_effect=lambda value, key: value), \
                mock.patch.object(model, "application__select", return_value={"default_schema": "default", "base_url": PUBLIC_URL}), \
                mock.patch.object(model, "user_registry__select", return_value={"discovery_url": PUBLIC_URL + "/realms/r"}), \
                mock.patch.object(model, "database_user_registry__select", return_value={"client_id": "client"}):
            return self.answers(lambda: client.get(ENDPOINT__oidc_get_token + "?code=the-code&state=" + state, headers=cookies))

    def assertRedirected(self, answer):
        status, headers, _ = answer
        self.assertEqual(302, status)
        self.assertEqual(RETURN_PAGE, dict(headers)["Location"])

    def test_a_token_endpoint_that_cannot_be_reached_is_reported(self):
        answer, reports = self.exchange(post=raiser(lambda: requests.exceptions.ConnectionError(
            "HTTPConnectionPool(host='keycloak', port=8080): Max retries exceeded with url: /realms/r/protocol/openid-connect/token?client_id=x "
            "(Caused by NewConnectionError('Failed to establish a new connection'))")))
        self.assertRedirected(answer)
        self.assertEqual(1, len(reports))
        self.assertServerContract(reports[0])
        self.assertTrue(reports[0]["error_condensed"].startswith("ConnectionError: "), reports[0]["error_condensed"])
        self.assertNotIn("client_id=x", json.dumps(reports[0]))
        self.assertIn("\nAnswered: 302, to the page the login started from or the application, not logged in\n", reports[0]["stacktrace"])
        # The authorization code, still unredeemed, and the state are never sent: the route's inputs are named only
        self.assertNotIn("the-code", json.dumps(reports[0]))
        self.assertNotIn('"s1"', json.dumps(reports[0]))
        self.assertIn("\nRequest inputs (names only, values not shown):\n\t", reports[0]["stacktrace"])

    def exchange_jarm(self, response="the.jarm.jwt", signing_key=None, decoded=None, fapi=False):
        # The JARM (and, with fapi, FAPI advanced) branch: Keycloak's keys and jwt.decode as given
        self.model.use_oidc_basic = False
        self.model.use_fapi_advanced = fapi
        self.model.fapi_enc_key = jwk.JWK.generate(kty="RSA", size=2048)
        oidc_state = {"application": APPLICATION, "provider": "Relay Systems", "tenant": "default", "database": "db", "code_verifier": "v" * 50,
                      "state": "s1", "nonce": "n1", "redirect_uri": RETURN_PAGE, "schema": "default"}
        client = self.controller.app.test_client(use_cookies=False)
        cookies = {"Cookie": "%s=oidc-cookie; %s=%s" % (COOKIE_OIDC, COOKIE_OIDC_RETURN, RETURN_PAGE)}
        jwk_client = SimpleNamespace(get_signing_key_from_jwt=signing_key or (lambda token: SimpleNamespace(key="k")))
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": "http://127.0.0.1:%d" % closed_port(), "OIDC_ISSUER": ""}), \
                mock.patch.object(model.crypt_utils, "jwt_decode", return_value=oidc_state), \
                mock.patch.object(model, "jaaql__decrypt", side_effect=lambda value, key: value), \
                mock.patch.object(model, "application__select", return_value={"default_schema": "default", "base_url": PUBLIC_URL}), \
                mock.patch.object(model, "user_registry__select", return_value={"discovery_url": PUBLIC_URL + "/realms/r"}), \
                mock.patch.object(model, "database_user_registry__select", return_value={"client_id": "client"}), \
                mock.patch.object(self.model, "fetch_jwks_client", return_value=jwk_client), \
                mock.patch.object(model.jwt, "decode", side_effect=decoded or raiser(lambda: jwt.DecodeError("Not enough segments"))):
            return self.answers(lambda: client.get(ENDPOINT__oidc_get_token + ("" if response is None else "?response=" + response),
                                                   headers=cookies))

    def test_a_jarm_response_failing_verification_by_the_servers_fault_is_reported(self):
        # Keycloak's keys out of reach; a response Keycloak signed (verified first) for another issuer or audience than JAAQL expects
        cases = {
            "keys out of reach": (raiser(lambda: jwt.PyJWKClientConnectionError("Fail to fetch data from the url, err: Connection refused")),
                                  None),
            "another issuer": (None, raiser(lambda: jwt.InvalidIssuerError("Invalid issuer"))),
            "another audience": (None, raiser(lambda: jwt.InvalidAudienceError("Audience doesn't match"))),
        }
        for name, (signing_key, decoded) in cases.items():
            with self.subTest(name):
                answer, reports = self.exchange_jarm(signing_key=signing_key, decoded=decoded)
                self.assertRedirected(answer)
                self.assertEqual(1, len(reports))
                self.assertServerContract(reports[0])
                self.assertEqual("jaaql/mvc/model.py", reports[0]["source_file"])
                self.assertIn("\nAnswered: 302, to the page the login started from", reports[0]["stacktrace"])
                self.assertNotIn("the.jarm.jwt", json.dumps(reports[0]))

    def test_a_jarm_response_anyone_can_send_is_not_reported(self):
        # A key Keycloak does not publish, an algorithm not allowed, a response expired or malformed, none at all, or one that is no JWE
        # for JAAQL's key (FAPI advanced)
        cases = {
            "a key Keycloak does not publish": dict(signing_key=raiser(lambda: jwt.PyJWKClientError(
                'Unable to find a signing key that matches: "kid"'))),
            "an algorithm not allowed": dict(decoded=raiser(lambda: jwt.InvalidAlgorithmError("The specified alg value is not allowed"))),
            "expired": dict(decoded=raiser(lambda: jwt.ExpiredSignatureError("Signature has expired"))),
            "malformed": dict(),
            "none at all": dict(response=None),
            "none at all, FAPI": dict(response=None, fapi=True),
            "no JWE, FAPI": dict(response="garbage", fapi=True),
        }
        other_key = jwk.JWK.generate(kty="RSA", size=2048)
        encrypted = jwe.JWE(b"payload", protected={"alg": "RSA-OAEP-256", "enc": "A256GCM"})
        encrypted.add_recipient(other_key)
        cases["a JWE for another key, FAPI"] = dict(response=encrypted.serialize(compact=True), fapi=True)
        for name, kwargs in cases.items():
            with self.subTest(name):
                answer, reports = self.exchange_jarm(**kwargs)
                self.assertRedirected(answer)
                self.assertEqual([], reports)

    def test_an_authorization_response_carrying_an_error(self):
        # Keycloak's own error in the verified response: the server's, unless the user caused it
        for error, description, reported in [("server_error", "Unexpected error", True), ("invalid_client", "Invalid client", True),
                                             ("unauthorized_client", None, True), ("access_denied", "User denied consent", False),
                                             ("login_required", None, False),
                                             ("temporarily_unavailable", "authentication_expired", False)]:
            with self.subTest(error=error):
                answer, reports = self.exchange_jarm(decoded=lambda *args, **kwargs: {"error": error, "error_description": description})
                self.assertRedirected(answer)
                self.assertEqual(1 if reported else 0, len(reports))
                if reported:
                    self.assertServerContract(reports[0])
                    self.assertEqual("AuthorizationResponseError: %s: %s" % (error, description), reports[0]["error_condensed"])
                    self.assertEqual(["jaaql/mvc/model.py", line_of(JAAQLModel.exchange_auth_code, "authorization_response_failed(")],
                                     [reports[0]["source_file"], reports[0]["file_line_number"]])

    def test_a_state_that_does_not_match_is_not_reported(self):
        answer, reports = self.exchange(post=raiser(AssertionError), state="other")
        self.assertRedirected(answer)
        self.assertEqual([], reports)

    def test_a_code_used_twice_is_not_reported(self):
        answer, reports = self.exchange(post=lambda url, data=None, **kwargs: SimpleNamespace(json=lambda: {
            "error": "invalid_grant", "error_description": "Code not valid"}))
        self.assertRedirected(answer)
        self.assertEqual([], reports)


class TestRedaction(ServerErrorCase):

    def test_a_password_and_a_value_an_error_quotes_are_redacted(self):
        def refuse(**kwargs):
            raise KeyError("no account for " + kwargs["password"])

        with mock.patch.object(self.model, "get_auth_token", refuse, create=True):
            (status, _, _), reports = self.answers(lambda: self.client.post("/oauth/token", json={
                "username": "someone@example.com", "password": "hunter2-secret"}))
        self.assertEqual(500, status)
        body = reports[0]
        self.assertNotIn("hunter2-secret", json.dumps(body))
        self.assertEqual("KeyError: 'no account for <redacted>'", body["error_condensed"])
        # A login's inputs are named only: its username is an email address, and the account is named by its id only
        self.assertIn("\nRequest inputs (names only, values not shown):\n\tpassword, username\n", body["stacktrace"])
        self.assertNotIn("someone@example.com", json.dumps(body))

    def test_the_login_and_account_routes_never_show_an_email_address(self):
        def refuse(*args, **kwargs):
            # Even quoted by the error
            raise KeyError("no account for " + kwargs.get("username", ""))

        for route, body in [("/oauth/token", {"username": "someone@example.com", "password": "p"}),
                            ("/oauth/cookie", {"username": "someone@example.com", "password": "p", "remember_me": True}),
                            ("/accounts", {"username": "someone@example.com", "password": "p", "attach_as": None})]:
            with self.subTest(route=route), mock.patch.object(self.model, "get_auth_token", refuse, create=True), \
                    mock.patch.object(self.model, "create_account_with_potential_api_key", refuse, create=True), \
                    mock.patch.object(base_controller, "create_interface_for_db", return_value=RaisingInterface()):
                (status, _, _), reports = self.answers(lambda: self.client.post(route, json=body, headers={HEADER__security_bypass: SUPER_KEY}))
                self.assertEqual(500, status)
                self.assertEqual(1, len(reports))
                self.assertNotIn("someone@example.com", json.dumps(reports[0]))
                self.assertEqual("KeyError: 'no account for <redacted>'", reports[0]["error_condensed"])
                self.assertIn("\nRequest inputs (names only, values not shown):\n\t", reports[0]["stacktrace"])

    def test_encrypted_literals_are_masked_in_the_inputs(self):
        # The database only ever sees them encrypted: masked as in a slow-query report, also where the inputs are cut, inside the literal
        literal = "jan.jansen@example.com"
        for cut in [None, len('{"application": "%s", "parameters": {}, "query": "SELECT #\'jan' % APPLICATION)]:
            with self.subTest(cut=cut), mock.patch.object(server_errors, "INPUTS__max_length", cut or server_errors.INPUTS__max_length), \
                    self.interface(RaisingInterface(rows={"gap": timedelta(days=1)})):
                (status, _, _), reports = self.answers(lambda: self.submit("SELECT #'" + literal + "' AS e, '1 day'::interval AS gap"))
                self.assertEqual(500, status)
                self.assertNotIn("#'jan", json.dumps(reports[0]))
                self.assertNotIn("jan.jansen", json.dumps(reports[0]))
                if cut is None:
                    self.assertIn("#'<encrypted>' AS e", reports[0]["stacktrace"])

    def test_encrypted_literals_are_masked_where_an_error_quotes_the_sql(self):
        # A message quoting the statement as the request wrote it, encrypted literal and all; never a traceback's code line
        self.assertEqual("ValueError: cannot run SELECT #'<encrypted>' AS e\n    query = \"#'kept'\"",
                         server_errors.scrub("ValueError: cannot run SELECT #'jan.jansen@example.com' AS e\n    query = \"#'kept'\"", set()))
        # A dict query's answer quotes it (the client's own), its report does not
        with self.interface(RaisingInterface(lambda: HttpStatusException("the server went away", 500), role=ACCOUNT)):
            (status, _, data), reports = self.answers(lambda: self.post("/submit", {"query": {"a": "SELECT #'jan.jansen@example.com' AS e"}}))
        self.assertEqual(500, status)
        self.assertIn(b"jan.jansen", data)
        self.assertEqual(1, len(reports))
        self.assertNotIn("jan.jansen", json.dumps(reports[0]))

    def test_a_report_is_one_line_in_the_log_whatever_the_request_names(self):
        sentinel.configure(None, None)
        try:
            with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("x"))):
                self.assertEqual(500, self.call_proc(application="app\nSERVER ERROR forged at nowhere").status_code)
        finally:
            sentinel.configure(self.stub.url, None)
        self.assertEqual(1, len(self.lines()))
        self.assertIn("(POST /call-proc, app SERVER ERROR forged at nowhere)", self.lines()[0])

    def test_encrypted_parameters_are_marked_and_the_account_named_by_id(self):
        with self.interface(RaisingInterface(rows={"gap": timedelta(days=1)})):
            (status, _, _), reports = self.answers(lambda: self.submit("SELECT #email AS e, :note AS n", {"email": "x@example.com",
                                                                                                         "note": "kept"}))
        self.assertEqual(500, status)
        trace = reports[0]["stacktrace"]
        self.assertIn('"email": "<encrypted>"', trace)
        self.assertIn('"note": "kept"', trace)
        self.assertNotIn("x@example.com", trace)
        self.assertIn("| account: " + ACCOUNT + "\n", trace)
        self.assertNotIn("super_db", trace)

    def test_a_long_report_keeps_its_head_and_the_exception(self):
        with mock.patch.object(server_errors, "STACKTRACE__max_length", 1500), \
                mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("federation_procedure"))):
            self.assertEqual(500, self.call_proc({"essay": "e" * 3000}).status_code)
        trace = self.report()["stacktrace"]
        self.assertGreater(len(trace), 1400)
        self.assertLessEqual(len(trace), 1500)
        self.assertTrue(trace.startswith("Server error: KeyError: 'federation_procedure'\nAnswered: "), trace[:100])
        self.assertIn(server_errors.REPORT__truncated, trace)
        self.assertTrue(trace.endswith("\nKeyError: 'federation_procedure'"), trace[-100:])

    def test_url_query_strings_are_removed(self):
        self.assertEqual("401 Client Error: Unauthorized for url: http://kc/admin/realms/r/users?<redacted>",
                         server_errors.scrub("401 Client Error: Unauthorized for url: http://kc/admin/realms/r/users?username=a%40b.c&exact=true",
                                             set()))
        self.assertEqual("Max retries exceeded with url: /x/users?<redacted> (Caused by X)",
                         server_errors.scrub("Max retries exceeded with url: /x/users?username=a@b.c (Caused by X)", set()))


class TestThrottle(ServerErrorCase):

    def setUp(self):
        super().setUp()
        self.clock = [1000.0]
        self.now = mock.patch.object(slow_queries, "_now", lambda: self.clock[0])
        self.now.start()

    def tearDown(self):
        self.now.stop()
        super().tearDown()

    def failing(self, account=ACCOUNT, make=lambda: KeyError("federation_procedure")):
        self.model.account = account
        with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(make)):
            self.assertEqual(500, self.call_proc().status_code)
        return self.lines()[-1]

    def test_an_error_is_reported_once_an_hour_with_its_repeats(self):
        self.failing()
        self.assertTrue(self.failing().endswith(" - repeat, not reported"))
        self.report(1)
        self.clock[0] += 3601
        self.failing()
        body = self.report(2)
        self.assertIn("\nRepeats: 1 more in this worker since its last report\n", body["stacktrace"])

    def test_at_most_ten_reports_an_hour_and_three_for_one_account(self):
        for idx in range(10):
            self.failing(account="account-%d" % (idx // 3), make=lambda idx=idx: type("Error%d" % idx, (Exception,), {})())
        self.assertTrue(self.failing(account="account-x", make=lambda: type("Error10", (Exception,), {})()).endswith(
            " - over 10 reports this hour, not reported"))
        self.report(10)
        self.stub.reset()
        self.clock[0] += 3601
        for idx in range(3):
            self.failing(make=lambda idx=idx: type("Again%d" % idx, (Exception,), {})())
        self.assertTrue(self.failing(make=lambda: type("Again3", (Exception,), {})()).endswith(
            " - over 3 reports this hour for this account, not reported"))
        self.assertTrue(self.failing(account="account-y", make=lambda: type("Again4", (Exception,), {})()).endswith(" - reported"))
        self.report(4)

    def test_the_errors_kept_track_of_are_bounded(self):
        with mock.patch.object(server_errors, "SERVER_ERROR__max_tracked_errors", 20):
            for idx in range(1000):
                server_errors._throttle.decide("error-%d" % idx)
            self.assertEqual(20, len(server_errors._throttle.identities))

    def test_slow_queries_and_server_errors_have_budgets_of_their_own(self):
        for idx in range(10):
            self.assertEqual(slow_queries.DECISION__report, slow_queries._throttle("slow-%d" % idx, 3.1)[0])
        self.assertEqual(slow_queries.DECISION__capped, slow_queries._throttle("slow-10", 3.1)[0])
        self.assertTrue(self.failing().endswith(" - reported"))
        for idx in range(9):
            self.assertEqual(slow_queries.DECISION__report, server_errors._throttle.decide("server-%d" % idx)[0])
        self.assertTrue(self.failing(make=lambda: KeyError("one more")).endswith(" - repeat, not reported"))
        self.assertEqual("over 10 reports this hour, not reported", server_errors._throttle.decide("server-10")[0])
        slow_queries.reset_throttle()
        self.assertEqual(slow_queries.DECISION__report, slow_queries._throttle("slow-after", 3.1)[0])
        self.assertEqual("over 10 reports this hour, not reported", server_errors._throttle.decide("server-11")[0])
        self.report(1)


class TestSafety(ServerErrorCase):

    def test_without_sentinel_a_server_error_is_only_printed(self):
        sentinel.configure(None, None)
        try:
            with mock.patch.object(sentinel, "_ensure_sender") as started, \
                    mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("x"))):
                self.assertEqual(500, self.call_proc().status_code)
            started.assert_not_called()
        finally:
            sentinel.configure(self.stub.url, None)
        self.assertEqual(["SERVER ERROR KeyError at jaaql/mvc/model.py:%d (POST /call-proc, %s) answered 500 (error_code 1099)" % (
            line_of(JAAQLModel.call_proc, "if is_federation_procedure("), APPLICATION)], self.lines())
        self.assertNoReport()

    def test_a_bug_in_the_reporting_changes_no_answer(self):
        with mock.patch.object(server_errors, "payload_of", side_effect=raiser(lambda: RuntimeError("a bug in the report"))), \
                mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("x"))):
            (status, _, _), reports = self.answers(self.call_proc)
        self.assertEqual((500, []), (status, reports))
        self.assertIn("Server error report failed: RuntimeError: a bug in the report", self.printed.getvalue())

    def test_requests_never_wait_for_sentinel(self):
        for status in ["refused", "hang", 500, 422]:
            with self.subTest(status=status), mock.patch.object(sentinel, "SENTINEL__read_timeout", 1), \
                    mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("x"))):
                server_errors.reset_throttle()
                if status == "refused":
                    sentinel.configure("http://127.0.0.1:%d" % closed_port(), None)
                else:
                    self.stub.status = status
                try:
                    started = time.monotonic()
                    res = self.call_proc()
                    self.assertLess(time.monotonic() - started, 1)
                    self.assertEqual(500, res.status_code)
                    self.assertEqual(1099, res.json["error_code"])
                    self.assertTrue(sentinel.wait_idle(10))
                finally:
                    sentinel.configure(self.stub.url, None)
                    self.stub.reset()

    def test_a_report_holds_only_text_sentinels_database_can_store(self):
        # Postgres text holds no NUL and only what UTF-8 encodes: the ingest route refuses a whole report with either (TestServerErrors
        # AgainstPostgres shows both)
        with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: RuntimeError("a NUL \x00 here"))):
            self.assertEqual(500, self.call_proc({"note": "a lone \ud800 surrogate"}).status_code)
        body = self.report()
        for key, value in body.items():
            if isinstance(value, str):
                self.assertNotIn("\x00", value, key)
                value.encode("utf-8")
        self.assertEqual("RuntimeError: a NUL \\0 here", body["error_condensed"])
        self.assertIn('"note": "a lone ? surrogate"', body["stacktrace"])
        self.assertEqual({"a": "x\\0y?", "b": 1, "c": None}, sentinel.storable({"a": "x\x00y\udfff", "b": 1, "c": None}))

    def test_a_full_queue_drops_the_report_without_raising(self):
        with mock.patch.object(sentinel, "send", return_value=False), \
                mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("x"))):
            self.assertEqual(500, self.call_proc().status_code)
        self.assertTrue(self.lines()[-1].endswith(" - Sentinel queue full, not reported"), self.lines())


TEST_DATABASE = "jaaql_test_err500"
TEST_ROLE = "jaaql_test_err500_user"


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestServerErrorsAgainstPostgres(ServerErrorCase):
    """
    The real request paths: the client's SQL raising every class of error through /submit, /execute and /call-proc is never reported, JAAQL's
    own SQL failing is, and a report is one Sentinel's ingest SQL takes
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
        cls.address, cls.port, _, cls.pool_user, cls.password = DBInterface.fracture_uri(uri)
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
                CREATE TABLE kept (id int PRIMARY KEY);
                INSERT INTO kept VALUES (1);
                CREATE TABLE child (id int PRIMARY KEY, kept_id int REFERENCES kept (id));
                CREATE TABLE hidden (x int);
                CREATE TABLE deferred_check (id int, CONSTRAINT deferred_unique UNIQUE (id) DEFERRABLE INITIALLY DEFERRED);
                INSERT INTO deferred_check VALUES (1);
                CREATE FUNCTION "lesson.save"(id int) RETURNS TABLE (saved int) LANGUAGE plpgsql AS $f$
                BEGIN INSERT INTO kept VALUES (id); RETURN QUERY SELECT id; END $f$;
                CREATE FUNCTION "lesson.raise"() RETURNS TABLE (x int) LANGUAGE plpgsql AS $f$ BEGIN RAISE EXCEPTION 'a business rule refused it'; END $f$;
                CREATE FUNCTION "lesson.rule"() RETURNS TABLE (x int) LANGUAGE plpgsql AS $f$
                BEGIN RAISE EXCEPTION USING ERRCODE = 'JQ000', MESSAGE = '[{"message": "refused by a rule"}]'; END $f$;
                CREATE FUNCTION "lesson.corrupt"() RETURNS TABLE (x int) LANGUAGE plpgsql AS $f$
                BEGIN RAISE EXCEPTION 'raised by the procedure' USING ERRCODE = 'data_corrupted'; END $f$;
                -- JAAQL's own application lookup (QUERY__fetch_application_schemas), as the jaaql database has it
                CREATE TABLE application (name varchar(63) PRIMARY KEY, default_schema varchar(63), is_live boolean);
                CREATE TABLE application_schema (application varchar(63), name varchar(63), database varchar(63));
                INSERT INTO application VALUES ('lesbij', 'default', true);
                INSERT INTO application_schema VALUES ('lesbij', 'default', '""" + TEST_DATABASE + """');
            """ + SENTINEL_DDL + """
                GRANT SELECT, INSERT ON kept, child, deferred_check, error TO """ + TEST_ROLE + """;
                GRANT pg_read_server_files TO """ + TEST_ROLE + """;
                GRANT EXECUTE ON FUNCTION pg_read_file(text) TO """ + TEST_ROLE + """;
            """)

    @classmethod
    def tearDownClass(cls):
        for user in [cls.pool_user]:
            pool = DBPGInterface.HOST_POOLS.get(user, {}).pop(TEST_DATABASE, None)
            DBPGInterface.HOST_POOLS_QUEUES.get(user, {}).pop(TEST_DATABASE, None)
            if pool is not None:
                pool.close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("DROP ROLE IF EXISTS " + TEST_ROLE)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        real_lookup = db_utils_no_circ.execute_supplied_statement

        def lookup(connection, query, parameters=None, **kwargs):
            # The application's schemas, as the jaaql database would answer: one schema, in the test database
            if query == QUERY__fetch_application_schemas:
                return [{KG__application_schema__name: "default", KEY__database: TEST_DATABASE, KEY__is_default: True,
                         KG__application__is_live: True}]
            return real_lookup(connection, query, parameters, **kwargs)

        self.quiet.enter_context(mock.patch.object(db_utils_no_circ, "execute_supplied_statement", side_effect=lookup))

    def make_model(self):
        stub_model = ErrorStubModel(vault=StubVault(os.environ[ENVIRON__test_postgres_uri]), account=TEST_ROLE)
        stub_model.db_cache = {"default": {KG__application_schema__name: "default", KEY__database: TEST_DATABASE, KEY__is_default: True,
                                           KG__application__is_live: True}}
        stub_model.query_caches["queries"]["broken"] = ["SELEC 1", "SELECT 1 / 0 AS x", "SELECT * FROM hidden", "SELECT nope()"]
        return stub_model

    def lookup_connection(self):
        # JAAQL's own connection, as the lookup connection is made: no role of its own; here to the test database, which has none of
        # JAAQL's tables
        return create_interface(CONFIG, self.address, self.port, TEST_DATABASE, self.pool_user, self.password)

    def test_the_clients_sql_whatever_it_raises(self):
        cases = {
            "syntax 42601 /submit": lambda: self.submit("SELEC 1"),
            "syntax 42601 /execute": lambda: self.post("/execute", {"query": {"a": "broken:0"}}),
            "division by zero 22012 /execute": lambda: self.post("/execute", {"query": {"a": "broken:1"}}),
            "permission 42501 /execute": lambda: self.post("/execute", {"query": {"a": "broken:2"}}),
            "undefined function 42883 /execute": lambda: self.post("/execute", {"query": {"a": "broken:3"}}),
            "permission 42501 /submit": lambda: self.submit("SELECT * FROM hidden"),
            "unique 23505 /call-proc": lambda: self.post("/call-proc", {"query": "lesson.save", "parameters": {"id": 1},
                                                                        "explicit_types": {"id": "int"}}),
            "foreign key 23503 /submit": lambda: self.submit("INSERT INTO child VALUES (1, 99)"),
            "raise P0001 /call-proc": lambda: self.post("/call-proc", {"query": "lesson.raise", "parameters": {}}),
            "rule JQ000 /call-proc": lambda: self.post("/call-proc", {"query": "lesson.rule", "parameters": {}}),
            "undefined function 42883 /call-proc": lambda: self.post("/call-proc", {"query": "lesson.missing", "parameters": {}}),
            "invalid input 22P02 /submit": lambda: self.submit("SELECT 'x'::int"),
            "statement timeout 57014 /submit": lambda: self.post("/submit", {"query": {"a": "SET LOCAL statement_timeout = 100",
                                                                                        "b": "SELECT pg_sleep(1)"}}),
            "lock timeout 55P03 /submit": lambda: self.post("/submit", {"query": {"a": "SET LOCAL lock_timeout = 100",
                                                                                   "b": "SELECT * FROM kept"}}),
            "deferred constraint at COMMIT /submit": lambda: self.submit("INSERT INTO deferred_check VALUES (1)"),
        }
        statuses = {}
        for name, request in cases.items():
            with self.subTest(name), psycopg.connect(self.test_uri) as holder:
                if "lock timeout" in name:
                    # Another transaction holds the table, so the request's wait for it times out
                    holder.execute("LOCK TABLE kept IN ACCESS EXCLUSIVE MODE")
                try:
                    (status, _, data), reports = self.answers(request)
                finally:
                    holder.rollback()
                statuses[name] = status
                self.assertEqual([], reports)
        self.assertEqual({name: 422 for name in cases}, statuses)
        self.assertEqual([], self.lines())

    def test_jaaqls_own_query_failing_is_reported(self):
        self.model.jaaql_lookup_connection = self.lookup_connection()
        with mock.patch.object(model, "is_federation_procedure", handmade_queries.is_federation_procedure):
            (status, _, data), reports = self.answers(lambda: self.post("/call-proc", {"query": "lesson.save", "parameters": {"id": 2},
                                                                                       "explicit_types": {"id": "int"}}))
        self.assertEqual(422, status)
        self.assertEqual(1004, json.loads(data)["error_code"])
        self.assertEqual(1, len(reports))
        body = reports[0]
        self.assertServerContract(body)
        self.assertEqual(["jaaql/mvc/handmade_queries.py", line_of(handmade_queries.is_federation_procedure, "return len(execute_supplied_statement(")],
                         [body["source_file"], body["file_line_number"]])
        self.assertEqual('UndefinedTable 42P01: relation "federation_procedure" does not exist', body["error_condensed"])
        self.assertIn("| database: " + TEST_DATABASE + " | account: " + TEST_ROLE + "\n", body["stacktrace"])
        self.assertEqual(0, self.admin("SELECT count(*) FROM kept WHERE id = 2")[0][0])

    def test_a_connection_jaaqls_own_query_lost_after_it_may_have_committed(self):
        interface = self.lookup_connection()
        with slow_queries.request_scope("/internal/is-alive", "GET", "/internal/is-alive"):
            try:
                execute_supplied_statement(interface, "SELECT 1; SELECT pg_terminate_backend(pg_backend_pid())")
                self.fail("the connection was not lost")
            except Exception as ex:
                self.assertEqual(1002, getattr(ex, "error_code", None), repr(ex))
                server_errors.request_failed(ex, "/internal/is-alive", True)
        body = self.report()
        self.assertIn("(the connection, lost after JAAQL's own query may have committed)", body["stacktrace"])
        self.assertIn("\nAnswered: 422 (error_code 1002), a server-side failure JAAQL answers as a client error\n", body["stacktrace"])

    def test_the_database_server_failing_under_the_clients_sql_is_reported_unless_the_sql_raised_it(self):
        # A file the server cannot read (58P01, as a relation's missing segment raises it) is reported once; the same class of SQLSTATE
        # raised by the client's DO block or the app's procedure is the SQL's own doing
        cases = {
            "the server failing": (lambda: self.submit("SELECT pg_read_file('/nonexistent/jaaql-test')"), 1),
            "a DO block raising disk_full": (lambda: self.submit("DO $$ BEGIN RAISE EXCEPTION 'x' USING ERRCODE = 'disk_full'; END $$"), 0),
            "a procedure raising data_corrupted": (lambda: self.post("/call-proc", {"query": "lesson.corrupt", "parameters": {}}), 0),
        }
        for name, (request, reported) in cases.items():
            with self.subTest(name):
                (status, _, _), reports = self.answers(request)
                self.assertEqual((422, reported), (status, len(reports)))
                if reported:
                    self.assertTrue(reports[0]["error_condensed"].startswith("UndefinedFile 58P01: "), reports[0]["error_condensed"])
                    self.assertIn("(the database server, failing under the request's query)", reports[0]["stacktrace"])

    def test_a_connection_lost_under_the_clients_sql_after_it_may_have_committed(self):
        # The database restarting under the app's multi-statement request, whose first statement may have committed: never re-run, and
        # reported, whoever wrote the SQL
        def request():
            def terminate():
                with psycopg.connect(self.test_uri, autocommit=True) as admin:
                    for _ in range(100):
                        if admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query LIKE '%pg_sleep(4.5)%' "
                                         "AND pid <> pg_backend_pid()").fetchall():
                            return
                        time.sleep(0.05)

            terminator = threading.Thread(target=terminate)
            terminator.start()
            try:
                return self.submit("INSERT INTO kept VALUES (8); SELECT pg_sleep(4.5)")
            finally:
                terminator.join()

        (status, _, data), reports = self.answers(request)
        self.assertEqual(422, status)
        self.assertEqual(1002, json.loads(data)["error_code"])
        self.assertEqual(1, len(reports))
        self.assertIn("(the connection, lost after the request's query may have committed)", reports[0]["stacktrace"])

    def test_a_malformed_application_or_role_is_the_clients(self):
        # JAAQL's own lookup of the application the request names: a value of another type fails it (42883), the client's; with the
        # lookup's table gone, the same query failing for the application's name is the server's
        self.model.jaaql_lookup_connection = self.lookup_connection()
        with mock.patch.object(db_utils_no_circ, "execute_supplied_statement", execute_supplied_statement):
            # (application, more inputs, the answer of /submit's SELECT, of /call-proc's procedure raising P0001)
            for application, extra, expected in [(1, {}, (422, 422)), (True, {}, (422, 422)), (1.5, {}, (422, 422)), ([1], {}, (422, 422)),
                                                 ("lesbij", {"role": 1}, (500, 500)), ("lesbij", {"schema": "nope"}, (500, 500)),
                                                 ("lesbij", {"autocommit": "yes"}, (200, 422)), ("lesbij", {}, (200, 422))]:
                for route, body, answer in [("/submit", {"query": "SELECT 1 AS one"}, expected[0]),
                                            ("/call-proc", {"query": "lesson.raise", "parameters": {}}, expected[1])]:
                    with self.subTest(application=application, extra=extra, route=route):
                        (status, _, data), reports = self.answers(lambda: self.post(route, dict(body, **extra), application=application))
                        self.assertEqual((answer, []), (status, reports), data)
            self.admin("ALTER TABLE application_schema RENAME TO application_schema_gone")
            try:
                (status, _, _), reports = self.answers(lambda: self.post("/submit", {"query": "SELECT 1"}, application="lesbij"))
            finally:
                self.admin("ALTER TABLE application_schema_gone RENAME TO application_schema")
        self.assertEqual((422, 1), (status, len(reports)))
        self.assertTrue(reports[0]["error_condensed"].startswith("UndefinedTable 42P01: "), reports[0]["error_condensed"])

    def test_a_report_quoting_a_nul_or_a_lone_surrogate_is_accepted_by_sentinels_ingest_sql(self):
        self.admin("DELETE FROM error")
        with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: RuntimeError("a NUL \x00 here"))):
            self.post("/call-proc", {"query": "lesson.save", "parameters": {"note": "a lone \ud800 surrogate"}})
        payload = self.report()
        self.stub.reset()
        stub_model = self.model
        stub_model.submit = lambda inputs, account_id, **kwargs: JAAQLModel.submit(stub_model, inputs, TEST_ROLE, **kwargs)
        # As it was before the sender made it storable: refused by the ingest as it was (422, the report lost); the ingest now stores it with
        # each such character as U+FFFD, noted after the stacktrace (jaaql/test/test_sentinel_ingest.py)
        raw = dict(payload, error_condensed=payload["error_condensed"].replace("\\0", "\x00"),
                   stacktrace=payload["stacktrace"].replace("a lone ? surrogate", "a lone \ud800 surrogate"))
        self.assertEqual(200, self.client.post(ENDPOINT__report_sentinel_error, json=raw).status_code)
        [(error_condensed, stacktrace)] = self.admin("SELECT error_condensed, stacktrace FROM error")
        self.assertEqual(raw["error_condensed"].replace("\x00", "�")[:200], error_condensed)
        self.assertTrue(stacktrace.startswith(raw["stacktrace"].replace("\ud800", "�").replace("\x00", "�") +
                                              "\n\nIngest adjustments:\n"), stacktrace[-300:])
        self.admin("DELETE FROM error")
        accepted = self.client.post(ENDPOINT__report_sentinel_error, json=payload)
        self.assertEqual(200, accepted.status_code, accepted.data)
        self.assertEqual([(payload["error_condensed"], payload["stacktrace"])], self.admin("SELECT error_condensed, stacktrace FROM error"))
        self.admin("DELETE FROM error")

    def test_a_result_json_cannot_serialise(self):
        (status, _, data), reports = self.answers(lambda: self.submit("SELECT '1 day'::interval AS gap"))
        self.assertEqual((500, 1), (status, len(reports)))

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def test_a_report_is_accepted_by_sentinels_ingest_sql(self):
        with mock.patch.object(model, "is_federation_procedure", side_effect=raiser(lambda: KeyError("federation_procedure"))):
            self.post("/call-proc", {"query": "lesson.save", "parameters": {"id": 3}}, user_agent="Mozilla/5.0 (Ünïcode)")
        payload = self.report()
        self.assertEqual("Mozilla/5.0 (?n?code)", payload["user_agent"])
        self.stub.reset()
        stub_model = self.model
        stub_model.submit = lambda inputs, account_id, **kwargs: JAAQLModel.submit(stub_model, inputs, TEST_ROLE, **kwargs)
        accepted = self.client.post(ENDPOINT__report_sentinel_error, json=payload)
        self.assertEqual(200, accepted.status_code, accepted.data)
        self.assertEqual([(payload["source_file"], payload["file_line_number"], payload["file_col_number"], payload["source_system"],
                           payload["error_condensed"], payload["stacktrace"])],
                         self.admin("SELECT source_file, file_line_number, file_col_number, source_system, error_condensed, stacktrace FROM error"))
        self.assertNoReport()


if __name__ == "__main__":
    unittest.main()
