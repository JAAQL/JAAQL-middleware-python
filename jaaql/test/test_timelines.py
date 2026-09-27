"""
The 'timelines' request key: the viewing moment per timeline, applied as transaction-local settings timeline.<name>.

    python -m unittest jaaql.test.test_timelines

The unit tests need only the package's requirements. TestTimelinesAgainstPostgres additionally drives the real request path
(submit -> get_required_db -> DBPGInterface -> the jaaql extension -> InterpretJAAQL) against a scratch Postgres that has the
jaaql extension available (e.g. a container of this repository's image); it runs only when JAAQL_TEST_POSTGRES_URI is set to
postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database jaaql_test_timelines
"""
import os
import queue
import time
import unittest
from http import HTTPStatus
from unittest import mock

from jaaql.constants import GUC__timeline_prefix, TIMELINES__max_count, KEY__timelines
from jaaql.db import db_pg_interface
from jaaql.db.db_pg_interface import DBPGInterface, QUERY__apply_session_settings, _execute_pending_statement
from jaaql.db.db_utils_no_circ import pop_timeline_settings, get_required_db, submit
from jaaql.exceptions.http_status_exception import HttpStatusException

CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_timelines"
TEST_ROLE = "jaaql_test_timelines_user"


class TestPopTimelineSettings(unittest.TestCase):

    def assertBadRequest(self, timelines, fragment, **extra):
        inputs = {KEY__timelines: timelines, **extra}
        with self.assertRaises(HttpStatusException) as caught:
            pop_timeline_settings(inputs)
        self.assertEqual(HTTPStatus.BAD_REQUEST, caught.exception.response_code)
        self.assertIn(fragment, caught.exception.message)

    def test_absent_key_gives_no_settings(self):
        inputs = {"query": "SELECT 1"}
        self.assertIsNone(pop_timeline_settings(inputs))
        self.assertEqual({"query": "SELECT 1"}, inputs)

    def test_key_is_popped_and_names_are_built_server_side(self):
        inputs = {"query": "SELECT 1", KEY__timelines: {"Registratie": "2024-03-01", "geldigheid": "2024-03-01T12:30:00+01:00"}}
        self.assertEqual({GUC__timeline_prefix + "registratie": "2024-03-01", GUC__timeline_prefix + "geldigheid": "2024-03-01T12:30:00+01:00"},
                         pop_timeline_settings(inputs))
        self.assertNotIn(KEY__timelines, inputs)
        self.assertEqual("timeline.", GUC__timeline_prefix)

    def test_null_moments_are_dropped(self):
        self.assertEqual({"timeline.registratie": "2024-03-01"}, pop_timeline_settings({KEY__timelines: {"registratie": "2024-03-01", "geldigheid": None}}))
        self.assertIsNone(pop_timeline_settings({KEY__timelines: {"registratie": None}}))
        self.assertIsNone(pop_timeline_settings({KEY__timelines: {}}))
        self.assertIsNone(pop_timeline_settings({KEY__timelines: None}))

    def test_accepted_moments(self):
        for moment in ["2024-03-01", "2024-03-01T12:30", "2024-03-01 12:30", "2024-03-01T12:30:15", "2024-03-01T12:30:15.5",
                       "2024-03-01T12:30:15.123456", "2024-03-01T12:30:15Z", "2024-03-01T12:30:15.123Z", "2024-03-01T12:30:15-05:30",
                       "2024-02-29", "0001-01-01", "9999-12-31T23:59:59", "2024-12-31T23:59:59.999999+14:00", "2024-03-01T00:00:00-00:00"]:
            self.assertEqual({"timeline.t": moment}, pop_timeline_settings({KEY__timelines: {"t": moment}}), moment)

    def test_rejected_moments(self):
        for moment in ["", "now", "today", "infinity", "-infinity", "2024-3-1", "01-03-2024", "2024/03/01", "20240301", "2024-13-01",
                       "2024-00-10", "2024-03-00", "2024-03-32", "2024-04-31", "2023-02-29", "2024-02-30", "0000-01-01", "2024-03-01T24:00",
                       "2024-03-01T24:00:00", "2024-03-01T12:60", "2024-03-01T12:30:60", "2024-03-01T12:30:15+24:00", "2024-03-01T12:30:15+01:60",
                       "2024-03-01T12:30:15+16:00", "2024-03-01T12:30:15-23:59",
                       "2024-03-01t12:30", "2024-03-01T12:30z", "2024-03-01T12", "2024-03-01T12:30:15+0100",
                       "2024-03-01T12:30:15+01", "2024-03-01T12:30:15.1234567", "2024-03-01\n", " 2024-03-01", "2024-03-01T12:30:15 CET",
                       "2024-03-01'); DROP TABLE x; --", "2024-03-01" + " " * 55, "٢٠٢٤-03-01", 20240301, 2024.0, True, [], {}]:
            self.assertBadRequest({"registratie": moment}, "for timeline 'registratie' is invalid")

    def test_rejected_names(self):
        for name in ["", "1registratie", "reg-istratie", "reg istratie", "timeline.registratie", "registratie ", "régistratie", "a" * 64,
                     "registratie\n", "$registratie", "Kelvin"]:
            self.assertBadRequest({name: "2024-03-01"}, "is invalid: expected a letter or underscore")

    def test_name_length_limit(self):
        self.assertEqual({"timeline." + "a" * 63: "2024-03-01"}, pop_timeline_settings({KEY__timelines: {"A" * 63: "2024-03-01"}}))

    def test_names_repeated_after_lower_casing(self):
        self.assertBadRequest({"Registratie": "2024-03-01", "registratie": "2024-04-01"}, "named more than once")
        self.assertBadRequest({"Registratie": None, "registratie": "2024-04-01"}, "named more than once")

    def test_malformed_and_too_many(self):
        for timelines in ["2024-03-01", ["registratie"], 1, True]:
            self.assertBadRequest(timelines, "must be an object")
        self.assertBadRequest({"t%d" % n: None for n in range(TIMELINES__max_count + 1)}, "at most 16 are allowed")
        self.assertIsNone(pop_timeline_settings({KEY__timelines: {"t%d" % n: None for n in range(TIMELINES__max_count)}}))

    def test_autocommit(self):
        self.assertBadRequest({"registratie": "2024-03-01"}, "cannot be combined with 'autocommit'", autocommit=True)
        self.assertEqual({"timeline.registratie": "2024-03-01"}, pop_timeline_settings({KEY__timelines: {"registratie": "2024-03-01"}, "autocommit": False}))
        # Nothing would be set, so nothing conflicts
        self.assertIsNone(pop_timeline_settings({KEY__timelines: {"registratie": None}, "autocommit": True}))


