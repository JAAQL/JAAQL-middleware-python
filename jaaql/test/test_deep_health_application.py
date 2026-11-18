"""
Deep health with an application's own verdict: when JAAQL_DEEP_HEALTH_APPLICATION names an application, /internal/deep-health reads that
application's view deep_health.fault as dba after JAAQL's own check, and answers 503 naming every cause it returns, in its order, or naming
why the view could not be read. None of those answers is reported to Sentinel: they are the application's verdict, polled every minute.
Unset, deep-health is what it was: JAAQL's own cache query alone, and a missing cache query is still the server error it always was.

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
from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import TimedInterface

APPLICATION_WITH_VIEW = "sentinel"
DEEP_HEALTH = "/internal/deep-health"


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

    def tearDown(self):
        self.real.stop()
        super().tearDown()

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
        self.assertEqual(503, status)
        self.assertTrue(data.startswith(b"deep_health.fault unavailable: "), data)
        self.assertIn(b'relation "deep_health.fault" does not exist', data)
        self.assertNotIn(b"\n", data)
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())

    def test_the_database_failing_under_the_view_is_unhealthy_and_never_reported(self):
        interface = Causes(make=lambda: pg.DiskFull("could not extend file: No space left on device"))
        (status, _, data), reports, _ = self.deep_health(interface)
        self.assertEqual(503, status)
        self.assertTrue(data.startswith(b"deep_health.fault unavailable: "), data)
        self.assertEqual([], reports)

    def test_jaaqls_own_check_still_comes_first_and_is_still_a_server_error(self):
        del self.model.query_caches["queries"][QUERY_CACHE_KEY__health]
        interface = Causes(["gateway heartbeat: none received"])
        (status, _, data), reports, required_db = self.deep_health(interface)
        self.assertEqual((500, b"Compiled query '__health__' is not present in the query cache"), (status, data))
        self.assertEqual([], interface.statements)
        required_db.assert_not_called()
        self.assertEqual(1, len(reports))
        self.assertEqual("HttpStatusException: Compiled query '__health__' is not present in the query cache", reports[0]["error_condensed"])


if __name__ == "__main__":
    unittest.main()
