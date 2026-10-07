"""
The Keycloak calls and the JAAQL session ends of the security events: R, and C on a Keycloak user that already exists, delete every
credential of the user (the password and every second factor), set a temporary password and log the user out of Keycloak; R, C on an
existing user and D delete the validated_ip_address rows of the user's JAAQL account(s), found by the Keycloak user id and by the email,
never from a caller parameter; a C that creates a new Keycloak user is unchanged.

    python -m unittest jaaql.test.test_security_events

The unit tests need only the package's requirements: Keycloak is a fake behind requests, and the gate, the jaaql lookups and the statements
are replaced, so neither Keycloak nor a database is reached. TestEndJaaqlSessionsAgainstPostgres runs the session end itself (the real account
lookups, with the sub encrypted as create_account stores it, and the DELETE through a DBPGInterface) against a scratch Postgres; it runs only
when JAAQL_TEST_POSTGRES_URI is set to postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database
jaaql_test_sessions
"""
import os
import unittest
from types import SimpleNamespace
from unittest import mock
from urllib.parse import urlsplit

import psycopg
import requests as real_requests

from jaaql.constants import VAULT_KEY__db_crypt_key, VAULT_KEY__db_repeatable_salt
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface, execute_supplied_statement
from jaaql.exceptions.http_status_exception import HttpSingletonStatusException
from jaaql.utilities.crypt_utils import get_repeatable_salt
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel, KG__account__id, KG__application__default_schema, KG__application_schema__database, \
    KG__database_user_registry__database, KG__database_user_registry__provider, KG__database_user_registry__tenant

KC = "http://kc:8080"
REALM = "MfaTest"
APPLICATION = "mfatest"
DATABASE = "mfatest_db"
PROVIDER = "Relay Systems"
TENANT = "default"
SECURITY_EVENT = {"application": APPLICATION, "name": "person.login", "database_procedure": "person.login"}
EVERY_CREDENTIAL_TYPE = ["password", "otp", "recovery-authn-codes", "webauthn", "webauthn-passwordless"]
DELETE_SESSIONS = "DELETE FROM validated_ip_address WHERE account = :account"