class TestGetRequiredDb(unittest.TestCase):

    def test_bad_timelines_are_rejected_before_any_database_work(self):
        with mock.patch("jaaql.db.db_utils_no_circ.create_interface_for_db", side_effect=AssertionError("interface created")), \
                mock.patch("jaaql.db.db_utils_no_circ.execute_supplied_statement", side_effect=AssertionError("application looked up")):
            with self.assertRaises(HttpStatusException) as caught:
                get_required_db(None, CONFIG, None, {"application": "app", "query": "SELECT 1", KEY__timelines: {"registratie": "yesterday"}}, "account")
        self.assertEqual(HTTPStatus.BAD_REQUEST, caught.exception.response_code)

    def test_settings_are_threaded_like_the_role(self):
        inputs = {"database": "db", "query": "SELECT 1", "role": "reader", KEY__timelines: {"REGISTRATIE": "2024-03-01"}}
        with mock.patch("jaaql.db.db_utils_no_circ.create_interface_for_db", return_value="interface") as create:
            self.assertEqual("interface", get_required_db("vault", CONFIG, None, inputs, "account"))
        create.assert_called_once_with("vault", CONFIG, "account", "db", "reader", session_settings={"timeline.registratie": "2024-03-01"})
        self.assertEqual({"database": "db", "query": "SELECT 1"}, inputs)

    def test_without_timelines_the_interface_gets_none(self):
        with mock.patch("jaaql.db.db_utils_no_circ.create_interface_for_db", return_value="interface") as create:
            get_required_db("vault", CONFIG, None, {"database": "db", "query": "SELECT 1"}, "account")
        create.assert_called_once_with("vault", CONFIG, "account", "db", None, session_settings=None)


class FakeConnection:
    def __init__(self, autocommit=False):
        self._autocommit = autocommit
        self.autocommit_writes = []
        self.pending = "never set"

    @property
    def autocommit(self):
        return self._autocommit

    @autocommit.setter
    def autocommit(self, value):
        self.autocommit_writes.append(value)
        self._autocommit = value

    def jaaql_set_pending_auth(self, statements):
        self.pending = statements


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def getconn(self, timeout=None):
        return self.conn


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))


