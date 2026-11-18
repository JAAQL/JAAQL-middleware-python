"""
The verification mail JAAQL has Keycloak send (PUT /admin/realms/{realm}/users/{id}/send-verify-email): from /resend-verify-email, which the
Resend button of BATON's email_verify page calls, and when a new account first signs in.

/resend-verify-email takes the address as a JSON body, {"email": ...}. It answers 200 when Keycloak sent the mail, and also for an empty
address, one that is no Keycloak user's and one Keycloak has already verified, without asking Keycloak to send anything, so the route, which
needs no login, cannot mail a verified account. When Keycloak answers the send with an error it never answers as if the mail went: the
Keycloak e-mail guard (jaaql/keycloak:26.8.3 and later) puts its baton-email-delivery required action on a user whose address the mail
service refused, so the user's next sign-in asks for another address, and that is 422 with error_code 1025 (VerificationEmailRefused); any
other error answer is 502 with error_code 1026 (VerificationEmailNotSent), reported to Sentinel as a server error. Keycloak out of reach
stays the 500 with error_code 1099 it was. A form body, as BATON's Resend button sent before (and JAAQL then answered 400 Field duplicated in
request), is refused with 400 and nothing is sent. At a new account's first sign-in a failure is only logged. No log line, answer or report
names the address.

An account is sent at most one mail a minute and five an hour per process (RESEND_VERIFY_EMAIL_COOLDOWN_SECONDS,
RESEND_VERIFY_EMAIL_MAX_PER_HOUR), the first sign-in's send included; a resend inside those limits sends nothing and answers as the last send
did, without a second report. The tests of what Keycloak answers lift both limits; TestResendLimits keeps them. While sends succeed, the
status of the answer does not tell an unverified account from an unknown or verified address; a failed send (422, 502) and the time a send
takes do, which is accepted so that the user is told when the mail did not go

    python -m unittest jaaql.test.test_verify_email

The unit tests need only the package's requirements: Keycloak is a stub HTTP server on 127.0.0.1 with the token route, the user lookup,
the user and send-verify-email, and a send it refuses adds the required action as the e-mail guard does
"""
import io
import json
import os
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest import mock
from urllib.parse import urlparse, parse_qs

import requests

from jaaql.constants import KEYCLOAK__email_delivery_required_action, ENVIRON__resend_verify_email_cooldown_seconds, \
    ENVIRON__resend_verify_email_max_per_hour
from jaaql.documentation.documentation_internal import DOCUMENTATION__resend_verify_email
from jaaql.exceptions.jaaql_interpretable_handled_errors import VerificationEmailRefused, VerificationEmailNotSent
from jaaql.generated_constants import RESPONSE_CODE_LOOKUP
from jaaql.mvc.model import JAAQLModel
from jaaql.openapi.swagger_documentation import SwaggerFlatResponse, RESPONSE__200_ok
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import closed_port
from jaaql.utilities import sentinel, verify_email_resends

REALM = "pubbl"
# Built from parts, so that a search of the log for the address cannot find the test's own source
LOCAL_PART = "jane.doe"
DOMAIN = "mailbox.example"
EMAIL = LOCAL_PART + "@" + DOMAIN
USER_ID = "4f9c2a8e-0b1d-4e3a-9c55-7d2e1f0a6b31"
REFUSED_BODY = b'{"errorMessage":"Failed to send verify email"}'

ANSWER__refused = {"error_code": 1025, "message": "The mail service refused the verification email. Sign in again to enter a different "
                   "address.", "column_name": None, "descriptor": None, "index": None, "set": None, "table_name": None}
ANSWER__not_sent = {"error_code": 1026, "message": "The verification email could not be sent. Please try again in a moment.",
                    "column_name": None, "descriptor": None, "index": None, "set": None, "table_name": None}


