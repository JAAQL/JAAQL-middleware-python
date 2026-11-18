"""
A cloud procedure's args reach it whatever their size up to the request size limit. handle_procedure starts the procedure through sh -c,
whose one argument, the whole command with the args base64-encoded in it, Linux allows at most 128 KiB, so args over about 95,000 bytes of
JSON failed to spawn (E2BIG) and were answered 500 as JAAQL's own server error. Args that make the command longer than
PROCEDURE__max_command_bytes now go to the process's stdin, the marker in their place, and node, preloading jaaql/scripts/webhook_body.mjs
through NODE_OPTIONS, puts them back there as base64, where BATON's cloud runtime reads them; args that fit are passed as before. A public
procedure, which the anonymous user may call, runs in one of PUBLIC_PROCEDURE_MAX_RUNNING places per worker, a few more waiting for one, and
one that finds no place is answered 503 with Retry-After without starting; private ones are not bounded.

    python -m unittest jaaql.test.test_procedure_args

Needs node on PATH (the JAAQL image has it); the procedure is a small node script that reads its arguments as BATON's initialize reads them
"""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

from jaaql.constants import WEBHOOK__body_on_stdin, ENVIRON__public_procedure_max_running, ENVIRON__public_procedure_max_waiting, \
    ENVIRON__webhook_max_running, ENVIRON__webhook_max_waiting, SLOT__retry_after_seconds
from jaaql.mvc import model
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import SUPER_KEY, APPLICATION
from jaaql.utilities import process_slots
from monitor.main import HEADER__security_bypass, HEADER__security

NODE = shutil.which("node")
TOKEN = "a.token"

# A cloud procedure as BATON compiles one, reading its arguments as initialize (BATON.cloud.ts) does for a private or public procedure:
# process.argv[2..6] are the args, the access token, the username, the IP address and the account id, each base64. It answers with what it
# was given, and the length of its own command line as the kernel holds it
PROCEDURE = r"""
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const decoded = (idx) => Buffer.from(process.argv[idx], "base64").toString();
const text = decoded(2);
let cmdline = -1;
try { cmdline = readFileSync("/proc/self/cmdline").length; } catch (_) {}
console.log(JSON.stringify({
	argc: process.argv.length - 2, length: text.length, sha256: createHash("sha256").update(text).digest("hex"), args: JSON.parse(text).note ?? null,
	token: decoded(3), ip: decoded(5), node_options: process.env.NODE_OPTIONS ?? null, cmdline
}));
"""


def args_of(size: int) -> dict:
    # Args whose JSON is size bytes long: {"note": "...", "filler": "xxx..."}
    return {"note": "kept", "filler": "x" * (size - len(json.dumps({"note": "kept", "filler": ""})))}