class TestPendingStatements(unittest.TestCase):
    USERNAME = "jaaql_test_pending_statements"
    DATABASE = "db"

    def tearDown(self):
        DBPGInterface.HOST_POOLS.pop(self.USERNAME, None)
        DBPGInterface.HOST_POOLS_QUEUES.pop(self.USERNAME, None)

    def checkout(self, conn, **kwargs):
        interface = DBPGInterface(CONFIG, "localhost", 5432, self.DATABASE, self.USERNAME, password=None, **kwargs)
        DBPGInterface.HOST_POOLS[self.USERNAME][self.DATABASE] = FakePool(conn)
        return interface._get_conn()

    def test_settings_statement_follows_the_authorization_statements(self):
        conn = self.checkout(FakeConnection(), role="account", sub_role="reader",
                             session_settings={"timeline.registratie": "2024-03-01", "timeline.geldigheid": "2024-03-01T12:00:00Z"})
        self.assertEqual(3, len(conn.pending))
        self.assertTrue(conn.pending[0].startswith("SELECT jaaql_extension.jaaql__set_session_authorization('account', '"))
        self.assertEqual("SET ROLE \"reader\"", conn.pending[1])
        self.assertEqual((QUERY__apply_session_settings, (["timeline.registratie", "timeline.geldigheid"], ["2024-03-01", "2024-03-01T12:00:00Z"])),
                         conn.pending[2])
        self.assertEqual("SELECT set_config(s.n, s.v, true) FROM unnest(%s::text[], %s::text[]) AS s(n, v)", QUERY__apply_session_settings)

    def test_without_settings_the_pending_statements_are_unchanged(self):
        conn = self.checkout(FakeConnection(), role="account", sub_role="reader")
        self.assertEqual(2, len(conn.pending))
        self.assertTrue(all(isinstance(statement, str) for statement in conn.pending))
        conn = self.checkout(FakeConnection(), role="account", session_settings={})
        self.assertEqual(1, len(conn.pending))

    def test_settings_alone_are_deferred_too(self):
        conn = self.checkout(FakeConnection(), session_settings={"timeline.registratie": "2024-03-01"})
        self.assertEqual([(QUERY__apply_session_settings, (["timeline.registratie"], ["2024-03-01"]))], conn.pending)
        conn = self.checkout(FakeConnection())
        self.assertEqual("never set", conn.pending)

    def test_checkout_ends_a_leaked_autocommit(self):
        conn = self.checkout(FakeConnection(autocommit=True), role="account")
        self.assertEqual([False], conn.autocommit_writes)
        conn = self.checkout(FakeConnection(autocommit=False), role="account")
        self.assertEqual([], conn.autocommit_writes)

    def test_pending_statement_forms(self):
        cursor = FakeCursor()
        _execute_pending_statement(cursor, "SET ROLE \"reader\"")
        _execute_pending_statement(cursor, (QUERY__apply_session_settings, (["timeline.registratie"], ["2024-03-01"])))
        self.assertEqual([("SET ROLE \"reader\"", None), (QUERY__apply_session_settings, (["timeline.registratie"], ["2024-03-01"]))], cursor.executed)


