"""
A request's connection from checkout to putback: a connection lost mid-request (the request is re-run on a fresh connection, never
retried in place behind the caller's back, and never when its own SQL may have committed part of it), how a read_only request's
transaction ends and what the putback thread does with a connection (it never commits a request's work and never keeps a connection
from the pool), and errors raised at COMMIT (answered as the same error raised by a statement; an error whose answer cannot be worked
out still hands the connection back).

    python -m unittest jaaql.test.test_connection_lifecycle

The unit tests need only the package's requirements. TestConnectionLifecycleAgainstPostgres drives the real request path (submit ->
get_required_db -> DBPGInterface -> the jaaql extension -> InterpretJAAQL -> COMMIT -> putback thread) against a scratch Postgres that
has the jaaql extension available (e.g. a container of this repository's image); it runs only when JAAQL_TEST_POSTGRES_URI is set to
postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database jaaql_test_lifecycle and the roles
jaaql_test_lifecycle_user and jaaql_test_lifecycle_other
"""
import json
import os
import queue
import threading
import time
import types
import unittest
from http import HTTPStatus
from unittest import mock

import psycopg
from psycopg.pq import TransactionStatus

from jaaql.db import db_pg_interface
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface_for_db, CONN_LOST__max_attempts
from jaaql.db.db_utils_no_circ import submit
from jaaql.exceptions.http_status_exception import HttpStatusException, ConnectionLostError, JaaqlInterpretableHandledError
from jaaql.interpreter import interpret_jaaql

CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_lifecycle"
TEST_ROLE = "jaaql_test_lifecycle_user"
OTHER_ROLE = "jaaql_test_lifecycle_other"

RESET_STATEMENTS = ["RESET ROLE;", "SELECT jaaql_extension.jaaql__reset_session_authorization('key');", "RESET ALL;"]


class ReturnedConnection:
    # Stands in for a pooled connection handed to the putback thread: records what is done to it, and fails the statement fail_on names
    def __init__(self, status=TransactionStatus.IDLE, fail_on=None):
        self.calls = []
        self.fail_on = fail_on
        self.closed = False
        self.jaaql_reset_key = "key"
        self.info = types.SimpleNamespace(transaction_status=status)

    def _call(self, what):
        self.calls.append(what)
        if self.fail_on is not None and self.fail_on in what:
            raise psycopg.OperationalError("failed: " + what)

    def cursor(self):
        connection = self

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, sql, params=None):
                connection._call(sql)

        return Cursor()

    def rollback(self):
        self._call("rollback")
        self.info.transaction_status = TransactionStatus.IDLE

    def commit(self):
        self._call("commit")

    def close(self):
        self.calls.append("close")
        self.closed = True


class ReturnPool:
    def __init__(self, refuse=False):
        self.returned = []
        self.refuse = refuse

    def putconn(self, conn):
        if self.refuse:
            raise ValueError("can't return connection to pool, it doesn't come from any pool")
        self.returned.append(conn)


class TestPutback(unittest.TestCase):
    USERNAME = "jaaql_test_putback"
    DATABASE = "db"

    def setUp(self):
        self.pool = ReturnPool()
        DBPGInterface.HOST_POOLS[self.USERNAME] = {self.DATABASE: self.pool}

    def tearDown(self):
        DBPGInterface.HOST_POOLS.pop(self.USERNAME, None)

    def put_back(self, conn, do_reset=True):
        DBPGInterface._process_returned_conn(self.USERNAME, self.DATABASE, conn, do_reset)

    def test_what_the_request_left_open_is_rolled_back_not_committed(self):
        for status in [TransactionStatus.INTRANS, TransactionStatus.INERROR]:
            conn = ReturnedConnection(status)
            self.put_back(conn)
            self.assertEqual(["rollback"] + RESET_STATEMENTS + ["commit"], conn.calls, status)
            self.assertEqual([conn], self.pool.returned[-1:])

    def test_a_finished_transaction_is_left_alone(self):
        conn = ReturnedConnection(TransactionStatus.IDLE)
        self.put_back(conn)
        self.assertEqual(RESET_STATEMENTS + ["commit"], conn.calls)
        self.assertEqual([conn], self.pool.returned)
        conn = ReturnedConnection(TransactionStatus.INTRANS)
        self.put_back(conn, do_reset=False)
        self.assertEqual([], conn.calls)
        self.assertEqual(conn, self.pool.returned[-1])

    def test_a_connection_that_cannot_be_reset_is_closed_and_still_returned(self):
        for fail_on in ["rollback", "RESET ROLE", "jaaql__reset_session_authorization", "RESET ALL", "commit"]:
            conn = ReturnedConnection(TransactionStatus.INTRANS, fail_on=fail_on)
            self.put_back(conn)
            self.assertEqual("close", conn.calls[-1], fail_on)
            self.assertTrue(conn.closed, fail_on)
            self.assertIs(conn, self.pool.returned[-1], fail_on)

    def test_a_connection_the_pool_refuses_is_closed(self):
        self.pool.refuse = True
        the_queue = queue.Queue()
        threading.Thread(target=DBPGInterface.put_conn_threaded, args=[self.USERNAME, self.DATABASE, the_queue], daemon=True).start()
        conn = ReturnedConnection()
        the_queue.put((conn, True))
        deadline = time.time() + 5
        while time.time() < deadline and not conn.closed:
            time.sleep(0.01)
        self.assertTrue(conn.closed)