class FakeResponse:
    def __init__(self, status_code, body=None, headers=None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.text = "" if body is None else str(body)

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise real_requests.HTTPError(str(self.status_code))


class FakeKeycloak:
    """
    The admin REST API of one realm, as far as the security events use it; every call is appended to the shared log as
    ("kc", METHOD, path), the user search with its username
    """

    def __init__(self, log, users):
        self.log = log
        self.users = {}
        self.next_id = 0
        for username, credential_types in users.items():
            user = self.add_user(username)
            for credential_type in credential_types:
                self.add_credential(user, credential_type)
        self.sessions = {user["id"]: 2 for user in self.users.values()}

    def add_user(self, username):
        self.next_id += 1
        user = {"id": "kc-" + username.split("@")[0], "username": username, "credentials": []}
        self.users[username] = user
        return user

    def add_credential(self, user, credential_type, temporary=False):
        self.next_id += 1
        user["credentials"].append({"id": "cred-" + str(self.next_id), "type": credential_type, "temporary": temporary})

    def by_id(self, user_id):
        return next(user for user in self.users.values() if user["id"] == user_id)

    def call(self, method, url, params=None, json=None, data=None):
        path = urlsplit(url).path
        assert url.startswith(KC), url
        users = "/admin/realms/" + REALM + "/users"
        if method == "POST" and path == "/realms/master/protocol/openid-connect/token":
            self.log.append(("kc", method, path))
            return FakeResponse(200, {"access_token": "admin-token"})
        self.log.append(("kc", method, path + ("?username=" + params["username"] if params else "")))
        parts = path[len(users):].strip("/").split("/") if path.startswith(users) else None
        if parts is None:
            return FakeResponse(404)
        if method == "GET" and parts == [""]:
            user = self.users.get(params["username"])
            return FakeResponse(200, [] if user is None else [{"id": user["id"], "username": user["username"]}])
        if method == "POST" and parts == [""]:
            user = self.add_user(json["username"])
            self.sessions[user["id"]] = 0
            return FakeResponse(201, headers={"Location": KC + users + "/" + user["id"]})
        user = self.by_id(parts[0])
        if method == "DELETE" and len(parts) == 1:
            del self.users[user["username"]]
            self.sessions.pop(user["id"])
            return FakeResponse(204)
        if method == "GET" and parts[1:] == ["credentials"]:
            return FakeResponse(200, [{"id": c["id"], "type": c["type"]} for c in user["credentials"]])
        if method == "DELETE" and parts[1] == "credentials":
            user["credentials"] = [c for c in user["credentials"] if c["id"] != parts[2]]
            return FakeResponse(204)
        if method == "PUT" and parts[1:] == ["reset-password"]:
            assert json["type"] == "password" and json["temporary"] is True and len(json["value"]) == 16 and json["value"].isalnum()
            user["credentials"] = [c for c in user["credentials"] if c["type"] != "password"]
            self.add_credential(user, "password", temporary=True)
            user["temporary_password"] = json["value"]
            return FakeResponse(204)
        if method == "POST" and parts[1:] == ["logout"]:
            self.sessions[user["id"]] = 0
            return FakeResponse(204)
        return FakeResponse(404)

    def requests_module(self):
        return SimpleNamespace(
            get=lambda url, headers=None, params=None, timeout=None: self.call("GET", url, params=params),
            post=lambda url, headers=None, json=None, data=None, timeout=None: self.call("POST", url, json=json, data=data),
            put=lambda url, headers=None, json=None, timeout=None: self.call("PUT", url, json=json),
            delete=lambda url, headers=None, timeout=None: self.call("DELETE", url))


class StubVault:
    def has_obj(self, key):
        return False

    def get_obj(self, key):
        return "k" * 32


class AppConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class SecurityEventCase(unittest.TestCase):
    """
    Each test sets up the Keycloak users (username -> credential types) and the JAAQL accounts, found by sub (the Keycloak user id) or
    by username, then runs one event through the real JAAQLModel methods
    """

    def setUp(self):
        self.log = []
        self.lookup = object()
        self.accounts_by_sub = {}
        self.accounts_by_username = {}
        self.registries = [{KG__database_user_registry__database: "other_db", KG__database_user_registry__provider: "Other",
                            KG__database_user_registry__tenant: "other"},
                           {KG__database_user_registry__database: DATABASE, KG__database_user_registry__provider: PROVIDER,
                            KG__database_user_registry__tenant: TENANT}]

    def keycloak(self, users):
        self.kc = FakeKeycloak(self.log, users)
        return self.kc

    def fetch_account_from_sub(self, connection, encryption_key, vault_repeatable_salt, sub, provider=None, tenant=None, **kwargs):
        self.assertIs(self.lookup, connection)
        self.assertEqual((PROVIDER, TENANT), (provider, tenant))
        if sub not in self.accounts_by_sub:
            raise HttpSingletonStatusException("not found", actual_count=0)
        return {KG__account__id: self.accounts_by_sub[sub]}

    def fetch_account_from_username(self, connection, username, **kwargs):
        self.assertIs(self.lookup, connection)
        if username not in self.accounts_by_username:
            raise HttpSingletonStatusException("not found", actual_count=0)
        return {KG__account__id: self.accounts_by_username[username]}

    def execute_supplied_statement(self, connection, query, parameters=None, **kwargs):
        self.log.append(("db", "lookup" if connection is self.lookup else "app", query, dict(parameters or {})))

    def run_event(self, event, email, parameters=None, create_account_error=None):
        jaaql_model = JAAQLModel.__new__(JAAQLModel)
        jaaql_model.vault = StubVault()
        jaaql_model.config = None
        jaaql_model.jaaql_lookup_connection = self.lookup
        jaaql_model.cached_canned_query_service = None
        jaaql_model._gate_run_singleton = mock.Mock(return_value={"gate": "row"})
        jaaql_model.create_account_with_potential_api_key = mock.Mock(return_value="account-new", side_effect=create_account_error)
        jaaql_model._run_federation_procedure = mock.Mock()
        self.app_connection = AppConnection()
        inputs = {"application": APPLICATION, "name": SECURITY_EVENT["name"], "type": event, "email": email,
                  "parameters": {"email": email, **(parameters or {})}}
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": KC, "KEYCLOAK_REALM": REALM}), \
                mock.patch.object(model, "requests", self.kc.requests_module()), \
                mock.patch.object(model, "fetch_account_from_sub", side_effect=self.fetch_account_from_sub), \
                mock.patch.object(model, "fetch_account_from_username", side_effect=self.fetch_account_from_username), \
                mock.patch.object(model, "execute_supplied_statement", side_effect=self.execute_supplied_statement), \
                mock.patch.object(model, "application__select", return_value={KG__application__default_schema: "default"}), \
                mock.patch.object(model, "application_schema__select", return_value={KG__application_schema__database: DATABASE}), \
                mock.patch.object(model, "database_user_registry__select_all", return_value=self.registries), \
                mock.patch.object(model, "create_interface_for_db", return_value=self.app_connection):
            method = {"R": JAAQLModel.security_event__reset_user_password, "C": JAAQLModel.security_event__create_user,
                      "D": JAAQLModel.security_event__delete_user}[event]
            result = method(jaaql_model, inputs, "caller-account", {**SECURITY_EVENT, "type": event})
        self.model = jaaql_model
        return result

    def kc_calls(self):
        return [(entry[1], entry[2]) for entry in self.log if entry[0] == "kc"]

    def session_deletes(self):
        return [entry[3]["account"] for entry in self.log if entry[0] == "db" and entry[2] == DELETE_SESSIONS]

    def assertWiped(self, username, result):
        user = self.kc.users[username]
        users = "/admin/realms/" + REALM + "/users/" + user["id"]
        self.assertEqual([{"id": user["credentials"][0]["id"], "type": "password", "temporary": True}], user["credentials"])
        self.assertEqual(user["temporary_password"], result["temporary_password"])
        self.assertEqual(user["id"], result["subject"])
        self.assertEqual({"gate": "row"}, result["response"])
        self.assertEqual(0, self.kc.sessions[user["id"]])
        # The wipe, in order: every credential deleted, then the temporary password, then the logout, then the JAAQL sessions
        calls = self.kc_calls()
        start = calls.index(("GET", users + "/credentials"))
        deleted = len(EVERY_CREDENTIAL_TYPE)
        self.assertEqual([("DELETE", users + "/credentials/")] * deleted, [(m, p.rsplit("/", 1)[0] + "/") for m, p in calls[start + 1:start + 1 + deleted]])
        self.assertEqual([("PUT", users + "/reset-password"), ("POST", users + "/logout")], calls[start + 1 + deleted:])
        last_kc = max(i for i, entry in enumerate(self.log) if entry[0] == "kc")
        self.assertTrue(all(i > last_kc for i, entry in enumerate(self.log) if entry[0] == "db"))


class TestReset(SecurityEventCase):

    def test_r_deletes_every_credential_sets_a_temporary_password_logs_out_and_ends_the_jaaql_sessions(self):
        self.keycloak({"ann@example.com": EVERY_CREDENTIAL_TYPE, "ben@example.com": ["password", "otp"]})
        self.accounts_by_sub["kc-ann"] = "account-ann-federated"
        self.accounts_by_username["ann@example.com"] = "account-ann-seeded"
        result = self.run_event("R", "ann@example.com")
        self.assertWiped("ann@example.com", result)
        self.assertEqual(["account-ann-federated", "account-ann-seeded"], self.session_deletes())
        # Nobody else is touched
        self.assertEqual(["password", "otp"], [c["type"] for c in self.kc.users["ben@example.com"]["credentials"]])
        self.assertEqual(2, self.kc.sessions["kc-ben"])

    def test_r_ends_the_sessions_of_an_account_found_both_ways_once(self):
        self.keycloak({"ann@example.com": EVERY_CREDENTIAL_TYPE})
        self.accounts_by_sub["kc-ann"] = "account-ann"
        self.accounts_by_username["ann@example.com"] = "account-ann"
        self.run_event("R", "ann@example.com")
        self.assertEqual(["account-ann"], self.session_deletes())

    def test_r_ends_the_sessions_of_whichever_account_exists(self):
        for by_sub, by_username, expected in [(True, False, ["account-ann"]), (False, True, ["account-ann"]), (False, False, [])]:
            with self.subTest(by_sub=by_sub, by_username=by_username):
                self.setUp()
                self.keycloak({"ann@example.com": EVERY_CREDENTIAL_TYPE})
                if by_sub:
                    self.accounts_by_sub["kc-ann"] = "account-ann"
                if by_username:
                    self.accounts_by_username["ann@example.com"] = "account-ann"
                result = self.run_event("R", "ann@example.com")
                self.assertWiped("ann@example.com", result)
                self.assertEqual(expected, self.session_deletes())

    def test_without_a_registry_for_the_application_database_only_the_username_is_looked_up(self):
        self.keycloak({"ann@example.com": EVERY_CREDENTIAL_TYPE})
        self.registries = [self.registries[0]]
        self.accounts_by_sub["kc-ann"] = "account-ann-federated"
        self.accounts_by_username["ann@example.com"] = "account-ann-seeded"
        self.run_event("R", "ann@example.com")
        self.assertEqual(["account-ann-seeded"], self.session_deletes())

    def test_the_accounts_never_come_from_a_caller_parameter(self):
        self.keycloak({"ann@example.com": EVERY_CREDENTIAL_TYPE})
        self.accounts_by_sub["kc-ann"] = "account-ann"
        self.run_event("R", "ann@example.com", parameters={"account_id": "account-someone-else", "account": "account-someone-else"})
        self.assertEqual(["account-ann"], self.session_deletes())

    def test_r_on_an_email_without_a_keycloak_user_creates_it_and_resets_it(self):
        self.keycloak({})
        self.accounts_by_username["new@example.com"] = "account-new-seeded"
        result = self.run_event("R", "new@example.com")
        users = "/admin/realms/" + REALM + "/users"
        self.assertEqual([("POST", "/realms/master/protocol/openid-connect/token"), ("GET", users + "?username=new@example.com"),
                          ("GET", users + "?username=new@example.com"), ("POST", users), ("GET", users + "/kc-new/credentials"),
                          ("PUT", users + "/kc-new/reset-password"), ("POST", users + "/kc-new/logout")], self.kc_calls())
        self.assertEqual(result["temporary_password"], self.kc.users["new@example.com"]["temporary_password"])
        self.assertEqual(["account-new-seeded"], self.session_deletes())


class TestCreate(SecurityEventCase):

    def test_c_on_an_existing_keycloak_user_resets_it_exactly_as_r_does(self):
        self.keycloak({"ben@example.com": EVERY_CREDENTIAL_TYPE})
        self.accounts_by_sub["kc-ben"] = "account-ben-federated"
        self.accounts_by_username["ben@example.com"] = "account-ben-seeded"
        result = self.run_event("C", "ben@example.com")
        self.assertWiped("ben@example.com", result)
        self.assertEqual(["account-ben-federated", "account-ben-seeded"], self.session_deletes())
        # A local account with this username exists, so no JAAQL account is created (unchanged)
        self.assertIsNone(result["account_id"])
        self.model.create_account_with_potential_api_key.assert_not_called()
        # The existing Keycloak user was looked up before anything could be created: no POST to /users
        self.assertNotIn(("POST", "/admin/realms/" + REALM + "/users"), self.kc_calls())

    def test_c_on_an_existing_keycloak_user_ends_the_sessions_before_creating_an_account(self):
        # A Keycloak user whose JAAQL account has no username: C still goes on to create a JAAQL account (unchanged), and the
        # sessions have been ended before that, whether or not it succeeds
        self.keycloak({"ben@example.com": EVERY_CREDENTIAL_TYPE})
        self.accounts_by_sub["kc-ben"] = "account-ben-federated"
        with self.assertRaises(RuntimeError):
            self.run_event("C", "ben@example.com", create_account_error=RuntimeError("duplicate key value violates unique constraint"))
        self.assertEqual(["account-ben-federated"], self.session_deletes())
        self.assertEqual(["password"], [c["type"] for c in self.kc.users["ben@example.com"]["credentials"]])
        self.assertEqual(0, self.kc.sessions["kc-ben"])

    def test_c_on_a_new_user_creates_it_with_a_temporary_password_as_before(self):
        self.keycloak({"ann@example.com": EVERY_CREDENTIAL_TYPE})
        result = self.run_event("C", "new@example.com")
        users = "/admin/realms/" + REALM + "/users"
        self.assertEqual([("POST", "/realms/master/protocol/openid-connect/token"), ("GET", users + "?username=new@example.com"),
                          ("GET", users + "?username=new@example.com"), ("POST", users), ("PUT", users + "/kc-new/reset-password")],
                         self.kc_calls())
        new_user = self.kc.users["new@example.com"]
        self.assertEqual([("password", True)], [(c["type"], c["temporary"]) for c in new_user["credentials"]])
        self.assertEqual(new_user["temporary_password"], result["temporary_password"])
        self.assertEqual({"temporary_password": result["temporary_password"], "response": {"gate": "row"}, "subject": "kc-new",
                          "account_id": "account-new"}, result)
        # No session is ended (a new user has none); the JAAQL account and its federation rows are created as before
        self.assertEqual([], self.session_deletes())
        self.model.create_account_with_potential_api_key.assert_called_once()
        self.assertEqual("kc-new", self.model.create_account_with_potential_api_key.call_args.kwargs["sub"])
        self.assertEqual(2, len([entry for entry in self.log if entry[0] == "db" and entry[1] == "app"]))
        self.assertTrue(self.app_connection.closed)
        # Others are untouched
        self.assertEqual(EVERY_CREDENTIAL_TYPE, [c["type"] for c in self.kc.users["ann@example.com"]["credentials"]])


class TestDelete(SecurityEventCase):

    def test_d_ends_the_jaaql_sessions_before_it_deletes_the_keycloak_user(self):
        self.keycloak({"cas@example.com": EVERY_CREDENTIAL_TYPE, "ann@example.com": ["password"]})
        self.accounts_by_sub["kc-cas"] = "account-cas-federated"
        self.accounts_by_username["cas@example.com"] = "account-cas-seeded"
        result = self.run_event("D", "cas@example.com", parameters={"account_id": "account-cas-federated"})
        self.assertEqual({"gate": "row"}, result)
        self.assertNotIn("cas@example.com", self.kc.users)
        self.assertIn("ann@example.com", self.kc.users)
        users = "/admin/realms/" + REALM + "/users"
        self.assertEqual([("POST", "/realms/master/protocol/openid-connect/token"), ("GET", users + "?username=cas@example.com"),
                          ("DELETE", users + "/kc-cas")], self.kc_calls())
        self.assertEqual(["account-cas-federated", "account-cas-seeded"], self.session_deletes())
        delete_user = self.log.index(("kc", "DELETE", users + "/kc-cas"))
        self.assertTrue(all(i < delete_user for i, entry in enumerate(self.log) if entry[0] == "db" and entry[2] == DELETE_SESSIONS))
        # The federation entries of the account named by the gate's caller are deactivated as before
        self.assertEqual(1, len([entry for entry in self.log if entry[0] == "db" and entry[1] == "app"]))


ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_sessions"
CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}
VAULT = {VAULT_KEY__db_crypt_key: "k" * 32, VAULT_KEY__db_repeatable_salt: "repeatable-salt-for-the-test"}


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestEndJaaqlSessionsAgainstPostgres(unittest.TestCase):
    """
    account and validated_ip_address as the jaaql database has them, with plain text columns for the domains; the accounts are written
    with their sub encrypted exactly as create_account encrypts it (the repeatable salt plus provider__tenant), so finding the federated
    account by the Keycloak user id proves the lookup matches what JAAQL stores, and the rows are counted on a separate connection, so
    the DELETE is committed
    """

    @classmethod
    def setUpClass(cls):
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
        address, port, _, cls.pool_user, password = DBInterface.fracture_uri(uri)
        cls.test_uri = uri.rsplit("/", 1)[0] + "/" + TEST_DATABASE
        with psycopg.connect(uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("CREATE DATABASE " + TEST_DATABASE)
        with psycopg.connect(cls.test_uri, autocommit=True) as conn:
            conn.execute("""
                CREATE TABLE account (id text PRIMARY KEY, sub text NOT NULL, username text UNIQUE, provider text, tenant text, api_key text,
                    UNIQUE (sub, provider, tenant));
                CREATE TABLE validated_ip_address (account text NOT NULL, uuid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    encrypted_salted_ip_address text NOT NULL UNIQUE, last_authentication_timestamp timestamptz NOT NULL DEFAULT now());
            """)
        cls.lookup = create_interface(CONFIG, address, int(port), TEST_DATABASE, cls.pool_user, password=password)

    @classmethod
    def tearDownClass(cls):
        pool = DBPGInterface.HOST_POOLS.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        DBPGInterface.HOST_POOLS_QUEUES.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        if pool is not None:
            pool.close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def add_account(self, account_id, sub, username, provider, tenant):
        execute_supplied_statement(self.lookup, "INSERT INTO account (id, sub, username, provider, tenant) VALUES (:id, :sub, :username, :provider, :tenant)",
                                   {"id": account_id, "sub": sub, "username": username, "provider": provider, "tenant": tenant},
                                   encryption_key=VAULT[VAULT_KEY__db_crypt_key].encode("ascii"), encrypt_parameters=["sub"],
                                   encryption_salts={"sub": get_repeatable_salt(VAULT[VAULT_KEY__db_repeatable_salt], provider + "__" + tenant)})
        for session in range(2):
            self.admin("INSERT INTO validated_ip_address (account, encrypted_salted_ip_address) VALUES (%s, %s)",
                       (account_id, account_id + "@" + str(session)))

    def setUp(self):
        self.admin("TRUNCATE account, validated_ip_address")
        self.add_account("account-ann-federated", "kc-ann", None, PROVIDER, TENANT)
        self.add_account("account-ann-seeded", "seed-ann", "ann@example.com", PROVIDER, TENANT)
        self.add_account("account-ben-federated", "kc-ben", None, PROVIDER, TENANT)
        self.add_account("account-ann-elsewhere", "kc-ann", None, "Other", "other")

    def end_sessions(self, kc_user_id, email):
        jaaql_model = JAAQLModel.__new__(JAAQLModel)
        jaaql_model.vault = SimpleNamespace(get_obj=lambda key: VAULT[key], has_obj=lambda key: key in VAULT)
        jaaql_model.jaaql_lookup_connection = self.lookup
        registries = [{KG__database_user_registry__database: "other_db", KG__database_user_registry__provider: "Other",
                       KG__database_user_registry__tenant: "other"},
                      {KG__database_user_registry__database: DATABASE, KG__database_user_registry__provider: PROVIDER,
                       KG__database_user_registry__tenant: TENANT}]
        with mock.patch.object(model, "application__select", return_value={KG__application__default_schema: "default"}), \
                mock.patch.object(model, "application_schema__select", return_value={KG__application_schema__database: DATABASE}), \
                mock.patch.object(model, "database_user_registry__select_all", return_value=registries):
            jaaql_model._end_jaaql_sessions(APPLICATION, kc_user_id, email)

    def sessions(self):
        return {account: count for account, count in self.admin("SELECT account, count(*) FROM validated_ip_address GROUP BY account")}

    def test_the_federated_and_the_seeded_account_of_the_user_lose_their_sessions_and_nobody_else(self):
        self.end_sessions("kc-ann", "ann@example.com")
        self.assertEqual({"account-ben-federated": 2, "account-ann-elsewhere": 2}, self.sessions())

    def test_a_user_with_only_a_federated_account(self):
        self.end_sessions("kc-ben", "ben@example.com")
        self.assertEqual({"account-ann-federated": 2, "account-ann-seeded": 2, "account-ann-elsewhere": 2}, self.sessions())

    def test_a_user_without_an_account_changes_nothing(self):
        self.end_sessions("kc-nobody", "nobody@example.com")
        self.assertEqual({"account-ann-federated": 2, "account-ann-seeded": 2, "account-ben-federated": 2, "account-ann-elsewhere": 2},
                         self.sessions())


if __name__ == "__main__":
    unittest.main()