@unittest.skipUnless(NODE, "needs node on PATH")
class TestProcedureArgs(ServerErrorCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.procs = tempfile.mkdtemp(prefix="jaaql-procedure-")
        with open(os.path.join(cls.procs, "__imports__.mjs"), "w") as file:
            file.write("globalThis.IMPORTED = true;\n")
        with open(os.path.join(cls.procs, "proc.mjs"), "w") as file:
            file.write(PROCEDURE)
        cls.command = "cd %s && node --import ./__imports__.mjs 'proc.mjs'" % cls.procs

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.procs, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        process_slots.PUBLIC_PROCEDURES.reset()
        process_slots.WEBHOOKS.reset()
        self.environ = mock.patch.dict(os.environ)
        self.environ.start()
        for setting in ["NODE_OPTIONS", ENVIRON__public_procedure_max_running, ENVIRON__public_procedure_max_waiting,
                        ENVIRON__webhook_max_running, ENVIRON__webhook_max_waiting]:
            os.environ.pop(setting, None)
        self.registration = None
        self.registered(self.command, model.RPC_ACCESS__private)
        self.runs = mock.patch.object(model.subprocess, "run", wraps=subprocess.run)
        self.run_calls = self.runs.start()

    def tearDown(self):
        self.runs.stop()
        self.registration.stop()
        self.environ.stop()
        process_slots.PUBLIC_PROCEDURES.reset()
        process_slots.WEBHOOKS.reset()
        super().tearDown()

    def registered(self, command, access):
        # The row set_procedures writes for a procedure
        if self.registration is not None:
            self.registration.stop()
        self.registration = mock.patch.object(model, "remote_procedure__select", return_value={"command": command, "access": access})
        self.registration.start()

    def call(self, args, client=None):
        # The body as a client writes it, its keys in the client's order (the test client's json= would sort them)
        return (client or self.client).post("/remote_procedure", data=json.dumps({"application": APPLICATION, "name": "import", "args": args}),
                                            headers={"Content-Type": "application/json", HEADER__security_bypass: SUPER_KEY,
                                                     HEADER__security: TOKEN})

    def assertReached(self, args, on_stdin: bool):
        (status, _, data), reports = self.answers(lambda: self.call(args))
        self.assertEqual(200, status, data[:300])
        seen = json.loads(data)
        text = json.dumps(args)
        self.assertEqual((5, len(text), hashlib.sha256(text.encode()).hexdigest(), "kept", TOKEN, "127.0.0.1"),
                         (seen["argc"], seen["length"], seen["sha256"], seen["args"], seen["token"], seen["ip"]))
        self.assertEqual([], reports)
        self.assertEqual([], self.lines())
        command, kwargs = self.run_calls.call_args[0][0], self.run_calls.call_args[1]
        self.assertEqual(on_stdin, WEBHOOK__body_on_stdin in command)
        if on_stdin:
            self.assertEqual(text, kwargs["input"])
            if seen["cmdline"] != -1:
                self.assertLess(seen["cmdline"], 4096)
        else:
            self.assertIn(base64.b64encode(text.encode()).decode(), command)
            self.assertEqual((None, None), (kwargs["input"], kwargs["env"]))
        return seen

    def test_args_of_150_kb_and_of_the_request_size_limit_reach_the_procedure(self):
        seen = self.assertReached(args_of(150 * 1000), on_stdin=True)
        self.assertEqual("--import=" + model.WEBHOOK__body_preload_url, seen["node_options"])
        self.assertReached(args_of(1900 * 1000), on_stdin=True)

    def test_args_that_fit_on_the_command_line_are_passed_there_as_before(self):
        seen = self.assertReached({"note": "kept"}, on_stdin=False)
        self.assertIsNone(seen["node_options"])
        self.assertReached(args_of(70 * 1000), on_stdin=False)

    def test_args_either_side_of_where_the_command_moves_them_to_stdin(self):
        # Base64 makes 4 bytes of 3: 70 kB of JSON keeps the command under PROCEDURE__max_command_bytes, 76 kB takes it over
        self.assertEqual(100000, model.PROCEDURE__max_command_bytes)
        for size, on_stdin in [(20, False), (70 * 1000, False), (76 * 1000, True), (90 * 1000, True)]:
            with self.subTest(size=size):
                self.assertReached(args_of(size), on_stdin)

    def test_the_boxs_own_node_options_are_kept(self):
        os.environ["NODE_OPTIONS"] = "--max-old-space-size=256"
        seen = self.assertReached(args_of(150 * 1000), on_stdin=True)
        self.assertEqual("--max-old-space-size=256 --import=" + model.WEBHOOK__body_preload_url, seen["node_options"])

    def test_args_too_big_for_one_argument_failed_to_spawn_before(self):
        # The control: what 5.3.29 did with the same 150 kB of args, base64-encoded into the one argument of sh -c
        text = json.dumps(args_of(150 * 1000))
        with self.assertRaises(OSError) as raised:
            subprocess.run(self.command + " " + base64.b64encode(text.encode()).decode(), shell=True, capture_output=True)
        self.assertEqual(7, raised.exception.errno)  # E2BIG


class TestPublicProcedureBound(TestProcedureArgs):

    def setUp(self):
        super().setUp()
        self.registered(self.command, model.RPC_ACCESS__public)

    def busy(self, count: int, slots=process_slots.PUBLIC_PROCEDURES):
        for _ in range(count):
            self.assertTrue(slots.claim(APPLICATION, "elsewhere"))

    def refusals(self) -> list:
        return [line for line in self.printed.getvalue().splitlines() if line.startswith("Public procedure ")]

    def until(self, condition, seconds: float = 10):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(condition())

    def test_args_of_150_kb_and_of_the_request_size_limit_reach_the_procedure(self):
        # A public procedure that finds a place runs as a private one does, and gives the place back
        super().test_args_of_150_kb_and_of_the_request_size_limit_reach_the_procedure()
        self.assertEqual((0, 0), (process_slots.PUBLIC_PROCEDURES.running(), process_slots.PUBLIC_PROCEDURES.waiting()))

    def test_a_public_procedure_finding_no_place_and_no_room_to_wait_is_503_with_retry_after_never_started_and_never_reported(self):
        os.environ[ENVIRON__public_procedure_max_running] = "1"
        os.environ[ENVIRON__public_procedure_max_waiting] = "0"
        self.busy(1)
        (status, headers, data), reports = self.answers(lambda: self.call({"note": "kept"}))
        self.assertEqual((503, b"Too many public procedures are running. Try again later", []), (status, data, reports))
        self.assertIn(("Retry-After", str(SLOT__retry_after_seconds)), headers)
        self.assertIn(("Content-Type", "text/plain; charset=utf-8"), headers)
        self.run_calls.assert_not_called()
        self.assertEqual([], self.lines())
        self.assertEqual((1, 0), (process_slots.PUBLIC_PROCEDURES.running(), process_slots.PUBLIC_PROCEDURES.waiting()))
        self.assertEqual(["Public procedure %s/import answered 503: this worker already runs 1 public procedure processes "
                          "(PUBLIC_PROCEDURE_MAX_RUNNING) and 0 more wait (PUBLIC_PROCEDURE_MAX_WAITING); 1 refused since the last line"
                          % APPLICATION], self.refusals())

    def test_a_public_procedure_waits_for_a_place_and_then_runs(self):
        os.environ[ENVIRON__public_procedure_max_running] = "1"
        os.environ[ENVIRON__public_procedure_max_waiting] = "1"
        self.busy(1)
        answer = {}
        client = self.controller.app.test_client()
        thread = threading.Thread(target=lambda: answer.update(res=self.call({"note": "kept"}, client)))
        thread.start()
        try:
            self.until(lambda: process_slots.PUBLIC_PROCEDURES.waiting() == 1)
            self.run_calls.assert_not_called()
        finally:
            process_slots.PUBLIC_PROCEDURES.release()
            thread.join(30)
        self.assertEqual(200, answer["res"].status_code, answer["res"].get_data()[:300])
        self.assertEqual("kept", json.loads(answer["res"].get_data())["args"])
        self.assertEqual((0, 0), (process_slots.PUBLIC_PROCEDURES.running(), process_slots.PUBLIC_PROCEDURES.waiting()))
        self.assertNoReport()

    def test_a_private_procedure_is_not_bounded(self):
        os.environ[ENVIRON__public_procedure_max_running] = "1"
        os.environ[ENVIRON__public_procedure_max_waiting] = "0"
        self.busy(1)
        self.registered(self.command, model.RPC_ACCESS__private)
        self.assertReached({"note": "kept"}, on_stdin=False)
        self.assertEqual(1, process_slots.PUBLIC_PROCEDURES.running())

    def test_webhooks_and_public_procedures_have_places_of_their_own(self):
        for setting in [ENVIRON__public_procedure_max_running, ENVIRON__webhook_max_running]:
            os.environ[setting] = "1"
        for setting in [ENVIRON__public_procedure_max_waiting, ENVIRON__webhook_max_waiting]:
            os.environ[setting] = "0"
        self.busy(1, process_slots.WEBHOOKS)
        self.assertReached({"note": "kept"}, on_stdin=False)
        self.busy(1)
        self.assertFalse(process_slots.WEBHOOKS.claim(APPLICATION, "hook"))
        process_slots.WEBHOOKS.release()
        self.assertTrue(process_slots.WEBHOOKS.claim(APPLICATION, "hook"))

    def test_a_place_is_given_back_whatever_the_procedure_does(self):
        os.environ[ENVIRON__public_procedure_max_running] = "1"
        for command in [self.command, "sh -c 'exit 3'", "echo not-json", "cd /nonexistent-%d && node x.mjs" % os.getpid()]:
            with self.subTest(command=command):
                self.registered(command, model.RPC_ACCESS__public)
                self.call(args_of(150 * 1000))
                self.assertEqual((0, 0), (process_slots.PUBLIC_PROCEDURES.running(), process_slots.PUBLIC_PROCEDURES.waiting()))

    def test_the_settings_and_their_defaults(self):
        slots = process_slots.PUBLIC_PROCEDURES
        self.assertEqual(("PUBLIC_PROCEDURE_MAX_RUNNING", "PUBLIC_PROCEDURE_MAX_WAITING", 4, 32),
                         (ENVIRON__public_procedure_max_running, ENVIRON__public_procedure_max_waiting, slots.max_running(),
                          slots.max_waiting()))
        os.environ[ENVIRON__public_procedure_max_running] = "2"
        os.environ[ENVIRON__public_procedure_max_waiting] = "-1"
        self.assertEqual((2, 0), (slots.max_running(), slots.max_waiting()))
        # Lifted: whatever runs, a public procedure runs
        os.environ[ENVIRON__public_procedure_max_running] = "0"
        self.busy(50)
        self.assertReached({"note": "kept"}, on_stdin=False)


class TestRemoteProcedureDocumentation(unittest.TestCase):

    def test_the_route_allows_any_answer_and_declares_the_503(self):
        from jaaql.documentation.documentation_public import DOCUMENTATION__remote_procedures
        from jaaql.openapi.swagger_documentation import RES__allow_all
        method = DOCUMENTATION__remote_procedures.methods[0]
        self.assertIs(RES__allow_all, method.responses[0])
        self.assertEqual([200, 503], sorted(int(response.code) for response in method.responses))


if __name__ == "__main__":
    unittest.main()