class FakeKeycloak:
    """
    Keycloak's token route and the admin routes JAAQL calls. users maps a username to its id. send answers send-verify-email with
    (status, body); verified names the usernames whose emailVerified is true; refuse makes it answer 500 and put the e-mail guard's
    required action on the user first, as the guard does in a transaction of its own. user_status, when set, is the answer to GET of a
    user. Every request is recorded as (method, path)
    """

    def __init__(self, users=None, send=(204, b""), refuse=False, user_status=None, required_actions=None, verified=()):
        self.users = dict(users if users is not None else {EMAIL: USER_ID})
        self.verified = set(verified)
        self.send = send
        self.refuse = refuse
        self.user_status = user_status
        self.required_actions = {user_id: list(required_actions or []) for user_id in self.users.values()}
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def answer(self, status, body=b""):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                fake.requests.append(("POST", urlparse(self.path).path))
                self.answer(200, b'{"access_token": "admin-token"}')

            def do_GET(self):
                url = urlparse(self.path)
                fake.requests.append(("GET", url.path))
                if url.path == "/admin/realms/%s/users" % REALM:
                    username = parse_qs(url.query).get("username", [""])[0]
                    found = []
                    if username in fake.users:
                        found = [{"id": fake.users[username], "username": username, "emailVerified": username in fake.verified}]
                    self.answer(200, json.dumps(found).encode())
                elif url.path.startswith("/admin/realms/%s/users/" % REALM):
                    if fake.user_status is not None:
                        self.answer(fake.user_status, b'{"error": "unknown_error"}')
                        return
                    user_id = url.path.rsplit("/", 1)[1]
                    self.answer(200, json.dumps({"id": user_id, "requiredActions": fake.required_actions.get(user_id, [])}).encode())
                else:
                    self.answer(404, b'{"error": "Not Found"}')

            def do_PUT(self):
                path = urlparse(self.path).path
                fake.requests.append(("PUT", path))
                user_id = path.split("/")[-2]
                if fake.refuse:
                    if KEYCLOAK__email_delivery_required_action not in fake.required_actions[user_id]:
                        fake.required_actions[user_id].append(KEYCLOAK__email_delivery_required_action)
                    self.answer(500, REFUSED_BODY)
                else:
                    self.answer(*fake.send)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def sends(self):
        return [path for method, path in self.requests if method == "PUT"]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


SEND_PATH = "/admin/realms/%s/users/%s/send-verify-email" % (REALM, USER_ID)
USER_PATH = "/admin/realms/%s/users/%s" % (REALM, USER_ID)


def resend_limits(cooldown=None, per_hour=None):
    """
    os.environ with the resend limits set, each the default where None
    """
    environ = {key: value for key, value in os.environ.items()
               if key not in (ENVIRON__resend_verify_email_cooldown_seconds, ENVIRON__resend_verify_email_max_per_hour)}
    if cooldown is not None:
        environ[ENVIRON__resend_verify_email_cooldown_seconds] = str(cooldown)
    if per_hour is not None:
        environ[ENVIRON__resend_verify_email_max_per_hour] = str(per_hour)
    return mock.patch.dict(os.environ, environ, clear=True)


class VerifyEmailCase(ServerErrorCase):
    # The resend limits of the test: lifted, so that every resend asks Keycloak, for the tests of what Keycloak answers
    LIMITS = {"cooldown": 0, "per_hour": 0}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # As create_app's produce_all_documentation leaves it at boot: a method that declares no 200 answers 200 OK
        for method in DOCUMENTATION__resend_verify_email.methods:
            if not any(response.code == 200 for response in method.responses):
                method.responses.append(SwaggerFlatResponse(RESPONSE__200_ok))

    def setUp(self):
        super().setUp()
        verify_email_resends.reset()
        self.addCleanup(verify_email_resends.reset)
        limits = resend_limits(**self.LIMITS)
        limits.start()
        self.addCleanup(limits.stop)

    def keycloak(self, **kwargs):
        fake = FakeKeycloak(**kwargs)
        self.addCleanup(fake.close)
        environ = mock.patch.dict(os.environ, {"KEYCLOAK_URL": fake.url, "KEYCLOAK_REALM": REALM})
        environ.start()
        self.addCleanup(environ.stop)
        return fake

    def resend(self, email=EMAIL):
        return self.client.post("/resend-verify-email", json={"email": email})

    def assertNoAddress(self, text):
        self.assertNotIn(LOCAL_PART, text)
        self.assertNotIn(DOMAIN, text)
        self.assertNotIn("jane", text)


