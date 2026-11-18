"""
A webhook's body reaches the webhook byte for byte whatever its size up to the request size limit: JAAQL writes it to the process's stdin and
passes a marker in its place on the command line, where Linux allows one argument at most 128 KiB, and node, preloading
jaaql/scripts/webhook_body.mjs, puts the body back in that place as base64 before the webhook's modules run, which is where BATON's cloud
runtime has always read it. Before, the body went onto the command line, so a body over about 98,000 bytes failed to spawn (E2BIG) and was
answered 500 as JAAQL's own server error. A body over the request size limit (Flask's MAX_CONTENT_LENGTH) is answered 413 and never starts the
webhook. A body's keys are no longer merged with the path's application and name. A worker runs at most WEBHOOK_MAX_RUNNING webhook processes
at once, at most WEBHOOK_MAX_WAITING more waiting for a place in the order they came, and a webhook that finds no place is answered 503
with Retry-After without starting one. None of these is reported to Sentinel; a webhook that crashes still is, as before.

    python -m unittest jaaql.test.test_webhook_body

Needs node on PATH (the JAAQL image has it) and Linux's /proc for the command-line checks; the webhooks are small node scripts that read
their arguments as BATON's initializeWebhook reads them
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from jaaql.constants import ENVIRON__webhook_max_running, ENVIRON__webhook_max_waiting, WEBHOOK__default_max_running, \
    WEBHOOK__default_max_waiting, SLOT__wait_seconds, SLOT__retry_after_seconds, WEBHOOK__body_on_stdin
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_server_errors import ServerErrorCase, ErrorStubModel
from jaaql.test.test_slow_queries import SUPER_KEY, APPLICATION
from jaaql.utilities import process_slots
from monitor.main import HEADER__security_bypass

NODE = shutil.which("node")
WEBHOOK = "hook"
ROUTE = "/webhook/%s/%s" % (APPLICATION, WEBHOOK)
SECURE_ROUTE = "/secure/%s/%s" % (APPLICATION, WEBHOOK)
JSON = {"Content-Type": "application/json"}
KB = 1000

# A webhook as BATON compiles one: an entrypoint run as "node --import ./__imports__.js <entrypoint>", reading its arguments as
# initializeWebhook (BATON.cloud.ts) does, process.argv.slice(2) being [headers, parameters, body, dbms user?], each but the user base64. It
# answers with what it was given: the body's length and SHA-256 as bytes, whether it parses as the JSON sent, its arguments, and the length
# of its own command line as the kernel holds it (/proc/self/cmdline), which the body must not be on
ENTRYPOINT = r"""
import { createHash } from "node:crypto";
import { readFileSync, existsSync } from "node:fs";

const args = process.argv.slice(2);
const headers = JSON.parse(Buffer.from(args[0], "base64").toString());
const parameters = JSON.parse(Buffer.from(args[1], "base64").toString());
const bytes = Buffer.from(args[2], "base64");
let parsed = null;
try { parsed = JSON.parse(bytes.toString()); } catch (_) {}
if (process.env.HOLD_UNTIL) {
	const until = Date.now() + 20000;
	while (!existsSync(process.env.HOLD_UNTIL) && Date.now() < until) { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 20); }
}
let cmdline = -1;
try { cmdline = readFileSync("/proc/self/cmdline").length; } catch (_) {}
console.log(JSON.stringify({ statusCode: 200, headers: { "X-Seen": "yes" }, body: JSON.stringify({
	argc: args.length, length: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex"), parsed, user: args[3] ?? null,
	content_type: headers["Content-Type"] ?? null, parameters, cmdline
}) }));
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_body(size: int, text: str = "x") -> bytes:
    # A JSON object of exactly size bytes: {"v":"xxx..."}
    filler = (text * size).encode("utf-8")[:size - 8]
    body = b'{"v":"' + filler + b'"}'
    assert len(body) == size, (len(body), size)
    return body


