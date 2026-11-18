"""
JAAQL's own check in the health routes, /internal/deep-health and /internal/is-alive, which need no login (nginx passes /api/internal/... on
as it is; Pingdom and the probes poll them): a failure answers the generic 503 "Deep health: JAAQL check failed" or "Keep alive failed",
never the error's text, which can name the database's internals (a socket path, a relation, a file under base/). The request is still
reported to Sentinel as the server error it is, by the error itself (server_errors.in_place_of), and why is printed for the server's log as
a line of its own at most once a minute, never while JAAQL is not installed.

    python -m unittest jaaql.test.test_health_checks

Needs only the package's requirements, as jaaql.test.test_server_errors: the lookup connection is a stand-in database interface
"""
import os
import unittest
from unittest import mock

import psycopg.errors as pg

from jaaql.constants import ENVIRON__deep_health_application, QUERY_CACHE_KEY__health
from jaaql.db import db_utils_no_circ
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_deep_health_application import Causes
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import TimedInterface

DEEP_HEALTH = "/internal/deep-health"
IS_ALIVE = "/internal/is-alive"
JAAQL_FAILED = b"Deep health: JAAQL check failed"
KEEP_ALIVE_FAILED = b"Keep alive failed"

# What the lookup connection raises, and the text that must never reach the body: what the database said
DATABASE_ERRORS = [
    (pg.DiskFull, 'could not extend file "base/16384/2619": No space left on device'),
    (pg.UndefinedTable, 'relation "jaaql_internal_secret_table" does not exist\nLINE 1: SELECT 1 FROM jaaql_internal_secret_table'),
    (pg.ConnectionTimeout, 'connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: timeout expired'),
    (pg.QueryCanceled, "canceling statement due to statement timeout"),
]


class Version(TimedInterface):
    """
    The lookup connection answering SELECT version() with text
    """

    def __init__(self, text):
        super().__init__()
        self.text = text

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        return ["version"], [0], [[self.text]]


