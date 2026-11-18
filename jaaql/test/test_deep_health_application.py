"""
Deep health with an application's own verdict: when JAAQL_DEEP_HEALTH_APPLICATION names an application, /internal/deep-health reads that
application's view deep_health.fault as dba after JAAQL's own check, and answers 503 naming every cause it returns, in its order, or, when
the view cannot be read, 503 "Deep health: application check unavailable": the body is public, so why the view could not be read is printed
for the server's log only, at most once a minute, and never as a SERVER ERROR line. None of those answers is reported to Sentinel: they are
the application's verdict, polled every minute. Unset, deep-health is what it was: JAAQL's own cache query alone, and a missing cache query
is still the server error it always was, answered with the generic 503 "Deep health: JAAQL check failed" (jaaql.test.test_health_checks).

    python -m unittest jaaql.test.test_deep_health_application

Needs only the package's requirements, as jaaql.test.test_server_errors: the application's query runs on a stand-in database interface
"""
import os
import unittest
from unittest import mock

import psycopg.errors as pg

from jaaql.constants import ENVIRON__deep_health_application, QUERY__deep_health_faults, QUERY_CACHE_KEY__health, ROLE__dba, KEY__application
from jaaql.db import db_utils_no_circ
from jaaql.interpreter.interpret_jaaql import KEY_query
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import TimedInterface

APPLICATION_WITH_VIEW = "sentinel"
DEEP_HEALTH = "/internal/deep-health"
UNAVAILABLE = b"Deep health: application check unavailable"


class Causes(TimedInterface):
    """
    The application database: answers the statement with one row per cause, or raises what make() builds. statements keeps what it ran
    """

    def __init__(self, causes=(), make=None):
        super().__init__()
        self.causes = list(causes)
        self.make = make
        self.statements = []

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        self.statements.append(query)
        if self.make is not None:
            raise self.make()
        return ["cause"], [0], [[cause] for cause in self.causes]


