"""
The HTTP methods of JAAQL's routes. Every route that takes GET also answers HEAD, as HTTP has it (RFC 9110, 9.3.2): with the status and
the headers the GET would have had and no body, so that an uptime checker sending HEAD to /internal/is-alive or /internal/deep-health
(neither needs a login) sees what Pingdom's GET sees. A method a route does not take is answered 405 with an Allow header naming the
methods it does, as the client's and never as JAAQL's server error: no SERVER ERROR line, no report to Sentinel.

    python -m unittest jaaql.test.test_http_methods

Needs only the package's requirements, as jaaql.test.test_server_errors: the lookup connection is a stand-in database interface
"""
import os
import unittest
from unittest import mock

import psycopg.errors as pg

from jaaql.constants import ENVIRON__deep_health_application, QUERY_CACHE_KEY__health
from jaaql.db import db_utils_no_circ
from jaaql.mvc import model
from jaaql.mvc.base_controller import BaseJAAQLController
from jaaql.mvc.model import JAAQLModel
from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, SwaggerFlatResponse, SwaggerException, REST__GET, \
    REST__POST
from jaaql.test.test_deep_health_application import Causes
from jaaql.test.test_health_checks import Version, DEEP_HEALTH, IS_ALIVE, JAAQL_FAILED, KEEP_ALIVE_FAILED
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import TimedInterface, SUPER_KEY
from monitor.main import HEADER__security_bypass

USER_AGENT = {"User-Agent": "UptimeChecker/1.0 (Test)"}
UNDECLARED = ["POST", "PUT", "DELETE", "PATCH"]
TWO_DOCUMENTATIONS = "/test/two-documentations"


def allowed(answered):
    return sorted(method.strip() for method in dict(answered[1])["Allow"].split(","))


def documentation(method, security, body, name="Test"):
    return SwaggerDocumentation(tags="Test", security=security,
                                methods=SwaggerMethod(name=name, description=name, method=method, response=SwaggerFlatResponse(body=body)))


class MethodCase(ServerErrorCase):

    def setUp(self):
        super().setUp()
        self.healthy(self.model)

    def tearDown(self):
        self.reset_reasons()
        for patch in self.real:
            patch.stop()
        super().tearDown()

    def healthy(self, stub_model):
        # The health routes as on a box: the health query in the cache, the real JAAQLModel checks on the lookup connection
        stub_model.query_caches["queries"][QUERY_CACHE_KEY__health] = ["SELECT 1 AS health"]
        stub_model.jaaql_lookup_connection = TimedInterface()
        self.real = [mock.patch.object(stub_model, "deep_health", lambda: JAAQLModel.deep_health(stub_model), create=True),
                     mock.patch.object(stub_model, "is_alive", lambda: JAAQLModel.is_alive(stub_model), create=True)]
        for patch in self.real:
            patch.start()
        self.reset_reasons()

    @staticmethod
    def reset_reasons():
        for reason in (model.DEEP_HEALTH__unavailable, model.DEEP_HEALTH__jaaql_failed, model.IS_ALIVE__failed):
            reason.reset()

    def clear_log(self):
        self.printed.truncate(0)
        self.printed.seek(0)
        self.reset_reasons()

    def request(self, method, route, **kwargs):
        """
        The answer to one request, made as answers() makes it (reporting, Sentinel unset, reporting off: the same answer), and its reports
        """
        headers = kwargs.pop("headers", USER_AGENT)
        self.clear_log()
        return self.answers(lambda: self.client.open(route, method=method, headers=headers, **kwargs))

    def assertHeadIsGet(self, route, **kwargs):
        """
        HEAD answers route as GET does, without the body; returns both answers and the HEAD's reports
        """
        got, _ = self.request("GET", route, **dict(kwargs))
        head, reports = self.request("HEAD", route, **dict(kwargs))
        self.assertEqual((got[0], got[1], b""), head)
        self.assertNotEqual(b"", got[2])
        return got, head, reports


