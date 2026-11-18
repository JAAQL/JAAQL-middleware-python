"""
Client errors: a request that conflicts with what exists (an account, or the role it would attach as, that exists already, a procedure named
twice) is answered 409 with JAAQL's error body, saying what exists, and never reported to Sentinel as a server error, while JAAQL's own SQL
failing for any other reason still is.

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
from unittest import mock

import psycopg
import psycopg.errors as pg
from psycopg.pq import DiagnosticField

from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface
from jaaql.documentation.documentation_internal import DOCUMENTATION__procedures
from jaaql.documentation.documentation_public import DOCUMENTATION__create_account, DOCUMENTATION__create_account_batch
from jaaql.exceptions.jaaql_interpretable_handled_errors import AccountAlreadyExists, UnhandledQueryError
from jaaql.generated_constants import RESPONSE_CODE_LOOKUP
from jaaql.mvc import base_controller, model
from jaaql.mvc.model import JAAQLModel
from jaaql.openapi.swagger_documentation import SwaggerFlatResponse, RESPONSE__200_ok
from jaaql.test.test_server_errors import ServerErrorCase, RaisingInterface, SUPER_KEY, CONFIG, ENVIRON__test_postgres_uri
from jaaql.utilities import slow_queries
from jaaql.utilities.utils import get_jaaql_root
from monitor.main import HEADER__security_bypass

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
