"""
Client errors: a request that conflicts with what exists (an account, or the role it would attach as, that exists already, a procedure named
twice) is answered 409 with JAAQL's error body, saying what exists, and a request JAAQL refuses (a query sent from where none may be sent, a
federation procedure called directly) 403, and neither is ever reported to Sentinel as a server error, while JAAQL's own SQL failing for any
other reason still is.

    python -m unittest jaaql.test.test_client_errors

The unit tests need only the package's requirements: statements run on stand-in database interfaces that raise the database errors a test
names, with the diagnostics PostgreSQL gives them, and Sentinel is a stub HTTP server on 127.0.0.1. TestRequestConflictsAgainstPostgres runs
JAAQL's own account table and create_account function (jaaql/scripts) in a scratch Postgres; it runs only when JAAQL_TEST_POSTGRES_URI is set
to postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database jaaql_test_conflicts and the roles
jaaql_test_conflict_*
"""
import json
import os
import re
import unittest
import urllib.parse
from unittest import mock

import psycopg
import psycopg.errors as pg
from psycopg.pq import DiagnosticField

from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface
from jaaql.documentation.documentation_internal import DOCUMENTATION__procedures
from jaaql.documentation.documentation_public import DOCUMENTATION__create_account, DOCUMENTATION__create_account_batch
from jaaql.exceptions.custom_http_status import CustomHTTPStatus
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.exceptions.jaaql_interpretable_handled_errors import AccountAlreadyExists, UnhandledQueryError, client_error
from jaaql.generated_constants import RESPONSE_CODE_LOOKUP
from jaaql.mvc import base_controller, model
from jaaql.mvc.model import JAAQLModel
from jaaql.openapi.swagger_documentation import SwaggerFlatResponse, RESPONSE__200_ok
from jaaql.test.test_server_errors import ServerErrorCase, RaisingInterface, SUPER_KEY, CONFIG, ENVIRON__test_postgres_uri, raiser
from jaaql.utilities import slow_queries
from jaaql.utilities.utils import get_jaaql_root
from monitor.main import HEADER__security_bypass, HEADER__security

ROLE = "my-role"
TEST_DATABASE = "jaaql_test_conflicts"
TEST_ROLE_PREFIX = "jaaql_test_conflict_"


def database_error(make, message, sqlstate, constraint=None, table=None):
    # A psycopg error with the diagnostics PostgreSQL gives it, so that the error JAAQL answers with describes it as it would on a box
    info = {DiagnosticField.SQLSTATE: sqlstate.encode(), DiagnosticField.MESSAGE_PRIMARY: message.encode(), DiagnosticField.SEVERITY: b"ERROR"}
    if constraint is not None:
        info[DiagnosticField.CONSTRAINT_NAME] = constraint.encode()
    if table is not None:
        info[DiagnosticField.TABLE_NAME] = table.encode()
    return lambda: make(message, info=info)


ROLE_EXISTS = database_error(pg.DuplicateObject, 'role "%s" already exists' % ROLE, "42710")
USERNAME_TAKEN = database_error(pg.UniqueViolation, 'duplicate key value violates unique constraint "account_username_key"', "23505",
                                "account_username_key", "account")
SUB_TAKEN = database_error(pg.UniqueViolation, 'duplicate key value violates unique constraint "account_sub_provider_tenant_key"', "23505",
                           "account_sub_provider_tenant_key", "account")
ACCOUNT_ID_TAKEN = database_error(pg.UniqueViolation, 'duplicate key value violates unique constraint "account_pkey"', "23505", "account_pkey",
                                  "account")