class TestHealthChecksAnswerGenerically(ServerErrorCase):

    def setUp(self):
        super().setUp()
        self.model.query_caches["queries"][QUERY_CACHE_KEY__health] = ["SELECT 1 AS health"]
        self.model.jaaql_lookup_connection = TimedInterface()
        self.real = [mock.patch.object(self.model, "deep_health", lambda: JAAQLModel.deep_health(self.model), create=True),
                     mock.patch.object(self.model, "is_alive", lambda: JAAQLModel.is_alive(self.model), create=True)]
        for patch in self.real:
            patch.start()
        self.reset_reasons()

    def tearDown(self):
        self.reset_reasons()
        for patch in self.real:
            patch.stop()
        super().tearDown()

    @staticmethod
    def reset_reasons():
        for reason in (model.DEEP_HEALTH__unavailable, model.DEEP_HEALTH__jaaql_failed, model.IS_ALIVE__failed):
            reason.reset()

    def reason_lines(self):
        return [line for line in self.printed.getvalue().splitlines() if line.startswith(("Deep health ", "Is alive "))]

    def get(self, route, application=None):
        environ = {ENVIRON__deep_health_application: application} if application is not None else {}
        application_db = Causes(["gateway heartbeat: none received"])
        with mock.patch.dict(os.environ, environ, clear=False), \
                mock.patch.object(db_utils_no_circ, "get_required_db", return_value=application_db) as required_db:
            if application is None:
                os.environ.pop(ENVIRON__deep_health_application, None)
            answered, reports = self.answers(lambda: self.client.get(route))
        # JAAQL's own check comes first: the application's view is never read once it failed
        self.assertEqual([], application_db.statements)
        if answered[0] != 200:
            required_db.assert_not_called()
        return answered, reports

    def assertGenericAnswer(self, answered, body, hidden):
        status, headers, data = answered
        self.assertEqual((503, body), (status, data))
        for line in hidden.splitlines():
            self.assertNotIn(line, repr(headers))
            for part in [line] + [word for word in line.split() if len(word) > 6]:
                self.assertNotIn(part.encode(), data)

    def assertReportedBy(self, reports, condensed, route):
        self.assertEqual(1, len(reports))
        self.assertServerContract(reports[0])
        self.assertEqual(condensed, reports[0]["error_condensed"])
        self.assertIn("\nAnswered: 503\n", reports[0]["stacktrace"])
        self.assertIn("Route: GET " + route, reports[0]["stacktrace"])
        lines = self.lines()
        self.assertEqual(2, len(lines))
        for line in lines:
            self.assertRegex(line, r"^SERVER ERROR \w+ at jaaql/mvc/model\.py:\d+ \(GET %s, [^)]*\) answered 503( - |$)" % route)

    def test_deep_health_answers_a_database_error_of_its_own_check_generically_and_reports_it(self):
        for make, text in DATABASE_ERRORS:
            for application in (None, "sentinel"):
                with self.subTest(error=make.__name__, application=application):
                    self.printed.truncate(0)
                    self.printed.seek(0)
                    self.reset_reasons()
                    self.model.jaaql_lookup_connection = Causes(make=lambda: make(text))
                    answered, reports = self.get(DEEP_HEALTH, application)
                    self.assertGenericAnswer(answered, JAAQL_FAILED, text)
                    self.assertReportedBy(reports, "%s %s: %s" % (make.__name__, make.sqlstate, text.splitlines()[0]) if make.sqlstate
                                          else "%s: %s" % (make.__name__, text.splitlines()[0]), DEEP_HEALTH)
                    # Why, once for the three requests answers() made, as a line of its own
                    reasons = self.reason_lines()
                    self.assertEqual(1, len(reasons), reasons)
                    self.assertTrue(reasons[0].startswith("Deep health answered 503: JAAQL's own check failed ("), reasons[0])
                    self.assertTrue(reasons[0].endswith(text.splitlines()[0] + "); 0 more since the last line"), reasons[0])

    def test_deep_health_answers_a_missing_health_query_generically_and_reports_it(self):
        del self.model.query_caches["queries"][QUERY_CACHE_KEY__health]
        answered, reports = self.get(DEEP_HEALTH, "sentinel")
        self.assertGenericAnswer(answered, JAAQL_FAILED, "Compiled query '__health__' is not present in the query cache")
        self.assertReportedBy(reports, "HttpStatusException: Compiled query '__health__' is not present in the query cache", DEEP_HEALTH)
        self.assertEqual(["Deep health answered 503: JAAQL's own check failed (HttpStatusException: Compiled query '__health__' is not "
                          "present in the query cache); 0 more since the last line"], self.reason_lines())

    def test_deep_health_and_is_alive_stay_healthy(self):
        for route, interface in [(DEEP_HEALTH, TimedInterface()), (IS_ALIVE, Version("PostgreSQL 18.1 on x86_64-pc-linux-gnu"))]:
            with self.subTest(route=route):
                self.model.jaaql_lookup_connection = interface
                (status, _, data), reports = self.get(route)
                self.assertEqual((200, b'"OK"\n', []), (status, data, reports))
        self.assertEqual([], self.lines())
        self.assertEqual([], self.reason_lines())

    def test_is_alive_answers_a_database_error_generically_and_reports_it(self):
        for make, text in DATABASE_ERRORS:
            with self.subTest(error=make.__name__):
                self.printed.truncate(0)
                self.printed.seek(0)
                self.reset_reasons()
                self.model.jaaql_lookup_connection = Causes(make=lambda: make(text))
                answered, reports = self.get(IS_ALIVE)
                self.assertGenericAnswer(answered, KEEP_ALIVE_FAILED, text)
                self.assertReportedBy(reports, "%s %s: %s" % (make.__name__, make.sqlstate, text.splitlines()[0]) if make.sqlstate
                                      else "%s: %s" % (make.__name__, text.splitlines()[0]), IS_ALIVE)
                reasons = self.reason_lines()
                self.assertEqual(1, len(reasons), reasons)
                self.assertTrue(reasons[0].startswith("Is alive answered 503: JAAQL's own check failed ("), reasons[0])
                self.assertTrue(reasons[0].endswith(text.splitlines()[0] + "); 0 more since the last line"), reasons[0])

    def test_is_alive_on_a_database_that_is_not_postgres_is_the_same_answer(self):
        self.model.jaaql_lookup_connection = Version("SQLite 3.46")
        answered, reports = self.get(IS_ALIVE)
        self.assertGenericAnswer(answered, KEEP_ALIVE_FAILED, "SQLite 3.46")
        self.assertReportedBy(reports, "HttpStatusException: Keep alive failed", IS_ALIVE)
        self.assertEqual(["Is alive answered 503: JAAQL's own check failed (HttpStatusException: Keep alive failed); 0 more since the "
                          "last line"], self.reason_lines())

    def test_the_reason_is_printed_at_most_once_a_minute_with_the_number_held_back(self):
        self.model.jaaql_lookup_connection = Causes(make=lambda: pg.DiskFull("could not write to file: No space left on device"))
        for _ in range(4):
            res = self.client.get(IS_ALIVE)
            self.assertEqual((503, KEEP_ALIVE_FAILED), (res.status_code, res.get_data()))
        self.assertEqual(1, len(self.reason_lines()))
        model.IS_ALIVE__failed._printed_at -= model.DEEP_HEALTH__print_seconds
        self.client.get(IS_ALIVE)
        reasons = self.reason_lines()
        self.assertEqual(2, len(reasons))
        self.assertTrue(reasons[0].endswith("; 0 more since the last line"), reasons[0])
        self.assertTrue(reasons[1].endswith("; 3 more since the last line"), reasons[1])
        # Each route keeps its own count
        self.client.get(DEEP_HEALTH)
        self.assertEqual(3, len(self.reason_lines()))
        self.assertTrue(self.reason_lines()[2].startswith("Deep health answered 503: JAAQL's own check failed ("))

    def test_while_not_installed_the_generic_answer_is_neither_reported_nor_explained(self):
        self.model.has_installed = False
        self.model.jaaql_lookup_connection = None
        for route, body in [(IS_ALIVE, KEEP_ALIVE_FAILED), (DEEP_HEALTH, JAAQL_FAILED)]:
            with self.subTest(route=route):
                (status, _, data), reports = self.answers(lambda: self.client.get(route))
                self.assertEqual((503, body, []), (status, data, reports))
        self.assertEqual([], self.lines())
        self.assertEqual([], self.reason_lines())


if __name__ == "__main__":
    unittest.main()