class TestResendVerifyEmail(VerifyEmailCase):

    def test_a_mail_keycloak_sent_answers_200(self):
        fake = self.keycloak()
        (status, _, data), reports = self.answers(self.resend)
        self.assertEqual(200, status)
        self.assertEqual([SEND_PATH] * 3, fake.sends())
        # Nothing more is asked of Keycloak once it has sent the mail
        self.assertNotIn(("GET", USER_PATH), fake.requests)
        self.assertEqual([], reports)

    def test_a_refused_address_answers_422_with_error_code_1025_and_is_not_reported(self):
        fake = self.keycloak(refuse=True)
        (status, _, data), reports = self.answers(self.resend)
        self.assertEqual((422, ANSWER__refused), (status, json.loads(data)))
        self.assertEqual(422, RESPONSE_CODE_LOOKUP[1025])
        self.assertEqual(3, len(fake.sends()))
        # The required actions are read after the send Keycloak refused
        self.assertEqual(("GET", USER_PATH), fake.requests[fake.requests.index(("PUT", SEND_PATH)) + 1])
        self.assertEqual([], reports)
        self.assertNoAddress(self.printed.getvalue())
        self.assertIn("Keycloak did not send the verification email to Keycloak user %s: it answered 500 (Failed to send verify email), "
                      "and the mail service refused the address" % USER_ID, self.printed.getvalue())

    def test_a_user_asked_for_another_address_before_is_still_told_to_sign_in_again(self):
        # The action already on the user from an earlier refusal: their next sign-in asks for another address whatever this send's error was
        self.keycloak(send=(500, REFUSED_BODY), required_actions=["VERIFY_EMAIL", KEYCLOAK__email_delivery_required_action])
        response = self.resend()
        self.assertEqual((422, 1025), (response.status_code, response.get_json()["error_code"]))

    def test_any_other_error_answer_is_502_with_error_code_1026_reported_without_the_address(self):
        self.assertEqual(502, RESPONSE_CODE_LOOKUP[1026])
        for send in [(500, REFUSED_BODY), (400, b'{"errorMessage":"User email missing"}'), (400, b'{"errorMessage":"User is disabled"}'),
                     (403, b'{"error":"HTTP 403 Forbidden"}'), (503, b"<html>Service Unavailable</html>")]:
            with self.subTest(status=send[0], body=send[1]):
                self.printed.seek(0)
                self.printed.truncate(0)
                fake = self.keycloak(send=send, required_actions=["VERIFY_EMAIL"])
                (status, _, data), reports = self.answers(self.resend)
                self.assertEqual((502, ANSWER__not_sent), (status, json.loads(data)))
                self.assertEqual(3, len(fake.sends()))
                self.assertEqual(1, len(reports))
                self.assertServerContract(reports[0])
                self.assertTrue(reports[0]["error_condensed"].startswith("VerificationEmailNotSent"), reports[0]["error_condensed"])
                self.assertEqual("jaaql/mvc/model.py", reports[0]["source_file"])
                self.assertNoAddress(json.dumps(reports[0]))
                self.assertNoAddress(self.printed.getvalue())
                self.assertIn("it answered %d" % send[0], self.printed.getvalue())

    def test_required_actions_keycloak_does_not_give_count_as_not_sent(self):
        # Without the user's required actions there is no sign that the next sign-in asks for another address
        self.keycloak(refuse=True, user_status=500)
        response = self.resend()
        self.assertEqual((502, 1026), (response.status_code, response.get_json()["error_code"]))
        self.assertIn("could not read the required actions of Keycloak user %s: HTTPError (Keycloak answered 500)" % USER_ID,
                      self.printed.getvalue())
        self.assertNoAddress(self.printed.getvalue())

    def test_an_empty_or_unknown_address_answers_200_and_sends_nothing(self):
        fake = self.keycloak()
        for email in ["", "   ", "nobody@" + DOMAIN]:
            with self.subTest(email=email):
                (status, _, data), reports = self.answers(lambda: self.resend(email))
                self.assertEqual((200, []), (status, reports))
        self.assertEqual([], fake.sends())
        # The empty addresses never reached Keycloak: only the unknown one was looked up (three times, once per answer)
        self.assertEqual(3, len([1 for method, path in fake.requests if method == "GET"]))

    def test_an_address_keycloak_has_verified_answers_200_and_sends_nothing(self):
        fake = self.keycloak(verified=[EMAIL])
        (status, _, data), reports = self.answers(self.resend)
        self.assertEqual((200, []), (status, reports))
        self.assertEqual([], fake.sends())

    def test_an_unknown_address_answers_exactly_as_a_sent_mail(self):
        self.keycloak()
        sent = self.resend()
        unknown = self.resend("nobody@" + DOMAIN)
        self.assertEqual((sent.status_code, sent.get_data()), (unknown.status_code, unknown.get_data()))
        verified = FakeKeycloak(verified=[EMAIL])
        self.addCleanup(verified.close)
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": verified.url}):
            already = self.resend()
        self.assertEqual((sent.status_code, sent.get_data()), (already.status_code, already.get_data()))

    def test_keycloak_out_of_reach_answers_500_with_error_code_1099_as_before(self):
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": "http://127.0.0.1:%d" % closed_port(), "KEYCLOAK_REALM": REALM}):
            (status, _, data), reports = self.answers(self.resend)
        self.assertEqual((500, 1099), (status, json.loads(data)["error_code"]))
        self.assertEqual(1, len(reports))
        self.assertNoAddress(json.dumps(reports[0]))

    def test_a_form_body_is_refused_and_sends_nothing(self):
        # As BATON's Resend button posted it before (application/x-www-form-urlencoded): JAAQL answered 400 Field duplicated in request
        # and never read the address. The address is now a JSON body, so a form is refused before anything is asked of Keycloak
        fake = self.keycloak()
        response = self.client.post("/resend-verify-email", data="email=" + LOCAL_PART + "%40" + DOMAIN,
                                    content_type="application/x-www-form-urlencoded")
        self.assertEqual(400, response.status_code)
        self.assertEqual([], fake.requests)

    def test_the_body_takes_only_the_address(self):
        fake = self.keycloak()
        self.assertEqual(400, self.client.post("/resend-verify-email", json={}).status_code)
        self.assertEqual(400, self.client.post("/resend-verify-email", json={"email": EMAIL, "application": "pubbl"}).status_code)
        self.assertEqual([], fake.requests)

    def test_the_documentation_names_the_contract(self):
        method = DOCUMENTATION__resend_verify_email.methods[0]
        self.assertEqual(["email"], [argument.name for argument in method.body])
        self.assertEqual({422, 502, 500}, {int(exception.code) for exception in method.exceptions})
        for text in ["error_code 1025", "error_code 1026", "error_code 1099", "JSON body", "RESEND_VERIFY_EMAIL_COOLDOWN_SECONDS",
                     "RESEND_VERIFY_EMAIL_MAX_PER_HOUR", "per gunicorn worker"]:
            self.assertIn(text, method.description)
        # Not the claim that the answer hides which addresses have an account
        self.assertNotIn("does not tell which", method.description)