class AccountCase(ServerErrorCase):
    """
    The account routes with the real JAAQLModel methods, whose statements run on the interface the route connects with
    """

    def setUp(self):
        super().setUp()
        for name in ("create_account_with_potential_api_key", "shallow_federate_batch_potential_with_api_key"):
            self.quiet.enter_context(mock.patch.object(self.model, name, getattr(JAAQLModel, name).__get__(self.model), create=True))
        self.quiet.enter_context(mock.patch.object(self.model, "get_db_crypt_key", lambda: b"k" * 32, create=True))
        self.quiet.enter_context(mock.patch.object(self.model, "get_vault_repeatable_salt", lambda: "repeatable-salt", create=True))
        self.quiet.enter_context(mock.patch.object(self.model, "get_repeatable_salt", lambda: "repeatable-salt", create=True))
        self.quiet.enter_context(mock.patch.object(model, "database_user_registry__select_all", return_value=[]))
        # As create_app's produce_all_documentation leaves them at boot: a method that declares no 200 answers 200 OK
        for documentation in (DOCUMENTATION__create_account, DOCUMENTATION__create_account_batch, DOCUMENTATION__procedures):
            for method in documentation.methods:
                if not any(response.code == 200 for response in method.responses):
                    self.quiet.enter_context(mock.patch.object(method, "responses", method.responses + [SwaggerFlatResponse(RESPONSE__200_ok)]))

    def connecting(self, interface):
        # The interface the route's connection argument is made with (create_interface_for_db, the requester's)
        return mock.patch.object(base_controller, "create_interface_for_db", return_value=interface)

    def account(self, body):
        return self.client.post("/accounts", json=body, headers={HEADER__security_bypass: SUPER_KEY})

    def batch(self, accounts):
        return self.client.post("/accounts/batch", json={"accounts": accounts}, headers={HEADER__security_bypass: SUPER_KEY})

    def assertConflict(self, answered, message, column):
        (status, headers, data), reports = answered
        self.assertEqual((409, []), (status, reports), data)
        self.assertIn(("Content-Type", "application/json"), headers)
        self.assertEqual({"error_code": 1001, "message": message, "table_name": "account", "column_name": column, "index": None, "set": None,
                          "descriptor": None}, json.loads(data))