class EndingInterface(DBInterface):
    # Only what ending a request's transaction touches
    def __init__(self, commit_error=None):
        super().__init__(CONFIG, "localhost", "user")
        self.calls = []
        self.commit_error = commit_error

    def get_conn(self):
        raise AssertionError("not used")

    def put_conn(self, conn):
        self.calls.append("put_conn")

    def commit(self, conn):
        self.calls.append("commit")
        if conn.closed:
            raise psycopg.OperationalError("the connection is closed")
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self, conn):
        self.calls.append("rollback")

    def is_connection_closed(self, conn):
        return conn.closed

    def check_dba(self, conn, wait_hook=None):
        raise AssertionError("not used")

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None):
        raise AssertionError("not used")

    def handle_db_error(self, err, echo):
        return HttpStatusException(str(err))

    def close(self):
        pass


class TestEndingTheTransaction(unittest.TestCase):

    def test_a_read_only_request_is_rolled_back(self):
        interface = EndingInterface()
        interface.put_conn_handle_error(types.SimpleNamespace(closed=False), None, skip_commit=True)
        self.assertEqual(["rollback", "put_conn"], interface.calls)

    def test_a_request_is_committed(self):
        interface = EndingInterface()
        interface.put_conn_handle_error(types.SimpleNamespace(closed=False), None)
        self.assertEqual(["commit", "put_conn"], interface.calls)

    def test_a_commit_that_never_reached_the_server_is_retriable(self):
        interface = EndingInterface()
        with self.assertRaises(ConnectionLostError):
            interface.put_conn_handle_error(types.SimpleNamespace(closed=True), None)
        self.assertEqual(["put_conn"], interface.calls)

    def test_a_commit_failure_that_cannot_be_translated_still_returns_the_connection(self):
        class UntranslatableInterface(EndingInterface):
            def translate_commit_error(self, conn, commit_err, error_set=None):
                raise RecursionError("maximum recursion depth exceeded while decoding a JSON array from a unicode string")

        interface = UntranslatableInterface(commit_error=psycopg.errors.ForeignKeyViolation("fk"))
        with self.assertRaises(HttpStatusException) as raised:
            interface.put_conn_handle_error(types.SimpleNamespace(closed=False), None)
        self.assertEqual((HTTPStatus.INTERNAL_SERVER_ERROR, "Commit failed, transaction not persisted: fk"),
                         (raised.exception.response_code, raised.exception.message))
        self.assertEqual(["commit", "put_conn"], interface.calls)


DEEP_JSON = "[" * 100000


class DeepJQ000(psycopg.Error):
    # A JQ000 raise whose JSON payload is nested too deeply for json.loads, which then raises RecursionError, not ValueError
    @property
    def diag(self):
        return types.SimpleNamespace(sqlstate="JQ000", message_primary=DEEP_JSON, table_name=None, column_name=None, constraint_name=None, context=None,
                                     datatype_name=None, message_detail=None, message_hint=None, schema_name=None, severity="ERROR")