class Clock:
    """
    verify_email_resends' monotonic clock, moved on by hand
    """

    def __init__(self, case):
        self.now = 1000.0
        patcher = mock.patch.object(verify_email_resends, "_now", side_effect=lambda: self.now)
        patcher.start()
        case.addCleanup(patcher.stop)


def answered(response):
    return response.status_code, response.get_data()


class TestResendLimits(VerifyEmailCase):
    # The default limits: one mail a minute, five an hour
    LIMITS = {}

    def setUp(self):
        super().setUp()
        self.clock = Clock(self)

    def reports(self):
        self.assertTrue(sentinel.wait_idle(10))
        return self.stub.bodies()

    def test_the_default_limits(self):
        self.assertEqual((60, 5), verify_email_resends.limits())

    def test_two_quick_resends_send_one_mail_and_answer_alike(self):
        fake = self.keycloak()
        first = self.resend()
        self.clock.now += 59
        second = self.resend()
        self.assertEqual(200, first.status_code)
        self.assertEqual(answered(first), answered(second))
        self.assertEqual([SEND_PATH], fake.sends())
        self.assertIn("Verification email to Keycloak user %s not sent again within the resend limits, answered as its last send: sent"
                      % USER_ID, self.printed.getvalue())
        self.assertNoAddress(self.printed.getvalue())

    def test_a_resend_after_the_cooldown_sends_again(self):
        fake = self.keycloak()
        self.resend()
        self.clock.now += 60
        self.assertEqual(200, self.resend().status_code)
        self.assertEqual([SEND_PATH] * 2, fake.sends())

    def test_at_most_five_mails_an_hour(self):
        fake = self.keycloak()
        for minute in range(10):
            self.assertEqual(200, self.resend().status_code)
            self.clock.now += 61
        self.assertEqual(5, len(fake.sends()))
        # An hour after the first, one more may go
        self.clock.now = 1000.0 + 3600
        self.resend()
        self.assertEqual(6, len(fake.sends()))
        self.resend()
        self.assertEqual(6, len(fake.sends()))

    def test_a_failed_send_counts_and_is_answered_again_without_a_second_report(self):
        fake = self.keycloak(send=(500, REFUSED_BODY))
        first = self.resend()
        self.assertEqual(1, len(self.reports()))
        self.stub.reset()
        self.clock.now += 30
        again = self.resend()
        self.assertEqual((502, ANSWER__not_sent), (again.status_code, again.get_json()))
        self.assertEqual(answered(first), answered(again))
        self.assertEqual([SEND_PATH], fake.sends())
        self.assertEqual([], self.reports())
        self.assertNoAddress(self.printed.getvalue())
        # Once the cooldown is over, the next resend asks Keycloak again
        fake.send = (204, b"")
        self.clock.now += 30
        self.assertEqual(200, self.resend().status_code)
        self.assertEqual([SEND_PATH] * 2, fake.sends())

    def test_a_refused_address_is_answered_again_as_refused(self):
        fake = self.keycloak(refuse=True)
        self.assertEqual(422, self.resend().status_code)
        self.clock.now += 10
        again = self.resend()
        self.assertEqual((422, ANSWER__refused), (again.status_code, again.get_json()))
        self.assertEqual(1, len(fake.sends()))
        self.assertEqual([], self.reports())

    def test_keycloak_out_of_reach_for_the_send_counts_as_not_sent(self):
        fake = self.keycloak()
        with mock.patch.object(type(self.model), "_kc_send_verify_email", side_effect=requests.exceptions.ConnectionError("gone")):
            response = self.resend()
        self.assertEqual((500, 1099), (response.status_code, json.loads(response.get_data())["error_code"]))
        self.clock.now += 10
        response = self.resend()
        self.assertEqual((502, 1026), (response.status_code, json.loads(response.get_data())["error_code"]))
        self.assertEqual([], fake.sends())

    def test_the_first_sign_in_send_counts(self):
        fake = self.keycloak()
        self.model._send_new_account_verification_email(EMAIL)
        self.clock.now += 5
        self.assertEqual(200, self.resend().status_code)
        self.assertEqual([SEND_PATH], fake.sends())

    def test_the_first_sign_in_send_is_not_held_back(self):
        fake = self.keycloak()
        self.resend()
        self.model._send_new_account_verification_email(EMAIL)
        self.assertEqual([SEND_PATH] * 2, fake.sends())

    def test_unknown_and_verified_addresses_are_not_counted(self):
        self.keycloak(verified=[EMAIL])
        self.resend()
        self.resend("nobody@" + DOMAIN)
        self.assertEqual(0, len(verify_email_resends._accounts))

    def test_each_account_has_limits_of_its_own(self):
        other = "c2d1e0f9-8a7b-4c6d-9e5f-0a1b2c3d4e5f"
        fake = self.keycloak(users={EMAIL: USER_ID, "j.smith@" + DOMAIN: other})
        self.resend()
        self.resend("j.smith@" + DOMAIN)
        self.assertEqual(2, len(fake.sends()))