class TestDeepHealthApplication(ServerErrorCase):

    def setUp(self):
        super().setUp()
        # JAAQL's own check as on a box: the health query in the cache, run on the lookup connection
        self.model.query_caches["queries"][QUERY_CACHE_KEY__health] = ["SELECT 1 AS health"]
        self.model.jaaql_lookup_connection = TimedInterface()
        self.real = mock.patch.object(self.model, "deep_health", lambda: JAAQLModel.deep_health(self.model), create=True)
        self.real.start()
        model.DEEP_HEALTH__unavailable.reset()

    def tearDown(self):
        model.DEEP_HEALTH__unavailable.reset()
        self.real.stop()
        super().tearDown()

    def unavailable_lines(self):
        return [line for line in self.printed.getvalue().splitlines() if line.startswith("Deep health ")]

    def deep_health(self, interface, application=APPLICATION_WITH_VIEW):
        environ = {ENVIRON__deep_health_application: application} if application is not None else {}
        with mock.patch.dict(os.environ, environ, clear=False), \
                mock.patch.object(db_utils_no_circ, "get_required_db", return_value=interface) as required_db:
            if application is None:
                os.environ.pop(ENVIRON__deep_health_application, None)
            answered, reports = self.answers(lambda: self.client.get(DEEP_HEALTH))
        return answered, reports, required_db

    def test_unset_reads_no_application(self):
        interface = Causes(["gateway heartbeat: none received"])
        (status, _, data), reports, required_db = self.deep_health(interface, application=None)
        self.assertEqual(200, status)
        self.assertEqual([], interface.statements)
        required_db.assert_not_called()
        self.assertEqual([], reports)

    def test_no_cause_is_healthy_and_reads_the_view_as_dba_in_the_application(self):
        interface = Causes([])
        (status, _, data), reports, required_db = self.deep_health(interface)
        self.assertEqual(200, status)
        self.assertEqual([QUERY__deep_health_faults] * 3, interface.statements)
        inputs, account_id = required_db.call_args[0][3], required_db.call_args[0][4]
        self.assertEqual(APPLICATION_WITH_VIEW, inputs[KEY__application])
        self.assertEqual(QUERY__deep_health_faults, inputs[KEY_query])
        self.assertEqual(ROLE__dba, account_id)
        self.assertEqual([], reports)

    def test_every_cause_is_named_in_the_order_of_the_view_and_never_reported(self):
        interface = Causes(["gateway heartbeat stale: last valid 2026-11-17T18:00:00Z (21 min ago)", "gateway: pushes: LesBij locked 12 min"])
        (status, _, data), reports, _ = self.deep_health(interface)
        self.assertEqual(503, status)
        self.assertEqual(b"Deep health: gateway heartbeat stale: last valid 2026-11-17T18:00:00Z (21 min ago); "
                         b"gateway: pushes: LesBij locked 12 min", data)
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())

    def test_a_view_that_cannot_be_read_is_unhealthy_and_never_reported(self):
        interface = Causes(make=lambda: pg.UndefinedTable('relation "deep_health.fault" does not exist\nLINE 1: SELECT cause FROM deep_health...'))
        (status, _, data), reports, _ = self.deep_health(interface)
        # The public body is generic; the reason is in the log, once for the three requests answers() made, as no SERVER ERROR
        self.assertEqual((503, UNAVAILABLE), (status, data))
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())
        self.assertEqual(['Deep health sentinel answered 503: deep_health.fault could not be read (UnhandledQueryError: relation '
                          '"deep_health.fault" does not exist); 0 more since the last line'], self.unavailable_lines())

    def test_the_database_failing_under_the_view_is_unhealthy_and_never_reported(self):
        interface = Causes(make=lambda: pg.DiskFull('could not extend file "base/16384/2619": No space left on device'))
        (status, _, data), reports, _ = self.deep_health(interface)
        self.assertEqual((503, UNAVAILABLE), (status, data))
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())
        self.assertEqual(['Deep health sentinel answered 503: deep_health.fault could not be read (DatabaseOperationalError: could not '
                          'extend file "base/16384/2619": No space left on device); 0 more since the last line'], self.unavailable_lines())

    def test_the_reason_is_printed_at_most_once_a_minute_with_the_number_held_back(self):
        interface = Causes(make=lambda: pg.ConnectionTimeout('connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: '
                                                             'timeout expired\nIs the server running locally?'))
        with mock.patch.dict(os.environ, {ENVIRON__deep_health_application: APPLICATION_WITH_VIEW}), \
                mock.patch.object(db_utils_no_circ, "get_required_db", return_value=interface):
            for _ in range(4):
                res = self.client.get(DEEP_HEALTH)
                self.assertEqual((503, UNAVAILABLE), (res.status_code, res.get_data()))
            line = 'Deep health sentinel answered 503: deep_health.fault could not be read (DatabaseOperationalError: connection to ' \
                   'server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: timeout expired); %d more since the last line'
            self.assertEqual([line % 0], self.unavailable_lines())
            # A minute on, the next is printed with the three held back since the line before
            model.DEEP_HEALTH__unavailable._printed_at -= model.DEEP_HEALTH__print_seconds
            self.client.get(DEEP_HEALTH)
            self.client.get(DEEP_HEALTH)
        self.assertEqual([line % 0, line % 3], self.unavailable_lines())
        self.assertEqual([], self.lines())
        self.assertNoReport()

    def test_causes_and_health_print_nothing(self):
        for causes, expected in [(["gateway heartbeat: stale"], (503, b"Deep health: gateway heartbeat: stale")), ([], (200, b'"OK"\n'))]:
            with self.subTest(causes=causes):
                (status, _, data), reports, _ = self.deep_health(Causes(causes))
                self.assertEqual((expected, []), ((status, data), reports))
        self.assertEqual([], self.unavailable_lines())

    def test_jaaqls_own_check_still_comes_first_and_is_still_a_server_error(self):
        del self.model.query_caches["queries"][QUERY_CACHE_KEY__health]
        interface = Causes(["gateway heartbeat: none received"])
        (status, _, data), reports, required_db = self.deep_health(interface)
        # The generic 503, the route needing no login; still reported by the error itself (jaaql.test.test_health_checks)
        self.assertEqual((503, b"Deep health: JAAQL check failed"), (status, data))
        self.assertEqual([], interface.statements)
        required_db.assert_not_called()
        self.assertEqual(1, len(reports))
        self.assertEqual("HttpStatusException: Compiled query '__health__' is not present in the query cache", reports[0]["error_condensed"])


if __name__ == "__main__":
    unittest.main()