class TestRequestConflicts(AccountCase):

    def test_an_account_whose_role_exists_already(self):
        # Up to 5.3.30: 422 with error_code 1004 and the database's error, and reported to Sentinel as JAAQL's own query failing
        # (DuplicateObject at jaaql/mvc/exception_queries.py, "a server-side failure JAAQL answers as a client error")
        for body in [{"username": "u", "password": "p", "attach_as": ROLE}, {"username": "u", "password": None, "attach_as": ROLE, "registered": False}]:
            with self.subTest(body=body), self.connecting(RaisingInterface(ROLE_EXISTS)):
                self.assertConflict(self.answers(lambda: self.account(body)), "The role 'my-role' already exists, so no account can be created as it",
                                    "id")
        self.assertEqual([], self.lines())

    def test_an_account_whose_username_or_identity_exists_already(self):
        # Answered 422 with the database's error (error_code 1004) up to 5.3.30, never reported (class 23 is the client's)
        cases = [(USERNAME_TAKEN, "An account with the username 'u' already exists", "username"),
                 (SUB_TAKEN, "An account for this user of the identity provider already exists", "sub"),
                 (ACCOUNT_ID_TAKEN, "An account as the role 'my-role' already exists", "id")]
        for make, message, column in cases:
            with self.subTest(message), self.connecting(RaisingInterface(make)):
                self.assertConflict(self.answers(lambda: self.account({"username": "u", "password": "p", "attach_as": ROLE})), message, column)
        self.assertEqual([], self.lines())

    def test_a_batch_with_an_account_that_exists_already(self):
        # A role that exists is an account to keep there (allow_already_exists); a username or a user of the identity provider taken is not
        for make, message, column in [(USERNAME_TAKEN, "An account with the username 'u' already exists", "username"),
                                      (SUB_TAKEN, "An account for this user of the identity provider already exists", "sub")]:
            with self.subTest(message), self.connecting(RaisingInterface(make)):
                self.assertConflict(self.answers(lambda: self.batch([{"username": "u", "password": "p", "attach_as": ROLE}])), message, column)
        self.assertEqual([], self.lines())

    def test_jaaqls_own_query_failing_otherwise_is_still_reported(self):
        # The role of an account that attaches as none is JAAQL's own name for it (a uuid): that it exists is JAAQL's state, not the request's
        cases = {"a uuid role that exists": ({"username": "u", "password": "p"}, ROLE_EXISTS, 1004),
                 "create_account missing": ({"username": "u", "password": "p", "attach_as": ROLE},
                                            database_error(pg.UndefinedFunction, "function create_account(text) does not exist", "42883"), 1004),
                 "a server failing": ({"username": "u", "password": "p", "attach_as": ROLE},
                                      database_error(pg.DiskFull, "could not extend file: No space left on device", "53100"), 1002)}
        for name, (body, make, code) in cases.items():
            with self.subTest(name), self.connecting(RaisingInterface(make)):
                (status, _, data), reports = self.answers(lambda: self.account(body))
                self.assertEqual((422, code, 1), (status, json.loads(data)["error_code"], len(reports)), data)
                self.assertIn("(JAAQL's own query)", reports[0]["stacktrace"])

    def test_a_unique_violation_of_another_constraint_is_answered_as_before(self):
        other = database_error(pg.UniqueViolation, 'duplicate key value violates unique constraint "account_api_key_key"', "23505",
                               "account_api_key_key", "account")
        with self.connecting(RaisingInterface(other)):
            (status, _, data), reports = self.answers(lambda: self.account({"username": "u", "password": "p", "attach_as": ROLE}))
        self.assertEqual((422, 1004, []), (status, json.loads(data)["error_code"], reports))

    def test_jaaqls_own_accounts_find_no_conflict_of_the_clients(self):
        # The install's accounts, a login's federation and a security event create accounts of JAAQL's own: what exists there is no
        # request's conflict, and is raised as the database's error, a server error as ever
        for make in [ROLE_EXISTS, USERNAME_TAKEN]:
            with self.subTest(make().diag.message_primary), slow_queries.request_scope("/oauth/token", "POST", "/oauth/token"):
                with self.assertRaises(UnhandledQueryError):
                    JAAQLModel.create_account_with_potential_api_key(self.model, RaisingInterface(make), None, username="jaaql",
                                                                     attach_as=ROLE)

    def test_the_conflict_is_the_clients_whatever_noted_it(self):
        # The role's CREATE notes JAAQL's own query failing (42710 is not a client's SQLSTATE), which the answer outranks: it is the client's
        with slow_queries.request_scope("/accounts", "POST", "/accounts"):
            with self.assertRaises(AccountAlreadyExists) as raised:
                JAAQLModel.create_account_with_potential_api_key(self.model, RaisingInterface(ROLE_EXISTS), None, username="u",
                                                                 attach_as=ROLE, requested=True)
            self.assertEqual(1, len(slow_queries.current_scope().faults))
        self.assertTrue(model.server_errors.is_clients(raised.exception))
        self.assertIsInstance(raised.exception.__cause__, UnhandledQueryError)

    def test_a_procedure_named_twice(self):
        # Answered 409 before anything is deleted. Up to 5.3.30 the DELETE of the application's procedures had committed when the second
        # INSERT was refused by the primary key (422, the database's error): the application kept only the procedures listed before it
        interface = RaisingInterface()
        procs = [{"name": "nightly", "command": "x", "access": "S", "cron": "0 3 * * *"}, {"name": "hook", "command": "y", "access": "W"},
                 {"name": "nightly", "command": "z", "access": "S", "cron": None}]
        stub = mock.patch.object(self.model, "set_procedures", JAAQLModel.set_procedures.__get__(self.model), create=True)
        with stub, self.connecting(interface):
            (status, headers, data), reports = self.answers(lambda: self.client.post(
                "/procedures", json={"application": "lesbij", "procs": procs}, headers={HEADER__security_bypass: SUPER_KEY}))
            self.assertEqual((409, []), (status, reports), data)
            self.assertEqual({"error_code": 1027, "message": "The procedure 'nightly' is named more than once", "table_name": "remote_procedure",
                              "column_name": "name", "index": None, "set": None, "descriptor": None}, json.loads(data))
            self.assertEqual([], interface.statements)
            res = self.client.post("/procedures", json={"application": "lesbij", "procs": procs[:2]}, headers={HEADER__security_bypass: SUPER_KEY})
            self.assertEqual(200, res.status_code, res.data)
            self.assertEqual(3, len(interface.statements))
        self.assertEqual([], self.lines())

    def test_the_status_of_a_conflict_relayed_by_a_cloud_procedure(self):
        self.assertEqual((409, 409), (RESPONSE_CODE_LOOKUP[1001], RESPONSE_CODE_LOOKUP[1027]))
        self.assertEqual((409, 1001), (AccountAlreadyExists().response_code, AccountAlreadyExists().error_code))