class TestResendLimitSettings(unittest.TestCase):

    def setUp(self):
        verify_email_resends.reset()
        self.addCleanup(verify_email_resends.reset)
        self.clock = Clock(self)

    def test_settings(self):
        for cooldown, per_hour, expected in [(None, None, (60, 5)), (0, 0, (0, 0)), (-5, -1, (0, 0)), (120, 2, (120, 2)),
                                             ("soon", "many", (60, 5))]:
            with self.subTest(cooldown=cooldown, per_hour=per_hour), resend_limits(cooldown, per_hour):
                self.assertEqual(expected, verify_email_resends.limits())

    def test_lifted_limits_hold_nothing_back(self):
        with resend_limits(0, 0):
            self.assertEqual([None] * 20, [verify_email_resends.claim(USER_ID) for _ in range(20)])
            # Only the last send is kept
            self.assertEqual(1, len(verify_email_resends._accounts[USER_ID][0]))

    def test_an_account_not_sent_to_for_an_hour_is_forgotten(self):
        with resend_limits():
            verify_email_resends.claim(USER_ID)
            self.clock.now += 3600
            verify_email_resends.claim("someone else")
            self.assertEqual(["someone else"], list(verify_email_resends._accounts))

    def test_a_cooldown_longer_than_an_hour_is_kept_for_its_length(self):
        with resend_limits(7200, 0):
            verify_email_resends.claim(USER_ID)
            self.clock.now += 3601
            self.assertEqual(verify_email_resends.OUTCOME__sent, verify_email_resends.claim(USER_ID))
            self.clock.now += 3600
            self.assertIsNone(verify_email_resends.claim(USER_ID))

    def test_beyond_the_cap_the_account_longest_not_sent_to_is_forgotten(self):
        with resend_limits(), mock.patch.object(verify_email_resends, "RESEND_VERIFY_EMAIL__max_tracked_accounts", 3):
            for user_id in ["a", "b", "c", "d"]:
                self.assertIsNone(verify_email_resends.claim(user_id))
                self.clock.now += 1
            self.assertEqual(["b", "c", "d"], list(verify_email_resends._accounts))
            self.assertIsNone(verify_email_resends.claim("a"))
            self.assertEqual(verify_email_resends.OUTCOME__sent, verify_email_resends.claim("d"))

    def test_a_settled_outcome_is_answered(self):
        with resend_limits():
            verify_email_resends.claim(USER_ID)
            verify_email_resends.settle(USER_ID, verify_email_resends.OUTCOME__refused)
            self.assertEqual(verify_email_resends.OUTCOME__refused, verify_email_resends.claim(USER_ID))
            # A settle for an account no longer kept count of changes nothing
            verify_email_resends.settle("unknown", verify_email_resends.OUTCOME__not_sent)
            self.assertNotIn("unknown", verify_email_resends._accounts)


