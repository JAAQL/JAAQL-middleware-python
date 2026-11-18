"""
A cloud procedure's args reach it whatever their size up to the request size limit. handle_procedure starts the procedure through sh -c,
whose one argument, the whole command with the args base64-encoded in it, Linux allows at most 128 KiB, so args over about 95,000 bytes of
JSON failed to spawn (E2BIG) and were answered 500 as JAAQL's own server error. Args that make the command longer than
PROCEDURE__max_command_bytes now go to the process's stdin, the marker in their place, and node, preloading jaaql/scripts/webhook_body.mjs
through NODE_OPTIONS, puts them back there as base64, where BATON's cloud runtime reads them; args that fit are passed as before.

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
import unittest
from unittest import mock

from jaaql.constants import WEBHOOK__body_on_stdin
from jaaql.mvc import model
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import SUPER_KEY, APPLICATION
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
        self.environ = mock.patch.dict(os.environ)
        self.environ.start()
        os.environ.pop("NODE_OPTIONS", None)
        self.registration = mock.patch.object(model, "remote_procedure__select", return_value={
            "command": self.command, "access": model.RPC_ACCESS__private})
        self.registration.start()
        self.runs = mock.patch.object(model.subprocess, "run", wraps=subprocess.run)
        self.run_calls = self.runs.start()

    def tearDown(self):
        self.runs.stop()
        self.registration.stop()
        self.environ.stop()
        super().tearDown()

    def call(self, args):
        # The body as a client writes it, its keys in the client's order (the test client's json= would sort them)
        return self.client.post("/remote_procedure", data=json.dumps({"application": APPLICATION, "name": "import", "args": args}),
                                headers={"Content-Type": "application/json", HEADER__security_bypass: SUPER_KEY, HEADER__security: TOKEN})

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


if __name__ == "__main__":
    unittest.main()