class TestRefusals(ServerErrorCase):

    def refused(self, answered, message):
        (status, headers, data), reports = answered
        self.assertEqual((403, []), (status, reports), data)
        self.assertIn(("Content-Type", "application/json"), headers)
        self.assertEqual({"error_code": 1028, "message": message, "table_name": None, "column_name": None, "index": None, "set": None,
                          "descriptor": None}, json.loads(data))

    def test_a_query_sent_from_where_none_may_be_sent(self):
        # PREVENT_ARBITRARY_QUERIES. Up to 5.3.30: 500 with error_code 1099 ("An unhandled exception has occurred with JAAQL.") and the
        # refusal as its descriptor, which BATON takes for a server error
        self.model.prevent_arbitrary_queries = True
        for headers in [{HEADER__security: "a.token", "X-Real-IP": "203.0.113.9"}, {HEADER__security: "a.token", "X-Real-IP": "2001:db8::9"}]:
            with self.subTest(headers=headers), self.interface(RaisingInterface()) as interface:
                self.refused(self.answers(lambda: self.client.post("/submit", json={"query": "SELECT 1", "application": "lesbij"},
                                                                   headers=headers)), "Not allowed to send queries to server!")
                self.assertEqual([], interface.return_value.statements)
        # From the box itself, and JAAQL's own queries from anywhere, as ever
        with self.interface(RaisingInterface()):
            res = self.client.post("/submit", json={"query": "SELECT 1", "application": "lesbij"}, headers={HEADER__security_bypass: SUPER_KEY})
            self.assertEqual(200, res.status_code, res.data)
            self.assertEqual([[0.0]], JAAQLModel.submit(
                self.model, {"query": "SELECT 1", "application": "lesbij"}, "account-1", ip_address="203.0.113.9", server_authored_query=True)["rows"])
        self.assertEqual([], self.lines())

    def test_a_federation_procedure_called_directly(self):
        # Up to 5.3.30: 403 with the refusal as plain text
        with mock.patch.object(model, "is_federation_procedure", return_value=True), self.interface(RaisingInterface()) as interface:
            self.refused(self.answers(self.call_proc), "A federation procedure cannot be called directly")
            self.assertEqual([], interface.return_value.statements)
        self.assertEqual([], self.lines())

    def test_the_status_of_a_refusal_relayed_by_a_cloud_procedure(self):
        self.assertEqual(403, RESPONSE_CODE_LOOKUP[1028])


ERROR_BODY__keys = {"error_code", "message", "table_name", "index", "column_name", "descriptor", "set"}
# The error code of a client error raised with a status and a message alone, by its status
CODES__by_status = {400: 1029, 401: 1009, 403: 1028, 404: 1030, 405: 1031, 409: 1027, 413: 1032, 422: 1033, 425: 1018, 460: 1033}
# The table and the column an error code names, where it names any: DocumentStillRendering, as BATON's DOCUMENT_STILL_RENDERING knows it
DESCRIBED__by_code = {1018: ("document_request", "render_timestamp")}