class TestNewAccountVerificationEmail(unittest.TestCase):
    """
    The send at a new account's first sign-in (_send_new_account_verification_email, called by the code exchange): never fatal, and never
    an address in the log
    """

    def setUp(self):
        self.model = JAAQLModel.__new__(JAAQLModel)
        self.model.vault = SimpleNamespace(has_obj=lambda key: False)
        verify_email_resends.reset()
        self.addCleanup(verify_email_resends.reset)

    def send(self, keycloak_url):
        printed = io.StringIO()
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": keycloak_url, "KEYCLOAK_REALM": REALM}), redirect_stdout(printed):
            self.model._send_new_account_verification_email(EMAIL)
        text = printed.getvalue()
        self.assertNotIn(LOCAL_PART, text)
        self.assertNotIn(DOMAIN, text)
        return text

    def fake(self, **kwargs):
        fake = FakeKeycloak(**kwargs)
        self.addCleanup(fake.close)
        return fake

    def test_a_sent_mail_is_logged_by_the_keycloak_user_id(self):
        fake = self.fake()
        self.assertEqual("Verification email sent to Keycloak user %s\n" % USER_ID, self.send(fake.url))
        self.assertEqual([SEND_PATH], fake.sends())

    def test_a_refused_address_is_only_logged(self):
        fake = self.fake(refuse=True)
        text = self.send(fake.url)
        self.assertIn("the mail service refused the address", text)
        self.assertTrue(text.endswith("Warning: the verification email of a new account was not sent: VerificationEmailRefused\n"), text)

    def test_any_other_error_answer_is_only_logged(self):
        fake = self.fake(send=(500, REFUSED_BODY))
        self.assertTrue(self.send(fake.url).endswith("not sent: VerificationEmailNotSent\n"))

    def test_an_address_without_a_keycloak_user_is_logged_without_it(self):
        fake = self.fake(users={})
        self.assertEqual("Warning: no Keycloak user has the new account's address as its username, no verification email sent\n",
                         self.send(fake.url))
        self.assertEqual([], fake.sends())

    def test_keycloak_out_of_reach_is_logged_without_the_url(self):
        # The error's own text names the URL, the user lookup's query string included
        text = self.send("http://127.0.0.1:%d" % closed_port())
        self.assertEqual("Warning: the verification email of a new account was not sent: ConnectionError\n", text)

    def test_the_lookup_refused_is_logged_by_its_status(self):
        fake = self.fake()

        def forbidden(token, username):
            # As raise_for_status raises it, naming the URL with the address in its query string
            raise requests.exceptions.HTTPError("403 Client Error: Forbidden for url: %s/admin/realms/%s/users?username=%s&exact=true"
                                                % (fake.url, REALM, username), response=SimpleNamespace(status_code=403))

        with mock.patch.object(JAAQLModel, "_kc_find_user_id_by_username", side_effect=forbidden):
            text = self.send(fake.url)
        self.assertEqual("Warning: the verification email of a new account was not sent: HTTPError (Keycloak answered 403)\n", text)


class TestErrorClasses(unittest.TestCase):

    def test_codes_statuses_and_messages(self):
        refused, not_sent = VerificationEmailRefused(), VerificationEmailNotSent()
        self.assertEqual((1025, 422, None), (refused.error_code, refused.response_code, refused.descriptor))
        self.assertEqual((1026, 502, None), (not_sent.error_code, not_sent.response_code, not_sent.descriptor))
        self.assertEqual("baton-email-delivery", KEYCLOAK__email_delivery_required_action)


if __name__ == "__main__":
    unittest.main()
