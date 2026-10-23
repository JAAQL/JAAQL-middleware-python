"""
The migrations manager runs the AUTORUN pattern, the handwritten before and after files and the migration .jaaql files through
jaaql-monitor inside the container. jaaql-monitor 1.7 runs the files of consecutive \\psql lines as one shell script that it feeds to
`[sudo] docker exec -i <container> sh -s`, every file preceded by SET SESSION AUTHORIZATION "<user>" and included as
\\i /slurp-in/<file>. _execute_monitor_jaaql feeds that script to a local sh instead, connecting as postgres, with the
SET SESSION AUTHORIZATION lines dropped from the script and from a copy of each file (the named user may lack CREATE on schema public),
each file found relative to the input file whose \\psql line named it, as monitor 1.6 found it. psql's messages, which name the file
as the script included it, reach the monitor naming that file instead of its copy.

    python -m unittest jaaql.test.test_monitor_psql

The unit tests stand in for the shell and need only the package's requirements. TestMonitorPsqlAgainstPostgres runs the script with the
real sh and psql against a scratch Postgres; it runs only when JAAQL_TEST_POSTGRES_URI is set to
postgresql://postgres:<password>@<host>:<port>/<database> and psql is on the PATH, and creates, then drops, the database
jaaql_test_monitor_psql
"""
import glob
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import psycopg
from psycopg.conninfo import conninfo_to_dict

import monitor.main as monitor_mod
from monitor.main import HEADER__security_bypass, JAAQLMonitorException
from jaaql.services import migrations_manager_service
from jaaql.services.migrations_manager_service import _execute_monitor_jaaql

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_monitor_psql"
BYPASS_HEADER = {HEADER__security_bypass: "test-bypass-key"}
ORIGINAL_PSQL_RUN = monitor_mod.psql__run


def write_files(root, files):
    for name, content in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)


def leftover_copy_dirs():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "jaaql-psql-*")))


class ShellStandIn:
    # Stands in for subprocess.run under psql__run: records each command, the script and the content of every file the script
    # includes (the copies are removed once _execute_monitor_jaaql returns), and answers with the markers psql would write to
    # stderr, failing the file of index fail_index with the error psql reports, which names the file as the script included it
    def __init__(self, fail_index=None):
        self.calls = []
        self.fail_index = fail_index

    def __call__(self, command, input=None, **kwargs):
        script = input.decode("utf-8")
        included = {}
        stderr = []
        failing = False
        for line in script.split("\n"):
            if line.startswith("\\i "):
                path = line[len("\\i "):]
                with open(path, "r", encoding="utf-8") as f:
                    included[path] = f.read()
                if failing:
                    stderr.append("psql:%s:2: ERROR:  relation \"missing\" does not exist" % path)
                    failing = False
            elif line.startswith("\\warn "):
                stderr.append(line[len("\\warn "):])
                failing = self.fail_index is not None and line == "\\warn @@B %d" % self.fail_index
        self.calls.append({"command": command, "script": script, "included": included})
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr="\n".join(stderr).encode("utf-8"))