class TestTheErrorBody(ServerErrorCase):
    """
    Every client error (4xx) JAAQL answers, whoever raised it, has JAAQL's error body, which BATON's handleResponse (BATON.jaaql.ts) hands
    to the request's own error handler as it does every JAAQL error: a JSON object, sent as application/json (parseResponse parses no other
    body), with an error_code. Up to 5.3.30 one raised with a status and a message alone was plain text, sent as text/html, and werkzeug's own
    an HTML page, which BATON took for an unexpected answer. The routes whose callers read them otherwise, and every server error, answer as
    they always did
    """

    def assertErrorBody(self, answered, status, code, message, startswith=False, described=(None, None)):
        (got, headers, data), reports = answered
        self.assertEqual((status, []), (got, reports), data)
        self.assertTrue(dict(headers)["Content-Type"].startswith("application/json"), headers)
        body = json.loads(data)
        self.assertEqual(ERROR_BODY__keys, set(body))
        self.assertEqual(code, body["error_code"], body)
        if startswith:
            self.assertTrue(body["message"].startswith(message), body)
        else:
            self.assertEqual(message, body["message"])
        self.assertEqual([described[0], None, described[1], None, None], [body[key] for key in ("table_name", "index", "column_name",
                                                                                                "descriptor", "set")])
        return dict(headers)

    def assertAsEver(self, answered, status, content_type, body):
        (got, headers, data), reports = answered
        self.assertEqual((status, [], content_type), (got, reports, dict(headers).get("Content-Type")), data)
        self.assertTrue(data.startswith(body), data)

    def test_a_client_error_raised_with_a_status_and_a_message(self):
        for status, code in CODES__by_status.items():
            refusal = HttpStatusException("Refused with %d" % status, CustomHTTPStatus.DATABASE_NO_EXIST if status == 460 else status)
            with self.subTest(status=status), mock.patch.object(self.model, "submit", raiser(lambda: refusal), create=True):
                self.assertErrorBody(self.answers(self.submit), status, code, "Refused with %d" % status,
                                     described=DESCRIBED__by_code.get(code, (None, None)))
        self.assertEqual([], self.lines())

    def test_a_malformed_request(self):
        # 5.3.30's 400s for malformed requests (5f6ac4e), each now with error_code 1029
        cases = [("/submit", {"query": "SELECT 1", "parameters": [1]}, "Malformed parameters! Please send as dictionary"),
                 ("/execute", {"query": {"a": "slow"}}, "Expected a compiled query as '<file>:<index>', not 'slow'"),
                 ("/call-proc", {"query": 123, "parameters": {}}, "Expected 'query' to be the name of the procedure to call, not 123"),
                 ("/submit", {"query": "SELECT 1", "parameters": {"unused": 1}}, "Unused parameter! Supplied with 'unused' but was never used")]
        for route, body, message in cases:
            with self.subTest(route=route, body=body), self.interface(RaisingInterface()):
                self.assertErrorBody(self.answers(lambda: self.post(route, body)), 400, 1029, message, startswith=True)
        self.assertEqual([], self.lines())

    def test_a_refused_query_of_a_dict_query_keeps_what_it_said(self):
        # Its set, query and parameters, as ever, in JAAQL's error body. Up to 5.3.30 the body had no error_code
        with self.interface(RaisingInterface()):
            (status, headers, data), reports = self.answers(lambda: self.post("/submit", {"query": {"a": {"query": "SELECT 1", "assert": 0}},
                                                                                          "parameters": {}}))
        self.assertEqual((400, []), (status, reports))
        self.assertEqual({"error_code": 1029, "message": "Assert expecting 0 row(s) but received 1 row(s)!", "table_name": None, "index": None,
                          "column_name": None, "descriptor": None, "set": "a", "error": "Assert expecting 0 row(s) but received 1 row(s)!",
                          "query": "SELECT 1", "parameters": {}}, json.loads(data))

    def test_werkzeugs_own_client_errors(self):
        super_key = {HEADER__security_bypass: SUPER_KEY}
        json_body = {"Content-Type": "application/json", HEADER__security_bypass: SUPER_KEY}
        with self.interface(RaisingInterface()):
            self.assertErrorBody(self.answers(lambda: self.client.post("/submit", data=b'{"query": ', headers=json_body)), 400, 1029,
                                 "Expected the request body to be JSON, which it is not (Expecting value: line 1 column 11 (char 10))")
            self.assertErrorBody(self.answers(lambda: self.client.post("/submit", data=b"", headers=json_body)), 400, 1029,
                                 "Expected the request body to be JSON, which it is not (Expecting value: line 1 column 1 (char 0))")
            self.assertErrorBody(self.answers(lambda: self.client.post("/submit", data=b"query=SELECT 1", headers=super_key)), 400, 1029,
                                 "Expected content-type application/json")
            self.assertErrorBody(self.answers(lambda: self.client.post("/submit", json={"query": "SELECT 1"}, headers={
                HEADER__security_bypass: "wrong"})), 401, 1009, "Invalid bypass key")
            self.assertErrorBody(self.answers(lambda: self.client.get("/nowhere")), 404, 1030, "The requested URL was not found", startswith=True)
            allowed = self.assertErrorBody(self.answers(lambda: self.client.delete("/submit")), 405, 1031,
                                           "The method is not allowed for the requested URL.")
            self.assertEqual("OPTIONS, POST", allowed["Allow"])
            self.assertErrorBody(self.answers(lambda: self.client.post("/submit", data=b"{}" + b" " * (2 * 1024 * 1024), headers=json_body)),
                                 413, 1032, "The data value transmitted exceeds the capacity limit.")
        # A HEAD sends no body, whatever it is
        (status, headers, data), reports = self.answers(lambda: self.client.head("/cron"))
        self.assertEqual((405, b"", "GET, OPTIONS", "application/json", []), (status, data, dict(headers)["Allow"], dict(headers)["Content-Type"],
                                                                              reports))
        self.assertEqual([], self.lines())

    def test_no_answer_shows_what_the_request_sent_as_a_page(self):
        # A key the route does not take, named in the answer: up to 5.3.30 the answer was sent as text/html, so that a link to GET
        # /rendered_documents, which needs no login, showed whatever HTML its query string held as a page of the box's own origin
        script = "<img src=x onerror=alert(document.cookie)>"
        (status, headers, data), reports = self.answers(lambda: self.client.get(
            "/rendered_documents?document_id=b47dc954-d608-4e1b-8a8c-d8b754ee554b&" + urllib.parse.quote(script, safe="") + "=1"))
        self.assertEqual((400, "application/json", []), (status, dict(headers)["Content-Type"], reports))
        self.assertEqual((1029, "Unexpected argument '%s'" % script), (json.loads(data)["error_code"], json.loads(data)["message"]))

    def test_the_routes_whose_callers_read_their_client_errors_otherwise(self):
        # A webhook's caller is anyone's (a payment provider), BATON's sendEmail hands only a plain-text failure to its onFailure, and BATON's
        # document functions (requestDocumentRender, pollDocumentRender) take a plain-text one quietly but throw, alert and report on JAAQL's
        # error body. Their own client errors are plain text, as ever, but sent as text/plain with nosniff where they were text/html;
        # werkzeug's own are its HTML page, as ever
        too_large = b"{}" + b" " * (2 * 1024 * 1024)
        html = b"<!doctype html>"
        plain = "text/plain; charset=utf-8"
        for route in ["/webhook/sentinel/hook", "/secure/sentinel/hook"]:
            with self.subTest(route), mock.patch.object(self.model, "handle_webhook", raiser(lambda: HttpStatusException(
                    "Procedure type is not type webhook")), create=True):
                login = {HEADER__security_bypass: SUPER_KEY} if route.startswith("/secure") else {}
                self.assertAsEver(self.answers(lambda: self.client.post(route, data=b"{", headers={"Content-Type": "application/json", **login})),
                                  400, "text/html; charset=utf-8", html)
                self.assertAsEver(self.answers(lambda: self.client.post(route, data=too_large, headers={"Content-Type": "application/json",
                                                                                                         **login})),
                                  413, "text/html; charset=utf-8", html)
                self.assertAsEver(self.answers(lambda: self.client.put(route)), 405, "text/html; charset=utf-8", html)
                self.assertAsEver(self.answers(lambda: self.client.head(route)), 405, "text/html; charset=utf-8", b"")
                self.assertAsEver(self.answers(lambda: self.client.post(route, json={}, headers=login)), 422, plain,
                                  b"Procedure type is not type webhook")
        email = {HEADER__security_bypass: SUPER_KEY, "Content-Type": "application/json"}
        with mock.patch.object(self.model, "send_email", raiser(lambda: HttpStatusException("Cannot send this template anonymously"))):
            self.assertAsEver(self.answers(lambda: self.client.post("/email", data=b"1", headers=email)), 400, plain,
                              b"Expected the request body to be a JSON object, not 1")
            self.assertAsEver(self.answers(lambda: self.client.post("/email", data=json.dumps({"template": "t", "application": "lesbij", "parameters": {}}),
                                                                    headers=email)), 422, plain,
                              b"Cannot send this template anonymously")
        document = {"document_id": "b47dc954-d608-4e1b-8a8c-d8b754ee554b"}
        with mock.patch.object(self.model, "fetch_document", raiser(lambda: HttpStatusException("Document still rendering", 425)), create=True),                 mock.patch.object(self.model, "render_document", raiser(lambda: HttpStatusException("Unknown template")), create=True):
            self.assertAsEver(self.answers(lambda: self.client.get("/documents", query_string=document, headers={
                HEADER__security_bypass: SUPER_KEY})), 425, plain, b"Document still rendering")
            self.assertAsEver(self.answers(lambda: self.client.post("/documents", data=b"[1]", headers=email)), 400, plain,
                              b"Expected the request body to be a JSON object, not an array")
            self.assertAsEver(self.answers(lambda: self.client.post("/documents", json={"name": "n", "parameters": {}, "create_file": True,
                                                                                        "application": "a"}, headers=email)), 422, plain,
                              b"Unknown template")
            self.assertAsEver(self.answers(lambda: self.client.post("/documents", data=b"{", headers=email)), 400, plain,
                              b"Expected the request body to be JSON, which it is not (Expecting property name")
            self.assertAsEver(self.answers(lambda: self.client.delete("/documents", headers=email)), 405, "text/html; charset=utf-8", html)
        self.assertEqual([], self.lines())

    def test_a_plain_text_answer_shows_nothing_the_request_sent_as_a_page(self):
        # GET /documents answers a query string key it does not take as plain text: sent as text/html, as up to 5.3.30, a link whose query
        # string held HTML showed it, scripts included, as a page of the box's own origin (the JAAQL cookie is SameSite=Lax, so it goes with
        # a top-level link, and nginx adds its nosniff and CSP to a 2xx or 3xx only)
        script = "<img src=x onerror=alert(document.cookie)>"
        (status, headers, data), reports = self.answers(lambda: self.client.get(
            "/documents?document_id=b47dc954-d608-4e1b-8a8c-d8b754ee554b&" + urllib.parse.quote(script, safe="") + "=1",
            headers={HEADER__security_bypass: SUPER_KEY}))
        self.assertEqual((400, "text/plain; charset=utf-8", "nosniff", []), (status, dict(headers)["Content-Type"],
                                                                             dict(headers)["X-Content-Type-Options"], reports))
        self.assertEqual("Unexpected argument '%s'" % script, data.decode())

    def test_a_server_error_is_answered_as_ever(self):
        # Its status and its text as ever, sent as text/plain with nosniff where it was text/html
        for status in [500, 502, 503]:
            with self.subTest(status=status), mock.patch.object(self.model, "submit", raiser(lambda: HttpStatusException("Down", status)),
                                                                create=True):
                (got, headers, data), _ = self.answers(self.submit)
                self.assertEqual((status, "text/plain; charset=utf-8", "nosniff", b"Down"), (got, dict(headers)["Content-Type"],
                                                                                             dict(headers)["X-Content-Type-Options"], data))

    def test_the_error_code_of_each_status(self):
        for status, code in CODES__by_status.items():
            with self.subTest(status=status):
                error = client_error(status, "m")
                self.assertEqual((code, status, "m"), (error.error_code, error.response_code, error.message))
                if code != 1009:
                    self.assertEqual(RESPONSE_CODE_LOOKUP[code], status if code != 1033 else 422)
        self.assertEqual(401, RESPONSE_CODE_LOOKUP[1009])