class TestCommitErrors(unittest.TestCase):

    def setUp(self):
        self.interface = DBPGInterface(CONFIG, "localhost", 5432, "db", "jaaql_test_commit_errors", password=None)

    def tearDown(self):
        DBPGInterface.HOST_POOLS.pop("jaaql_test_commit_errors", None)
        DBPGInterface.HOST_POOLS_QUEUES.pop("jaaql_test_commit_errors", None)

    def translate(self, error, error_set, closed=False):
        return self.interface.translate_commit_error(types.SimpleNamespace(closed=closed), error, error_set)

    def test_a_refused_commit_maps_as_a_statement_error_would(self):
        from jaaql.exceptions.jaaql_interpretable_handled_errors import UnhandledQueryError, UnhandledProcedureError, DatabaseOperationalError

        query_error = self.translate(psycopg.errors.ForeignKeyViolation("fk"), "query")
        self.assertEqual((UnhandledQueryError, 1004, 422, "query"), (type(query_error), query_error.error_code, query_error.response_code, query_error.set))
        procedure_error = self.translate(psycopg.errors.UniqueViolation("unique"), "_jaaql_procedure")
        self.assertEqual((UnhandledProcedureError, 1005, None), (type(procedure_error), procedure_error.error_code, procedure_error.set))
        operational_error = self.translate(psycopg.errors.SerializationFailure("serialization"), None)
        self.assertEqual((DatabaseOperationalError, 1002, "serialization"), (type(operational_error), operational_error.error_code, operational_error.message))
        self.assertIsNone(self.translate(ValueError("not a database error"), "query"))

    def test_a_commit_lost_in_flight_is_reported_as_of_unknown_outcome(self):
        from jaaql.exceptions.jaaql_interpretable_handled_errors import DatabaseOperationalError

        lost = self.translate(psycopg.errors.AdminShutdown("terminating connection due to administrator command"), "query", closed=True)
        self.assertIsInstance(lost, DatabaseOperationalError)
        self.assertEqual(db_pg_interface.ERR__commit_outcome_unknown + "terminating connection due to administrator command", lost.message)

    def test_an_error_without_sqlstate_still_maps(self):
        from jaaql.exceptions.jaaql_interpretable_handled_errors import handled_error_from_database_error, UnhandledQueryError

        err = handled_error_from_database_error(psycopg.DataError("PostgreSQL text fields cannot contain NUL (0x00) bytes"), "query")
        self.assertIsInstance(err, UnhandledQueryError)
        self.assertEqual((None, None), (err.descriptor["class"], err.descriptor["sqlstate"]))

    def test_a_jq000_payload_too_deep_to_parse_is_answered_not_raised(self):
        from jaaql.exceptions.jaaql_interpretable_handled_errors import handled_procedure_error_from_raise, handled_error_from_database_error, \
            UnhandledQueryError, UnhandledProcedureError

        self.assertRaises(RecursionError, json.loads, DEEP_JSON)
        self.assertIsNone(handled_procedure_error_from_raise(DeepJQ000("deep")))
        statement_error = handled_error_from_database_error(DeepJQ000("deep"), "query")
        self.assertEqual((UnhandledQueryError, 1004, "query", "JQ000"),
                         (type(statement_error), statement_error.error_code, statement_error.set, statement_error.descriptor["sqlstate"]))
        commit_error = self.translate(DeepJQ000("deep"), "_jaaql_procedure")
        self.assertEqual((UnhandledProcedureError, 1005, "JQ000"), (type(commit_error), commit_error.error_code, commit_error.descriptor["sqlstate"]))


class TestStatementsThatMayEndTheTransaction(unittest.TestCase):
    # A request whose own SQL may have committed is never re-run after losing its connection, so this must never answer False for
    # a text that can end the transaction; answering True for one that cannot only costs that request its re-run

    def test_texts_that_may_end_the_transaction(self):
        for query in ["COMMIT", "commit;", "  END WORK", "Rollback", "ABORT", "COMMIT AND CHAIN", "ROLLBACK TO SAVEPOINT s",
                      "PREPARE TRANSACTION 'x'", "prepare /* c */ transaction 'x'", "-- a note\nCOMMIT", "-- a note\rCOMMIT",
                      "/* a /* nested */ still the comment */ COMMIT", "INSERT INTO audit VALUES (1); COMMIT", "INSERT INTO audit VALUES (1); END",
                      "SELECT 1; SELECT 2", "SELECT 'a;b'", "DO $$ BEGIN PERFORM 1; END $$"]:
            self.assertTrue(db_pg_interface._statement_may_end_transaction(query), query)

    def test_texts_that_cannot(self):
        for query in ["SELECT CASE WHEN true THEN 1 END", "INSERT INTO commit_log VALUES (1)", "UPDATE lesson SET ended = true", "SELECT 1;",
                      "SELECT 1 ;;", "-- COMMIT\nSELECT 1", "/* COMMIT */ SELECT 1", "/* a /* COMMIT */ END */ SELECT 1", "PREPARE q AS SELECT 1",
                      "SELECT * FROM \"child.add\"(\n\tpid => %(pid)s )", "/* COMMIT", ""]:
            self.assertFalse(db_pg_interface._statement_may_end_transaction(query), query)