class WebhookStubModel(ErrorStubModel):
    handle_webhook = JAAQLModel.handle_webhook
    env_with_super_bypass_key = JAAQLModel.env_with_super_bypass_key


@unittest.skipUnless(NODE, "needs node on PATH")
class WebhookCase(ServerErrorCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.procs = tempfile.mkdtemp(prefix="jaaql-webhook-")
        with open(os.path.join(cls.procs, "__imports__.mjs"), "w") as file:
            file.write("globalThis.IMPORTED = true;\n")
        with open(os.path.join(cls.procs, "entry.mjs"), "w") as file:
            file.write(ENTRYPOINT)
        cls.command = "cd %s && node --import ./__imports__.mjs 'entry.mjs'" % cls.procs

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.procs, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        process_slots.WEBHOOKS.reset()
        self.environ = mock.patch.dict(os.environ)
        self.environ.start()
        os.environ.pop(ENVIRON__webhook_max_running, None)
        self.registered(self.command)
        self.runs = mock.patch.object(model.subprocess, "run", wraps=subprocess.run)
        self.run_calls = self.runs.start()

    def tearDown(self):
        self.runs.stop()
        self.registration.stop()
        self.environ.stop()
        process_slots.WEBHOOKS.reset()
        super().tearDown()

    def make_model(self):
        return WebhookStubModel()

    def registered(self, command):
        # The row set_procedures writes for a webhook
        if getattr(self, "registration", None) is not None:
            self.registration.stop()
        self.registration = mock.patch.object(model, "remote_procedure__select", return_value={
            "command": command, "access": model.RPC_ACCESS__webhook})
        self.registration.start()

    def post(self, body: bytes, route=ROUTE, headers=None):
        return self.client.post(route, data=body, headers=dict(JSON, **(headers or {})))

    def seen(self, data: bytes) -> dict:
        return json.loads(data)


class TestWebhookBody(WebhookCase):

    def assertDelivered(self, body: bytes, route=ROUTE, headers=None, argc=3):
        (status, answer_headers, data), reports = self.answers(lambda: self.post(body, route, headers))
        self.assertEqual(200, status, data[:300])
        self.assertIn(("X-Seen", "yes"), answer_headers)
        seen = self.seen(data)
        self.assertEqual((argc, len(body), sha256(body)), (seen["argc"], seen["length"], seen["sha256"]))
        self.assertEqual(json.loads(body), seen["parsed"])
        if seen["cmdline"] != -1:
            # The command line holds the marker, never the body
            self.assertLess(seen["cmdline"], 4096)
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())
        return seen

    def test_a_150_kb_body_reaches_the_webhook_byte_for_byte(self):
        self.assertDelivered(json_body(150 * KB))

    def test_a_2_mb_body_reaches_the_webhook_byte_for_byte(self):
        self.assertDelivered(json_body(2000 * KB))

    def test_a_body_of_the_size_limit_reaches_the_webhook_and_one_byte_more_is_413_and_starts_nothing(self):
        limit = self.controller.app.config["MAX_CONTENT_LENGTH"]
        self.assertEqual(2 * 1024 * 1024, limit)
        self.assertDelivered(json_body(limit))
        self.run_calls.reset_mock()
        (status, _, _), reports = self.answers(lambda: self.post(json_body(limit + 1)))
        self.assertEqual((413, []), (status, reports))
        self.run_calls.assert_not_called()
        self.assertEqual([], self.lines())
        self.assertEqual(0, process_slots.WEBHOOKS.running())

    def test_a_body_too_big_for_one_argument_failed_to_spawn_before(self):
        # The control: what 5.3.29 did with the same 150 kB body, the body base64-encoded as one argument
        body = json_body(150 * KB)
        with self.assertRaises(OSError) as raised:
            subprocess.run([NODE, os.path.join(self.procs, "entry.mjs"), "e30=", "e30=", __import__("base64").b64encode(body).decode()],
                           capture_output=True)
        self.assertEqual(7, raised.exception.errno)  # E2BIG

    def test_small_unicode_and_list_bodies_reach_the_webhook_as_before(self):
        self.assertDelivered(b'{"a": 1}')
        self.assertDelivered(json.dumps({"naam": "Renée Çelik \U0001F600", "lijst": [1, 2]}, ensure_ascii=False).encode("utf-8"))
        self.assertDelivered(b'[1, 2, 3]')

    def test_a_body_naming_the_application_or_a_name_or_that_is_no_object_reaches_the_webhook(self):
        # Before, the body was merged with the path's application and name: such keys were answered 400 Field duplicated in request, and a
        # JSON string, number or null 500
        self.assertDelivered(b'{"name": "Jane", "application": "other", "email": "jane@example.com"}')
        for body in [b'"just a string"', b'42', b'null']:
            with self.subTest(body=body):
                self.assertDelivered(body)

    def test_a_body_that_is_not_json_is_still_refused_before_the_webhook(self):
        for data, headers in [(b'not json', JSON), (b'', JSON), (b'id=tr_1', {"Content-Type": "application/x-www-form-urlencoded"})]:
            with self.subTest(data=data):
                (status, _, _), reports = self.answers(lambda: self.client.post(ROUTE, data=data, headers=headers))
                self.assertEqual((400, []), (status, reports))
        self.run_calls.assert_not_called()

    def test_the_headers_and_parameters_reach_the_webhook_as_before(self):
        (status, _, data), _ = self.answers(lambda: self.client.post(ROUTE + "?page=2&sort=name", data=b'{"a": 1}', headers=JSON))
        self.assertEqual(200, status)
        seen = self.seen(data)
        self.assertEqual(("application/json", {"page": "2", "sort": "name"}), (seen["content_type"], seen["parameters"]))

    def test_a_secure_webhook_gets_its_body_and_the_user(self):
        seen = self.assertDelivered(json_body(150 * KB), SECURE_ROUTE, {HEADER__security_bypass: SUPER_KEY}, argc=4)
        self.assertIsNotNone(seen["user"])

    def test_the_command_line_has_the_marker_in_the_bodys_place_and_the_preload_first(self):
        self.answers(lambda: self.post(b'{"a": 1}'))
        argv = self.run_calls.call_args[0][0]
        self.assertEqual(["node", "--import", model.WEBHOOK__body_preload_url, "--import", "./__imports__.mjs", "entry.mjs"], argv[:6])
        self.assertTrue(model.WEBHOOK__body_preload_url.startswith("file:///"))
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(model.__file__), "..", "scripts", "webhook_body.mjs")))
        self.assertEqual(WEBHOOK__body_on_stdin, argv[8])
        self.assertEqual(b'{"a": 1}', self.run_calls.call_args[1]["input"])

    def test_a_command_that_is_not_node_reads_the_body_on_its_stdin(self):
        self.registered('"%s" -c "import hashlib, json, sys; data = sys.stdin.buffer.read(); print(json.dumps(dict(statusCode=200, '
                        'body=json.dumps(dict(argv=sys.argv[1:], length=len(data), sha256=hashlib.sha256(data).hexdigest())))))"'
                        % sys.executable)
        body = json_body(300 * KB)
        (status, _, data), reports = self.answers(lambda: self.post(body))
        seen = self.seen(data)
        self.assertEqual((200, [], len(body), sha256(body)), (status, reports, seen["length"], seen["sha256"]))
        self.assertEqual(WEBHOOK__body_on_stdin, seen["argv"][2])

    def test_a_webhook_that_crashes_without_reading_a_large_body_is_still_reported_once(self):
        self.registered("sh -c 'exit 3'")
        (status, _, data), reports = self.answers(lambda: self.post(json_body(1000 * KB)))
        self.assertEqual(500, status)
        self.assertEqual(1, len(reports))
        self.assertEqual("remote-procedure:" + APPLICATION + "/" + WEBHOOK, reports[0]["source_file"])
        self.assertIn("the remote procedure exited with code 3", reports[0]["stacktrace"])
        self.assertEqual(0, process_slots.WEBHOOKS.running())