def statement_of(script: str, pattern: str) -> str:
    # A statement of one of JAAQL's own install scripts, as they install it
    with open(os.path.join(get_jaaql_root(), "scripts", script), encoding="utf-8") as file:
        found = re.search(pattern, file.read(), re.DOTALL | re.IGNORECASE)
    if found is None:
        raise AssertionError("no %s in %s" % (pattern, script))
    return found.group(0)


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestRequestConflictsAgainstPostgres(AccountCase):
    """
    JAAQL's own account table (04.install_jaaql_data_structures.generated.sql, its domains as text) and create_account and
    mark_account_registered (02.install_super_user.exceptions.sql), as installed, in a scratch database: the errors PostgreSQL raises when what
    /accounts and /accounts/batch ask for exists already are answered 409 and never reported, and nothing of the refused account is left
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
            cls.made_registered = not admin.execute("SELECT 1 FROM pg_roles WHERE rolname = 'registered'").fetchall()
            if cls.made_registered:
                admin.execute("CREATE ROLE registered")
        with psycopg.connect(cls.test_uri, autocommit=True) as conn:
            for domain in ["postgres_role", "encrypted__oidc_sub", "username", "encrypted__email", "provider_name", "tenant_name", "api_key"]:
                conn.execute("CREATE DOMAIN " + domain + " AS text")
            conn.execute("CREATE TABLE identity_provider_service (name text PRIMARY KEY, requires_email_verification boolean)")
            conn.execute(statement_of("04.install_jaaql_data_structures.generated.sql", r"create table account \(.*?\);"))
            for function in ["create_account", "mark_account_registered"]:
                conn.execute(statement_of("02.install_super_user.exceptions.sql",
                                          r"create function " + function + r"\(.*?\$\$ language plpgsql SECURITY DEFINER;"))

    @classmethod
    def tearDownClass(cls):
        pool = DBPGInterface.HOST_POOLS.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        DBPGInterface.HOST_POOLS_QUEUES.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        if pool is not None:
            pool.close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            for (role,) in admin.execute("SELECT rolname FROM pg_roles WHERE rolname LIKE %s", (TEST_ROLE_PREFIX + "%",)).fetchall():
                admin.execute('DROP ROLE "%s"' % role)
            if cls.made_registered:
                admin.execute("DROP ROLE IF EXISTS registered")
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.interface = create_interface(CONFIG, self.address, self.port, TEST_DATABASE, self.pool_user, self.password)
        self.quiet.enter_context(self.connecting(self.interface))

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            return conn.execute(sql, params).fetchall()

    def roles(self):
        return sorted(role for (role,) in self.admin("SELECT rolname FROM pg_roles WHERE rolname LIKE %s", (TEST_ROLE_PREFIX + "%",)))

    def test_what_exists_already_is_409_and_never_reported(self):
        first, second, third = (TEST_ROLE_PREFIX + name for name in ("ann", "ben", "cas"))
        res = self.account({"username": first + "@example.com", "password": "p", "attach_as": first})
        self.assertEqual(200, res.status_code, res.data)
        # The role exists: CREATE ROLE raises duplicate_object (42710), which create_account raises on
        self.assertConflict(self.answers(lambda: self.account({"username": second + "@example.com", "password": "p", "attach_as": first})),
                            "The role '%s' already exists, so no account can be created as it" % first, "id")
        # The username is taken: the INSERT raises unique_violation (23505) on account_username_key, and the role it created is rolled back
        self.assertConflict(self.answers(lambda: self.account({"username": first + "@example.com", "password": "p", "attach_as": second})),
                            "An account with the username '%s@example.com' already exists" % first, "username")
        self.assertConflict(self.answers(lambda: self.batch([{"username": first + "@example.com", "password": "p", "attach_as": third}])),
                            "An account with the username '%s@example.com' already exists" % first, "username")
        self.assertEqual([first], self.roles())
        self.assertEqual([(first, first + "@example.com")], self.admin("SELECT id, username FROM account"))
        # A role that exists is kept as the account's in a batch, as ever
        res = self.batch([{"username": first + "@example.com", "password": "p", "attach_as": first}])
        self.assertEqual(200, res.status_code, res.data)
        self.assertEqual([], self.lines())


if __name__ == "__main__":
    unittest.main()