class StubVault:
    def __init__(self, uri):
        self.uri = uri

    def get_obj(self, key):
        return self.uri


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestTimelinesAgainstPostgres(unittest.TestCase):
    """
    One usable pooled connection (pool of two, DBPGInterface.__init__ keeps one checked out), so consecutive requests share a
    connection, which pg_backend_pid() confirms
    """

    @classmethod
    def setUpClass(cls):
        import psycopg
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
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
                CREATE TABLE "person__$log" (id int NOT NULL, name text, registered_from date NOT NULL, registered_to date NOT NULL,
                                             PRIMARY KEY (id, registered_to));
                CREATE VIEW person AS SELECT id, name, registered_from, registered_to FROM "person__$log"
                WHERE CASE WHEN (SELECT nullif(current_setting('timeline.registration', true), '')::date) IS NULL
                    THEN registered_to = '2300-01-01'::date
                    ELSE registered_from <= (SELECT nullif(current_setting('timeline.registration', true), '')::date)
                        AND (SELECT nullif(current_setting('timeline.registration', true), '')::date) < registered_to END;
                INSERT INTO "person__$log" VALUES (1, 'old', '2020-01-01', '2022-01-01'), (1, 'new', '2022-01-01', '2300-01-01');
                CREATE TABLE audit (note text);
                CREATE FUNCTION "person.name"(id int) RETURNS TABLE (name text, moment text) LANGUAGE sql STABLE AS
                    $f$ SELECT P.name, current_setting('timeline.registration', true) FROM person P WHERE P.id = "person.name".id $f$;
                GRANT SELECT ON person TO """ + TEST_ROLE + """;
                GRANT SELECT, INSERT ON audit TO """ + TEST_ROLE + """;
                GRANT EXECUTE ON FUNCTION "person.name"(int) TO """ + TEST_ROLE + """;
            """)
        cls.saved_pool_sizes = (db_pg_interface.PGCONN__min_conns, db_pg_interface.PGCONN__max_conns)
        db_pg_interface.PGCONN__min_conns = 2
        db_pg_interface.PGCONN__max_conns = 2
        cls.vault = StubVault(uri)

    @classmethod
    def tearDownClass(cls):
        import psycopg
        db_pg_interface.PGCONN__min_conns, db_pg_interface.PGCONN__max_conns = cls.saved_pool_sizes
        for user_pools in DBPGInterface.HOST_POOLS.values():
            if TEST_DATABASE in user_pools:
                user_pools.pop(TEST_DATABASE).close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("DROP ROLE IF EXISTS " + TEST_ROLE)

    def pool(self):
        return [pools[TEST_DATABASE] for pools in DBPGInterface.HOST_POOLS.values() if TEST_DATABASE in pools][0]

    def request(self, inputs, prepare_statements=False):
        hook = queue.Queue()
        hook.put((True, None, None))
        inputs = dict({"database": TEST_DATABASE}, **inputs)
        result = submit(self.vault, CONFIG, None, None, inputs, TEST_ROLE, hook, prepare_statements=prepare_statements)
        deadline = time.time() + 5
        while time.time() < deadline and self.pool().get_stats().get("pool_available", 0) < 1:
            time.sleep(0.02)
        return result

    @staticmethod
    def row(result):
        return dict(zip(result["columns"], result["rows"][0]))

    PROBE = "SELECT pg_backend_pid() AS pid, txid_current() AS tx, current_setting('timeline.registration', true) AS moment, " \
            "(SELECT string_agg(name, ',') FROM person) AS names"

    def test_moment_holds_for_every_query_of_the_request_and_ends_with_it(self):
        result = self.request({"query": {"a": self.PROBE, "b": "SELECT txid_current() AS tx, (SELECT string_agg(name, ',') FROM person) AS names"},
                               KEY__timelines: {"Registration": "2021-01-01"}})
        first, second = self.row(result["a"]), self.row(result["b"])
        self.assertEqual(("2021-01-01", "old", "old"), (first["moment"], first["names"], second["names"]))
        self.assertEqual(first["tx"], second["tx"])

        after = self.row(self.request({"query": self.PROBE}))
        self.assertEqual(first["pid"], after["pid"])
        self.assertIn(after["moment"], (None, ""))
        self.assertEqual("new", after["names"])

    def test_prepared_and_procedure_requests(self):
        for moment, expected in [("2021-01-01", "old"), (None, "new"), ("2021-06-01T10:00:00", "old"), (None, "new")]:
            extra = {} if moment is None else {KEY__timelines: {"registration": moment}}
            self.assertEqual(expected, self.row(self.request(dict({"query": {"q": self.PROBE}}, **extra), prepare_statements=True)["q"])["names"])
            procedure = {"query": {"_jaaql_procedure": "SELECT * FROM \"person.name\"(\n\tid => :id )"}, "parameters": {"id": 1}}
            self.assertEqual(expected, self.row(self.request(dict(procedure, **extra))["_jaaql_procedure"])["name"])

    def test_bad_timelines_are_rejected_and_nothing_runs(self):
        self.request({"query": "SELECT 1"})
        requests_before = self.pool().get_stats().get("requests_num")
        for timelines in [{"registration": "2021-02-30"}, {"regis-tration": "2021-01-01"}, "2021-01-01"]:
            with self.assertRaises(HttpStatusException) as caught:
                self.request({"query": "INSERT INTO audit VALUES ('ran')", KEY__timelines: timelines})
            self.assertEqual(HTTPStatus.BAD_REQUEST, caught.exception.response_code)
        self.assertEqual(requests_before, self.pool().get_stats().get("requests_num"))
        self.assertEqual([], self.request({"query": "SELECT note FROM audit"})["rows"])

    def test_autocommit_request_does_not_leak_into_the_next_request(self):
        pid = self.row(self.request({"query": "SELECT pg_backend_pid() AS pid", "autocommit": True}))["pid"]
        result = self.request({"query": {"a": self.PROBE, "b": "SELECT txid_current() AS tx"}, KEY__timelines: {"registration": "2021-01-01"}})
        self.assertEqual(pid, self.row(result["a"])["pid"])
        self.assertEqual(("2021-01-01", "old"), (self.row(result["a"])["moment"], self.row(result["a"])["names"]))
        self.assertEqual(self.row(result["a"])["tx"], self.row(result["b"])["tx"])

    def test_request_without_timelines_is_unchanged(self):
        row = self.row(self.request({"query": self.PROBE}))
        self.assertIn(row["moment"], (None, ""))
        self.assertEqual("new", row["names"])


if __name__ == "__main__":
    unittest.main()
