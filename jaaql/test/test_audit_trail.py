"""
The audit trail of record changes (jaaql/scripts/audit_trail.sql) that JAAQL installs into every application database: who changed
which row of which table, when, with the old and new values; secret columns withheld (and hashed in a key); COPY loads and a migration's reload summarised;
the history of erased rows deleted; records purged after keep_changes and rows after their retention rule; none of it readable or
writable by an application user; and nothing a table owner adds running as a superuser inside it.

    python -m unittest jaaql.test.test_audit_trail

TestSubmitRules needs nothing. TestAuditTrail runs only when JAAQL_TEST_POSTGRES_URI is set to
postgresql://<superuser>:<password>@<host>:<port>/<database> (a server from this image, reached by its address, not localhost) and
creates, then drops, the database jaaql_test_audit and the roles jaaql_test_audit_alice and jaaql_test_audit_bob (and dba when the
server has none). All data here is synthetic
"""
import os
import re
import time
import unittest
from os.path import dirname, join

import psycopg

from jaaql.interpreter.interpret_jaaql import REGEX_query_argument

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_audit"
ALICE = "jaaql_test_audit_alice"
BOB = "jaaql_test_audit_bob"
AUDIT_TRAIL_SQL = join(dirname(dirname(__file__)), "scripts", "audit_trail.sql")

SCHEMA = """
CREATE DOMAIN encrypted__thing AS varchar(200);
CREATE TABLE person (id serial PRIMARY KEY, name text NOT NULL, email text, password_hash text, ssn encrypted__thing);
CREATE TABLE lesson (id serial PRIMARY KEY, person integer REFERENCES person ON DELETE CASCADE, at date, note text);
CREATE TABLE booking_note (id serial PRIMARY KEY, person integer REFERENCES person ON DELETE SET NULL, note text);
CREATE TABLE pair (a integer, b text, v text, PRIMARY KEY (a, b));
CREATE TABLE loose (a integer, b text);
CREATE TABLE service (code varchar(24) PRIMARY KEY, caption text);
CREATE TABLE error_report (id serial PRIMARY KEY, created timestamptz NOT NULL DEFAULT now(), message text);
CREATE TABLE alert (id serial PRIMARY KEY, error integer REFERENCES error_report ON DELETE RESTRICT, created timestamptz NOT NULL DEFAULT now());
CREATE TABLE shadow (id serial PRIMARY KEY, n integer, o integer, x integer, j integer, s integer, p integer, d integer, e integer, k integer, w integer);
CREATE TABLE session_token (token text PRIMARY KEY, user_name text);
CREATE TABLE bulk (id integer PRIMARY KEY, v text, w integer);
CREATE TABLE swap (id integer, v text, PRIMARY KEY (id) DEFERRABLE INITIALLY IMMEDIATE);
GRANT USAGE ON SCHEMA public TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public TO PUBLIC;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO PUBLIC;
"""
TABLES = "person, lesson, booking_note, pair, loose, service, error_report, alert, shadow, session_token, bulk, swap"


def _uri_for(database):
    uri = os.environ[ENVIRON__test_postgres_uri]
    return uri.rsplit("/", 1)[0] + "/" + database