class TestHeadIsGetWithoutTheBody(MethodCase):

    def test_deep_health_and_is_alive(self):
        for route, interface in [(DEEP_HEALTH, TimedInterface()), (IS_ALIVE, Version("PostgreSQL 18.1 on x86_64-pc-linux-gnu"))]:
            with self.subTest(route=route):
                self.model.jaaql_lookup_connection = interface
                got, (_, headers, _), reports = self.assertHeadIsGet(route)
                self.assertEqual((200, b'"OK"\n'), (got[0], got[2]))
                self.assertEqual([("Content-Length", "5"), ("Content-Type", "application/json")], headers)
                self.assertEqual([], reports)
                self.assertEqual([], self.lines())

    def test_deep_health_of_an_application_with_a_cause(self):
        # Sentinel's box: JAAQL_DEEP_HEALTH_APPLICATION=sentinel, the gateway's heartbeat missing
        with mock.patch.dict(os.environ, {ENVIRON__deep_health_application: "sentinel"}), \
                mock.patch.object(db_utils_no_circ, "get_required_db", return_value=Causes(["gateway heartbeat: none received"])):
            got, _, reports = self.assertHeadIsGet(DEEP_HEALTH)
        self.assertEqual((503, b"Deep health: gateway heartbeat: none received"), (got[0], got[2]))
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())

    def test_a_failure_of_jaaqls_own_check_is_answered_and_reported_as_for_get(self):
        text = 'could not extend file "base/16384/2619": No space left on device'
        self.model.jaaql_lookup_connection = Causes(make=lambda: pg.DiskFull(text))
        for route, body, line in [(DEEP_HEALTH, JAAQL_FAILED, "Deep health answered 503"), (IS_ALIVE, KEEP_ALIVE_FAILED, "Is alive answered 503")]:
            with self.subTest(route=route):
                got, _, reports = self.assertHeadIsGet(route)
                self.assertEqual((503, body), (got[0], got[2]))
                # Reported by the database error, as the GET is, never as a failure of the routing (AttributeError)
                self.assertEqual(1, len(reports))
                self.assertServerContract(reports[0])
                self.assertEqual("DiskFull 53100: " + text, reports[0]["error_condensed"])
                self.assertIn("\nRoute: HEAD " + route + " on ", reports[0]["stacktrace"])
                self.assertNotIn("AttributeError", reports[0]["stacktrace"])
                lines = self.lines()
                self.assertEqual(2, len(lines), lines)
                for printed in lines:
                    self.assertRegex(printed, r"^SERVER ERROR DiskFull at jaaql/mvc/model\.py:\d+ \(HEAD %s, [^)]*\) answered 503( - |$)" % route)
                self.assertEqual(1, len([printed for printed in self.printed.getvalue().splitlines() if printed.startswith(line)]))

    def test_while_jaaql_is_not_installed(self):
        # As reboot.sh and reset_app.sh poll is-alive at boot: 503, neither reported nor explained
        self.model.has_installed = False
        self.model.jaaql_lookup_connection = None
        for route, body in [(IS_ALIVE, KEEP_ALIVE_FAILED), (DEEP_HEALTH, JAAQL_FAILED)]:
            with self.subTest(route=route):
                got, _, reports = self.assertHeadIsGet(route)
                self.assertEqual((503, body, []), (got[0], got[2], reports))
                self.assertEqual([], [printed for printed in self.printed.getvalue().splitlines()
                                      if printed.startswith(("SERVER ERROR", "Deep health ", "Is alive "))])

    def test_a_get_route_of_a_route_that_also_takes_post(self):
        # /build-time: HEAD runs the GET, never the POST
        with mock.patch.object(self.model, "get_last_successful_build_time", create=True, return_value=1735462031), \
                mock.patch.object(self.model, "set_last_successful_build_time", create=True) as set_time:
            got, _, reports = self.assertHeadIsGet("/build-time")
        self.assertEqual((200, b"1735462031\n", []), (got[0], got[2], reports))
        set_time.assert_not_called()

    def test_documents_fetches_and_never_renders(self):
        # /documents: GET (is_get) fetches a rendered document's URL, POST renders one. A HEAD is a GET
        url = "https://lesbij.example/api/rendered_documents/b47dc954-d608-4e1b-8a8c-d8b754ee554b"
        with mock.patch.object(self.model, "fetch_document", create=True, return_value=url) as fetch, \
                mock.patch.object(self.model, "render_document", create=True) as render:
            got, _, reports = self.assertHeadIsGet("/documents", query_string={"document_id": "b47dc954-d608-4e1b-8a8c-d8b754ee554b"},
                                                   headers=dict(USER_AGENT, **{HEADER__security_bypass: SUPER_KEY}))
        self.assertEqual((200, ('"%s"\n' % url).encode(), []), (got[0], got[2], reports))
        self.assertEqual(6, fetch.call_count)
        render.assert_not_called()