class TestMonitorPsqlScript(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="jaaql-test-monitor-")
        self.addCleanup(shutil.rmtree, self.root, True)
        write_files(self.root, {
            "reset.jaaql": "\\psql @dba_db domains.jsql\n"
                           "\\psql @dba_db procedures/p.0000.dba\n"
                           "\\import handwritten/after/hw.jqli\n",
            "domains.jsql": "SET SESSION AUTHORIZATION \"dba\";\nCREATE DOMAIN d AS text;\n  set session authorization jaaql;\nSELECT 1;\n",
            "procedures/p.0000.dba": "﻿CREATE FUNCTION p() RETURNS int LANGUAGE sql AS 'SELECT 1';\n",
            "handwritten/after/hw.jqli": "\\psql @jaaql inner.sql\n",
            "handwritten/after/inner.sql": "SELECT 'the inner.sql beside hw.jqli';\n",
            "inner.sql": "SELECT 'the inner.sql beside reset.jaaql';\n",
        })
        self.before = leftover_copy_dirs()

    def run_monitor(self, shell):
        with mock.patch("monitor.main.subprocess.run", side_effect=shell):
            _execute_monitor_jaaql("http://localhost", BYPASS_HEADER, [os.path.join(self.root, "reset.jaaql")])

    def assert_restored(self):
        self.assertIs(monitor_mod.psql__run, ORIGINAL_PSQL_RUN)
        self.assertEqual(leftover_copy_dirs(), self.before)

    def test_the_script_runs_in_a_local_shell_as_postgres(self):
        shell = ShellStandIn()
        self.run_monitor(shell)

        # one batch per input file: reset.jaaql's two \psql lines, then the line of the file it imports
        self.assertEqual(len(shell.calls), 2)
        for call in shell.calls:
            self.assertEqual(call["command"], ["sh", "-s"])
            self.assertNotIn("docker", " ".join(call["command"]))
            self.assertNotIn("SET SESSION AUTHORIZATION", call["script"].upper())
            self.assertNotIn("/slurp-in/", call["script"])
            self.assertIn("psql -U postgres -d ", call["script"])
        self.assert_restored()

    def test_each_file_is_found_beside_its_input_file_and_copied_without_session_authorization(self):
        shell = ShellStandIn()
        self.run_monitor(shell)

        first, second = [list(call["included"].values()) for call in shell.calls]
        self.assertEqual(first, [
            "\nCREATE DOMAIN d AS text;\n\nSELECT 1;\n",
            "CREATE FUNCTION p() RETURNS int LANGUAGE sql AS 'SELECT 1';\n",
        ])
        self.assertEqual(second, ["SELECT 'the inner.sql beside hw.jqli';\n"])
        for call in shell.calls:
            for path in call["included"]:
                self.assertFalse(path.startswith(self.root), path)
                self.assertTrue(os.path.basename(os.path.dirname(path)).startswith("jaaql-psql-"), path)
        self.assert_restored()

    def test_no_slurp_in_location_is_passed(self):
        passed = []
        real_initialise = migrations_manager_service.monitor_initialise

        def initialise(**kwargs):
            passed.append(kwargs["additional_args"])
            return real_initialise(**kwargs)

        with mock.patch.object(migrations_manager_service, "monitor_initialise", side_effect=initialise):
            self.run_monitor(ShellStandIn())

        self.assertEqual(passed[0][:2], ["-i", os.path.join(self.root, "reset.jaaql")])
        self.assertNotIn("--jaaql-slurp-in-location", passed[0])

    def test_a_failing_file_raises_and_still_restores_the_monitor(self):
        shell = ShellStandIn(fail_index=1)
        with self.assertRaises(JAAQLMonitorException) as raised:
            self.run_monitor(shell)

        self.assertIn("Error executing: procedures/p.0000.dba", str(raised.exception))
        self.assert_restored()

    def test_psql_s_messages_name_the_file_not_its_copy(self):
        # The copies are gone by the time anyone reads the message, so it names the file the copy was made from, at psql's line
        shell = ShellStandIn(fail_index=1)
        with self.assertRaises(JAAQLMonitorException) as raised:
            self.run_monitor(shell)

        message = str(raised.exception)
        self.assertIn("psql:%s:2: ERROR:  relation \"missing\" does not exist" % os.path.join(self.root, "procedures/p.0000.dba"), message)
        self.assertNotIn("jaaql-psql-", message)
        copy = [path for path in shell.calls[0]["included"] if path.endswith(".p.0000.dba")]
        self.assertEqual(len(copy), 1)
        self.assertNotIn(copy[0], message)
        self.assert_restored()

    def test_each_copy_s_path_becomes_its_source_s(self):
        copies = {"/slurp-in/a.sql": "/tmp/jaaql-psql-x/0.a.sql", "/slurp-in/sub/b.sql": "/tmp/jaaql-psql-x/1.b.sql",
                  "/slurp-in/c.sql": "/tmp/jaaql-psql-x/10.c.sql"}
        stderr = ("@@B 0\npsql:/tmp/jaaql-psql-x/0.a.sql:3: ERROR:  boom\n@@E 0\n"
                  "psql:/tmp/jaaql-psql-x/1.b.sql:12: NOTICE:  x\npsql:/tmp/jaaql-psql-x/10.c.sql:1: ERROR:  y")
        self.assertEqual(migrations_manager_service._name_sources_in_psql_output(stderr, copies),
                         "@@B 0\npsql:/slurp-in/a.sql:3: ERROR:  boom\n@@E 0\n"
                         "psql:/slurp-in/sub/b.sql:12: NOTICE:  x\npsql:/slurp-in/c.sql:1: ERROR:  y")
        self.assertIsNone(migrations_manager_service._name_sources_in_psql_output(None, copies))
        # As monitor 1.7.17 finds the failing line of a file it included as \i /slurp-in/<file>
        self.assertEqual(monitor_mod.psql__error_line(migrations_manager_service._name_sources_in_psql_output(stderr, copies), "c.sql"), 1)

    def test_a_missing_file_raises_and_still_restores_the_monitor(self):
        os.unlink(os.path.join(self.root, "domains.jsql"))
        with self.assertRaises(FileNotFoundError):
            self.run_monitor(ShellStandIn())

        self.assert_restored()


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri) and shutil.which("psql") and shutil.which("sh"),
                     "set " + ENVIRON__test_postgres_uri + " and put psql on the PATH to run against a scratch Postgres")
class TestMonitorPsqlAgainstPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        uri = os.environ[ENVIRON__test_postgres_uri]
        params = conninfo_to_dict(uri)
        if params.get("user") != "postgres":
            raise unittest.SkipTest("the monitor's script connects as postgres, so the URI must too")
        cls.admin_uri = uri
        cls.test_uri = uri.rsplit("/", 1)[0] + "/" + TEST_DATABASE
        cls.psql_environ = {"PGHOST": params.get("host", "localhost"), "PGPORT": str(params.get("port", 5432)),
                            "PGPASSWORD": params.get("password", ""), "AUTORUN_DATABASE": TEST_DATABASE}

    def setUp(self):
        with psycopg.connect(self.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("CREATE DATABASE " + TEST_DATABASE)
        self.root = tempfile.mkdtemp(prefix="jaaql-test-monitor-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.before = leftover_copy_dirs()

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")

    def run_monitor(self):
        with mock.patch.dict(os.environ, self.psql_environ):
            _execute_monitor_jaaql("http://localhost", BYPASS_HEADER, [os.path.join(self.root, "reset.jaaql")])

    def test_files_run_as_postgres_in_order_with_tests_and_expected_errors(self):
        # The role named in domains.jsql does not exist, and neither need dba: both would fail the file were they not dropped.
        # Five test files and an error file after the procedure make the monitor run them in parallel sessions
        tests = {"procedures/p.%04d.test.dba" % n: "BEGIN;\nSET SESSION AUTHORIZATION \"dba\";\n"
                                                    "DO $$ BEGIN IF p() <> 1 THEN RAISE EXCEPTION 'p'; END IF; END $$;\nROLLBACK;\n"
                 for n in range(1, 6)}
        write_files(self.root, {
            "reset.jaaql": "\\psql @dba_db domains.jsql\n\\psql @dba_db structure.jsql\n\\import sub/procedures.jqli\n",
            "domains.jsql": "SET SESSION AUTHORIZATION \"jaaql_test_monitor_absent_role\";\nCREATE DOMAIN d AS text;\n",
            "structure.jsql": "CREATE TABLE ran_as (who name, value d);\nINSERT INTO ran_as VALUES (current_user, 'structure');\n",
            "sub/procedures.jqli": "".join("\\psql @dba_db " + name + "\n" for name in
                                           ["procedures/p.0000.dba", *sorted(tests), "procedures/p.0006.error.dba"]),
            "sub/procedures/p.0000.dba": "CREATE FUNCTION p() RETURNS int LANGUAGE sql AS 'SELECT 1';\n",
            "sub/procedures/p.0006.error.dba": "SELECT 1 / 0;\n",
            **{"sub/" + name: content for name, content in tests.items()},
        })

        self.run_monitor()

        with psycopg.connect(self.test_uri) as conn:
            self.assertEqual(conn.execute("SELECT who, value FROM ran_as").fetchall(), [("postgres", "structure")])
            self.assertEqual(conn.execute("SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE proname = 'p'").fetchall(),
                             [("postgres",)])
        self.assertIs(monitor_mod.psql__run, ORIGINAL_PSQL_RUN)
        self.assertEqual(leftover_copy_dirs(), self.before)

    def test_a_failing_file_stops_the_run(self):
        write_files(self.root, {
            "reset.jaaql": "\\psql @dba_db broken.jsql\n\\psql @dba_db after.jsql\n",
            "broken.jsql": "SELECT * FROM missing;\n",
            "after.jsql": "CREATE TABLE after_the_failure (id int);\n",
        })

        with self.assertRaises(JAAQLMonitorException) as raised:
            self.run_monitor()

        self.assertIn("Error executing: broken.jsql", str(raised.exception))
        self.assertIn("psql:%s:1: ERROR:  relation \"missing\" does not exist" % os.path.join(self.root, "broken.jsql"), str(raised.exception))
        self.assertNotIn("jaaql-psql-", str(raised.exception))
        with psycopg.connect(self.test_uri) as conn:
            self.assertIsNone(conn.execute("SELECT to_regclass('after_the_failure')").fetchone()[0])
        self.assertEqual(leftover_copy_dirs(), self.before)


if __name__ == "__main__":
    unittest.main()