class StubVault:
    def __init__(self, uri):
        self.uri = uri

    def get_obj(self, key):
        return self.uri


def outcome(result_or_error):
    if isinstance(result_or_error, JaaqlInterpretableHandledError):
        return {"type": type(result_or_error).__name__, "status": result_or_error.response_code, "error_code": result_or_error.error_code,
                "set": result_or_error.set, "table_name": result_or_error.table_name, "column_name": result_or_error.column_name,
                "descriptor": {key: result_or_error.descriptor.get(key) for key in ["sqlstate", "constraint_name", "message_primary",
                                                                                     "message_detail", "schema_name"]}
                if isinstance(result_or_error.descriptor, dict) else result_or_error.descriptor}
    if isinstance(result_or_error, HttpStatusException):
        return {"type": type(result_or_error).__name__, "status": int(result_or_error.response_code), "message": result_or_error.message}
    return {"status": 200, "result": result_or_error}


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestConnectionLifecycleAgainstPostgres(unittest.TestCase):
    """
    Each test starts on a fresh pool of four (DBPGInterface.__init__ keeps one checked out, so three serve requests) with every backend
    of the test database terminated. A leaked connection is one the pool counts but never gets back: pool_size - pool_available stays
    above the one __init__ keeps
    """

    @classmethod
    def setUpClass(cls):
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
        cls.pool_user = DBInterface.fracture_uri(uri)[3]
        cls.test_uri = uri.rsplit("/", 1)[0] + "/" + TEST_DATABASE
        with psycopg.connect(uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("CREATE DATABASE " + TEST_DATABASE)
            for role in [TEST_ROLE, OTHER_ROLE]:
                admin.execute("DO $$ BEGIN CREATE ROLE " + role + "; EXCEPTION WHEN duplicate_object THEN NULL; END $$")
        with psycopg.connect(cls.test_uri, autocommit=True) as conn:
            try:
                conn.execute("CREATE SCHEMA jaaql_extension")
                conn.execute("GRANT USAGE ON SCHEMA jaaql_extension TO PUBLIC")
                conn.execute("CREATE EXTENSION jaaql")
            except psycopg.Error as ex:
                raise unittest.SkipTest("the jaaql extension is not available: " + str(ex))
            conn.execute("""
                CREATE TABLE audit (note text);
                CREATE SEQUENCE runs;
                CREATE TABLE parent (id int PRIMARY KEY);
                INSERT INTO parent VALUES (1);
                CREATE TABLE child (pid int CONSTRAINT child_pid_fkey REFERENCES parent (id) DEFERRABLE INITIALLY DEFERRED);
                CREATE TABLE trig (kind text);
                CREATE FUNCTION trig_check() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $f$
                BEGIN
                    IF NEW.kind = 'jq000' THEN
                        RAISE EXCEPTION '[{"table_name": "trig", "message": "handled"}]' USING ERRCODE = 'JQ000';
                    ELSIF NEW.kind = 'deep' THEN
                        RAISE EXCEPTION USING ERRCODE = 'JQ000', MESSAGE = repeat('[', 100000);
                    ELSIF NEW.kind = 'serialization' THEN
                        RAISE EXCEPTION 'could not serialize access' USING ERRCODE = '40001';
                    ELSIF NEW.kind = 'die' THEN
                        PERFORM pg_terminate_backend(pg_backend_pid());
                        PERFORM pg_sleep(5);
                    END IF;
                    RETURN NULL;
                END $f$;
                CREATE CONSTRAINT TRIGGER trig_deferred AFTER INSERT ON trig DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trig_check();
                CREATE FUNCTION "child.add"(pid int) RETURNS TABLE (added int) LANGUAGE sql AS
                    $f$ INSERT INTO child VALUES ("child.add".pid) RETURNING child.pid $f$;
                CREATE FUNCTION "child.add_now"(pid int) RETURNS TABLE (added int) LANGUAGE plpgsql AS $f$
                BEGIN
                    SET CONSTRAINTS child_pid_fkey IMMEDIATE;
                    RETURN QUERY INSERT INTO child VALUES ("child.add_now".pid) RETURNING child.pid;
                END $f$;
                CREATE FUNCTION die_now() RETURNS int LANGUAGE plpgsql SECURITY DEFINER AS $f$
                BEGIN
                    PERFORM pg_terminate_backend(pg_backend_pid());
                    PERFORM pg_sleep(5);
                    RETURN 1;
                END $f$;
                GRANT SELECT, INSERT ON audit, child, trig TO """ + TEST_ROLE + ", " + OTHER_ROLE + """;
                GRANT SELECT ON parent TO """ + TEST_ROLE + ", " + OTHER_ROLE + """;
                GRANT USAGE ON SEQUENCE runs TO """ + TEST_ROLE + ", " + OTHER_ROLE + """;
            """)
        cls.saved_pool_sizes = (db_pg_interface.PGCONN__min_conns, db_pg_interface.PGCONN__max_conns)
        db_pg_interface.PGCONN__min_conns = 4
        db_pg_interface.PGCONN__max_conns = 4
        cls.vault = StubVault(uri)

    @classmethod
    def tearDownClass(cls):
        db_pg_interface.PGCONN__min_conns, db_pg_interface.PGCONN__max_conns = cls.saved_pool_sizes
        cls.drop_pool()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            for role in [TEST_ROLE, OTHER_ROLE]:
                admin.execute("DROP ROLE IF EXISTS " + role)

    @classmethod
    def drop_pool(cls):
        pool = DBPGInterface.HOST_POOLS.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        DBPGInterface.HOST_POOLS_QUEUES.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        if pool is not None:
            pool.close()

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def backends(self, state_like="%"):
        return self.admin("SELECT count(*) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid() AND backend_type = 'client backend' "
                          "AND coalesce(state, '') LIKE %s", (TEST_DATABASE, state_like))[0][0]

    def terminate_backends(self):
        self.admin("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid() "
                   "AND backend_type = 'client backend'", (TEST_DATABASE,))
        deadline = time.time() + 5
        while time.time() < deadline and self.backends() != 0:
            time.sleep(0.05)

    def setUp(self):
        self.settle()
        self.drop_pool()
        self.terminate_backends()
        self.admin("TRUNCATE audit, child, trig")
        self.admin("SELECT setval('runs', 1, false)")

    def pool(self):
        return DBPGInterface.HOST_POOLS[self.pool_user][TEST_DATABASE]

    def settle(self):
        # The putback is asynchronous (queue + thread): wait for the queue to drain and the pool to stop moving
        deadline = time.time() + 8
        last = None
        while time.time() < deadline:
            the_queue = DBPGInterface.HOST_POOLS_QUEUES.get(self.pool_user, {}).get(TEST_DATABASE)
            if the_queue is None:
                return
            stats = self.pool().get_stats()
            now = (the_queue.qsize(), stats.get("pool_size"), stats.get("pool_available"))
            if now == last and now[0] == 0:
                return
            last = now
            time.sleep(0.2)

    def assertNothingLeaked(self):
        deadline = time.time() + 5
        while True:
            self.settle()
            stats = self.pool().get_stats()
            checked_out = stats.get("pool_size", 0) - stats.get("pool_available", 0)
            open_transactions = self.backends("idle in transaction%")
            if (checked_out, open_transactions) == (1, 0) or time.time() > deadline:
                break
            time.sleep(0.2)
        self.assertEqual((1, 0), (checked_out, open_transactions), "connections kept from the pool, backends left in a transaction")

    def request(self, inputs, account=TEST_ROLE, verified=True):
        return outcome(self.answer(inputs, account, verified))

    def answer(self, inputs, account=TEST_ROLE, verified=True):
        # The result, or the error the request answered with
        hook = None
        if verified:
            hook = queue.Queue()
            hook.put((True, None, None))
        inputs = dict({"database": TEST_DATABASE}, **inputs)
        try:
            return submit(self.vault, CONFIG, None, None, inputs, account, hook)
        except (JaaqlInterpretableHandledError, HttpStatusException) as ex:
            return ex
        finally:
            self.settle()

    def rows(self, answer):
        self.assertEqual(200, answer["status"], answer)
        return [dict(zip(answer["result"]["columns"], row)) for row in answer["result"]["rows"]]

    def audit(self):
        return [row[0] for row in self.admin("SELECT note FROM audit ORDER BY note")]

    def executions(self):
        return self.admin("SELECT CASE WHEN is_called THEN last_value ELSE 0 END FROM runs")[0][0]

    def kill_pooled_connections(self):
        self.request({"query": "SELECT 1"})
        self.terminate_backends()

    def identity(self):
        return self.rows(self.request({"query": "SELECT current_user::text AS cur, session_user::text AS ses"}, account=OTHER_ROLE))[0]

    # A connection lost mid-request -------------------------------------------------------------------------------------------------

    def test_dead_pooled_connections_verified_request(self):
        self.kill_pooled_connections()
        started = time.time()
        with mock.patch.object(db_pg_interface, "WAIT_HOOK__timeout", 5):
            answer = self.request({"query": "INSERT INTO audit VALUES ('verified') RETURNING note"})
        self.assertEqual([{"note": "verified"}], self.rows(answer))
        self.assertLess(time.time() - started, 4, "waited for a second verifier verdict")
        self.assertEqual(["verified"], self.audit())
        self.assertNothingLeaked()

    def test_dead_pooled_connections_unverified_request(self):
        self.kill_pooled_connections()
        self.assertEqual([{"note": "unverified"}], self.rows(self.request({"query": "INSERT INTO audit VALUES ('unverified') RETURNING note"},
                                                                         verified=False)))
        self.assertEqual(["unverified"], self.audit())
        self.assertNothingLeaked()

    def test_connection_lost_between_statements_reruns_the_whole_request_once(self):
        self.request({"query": "SELECT 1"})

        def terminate_the_sleeper():
            deadline = time.time() + 10
            while time.time() < deadline:
                pids = self.admin("SELECT pid FROM pg_stat_activity WHERE datname = %s AND state = 'active' AND query LIKE %s "
                                  "AND pid <> pg_backend_pid()", (TEST_DATABASE, "%pg_sleep(1.1)%"))
                if pids:
                    self.admin("SELECT pg_terminate_backend(%s)", (pids[0][0],))
                    return
                time.sleep(0.02)

        killer = threading.Thread(target=terminate_the_sleeper)
        killer.start()
        with mock.patch.object(db_pg_interface, "WAIT_HOOK__timeout", 5):
            answer = self.request({"query": {"a": "INSERT INTO audit VALUES ('a') RETURNING note", "b": "SELECT pg_sleep(1.1)::text AS slept",
                                             "c": "INSERT INTO audit VALUES ('c') RETURNING note"}})
        killer.join()
        self.assertEqual(200, answer["status"], answer)
        self.assertEqual(["a", "c"], self.audit())
        self.assertNothingLeaked()
        self.assertEqual({"cur": OTHER_ROLE, "ses": OTHER_ROLE}, self.identity())

    def test_reruns_are_bounded(self):
        self.request({"query": "SELECT 1"})
        with mock.patch.object(db_pg_interface, "WAIT_HOOK__timeout", 5):
            answer = self.request({"query": "SELECT nextval('runs') AS run, die_now() AS died"})
        self.assertEqual(("ConnectionLostError", 500), (answer.get("type"), answer["status"]), answer)
        self.assertEqual(CONN_LOST__max_attempts, self.executions())
        self.assertNothingLeaked()

    def test_a_request_whose_own_sql_committed_is_not_rerun(self):
        # The loss comes after the request's own COMMIT: a re-run would apply the committed part again
        self.request({"query": "SELECT 1"})
        with mock.patch.object(db_pg_interface, "WAIT_HOOK__timeout", 5):
            in_one_string = self.answer({"query": "INSERT INTO audit VALUES ('string'); COMMIT; SELECT die_now()"})
            as_a_query_set = self.answer({"query": {"a": "INSERT INTO audit VALUES ('set') RETURNING note", "b": "COMMIT",
                                                    "c": "SELECT die_now() AS died"}})
        for answer in [in_one_string, as_a_query_set]:
            self.assertEqual(("DatabaseOperationalError", 1002), (type(answer).__name__, getattr(answer, "error_code", None)), outcome(answer))
            self.assertTrue(answer.message.startswith(interpret_jaaql.ERR__connection_lost_outcome_unknown), answer.message)
        self.assertEqual(["set", "string"], self.audit())
        self.assertNothingLeaked()
        self.assertEqual({"cur": OTHER_ROLE, "ses": OTHER_ROLE}, self.identity())

    def test_an_autocommit_request_is_not_rerun(self):
        self.kill_pooled_connections()
        answer = self.request({"query": "SELECT nextval('runs') AS run", "autocommit": True}, verified=False)
        self.assertEqual(("DatabaseOperationalError", 1002), (answer.get("type"), answer.get("error_code")), answer)
        self.assertEqual(0, self.executions())
        self.assertNothingLeaked()

    # read_only and the putback ------------------------------------------------------------------------------------------------------

    def test_read_only_writes_are_not_persisted(self):
        self.assertEqual([{"note": "read only"}], self.rows(self.request({"query": "INSERT INTO audit VALUES ('read only') RETURNING note",
                                                                          "read_only": True})))
        self.assertEqual([], self.audit())
        self.assertNothingLeaked()
        self.assertEqual({"cur": OTHER_ROLE, "ses": OTHER_ROLE}, self.identity())

    def test_read_only_failures_and_deferred_violations_leak_nothing(self):
        failed = self.request({"query": {"a": "INSERT INTO audit VALUES ('failed') RETURNING note", "b": "SELECT 1 / 0 AS boom"}, "read_only": True})
        self.assertEqual(("UnhandledQueryError", "b"), (failed.get("type"), failed.get("set")), failed)
        self.assertNothingLeaked()
        # Nothing commits, so the deferred check never runs: the request answers, and nothing persists
        self.assertEqual([{"pid": 99}], self.rows(self.request({"query": "INSERT INTO child VALUES (99) RETURNING pid", "read_only": True})))
        self.assertEqual(200, self.request({"query": {"_jaaql_procedure": "SELECT * FROM \"child.add\"(\n\tpid => :pid )"}, "parameters": {"pid": 99},
                                            "read_only": True})["status"])
        self.assertEqual([(0,)], self.admin("SELECT count(*) FROM child"))
        self.assertEqual([], self.audit())
        self.assertNothingLeaked()
        self.assertEqual({"cur": OTHER_ROLE, "ses": OTHER_ROLE}, self.identity())

    def test_a_connection_the_putback_cannot_reset_is_discarded_not_leaked(self):
        self.request({"query": "SELECT 1"})
        interface = create_interface_for_db(self.vault, CONFIG, TEST_ROLE, TEST_DATABASE)
        conn = interface.get_conn()
        interface.execute_query(conn, "SELECT 1")
        interface.commit(conn)
        returns_bad = self.pool().get_stats().get("returns_bad", 0)
        self.admin("SELECT pg_terminate_backend(%s)", (conn.info.backend_pid,))
        time.sleep(0.2)
        interface.put_conn(conn)
        self.assertNothingLeaked()
        self.assertEqual(returns_bad + 1, self.pool().get_stats().get("returns_bad", 0))
        self.assertEqual({"cur": OTHER_ROLE, "ses": OTHER_ROLE}, self.identity())

    # Errors raised at COMMIT ----------------------------------------------------------------------------------------------------------

    def test_submit_deferred_violation_at_commit_answers_as_mid_statement(self):
        at_commit = self.request({"query": "INSERT INTO child VALUES (99)"})
        mid_statement = self.request({"query": "SET CONSTRAINTS ALL IMMEDIATE; INSERT INTO child VALUES (99)"})
        self.assertEqual(mid_statement, at_commit)
        self.assertEqual(("UnhandledQueryError", 422, 1004, "query", "child", "23503", "child_pid_fkey"),
                         (at_commit.get("type"), at_commit["status"], at_commit.get("error_code"), at_commit.get("set"), at_commit.get("table_name"),
                          at_commit["descriptor"]["sqlstate"], at_commit["descriptor"]["constraint_name"]))
        self.assertNothingLeaked()

    def test_call_proc_deferred_violation_at_commit_answers_as_mid_statement(self):
        at_commit = self.request({"query": {"_jaaql_procedure": "SELECT * FROM \"child.add\"(\n\tpid => :pid )"}, "parameters": {"pid": 99}})
        mid_statement = self.request({"query": {"_jaaql_procedure": "SELECT * FROM \"child.add_now\"(\n\tpid => :pid )"}, "parameters": {"pid": 99}})
        self.assertEqual(mid_statement, at_commit)
        self.assertEqual(("UnhandledProcedureError", 422, 1005, None, "23503"),
                         (at_commit.get("type"), at_commit["status"], at_commit.get("error_code"), at_commit.get("set"), at_commit["descriptor"]["sqlstate"]))
        self.assertEqual([], self.admin("SELECT pid FROM child"))
        self.assertNothingLeaked()

    def test_commit_error_is_attributed_to_the_only_query_set(self):
        self.assertEqual("a", self.request({"query": {"a": "INSERT INTO child VALUES (99)"}}).get("set"))
        self.assertEqual("a", self.request({"query": {"s": "SET CONSTRAINTS ALL IMMEDIATE", "a": "INSERT INTO child VALUES (99)"}}).get("set"))
        several = self.request({"query": {"a": "INSERT INTO child VALUES (99)", "b": "SELECT 1 AS one"}})
        self.assertEqual(("UnhandledQueryError", None), (several.get("type"), several.get("set")), several)

    def test_jq000_at_commit_is_unchanged(self):
        answer = self.request({"query": "INSERT INTO trig VALUES ('jq000')"})
        self.assertEqual(("HandledProcedureError", 1003, [{"table_name": "trig", "message": "handled"}]),
                         (answer.get("type"), answer.get("error_code"), answer.get("descriptor")))

    def test_operational_error_refused_at_commit_is_answered_not_rerun(self):
        at_commit = self.request({"query": "SELECT nextval('runs') AS run; INSERT INTO trig VALUES ('serialization')"})
        self.assertEqual(1, self.executions())
        mid_statement = self.request({"query": "SET CONSTRAINTS ALL IMMEDIATE; INSERT INTO trig VALUES ('serialization')"})
        self.assertEqual(mid_statement, at_commit)
        self.assertEqual(("DatabaseOperationalError", 1002, "40001"), (at_commit.get("type"), at_commit.get("error_code"), at_commit["descriptor"]["sqlstate"]))
        self.assertNothingLeaked()

    def test_connection_lost_during_commit_is_reported_not_rerun(self):
        self.request({"query": "SELECT 1"})
        with mock.patch.object(db_pg_interface, "WAIT_HOOK__timeout", 5):
            answer = self.request({"query": "SELECT nextval('runs') AS run; INSERT INTO trig VALUES ('die'); INSERT INTO audit VALUES ('lost')"})
        self.assertEqual(("DatabaseOperationalError", 1002), (answer.get("type"), answer.get("error_code")), answer)
        self.assertEqual(1, self.executions())
        self.assertEqual([], self.audit())
        self.assertNothingLeaked()

    def test_client_side_error_without_sqlstate_is_answered_and_leaks_nothing(self):
        answer = self.request({"query": "SELECT :v AS v", "parameters": {"v": "a\u0000b"}})
        self.assertEqual(("UnhandledQueryError", 1004, None), (answer.get("type"), answer.get("error_code"), answer["descriptor"]["sqlstate"]))
        self.assertNothingLeaked()

    def test_a_jq000_payload_too_deep_to_parse_is_answered_and_leaks_nothing(self):
        for _ in range(3):
            at_commit = self.request({"query": "INSERT INTO trig VALUES ('deep')"})
            mid_statement = self.request({"query": "SET CONSTRAINTS ALL IMMEDIATE; INSERT INTO trig VALUES ('deep')"})
            self.assertEqual(mid_statement, at_commit)
            self.assertEqual(("UnhandledQueryError", 1004, "JQ000"), (at_commit.get("type"), at_commit.get("error_code"), at_commit["descriptor"]["sqlstate"]))
        self.assertNothingLeaked()

    def test_an_answer_that_cannot_be_worked_out_still_returns_the_connection(self):
        failing = mock.Mock(side_effect=RecursionError("maximum recursion depth exceeded"))
        with mock.patch.object(interpret_jaaql, "handled_error_from_database_error", failing):
            mid_statement = self.request({"query": "SELECT 1 / 0 AS boom"})
        self.assertEqual((422, "division by zero"), (mid_statement["status"], mid_statement.get("message")), mid_statement)
        with mock.patch.object(DBPGInterface, "translate_commit_error", failing):
            at_commit = self.request({"query": "INSERT INTO child VALUES (99)"})
        self.assertEqual(500, at_commit["status"], at_commit)
        self.assertTrue(at_commit["message"].startswith("Commit failed, transaction not persisted: "), at_commit)
        self.assertEqual(2, failing.call_count)
        self.assertNothingLeaked()


if __name__ == "__main__":
    unittest.main()