class TestUndeclaredMethodsAre405(MethodCase):

    def test_a_method_the_health_routes_do_not_take(self):
        for route in (DEEP_HEALTH, IS_ALIVE):
            for method in UNDECLARED:
                with self.subTest(route=route, method=method):
                    answered, reports = self.request(method, route)
                    self.assertEqual(405, answered[0])
                    self.assertEqual(["GET", "HEAD", "OPTIONS"], allowed(answered))
                    self.assertEqual([], reports)
        self.assertEqual([], self.lines())

    def test_head_on_a_route_without_get(self):
        answered, reports = self.request("HEAD", "/submit")
        self.assertEqual((405, ["OPTIONS", "POST"], []), (answered[0], allowed(answered), reports))
        self.assertEqual([], self.lines())

    def test_options_is_still_answered(self):
        answered, reports = self.request("OPTIONS", DEEP_HEALTH)
        self.assertEqual((200, ["GET", "HEAD", "OPTIONS"], []), (answered[0], allowed(answered), reports))

    def test_a_method_that_reaches_the_route_but_no_documentation_of_it_declares(self):
        # Flask passes on only the methods the route takes, each of which its documentations declare; should one ever reach the route
        # undeclared, it is answered as one the route does not take
        with mock.patch.object(BaseJAAQLController, "resolve_method", return_value=(None, None)):
            for method in ("GET", "HEAD"):
                with self.subTest(method=method):
                    answered, reports = self.request(method, DEEP_HEALTH)
                    self.assertEqual((405, "GET, HEAD, OPTIONS", []), (answered[0], dict(answered[1])["Allow"], reports))
        self.assertEqual([], self.lines())


class TestRoutesOfMoreThanOneDocumentation(MethodCase):

    def publish(self):
        @self.controller.publish_route(TWO_DOCUMENTATIONS, [documentation(REST__GET, False, "read"), documentation(REST__POST, True, "written")])
        def two_documentations(ip_address: str):
            return "read" if self.controller.is_get() else "written"

    def test_each_method_is_answered_by_its_own_documentation(self):
        self.publish()
        got, _, reports = self.assertHeadIsGet(TWO_DOCUMENTATIONS)
        self.assertEqual((200, b'"read"\n', []), (got[0], got[2], reports))
        # The POST's documentation is secured, the GET's is not
        refused, reports = self.request("POST", TWO_DOCUMENTATIONS)
        self.assertEqual((401, []), (refused[0], reports))
        written, reports = self.request("POST", TWO_DOCUMENTATIONS, headers=dict(USER_AGENT, **{HEADER__security_bypass: SUPER_KEY}))
        self.assertEqual((200, b'"written"\n', []), (written[0], written[2], reports))
        answered, reports = self.request("PUT", TWO_DOCUMENTATIONS)
        self.assertEqual((405, ["GET", "HEAD", "OPTIONS", "POST"], []), (answered[0], allowed(answered), reports))
        self.assertEqual([], self.lines())

    def test_a_method_declared_twice_is_refused_when_the_route_is_published(self):
        with self.assertRaisesRegex(SwaggerException, "HTTP method 'GET' was duplicated"):
            SwaggerDocumentation(tags="Test", methods=[SwaggerMethod(name="One", description="One", method=REST__GET),
                                                       SwaggerMethod(name="Two", description="Two", method=REST__GET)])
        with self.assertRaisesRegex(Exception, "HTTP method 'GET' is declared twice for the route '/test/twice'"):
            self.controller.publish_route("/test/twice", [documentation(REST__GET, False, "one"), documentation(REST__GET, False, "two")])


class TestOnABoxThatIsNoContainer(MethodCase):
    """
    JAAQL run outside its container (is_container false) answers CORS: its routes declare OPTIONS themselves
    """

    def setUp(self):
        super().setUp()
        for patch in self.real:
            patch.stop()
        stub_model = self.make_model()
        stub_model.is_container = False
        self.controller = self.make_controller(stub_model)
        self.healthy(stub_model)

    def test_head_options_and_an_undeclared_method(self):
        got, (_, headers, _), reports = self.assertHeadIsGet(DEEP_HEALTH)
        self.assertEqual((200, b'"OK"\n', []), (got[0], got[2], reports))
        self.assertIn(("Access-Control-Allow-Origin", "*"), headers)
        options, reports = self.request("OPTIONS", DEEP_HEALTH)
        self.assertEqual((200, []), (options[0], reports))
        answered, reports = self.request("PUT", DEEP_HEALTH)
        self.assertEqual((405, ["GET", "HEAD", "OPTIONS"], []), (answered[0], allowed(answered), reports))
        self.assertEqual([], self.lines())


if __name__ == "__main__":
    unittest.main()