class TestWebhookBound(WebhookCase):

    def setUp(self):
        super().setUp()
        os.environ.pop(ENVIRON__webhook_max_waiting, None)
        self.release_file = os.path.join(self.procs, "release-%d-%s" % (os.getpid(), self._testMethodName))

    def tearDown(self):
        os.environ.pop("HOLD_UNTIL", None)
        if os.path.exists(self.release_file):
            os.unlink(self.release_file)
        super().tearDown()

    def busy(self, count: int):
        for _ in range(count):
            self.assertTrue(process_slots.WEBHOOKS.claim(APPLICATION, "elsewhere"))

    def refusals(self) -> list:
        return [line for line in self.printed.getvalue().splitlines() if line.startswith("Webhook ")]

    def clear_printed(self):
        self.printed.seek(0)
        self.printed.truncate(0)

    def until(self, condition, seconds: float = 10):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(condition())

    def in_background(self, client=None, body=None):
        # A webhook request on a thread of its own; the answer lands in the returned dict
        answer = {}
        client = client or self.controller.app.test_client()
        thread = threading.Thread(target=lambda: answer.update(res=client.post(ROUTE, data=body or json_body(150 * KB), headers=JSON)))
        thread.start()
        return thread, answer

    def test_a_webhook_finding_no_place_and_no_room_to_wait_is_503_with_retry_after_never_started_and_never_reported(self):
        os.environ[ENVIRON__webhook_max_running] = "2"
        os.environ[ENVIRON__webhook_max_waiting] = "0"
        self.busy(2)
        self.clear_printed()
        (status, headers, data), reports = self.answers(lambda: self.post(json_body(150 * KB)))
        self.assertEqual((503, b"Too many webhooks are running. Try again later", []), (status, data, reports))
        self.assertIn(("Retry-After", str(SLOT__retry_after_seconds)), headers)
        self.assertIn(("Content-Type", "text/plain; charset=utf-8"), headers)
        self.run_calls.assert_not_called()
        self.assertEqual([], self.lines())
        self.assertEqual((2, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))
        # Printed once, for the first of the three requests answers() made
        self.assertEqual(["Webhook %s/%s answered 503: this worker already runs 2 webhook processes (WEBHOOK_MAX_RUNNING) and 0 more wait "
                          "(WEBHOOK_MAX_WAITING); 1 refused since the last line" % (APPLICATION, WEBHOOK)], self.refusals())
        process_slots.WEBHOOKS.release()
        (status, _, _), _ = self.answers(lambda: self.post(b'{"a": 1}'))
        self.assertEqual(200, status)
        self.assertEqual(1, process_slots.WEBHOOKS.running())

    def test_a_webhook_that_waits_in_vain_is_503_after_the_wait(self):
        os.environ[ENVIRON__webhook_max_running] = "1"
        self.busy(1)
        self.clear_printed()
        with mock.patch.object(process_slots.WEBHOOKS, "wait_seconds", 0.3):
            started = time.monotonic()
            res = self.post(b'{"a": 1}')
            waited = time.monotonic() - started
        self.assertEqual(503, res.status_code)
        self.assertEqual(str(SLOT__retry_after_seconds), res.headers["Retry-After"])
        self.assertGreaterEqual(waited, 0.3)
        self.assertLess(waited, 3)
        self.run_calls.assert_not_called()
        self.assertEqual((1, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))
        self.assertEqual(["Webhook %s/%s answered 503: this worker already runs 1 webhook processes (WEBHOOK_MAX_RUNNING) and no place "
                          "came free in 0.3 s; 1 refused since the last line" % (APPLICATION, WEBHOOK)], self.refusals())
        self.assertEqual([], self.lines())
        self.assertNoReport()

    def test_a_secure_webhook_and_a_get_are_bounded_too(self):
        os.environ[ENVIRON__webhook_max_running] = "1"
        os.environ[ENVIRON__webhook_max_waiting] = "0"
        self.busy(1)
        for request in [lambda: self.post(b'{"a": 1}', SECURE_ROUTE, {HEADER__security_bypass: SUPER_KEY}),
                        lambda: self.client.get(ROUTE + "?page=1")]:
            (status, headers, _), reports = self.answers(request)
            self.assertEqual((503, []), (status, reports))
            self.assertIn(("Retry-After", str(SLOT__retry_after_seconds)), headers)
        self.run_calls.assert_not_called()

    def test_a_burst_is_served_in_the_order_it_came_and_beyond_the_room_to_wait_refused(self):
        # One place and room for one to wait: the first webhook runs until the file appears, the second waits for its place, the third is
        # refused at once; once the first ends the second runs, and both get their bodies
        os.environ[ENVIRON__webhook_max_running] = "1"
        os.environ[ENVIRON__webhook_max_waiting] = "1"
        os.environ["HOLD_UNTIL"] = self.release_file
        first, first_answer = self.in_background(body=json_body(150 * KB))
        self.until(lambda: process_slots.WEBHOOKS.running() == 1)
        second, second_answer = self.in_background(body=json_body(200 * KB))
        try:
            self.until(lambda: process_slots.WEBHOOKS.waiting() == 1)
            started = time.monotonic()
            third = self.post(b'{"a": 1}')
            self.assertLess(time.monotonic() - started, 1)
            self.assertEqual(503, third.status_code)
        finally:
            open(self.release_file, "w").close()
            first.join(30)
            second.join(30)
        self.assertEqual([200, 200], [first_answer["res"].status_code, second_answer["res"].status_code])
        self.assertEqual([150 * KB, 200 * KB], [self.seen(answer["res"].get_data())["length"] for answer in [first_answer, second_answer]])
        self.assertEqual((0, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))
        self.assertEqual(200, self.post(b'{"a": 1}').status_code)
        self.assertNoReport()

    def claim_in_background(self, name: str, served: list):
        # A claim on a thread of its own, as a waiting request is a greenlet of its own in a worker: once it has a place it notes its name
        # and gives the place back
        def claim():
            if process_slots.WEBHOOKS.claim(APPLICATION, name):
                served.append(name)
                process_slots.WEBHOOKS.release()
            else:
                served.append("refused " + name)
        thread = threading.Thread(target=claim)
        thread.start()
        return thread

    def test_the_waiting_are_served_in_the_order_they_came(self):
        # One place, held; A, B and C come one after the other and wait. Each place given back goes to the one that has waited longest
        os.environ[ENVIRON__webhook_max_running] = "1"
        os.environ[ENVIRON__webhook_max_waiting] = "3"
        self.busy(1)
        served, threads = [], []
        for count, name in enumerate(["A", "B", "C"], start=1):
            threads.append(self.claim_in_background(name, served))
            self.until(lambda: process_slots.WEBHOOKS.waiting() == count)
        process_slots.WEBHOOKS.release()
        for thread in threads:
            thread.join(10)
        self.assertEqual(["A", "B", "C"], served)
        self.assertEqual((0, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))

    def test_a_newcomer_does_not_take_a_place_from_one_that_waits(self):
        os.environ[ENVIRON__webhook_max_running] = "1"
        os.environ[ENVIRON__webhook_max_waiting] = "1"
        self.busy(1)
        served = []
        waiter = self.claim_in_background("A", served)
        self.until(lambda: process_slots.WEBHOOKS.waiting() == 1)
        # Now a place is free by the setting, but A waits for one: the newcomer does not take it, and finding no room to wait is refused
        os.environ[ENVIRON__webhook_max_running] = "2"
        self.assertFalse(process_slots.WEBHOOKS.claim(APPLICATION, WEBHOOK))
        self.assertEqual((1, 1), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))
        process_slots.WEBHOOKS.release()
        waiter.join(10)
        self.assertEqual(["A"], served)
        self.assertEqual((0, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))

    def test_a_waiter_that_is_interrupted_leaves_the_queue(self):
        os.environ[ENVIRON__webhook_max_running] = "1"
        self.busy(1)
        with mock.patch.object(process_slots.threading.Event, "wait", side_effect=RuntimeError("killed")):
            with self.assertRaises(RuntimeError):
                process_slots.WEBHOOKS.claim(APPLICATION, WEBHOOK)
        self.assertEqual((1, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))
        process_slots.WEBHOOKS.release()
        self.assertEqual(0, process_slots.WEBHOOKS.running())

    def test_a_place_is_given_back_whatever_the_webhook_does(self):
        os.environ[ENVIRON__webhook_max_running] = "1"
        for command in [self.command, "sh -c 'exit 3'", "sh -c 'echo not-json'", "cd /nonexistent-%d && node x.mjs" % os.getpid()]:
            with self.subTest(command=command):
                self.registered(command)
                self.post(json_body(150 * KB))
                self.assertEqual((0, 0), (process_slots.WEBHOOKS.running(), process_slots.WEBHOOKS.waiting()))

    def test_the_settings_their_defaults_lifted_and_unreadable(self):
        self.assertEqual((4, 32, 5, 5), (WEBHOOK__default_max_running, WEBHOOK__default_max_waiting, SLOT__wait_seconds,
                                         SLOT__retry_after_seconds))
        for setting, read, default in [(ENVIRON__webhook_max_running, process_slots.WEBHOOKS.max_running, 4),
                                       (ENVIRON__webhook_max_waiting, process_slots.WEBHOOKS.max_waiting, 32)]:
            for value, expected in [(None, default), ("3", 3), ("0", 0), ("-2", 0), ("many", default), ("", default)]:
                with self.subTest(setting=setting, value=value):
                    if value is None:
                        os.environ.pop(setting, None)
                    else:
                        os.environ[setting] = value
                    self.assertEqual(expected, read())
            os.environ.pop(setting, None)
        # Lifted: whatever runs, a webhook runs
        os.environ[ENVIRON__webhook_max_running] = "0"
        self.busy(50)
        self.assertEqual(200, self.post(b'{"a": 1}').status_code)

    def test_refusals_are_printed_at_most_once_a_minute_with_their_count(self):
        os.environ[ENVIRON__webhook_max_running] = "1"
        os.environ[ENVIRON__webhook_max_waiting] = "0"
        self.busy(1)
        clock = [1000.0]
        with mock.patch.object(process_slots, "_now", lambda: clock[0]):
            self.clear_printed()
            for advance in [0, 10, 49, 1, 5]:
                clock[0] += advance
                self.assertFalse(process_slots.WEBHOOKS.claim(APPLICATION, WEBHOOK))
        lines = self.refusals()
        self.assertEqual(2, len(lines))
        self.assertTrue(lines[0].endswith("; 1 refused since the last line"), lines[0])
        self.assertTrue(lines[1].endswith("; 3 refused since the last line"), lines[1])


class TestWebhookDocumentation(unittest.TestCase):

    def test_the_webhook_routes_declare_the_413_and_the_503(self):
        from jaaql.documentation.documentation_public import DOCUMENTATION__webhook, DOCUMENTATION__secure_webhook
        for documentation in [DOCUMENTATION__webhook, DOCUMENTATION__secure_webhook]:
            codes = {method.method: sorted(int(response.code) for response in method.responses) for method in documentation.methods}
            self.assertEqual({"GET": [200, 503], "POST": [200, 413, 503]}, codes)


if __name__ == "__main__":
    unittest.main()