class TestSubmitRules(unittest.TestCase):
    """The file also goes through JAAQL /submit (a .jaaql migration file), so it must hold no parameter-like text outside quotes,
    an even number of apostrophes, and no line that the monitor reads as a command"""

    def test_file_passes_submit_and_monitor_rules(self):
        with open(AUDIT_TRAIL_SQL, encoding="utf-8", newline="") as file:
            text = file.read()
        self.assertNotIn("\r", text)
        self.assertEqual(text.count("'") % 2, 0)
        params = [m.group(0) for m in re.finditer(REGEX_query_argument, text) if m.start() == 0 or text[m.start() - 1] != ":"]
        self.assertEqual(params, [])
        self.assertNotIn("#'", text)
        for line in text.split("\n"):
            self.assertFalse(line.startswith(chr(92)), line)
            self.assertFalse(line.upper().startswith("WITH USER"), line)


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), ENVIRON__test_postgres_uri + " is not set")
class TestAuditTrail(unittest.TestCase):
    created_dba = False

    @classmethod
    def setUpClass(cls):
        with psycopg.connect(os.environ[ENVIRON__test_postgres_uri], autocommit=True) as conn:
            conn.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            for role in (ALICE, BOB):
                conn.execute("DROP ROLE IF EXISTS " + role)
                conn.execute("CREATE ROLE " + role)
            if conn.execute("SELECT count(*) FROM pg_roles WHERE rolname = 'dba'").fetchone()[0] == 0:
                conn.execute("CREATE ROLE dba")
                cls.created_dba = True
            conn.execute("CREATE DATABASE " + TEST_DATABASE)
        cls.conn = psycopg.connect(_uri_for(TEST_DATABASE), autocommit=True)
        cls.conn.execute(SCHEMA)
        cls.install()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        with psycopg.connect(os.environ[ENVIRON__test_postgres_uri], autocommit=True) as conn:
            conn.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            for role in (ALICE, BOB):
                conn.execute("DROP ROLE IF EXISTS " + role)
            if cls.created_dba:
                conn.execute("DROP ROLE IF EXISTS dba")

    @classmethod
    def install(cls):
        with open(AUDIT_TRAIL_SQL, encoding="utf-8") as file:
            cls.conn.execute(file.read())

    def setUp(self):
        self.conn.execute("RESET SESSION AUTHORIZATION")
        self.conn.execute("TRUNCATE " + TABLES + " RESTART IDENTITY CASCADE")
        self.conn.execute("DELETE FROM audit.record_change")
        self.conn.execute("DELETE FROM audit.erasure")

    def as_role(self, role, sql, params=None):
        self.conn.execute("SET SESSION AUTHORIZATION " + role)
        try:
            return self.conn.execute(sql, params)
        finally:
            self.conn.execute("RESET SESSION AUTHORIZATION")

    def changes(self, table=None):
        sql = "SELECT actor, table_name, operation, row_key, old_values, new_values FROM audit.record_change"
        if table:
            sql += " WHERE table_name = 'public." + table + "'"
        return self.conn.execute(sql + " ORDER BY id").fetchall()

    def everything(self):
        return str(self.conn.execute("SELECT array_agg(R) FROM audit.record_change R").fetchone()[0])

    def test_who_changed_what(self):
        self.as_role(ALICE, "INSERT INTO person (name, email, password_hash, ssn) VALUES ('P One', 'one@example.test', 'x', 'y')")
        self.as_role(BOB, "UPDATE person SET name = 'P Uno', password_hash = 'z' WHERE id = 1")
        self.as_role(ALICE, "INSERT INTO lesson (person, at) VALUES (1, '2026-01-05')")
        self.as_role(BOB, "DELETE FROM lesson WHERE id = 1")
        self.assertEqual(self.changes(), [
            (ALICE, "public.person", "INSERT", {"id": 1}, None,
             {"id": 1, "name": "P One", "email": "one@example.test", "password_hash": "(withheld)", "ssn": "(withheld)"}),
            (BOB, "public.person", "UPDATE", {"id": 1}, {"name": "P One", "password_hash": "(withheld)"},
             {"name": "P Uno", "password_hash": "(withheld)"}),
            (ALICE, "public.lesson", "INSERT", {"id": 1}, None, {"id": 1, "person": 1, "at": "2026-01-05", "note": None}),
            (BOB, "public.lesson", "DELETE", {"id": 1}, {"id": 1, "person": 1, "at": "2026-01-05", "note": None}, None),
        ])

    def test_secret_values_are_never_copied(self):
        self.as_role(ALICE, "INSERT INTO person (name, password_hash, ssn) VALUES ('P', 'secret-value-1', 'secret-value-2')")
        self.as_role(ALICE, "UPDATE person SET password_hash = 'secret-value-3'")
        self.as_role(ALICE, "DELETE FROM person")
        self.assertNotIn("secret-value", self.everything())
        self.assertEqual(len(self.changes()), 3)

    def test_a_secret_primary_key_is_hashed_and_erasure_still_finds_it(self):
        self.as_role(ALICE, "INSERT INTO session_token VALUES ('tok-secret-1', 'u1'), ('tok-secret-2', 'u2')")
        self.as_role(ALICE, "UPDATE session_token SET user_name = 'u1b' WHERE token = 'tok-secret-1'")
        self.assertNotIn("tok-secret", self.everything())
        keys = [c[3]["token"] for c in self.changes("session_token")]
        self.assertTrue(all(k.startswith("(withheld ") for k in keys), keys)
        self.assertEqual(keys[0], keys[2])
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('test')")
            self.conn.execute("DELETE FROM session_token WHERE token = 'tok-secret-1'")
        self.assertEqual([c[2] for c in self.changes("session_token")], ["INSERT", "ERASE"])

    def test_columns_named_like_the_trigger_aliases(self):
        self.as_role(ALICE, "INSERT INTO shadow (n, o, x, j, s, p, d, e, k, w) VALUES (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)")
        self.as_role(ALICE, "UPDATE shadow SET x = 30, n = 10")
        self.as_role(ALICE, "DELETE FROM shadow")
        rows = self.changes("shadow")
        self.assertEqual([c[2] for c in rows], ["INSERT", "UPDATE", "DELETE"])
        self.assertEqual(rows[1][4:], ({"n": 1, "x": 3}, {"n": 10, "x": 30}))
        self.assertEqual(rows[2][4]["o"], 2)

    def test_update_that_changes_nothing_is_not_recorded(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        self.as_role(BOB, "UPDATE person SET name = name")
        self.assertEqual([c[2] for c in self.changes()], ["INSERT"])

    def test_primary_key_change_and_composite_key(self):
        self.as_role(ALICE, "INSERT INTO service VALUES ('1op1', 'One to one')")
        self.as_role(ALICE, "UPDATE service SET code = '1-op-1' WHERE code = '1op1'")
        self.as_role(ALICE, "INSERT INTO pair VALUES (1, 'x', 'v1'), (2, 'y', 'v2')")
        self.as_role(BOB, "UPDATE pair SET v = v || '!'")
        self.assertEqual(self.changes("service")[1][3:], ({"code": "1-op-1"}, {"code": "1op1"}, {"code": "1-op-1"}))
        self.assertEqual(sorted((c[3:] for c in self.changes("pair") if c[2] == "UPDATE"), key=str), sorted([
            ({"a": 1, "b": "x"}, {"v": "v1"}, {"v": "v1!"}), ({"a": 2, "b": "y"}, {"v": "v2"}, {"v": "v2!"})], key=str))

    def test_keys_that_move_between_rows_are_paired_with_their_own_row(self):
        self.as_role(ALICE, "INSERT INTO swap VALUES (1, 'row-a'), (2, 'row-b')")
        self.as_role(ALICE, "UPDATE swap SET id = 3 - id")
        self.assertEqual(sorted((c[3:] for c in self.changes("swap") if c[2] == "UPDATE"), key=str), sorted([
            ({"id": 2}, {"id": 1}, {"id": 2}), ({"id": 1}, {"id": 2}, {"id": 1})], key=str))
        self.as_role(ALICE, "UPDATE swap SET id = id + 10")
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('test')")
            self.conn.execute("DELETE FROM swap WHERE v = 'row-a'")
        self.assertNotIn("row-a", self.everything())
        self.assertIn("row-b", self.everything())

    def test_a_bulk_update_stays_linear_on_a_warm_connection(self):
        self.conn.execute("INSERT INTO bulk SELECT i, 'v' || i, 0 FROM generate_series(1, 8000) i")
        for i in range(12):
            self.as_role(ALICE, "UPDATE bulk SET w = w + 1 WHERE id = %s", (i + 1,))
        started = time.perf_counter()
        self.as_role(ALICE, "UPDATE bulk SET w = w + 1")
        took = time.perf_counter() - started
        self.assertEqual(self.conn.execute("SELECT count(*) FROM audit.record_change WHERE table_name = 'public.bulk' AND operation = 'UPDATE'").fetchone()[0],
                         8012)
        self.assertLess(took, 5.0)

    def test_table_without_a_key(self):
        self.as_role(ALICE, "INSERT INTO loose VALUES (1, 'x'), (2, 'y')")
        self.as_role(ALICE, "UPDATE loose SET b = 'z' WHERE a = 1")
        self.as_role(ALICE, "UPDATE loose SET b = 'w'")
        updates = [c[3:] for c in self.changes("loose") if c[2] == "UPDATE"]
        self.assertEqual(sorted(updates, key=str), sorted([(None, {"b": "x"}, {"b": "z"}), (None, {"b": "z"}, {"b": "w"}),
                                                           (None, {"b": "y"}, {"b": "w"})], key=str))

    def test_copy_by_an_installer_is_one_load_row_and_by_a_user_is_itemised(self):
        with self.conn.cursor().copy("COPY person (name) FROM STDIN") as copy:
            for i in range(250):
                copy.write_row(("P%d" % i,))
        self.conn.execute("SET SESSION AUTHORIZATION " + ALICE)
        try:
            with self.conn.cursor().copy("COPY service (code) FROM STDIN") as copy:
                copy.write_row(("2op2",))
                copy.write_row(("3op3",))
        finally:
            self.conn.execute("RESET SESSION AUTHORIZATION")
        self.assertEqual(self.changes("person"), [(self.conn.info.user, "public.person", "LOAD", None, None, {"rows": 250})])
        self.assertEqual([c[2:4] for c in self.changes("service")], [("INSERT", {"code": "2op2"}), ("INSERT", {"code": "3op3"})])

    def test_the_reload_of_a_migration_is_one_load_row_and_an_erasure_still_reaches_back_past_it(self):
        # what FIESTA's migrate.dynamic_data.01.pre-wipe and 02.post-structure do, as dba: save every row in migration.*_json,
        # drop public, re-create the model, put the rows back with INSERT ... SELECT from migration.*_json
        self.as_role(ALICE, "INSERT INTO person (name, email) VALUES ('Before Reload', 'before@example.test'), ('Stays', NULL)")
        self.as_role(BOB, "UPDATE person SET name = 'Before Reload 2' WHERE id = 1")
        self.as_role(ALICE, "INSERT INTO lesson (person, at, note) VALUES (1, '2026-01-05', 'lesson before reload'), (2, '2026-01-05', NULL)")
        try:
            self.conn.execute("CREATE SCHEMA migration")
            self.conn.execute("CREATE TABLE migration.person_json AS SELECT to_jsonb(P.*) AS row_json FROM public.person P")
            self.conn.execute("CREATE TABLE migration.lesson_json AS SELECT to_jsonb(L.*) AS row_json FROM public.lesson L")
            self.conn.execute("DROP SCHEMA public CASCADE")
            self.conn.execute("CREATE SCHEMA public")
            self.conn.execute(SCHEMA)
            self.conn.execute("""DO $post$
BEGIN
    insert into public.person (id, name, email)
    select (row_json->>'id')::integer, row_json->>'name', row_json->>'email'
    from migration.person_json;
    insert into public.lesson (id, person, at, note)
    select (row_json->>'id')::integer, (row_json->>'person')::integer, (row_json->>'at')::date, row_json->>'note'
    from migration.lesson_json;
END $post$""")
        finally:
            self.conn.execute("DROP SCHEMA IF EXISTS migration CASCADE")
        self.conn.execute("SELECT setval('person_id_seq', 2)")
        self.assertEqual([c[1:] for c in self.changes() if c[0] == self.conn.info.user], [
            ("public.person", "LOAD", None, None, {"rows": 2}), ("public.lesson", "LOAD", None, None, {"rows": 2})])
        self.as_role(BOB, "UPDATE person SET name = 'After Reload' WHERE id = 1")
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('erasure request E-3')")
            self.conn.execute("DELETE FROM person WHERE id = 1")
        everything = self.everything()
        for gone in ("Before Reload", "before@example.test", "After Reload", "lesson before reload"):
            self.assertNotIn(gone, everything)
        self.assertIn("Stays", everything)

    def test_an_insert_from_migration_tables_is_itemised_unless_an_installer_reloads(self):
        try:
            self.conn.execute("CREATE SCHEMA migration")
            self.conn.execute("CREATE TABLE migration.person_json AS SELECT jsonb_build_object('name', 'From JSON') AS row_json")
            self.conn.execute("GRANT USAGE ON SCHEMA migration TO PUBLIC")
            self.conn.execute("GRANT SELECT ON migration.person_json TO PUBLIC")
            self.as_role(ALICE, "INSERT INTO person (name) SELECT row_json->>'name' FROM migration.person_json")
        finally:
            self.conn.execute("DROP SCHEMA IF EXISTS migration CASCADE")
        self.conn.execute("INSERT INTO service VALUES ('fix', 'a fix by an operator')")
        self.assertEqual([c[:3] for c in self.changes()], [
            (ALICE, "public.person", "INSERT"), (self.conn.info.user, "public.service", "INSERT")])

    def test_erasure_deletes_the_history_of_the_row_and_of_what_cascades(self):
        self.as_role(ALICE, "INSERT INTO person (name, email) VALUES ('Erase Me', 'erase@example.test'), ('Keep Me', 'keep@example.test')")
        self.as_role(ALICE, "INSERT INTO lesson (person, at) VALUES (1, '2026-01-05'), (1, '2026-01-12'), (2, '2026-01-05')")
        self.as_role(BOB, "UPDATE person SET email = 'erase2@example.test' WHERE id = 1")
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('erasure request E-1')")
            self.conn.execute("DELETE FROM person WHERE id = 1")
        everything = self.everything()
        self.assertNotIn("Erase Me", everything)
        self.assertNotIn("erase", everything)
        self.assertIn("Keep Me", everything)
        self.assertEqual(sorted((c[1], c[2], c[3], c[4], c[5]) for c in self.changes() if c[2] == "ERASE"), sorted([
            ("public.person", "ERASE", None, None, None), ("public.lesson", "ERASE", None, None, None),
            ("public.lesson", "ERASE", None, None, None)]))
        self.assertEqual(self.conn.execute("SELECT reason FROM audit.erasure").fetchall(), [("erasure request E-1",)])
        self.assertEqual(len([c for c in self.changes("lesson") if c[2] == "INSERT"]), 1)

    def test_erasure_by_pseudonymising_in_place(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('Real Name')")
        self.as_role(BOB, "UPDATE person SET name = 'Real Name 2'")
        with self.assertRaises(psycopg.errors.RaiseException):
            self.conn.execute("SELECT audit.forget_record('public.person', '{\"id\": 1}')")
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('erasure request E-2')")
            self.conn.execute("UPDATE person SET name = 'Erased person 1'")
            self.conn.execute("SELECT audit.forget_record('public.person', '{\"id\": 1}')")
        self.assertEqual(self.changes(), [(self.conn.info.user, "public.person", "ERASE", {"id": 1}, None, {"name": "Erased person 1"})])

    def test_an_erasure_keeps_the_history_of_rows_that_stay(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('Leaver')")
        self.as_role(ALICE, "INSERT INTO booking_note (person, note) VALUES (1, 'cancelled by the leaver')")
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('erasure request E-4')")
            self.conn.execute("DELETE FROM person")
        notes = self.changes("booking_note")
        self.assertEqual([c[2] for c in notes], ["INSERT", "ERASE"])
        self.assertEqual(notes[1][4:], (None, {"person": None}))

    def test_erasure_follows_a_primary_key_change(self):
        self.as_role(ALICE, "INSERT INTO service VALUES ('old', 'Old caption')")
        self.as_role(ALICE, "UPDATE service SET code = 'new'")
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('erasure request E-3')")
            self.conn.execute("DELETE FROM service")
        self.assertEqual([c[2] for c in self.changes()], ["ERASE"])

    def test_forget_actor(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        self.as_role(BOB, "UPDATE person SET name = 'Q'")
        self.assertEqual(self.conn.execute("SELECT audit.forget_actor(%s)", (ALICE,)).fetchone()[0], 1)
        actors = [c[0] for c in self.changes()]
        self.assertTrue(actors[0].startswith("erased-"))
        self.assertEqual(actors[1], BOB)
        self.as_role(ALICE, "UPDATE person SET name = 'R'")
        self.conn.execute("SELECT audit.forget_actor(%s)", (ALICE,))
        self.assertEqual(self.changes()[2][0], actors[0])

    def test_purge_after_keep_changes_and_retention_rules(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('Old'), ('New')")
        self.conn.execute("UPDATE audit.record_change SET changed_at = now() - interval '24 months 1 day' WHERE row_key = '{\"id\": 1}'")
        self.conn.execute("INSERT INTO audit.retention_rule VALUES ('public.error_report', 'created', interval '180 days', 'test')")
        try:
            self.as_role(ALICE, "INSERT INTO error_report (created, message) VALUES (now() - interval '181 days', 'old'), (now(), 'new')")
            purged = self.as_role("dba", "SELECT audit.purge_expired()").fetchone()[0]
            self.assertEqual(purged, 2)
            self.assertEqual(self.conn.execute("SELECT message FROM error_report").fetchall(), [("new",)])
            self.assertEqual([(c[1], c[2], c[3]) for c in self.changes()], [
                ("public.person", "INSERT", {"id": 2}), ("public.error_report", "INSERT", {"id": 2}),
                ("public.error_report", "ERASE", None)])
            self.assertEqual(self.conn.execute("SELECT last_purge_rows, last_purge_errors FROM audit.setting").fetchone(), (2, None))
        finally:
            self.conn.execute("DELETE FROM audit.retention_rule")

    def test_a_failing_retention_rule_does_not_stop_the_purge(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('Old')")
        self.conn.execute("UPDATE audit.record_change SET changed_at = now() - interval '25 months'")
        self.conn.execute("INSERT INTO error_report (created, message) VALUES (now() - interval '200 days', 'old, still alerted'), "
                          "(now() - interval '200 days', 'old')")
        self.conn.execute("INSERT INTO alert (error, created) VALUES (1, now())")
        self.conn.execute("INSERT INTO audit.retention_rule VALUES ('public.alert', 'created', interval '180 days', 'test'), "
                          "('public.error_report', 'created', interval '180 days', 'test')")
        try:
            purged = self.as_role("dba", "SELECT audit.purge_expired()").fetchone()[0]
            self.assertEqual(purged, 2)
            self.assertEqual(self.conn.execute("SELECT message FROM error_report").fetchall(), [("old, still alerted",)])
            errors = self.conn.execute("SELECT last_purge_errors FROM audit.setting").fetchone()[0]
            self.assertIn("public.error_report: 1 expired rows kept", errors)
        finally:
            self.conn.execute("DELETE FROM audit.retention_rule")

    def test_retention_rules_are_checked(self):
        for values in ("('audit.record_change', 'changed_at', interval '1 day', 'x')", "('public.person', 'name', interval '1 day', 'x')",
                       "('public.nothing', 'created', interval '1 day', 'x')"):
            with self.subTest(values=values):
                with self.assertRaises(psycopg.errors.RaiseException):
                    self.as_role("dba", "INSERT INTO audit.retention_rule VALUES " + values)

    def test_users_can_neither_read_nor_change_the_log(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        for sql in ("SELECT * FROM audit.record_change", "DELETE FROM audit.record_change",
                    "UPDATE audit.record_change SET actor = 'x'", "SELECT audit.begin_erasure('x')",
                    "SELECT audit.purge_expired()", "SELECT audit.purge_log()", "SELECT audit.forget_record('public.person', '{}')",
                    "INSERT INTO audit.excluded_table VALUES ('public.person', 'x')"):
            with self.subTest(sql=sql):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.as_role(ALICE, sql)
        self.assertEqual(len(self.changes()), 1)

    def test_dba_reads_the_log_and_sets_exclusions_but_cannot_change_it(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        self.assertEqual(self.as_role("dba", "SELECT count(*) FROM audit.record_change").fetchone()[0], 1)
        self.as_role("dba", "SELECT count(*) FROM audit.coverage")
        for sql in ("DELETE FROM audit.record_change", "SELECT * FROM audit.secret"):
            with self.subTest(sql=sql):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.as_role("dba", sql)

    def test_nothing_runs_as_a_superuser_inside_the_trigger(self):
        self.conn.execute("CREATE TYPE mood AS ENUM ('happy')")
        self.conn.execute("CREATE FUNCTION mood_to_json(mood) RETURNS json LANGUAGE sql AS $$ SELECT to_json(current_user::text) $$")
        self.conn.execute("CREATE CAST (mood AS json) WITH FUNCTION mood_to_json(mood)")
        self.conn.execute("CREATE TABLE moody (id serial PRIMARY KEY, m mood)")
        try:
            self.conn.execute("GRANT ALL ON moody TO PUBLIC")
            self.conn.execute("GRANT ALL ON SEQUENCE moody_id_seq TO PUBLIC")
            self.as_role(ALICE, "INSERT INTO moody (m) VALUES ('happy')")
            self.assertEqual(self.changes("moody")[0][5]["m"], "jaaql_audit")
            self.assertFalse(self.conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname = 'jaaql_audit'").fetchone()[0])
            self.assertFalse(self.conn.execute("SELECT prosecdef FROM pg_proc WHERE oid = 'audit.purge_expired()'::regprocedure").fetchone()[0])
        finally:
            self.conn.execute("DROP TABLE moody")
            self.conn.execute("DROP CAST (mood AS json)")
            self.conn.execute("DROP FUNCTION mood_to_json(mood)")
            self.conn.execute("DROP TYPE mood")

    def test_new_and_altered_tables_are_attached(self):
        self.conn.execute("CREATE TABLE late (id integer PRIMARY KEY, v text)")
        try:
            self.conn.execute("GRANT ALL ON late TO PUBLIC")
            self.as_role(ALICE, "INSERT INTO late VALUES (1, 'a')")
            self.conn.execute("ALTER TABLE late ADD COLUMN api_key text")
            self.as_role(ALICE, "INSERT INTO late VALUES (2, 'b', 'k-123')")
            self.assertEqual([c[5] for c in self.changes("late")], [
                {"id": 1, "v": "a"}, {"id": 2, "v": "b", "api_key": "(withheld)"}])
        finally:
            self.conn.execute("DROP TABLE late")

    def test_non_ascii_column_names(self):
        self.conn.execute('CREATE TABLE "naïve" (id integer PRIMARY KEY, "émail" text, "geheim_ü" text)')
        try:
            self.conn.execute('GRANT ALL ON "naïve" TO PUBLIC')
            self.conn.execute('ALTER TABLE "naïve" ADD COLUMN "straße" text')
            self.as_role(ALICE, 'INSERT INTO "naïve" VALUES (1, \'e\', \'secret-ü\', \'s\')')
            self.assertEqual(self.changes("naïve")[0][5], {"id": 1, "émail": "e", "geheim_ü": "(withheld)", "straße": "s"})
            self.assertEqual(self.conn.execute("SELECT status FROM audit.coverage WHERE table_name = 'public.naïve'").fetchone()[0], "audited")
            self.assertEqual(self.conn.execute("SELECT audit.attach_all()").fetchone()[0], 0)
        finally:
            self.conn.execute('DROP TABLE "naïve"')

    def test_a_disabled_or_dropped_trigger_comes_back(self):
        self.conn.execute("ALTER TABLE person DISABLE TRIGGER zzz_audit_insert")
        self.conn.execute("DROP TRIGGER zzz_audit_update ON person")
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        self.as_role(ALICE, "UPDATE person SET name = 'Q'")
        self.assertEqual([c[2] for c in self.changes()], ["INSERT", "UPDATE"])
        self.assertEqual(self.conn.execute("SELECT status FROM audit.coverage WHERE table_name = 'public.person'").fetchone()[0], "audited")

    def test_withheld_columns_and_exclusions_take_effect_at_once(self):
        self.conn.execute("INSERT INTO audit.withheld_column VALUES ('public.person', 'email')")
        self.conn.execute("INSERT INTO audit.excluded_table VALUES ('public.error_report', 'a log with a retention rule of its own')")
        try:
            self.as_role(ALICE, "INSERT INTO person (name, email) VALUES ('P', 'p@example.test')")
            self.as_role(ALICE, "INSERT INTO error_report (message) VALUES ('m')")
            self.assertEqual(self.changes("person")[0][5]["email"], "(withheld)")
            self.assertEqual(self.changes("error_report"), [])
            statuses = dict(self.conn.execute("SELECT table_name, status FROM audit.coverage").fetchall())
            self.assertEqual((statuses["public.person"], statuses["public.error_report"]), ("audited", "excluded"))
        finally:
            self.conn.execute("DELETE FROM audit.withheld_column")
            self.conn.execute("DELETE FROM audit.excluded_table")
        self.as_role(ALICE, "INSERT INTO error_report (message) VALUES ('n')")
        self.assertEqual(len(self.changes("error_report")), 1)

    def test_truncate_is_recorded(self):
        self.as_role(ALICE, "INSERT INTO pair VALUES (1, 'x', 'v')")
        self.as_role(ALICE, "TRUNCATE pair")
        self.assertEqual([c[2] for c in self.changes("pair")], ["INSERT", "TRUNCATE"])

    def test_export_names_the_people(self):
        self.as_role(ALICE, "INSERT INTO person (name, email) VALUES ('Alice A', %s)", (ALICE,))
        rows = self.as_role("dba", "SELECT actor, actor_label, operation FROM audit.export(now() - interval '1 hour', now() + interval '1 hour', "
                                   "'SELECT email, name FROM public.person')").fetchall()
        self.assertEqual(rows, [(ALICE, "Alice A", "INSERT")])

    def test_everything_is_audited_and_the_install_is_idempotent(self):
        statuses = dict(self.conn.execute("SELECT table_name, status FROM audit.coverage").fetchall())
        self.assertEqual(set(statuses.values()), {"audited"})
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        self.install()
        self.assertEqual(self.conn.execute("SELECT audit.attach_all()").fetchone()[0], 0)
        self.assertEqual(len(self.changes()), 1)

    def test_a_reinstall_adds_what_an_older_install_lacks(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('P')")
        self.conn.execute("ALTER TABLE audit.setting DROP COLUMN last_purge_errors")
        self.install()
        self.assertEqual(self.conn.execute("SELECT last_purge_errors FROM audit.setting").fetchone(), (None,))
        self.assertEqual(len(self.changes()), 1)

    def test_every_erasure_reason_of_a_transaction_is_kept(self):
        with self.conn.transaction():
            self.conn.execute("SELECT audit.begin_erasure('request R-1')")
            self.conn.execute("SELECT audit.begin_erasure('request R-2')")
            self.conn.execute("SELECT audit.begin_erasure('request R-2')")
        self.assertEqual(self.conn.execute("SELECT reason FROM audit.erasure").fetchall(), [("request R-1; request R-2",)])

    def test_drop_schema_public_cascade_keeps_the_log_and_reattaches(self):
        self.as_role(ALICE, "INSERT INTO person (name) VALUES ('Before the wipe')")
        self.conn.execute("DROP SCHEMA public CASCADE")
        self.conn.execute("CREATE SCHEMA public")
        self.conn.execute(SCHEMA)
        self.as_role(BOB, "INSERT INTO person (name) VALUES ('After the wipe')")
        self.assertEqual([(c[0], c[2], c[5]["name"]) for c in self.changes("person")], [
            (ALICE, "INSERT", "Before the wipe"), (BOB, "INSERT", "After the wipe")])
        self.assertEqual(set(dict(self.conn.execute("SELECT table_name, status FROM audit.coverage").fetchall()).values()), {"audited"})

    def test_a_rolled_back_change_leaves_nothing(self):
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.conn.transaction():
                self.conn.execute("INSERT INTO service VALUES ('x', 'a')")
                self.conn.execute("INSERT INTO service VALUES ('x', 'b')")
        self.assertEqual(self.changes(), [])


if __name__ == "__main__":
    unittest.main()
