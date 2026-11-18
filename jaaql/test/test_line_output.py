"""
Every line a gunicorn worker prints reaches gunicorn.log whole: jaaql.utilities.line_output, which gunicorn_config.py's on_starting installs
in the master, writes all the complete lines it holds in one write(), so lines that processes print at the same moment into the log, opened
for appending, are never joined or cut, none is lost, and the lines of one process keep their order, stdout and stderr together. Python's
own streams wrote print()'s pieces one by one (unbuffered), or 8 KiB at a time wherever a line ended (buffered).

    python -m unittest jaaql.test.test_line_output

The race runs in a process of its own that forks the printing processes (Linux, macOS)
"""
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import jaaql
from jaaql.utilities import line_output
from jaaql.utilities.line_output import LineWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(jaaql.__file__)))
GUNICORN_CONFIG = os.path.join(ROOT, "docker", "gunicorn_config.py")

# PROCESSES processes, forked by one that installed line_output (or not, "python"), start at once and each print LINES lines of known
# lengths, one in 50 of 20,000 characters, by print() of one string, of several pieces, and to stderr, into one file opened for appending.
# The parent then checks every line and prints "<intact> <damaged> <out of order>"
RACE = r"""
import os, re, sys
mode, log, processes, lines = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
size_of = lambda j: 20000 if j % 50 == 0 else (j * 7919) % 3000
report = os.fdopen(os.dup(1), "w")
log_file = open(log, "a+")
os.dup2(log_file.fileno(), 1)
os.dup2(log_file.fileno(), 2)
if mode == "fixed":
    from jaaql.utilities import line_output
    line_output.install()
    print("a line the parent has not ended,", end="")
gate_r, gate_w = os.pipe()
children = []
for i in range(processes):
    pid = os.fork()
    if pid == 0:
        os.close(gate_w)
        os.read(gate_r, 1)
        for j in range(lines):
            pad = "x" * size_of(j)
            if j % 3 == 0:
                print("worker %d line %d %s end" % (i, j, pad))
            elif j % 3 == 1:
                print("worker", i, "line", j, pad, "end", file=sys.stderr)
            else:
                print("worker %d line %d" % (i, j), pad, "end")
        sys.exit(0)
    children.append(pid)
os.close(gate_r)
os.close(gate_w)
for pid in children:
    os.waitpid(pid, 0)
if mode == "fixed":
    print(" ended by the parent")
sys.stdout.flush()
pattern = re.compile(r"^worker (\d+) line (\d+) (x*) end$")
last, intact, damaged, order, parents = {}, 0, 0, 0, 0
for line in open(log, encoding="utf-8"):
    line = line.rstrip("\n")
    if line == "a line the parent has not ended, ended by the parent":
        parents += 1
        continue
    match = pattern.match(line)
    if not match or len(match.group(3)) != size_of(int(match.group(2))):
        damaged += 1
        continue
    i, j = int(match.group(1)), int(match.group(2))
    order += last.get(i, -1) >= j
    last[i] = j
    intact += 1
report.write("%d %d %d %d\n" % (intact, damaged, order, parents))
"""

# A process that has written a line not complete forks; the child prints a line of its own and exits, then the parent ends its line
FORK = r"""
import os, sys
from jaaql.utilities.line_output import LineWriter
writer = LineWriter(os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))
writer.write("the parent's line")
pid = os.fork()
if pid == 0:
    print("the child's line", file=writer)
    writer.flush()
    os._exit(0)
os.waitpid(pid, 0)
print(", ended by the parent", file=writer)
"""


def run_script(case: unittest.TestCase, script: str, *args: str, unbuffered: bool = False) -> str:
    # The script in a process of its own, which forks without the test runner's threads, with this jaaql first on its path
    with tempfile.TemporaryDirectory(prefix="jaaql-lines-") as directory:
        path = os.path.join(directory, "script.py")
        with open(path, "w", encoding="utf-8") as file:
            file.write(script)
        environ = {key: value for key, value in os.environ.items() if key != "PYTHONUNBUFFERED"}
        environ["PYTHONPATH"] = ROOT + os.pathsep + environ.get("PYTHONPATH", "")
        if unbuffered:
            environ["PYTHONUNBUFFERED"] = "1"
        result = subprocess.run([sys.executable, "-B", path, *args], capture_output=True, text=True, env=environ, timeout=300)
        case.assertEqual(0, result.returncode, result.stderr[-2000:])
        return result.stdout


class Raw(io.RawIOBase):
    """
    A file descriptor's writes as they come
    """

    def __init__(self):
        super().__init__()
        self.writes = []

    def writable(self):
        return True

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)


class TestLineWriter(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="jaaql-lines-")
        self.path = os.path.join(self.directory.name, "gunicorn.log")
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        self.writes = []
        real_write = os.write
        self.recording = mock.patch.object(line_output.os, "write", side_effect=lambda fd, data: self.writes.append(bytes(data)) or
                                           real_write(fd, data))
        self.recording.start()
        self.writer = LineWriter(self.fd, "utf-8", "strict", "<stdout>")

    def tearDown(self):
        self.recording.stop()
        os.close(self.fd)
        self.directory.cleanup()

    def logged(self) -> bytes:
        with open(self.path, "rb") as file:
            return file.read()

    def test_a_print_of_several_pieces_is_one_write(self):
        print("SERVER ERROR", "Webhook a/b", 503, file=self.writer)
        print("Webhook a/b answered 503", file=self.writer)
        self.assertEqual([b"SERVER ERROR Webhook a/b 503\n", b"Webhook a/b answered 503\n"], self.writes)
        self.assertEqual(b"SERVER ERROR Webhook a/b 503\nWebhook a/b answered 503\n", self.logged())

    def test_python_s_own_unbuffered_stream_wrote_the_pieces_one_by_one(self):
        # The control: sys.stdout as PYTHONUNBUFFERED builds it, a TextIOWrapper writing through to the file descriptor
        raw = Raw()
        stream = io.TextIOWrapper(raw, encoding="utf-8", write_through=True)
        print("Webhook a/b answered 503", file=stream)
        self.assertEqual([b"Webhook a/b answered 503", b"\n"], raw.writes)

    def test_a_line_is_held_until_it_is_complete_and_all_complete_lines_go_in_one_write(self):
        self.writer.write("first ")
        self.writer.write("half")
        self.assertEqual([], self.writes)
        self.writer.write(" of it\nsecond\nthird, not yet")
        self.assertEqual([b"first half of it\nsecond\n"], self.writes)
        self.writer.write(" done\n")
        self.assertEqual(b"first half of it\nsecond\nthird, not yet done\n", self.logged())
        self.assertEqual(2, len(self.writes))

    def test_flush_and_close_write_a_line_not_complete(self):
        self.writer.write("no newline yet")
        self.writer.flush()
        self.assertEqual(b"no newline yet", self.logged())
        self.writer.flush()
        self.writer.write(", then the rest")
        self.writer.close()
        self.assertEqual(b"no newline yet, then the rest", self.logged())
        self.assertTrue(self.writer.closed)
        os.fstat(self.fd)

    def test_a_line_longer_than_the_most_held_is_written_as_it_is(self):
        self.writer.write("y" * (line_output.LINE__max_pending_bytes - 1))
        self.assertEqual([], self.writes)
        self.writer.write("yz")
        self.assertEqual([line_output.LINE__max_pending_bytes + 1], [len(data) for data in self.writes])

    def test_a_long_line_is_one_write(self):
        print("x" * 300000, file=self.writer)
        self.assertEqual([300001], [len(data) for data in self.writes])

    def test_text_is_encoded_as_the_stream_was_and_bytes_go_to_the_same_line(self):
        print("Renée Çelik \U0001F600", file=self.writer)
        self.writer.write("half, ")
        self.writer.buffer.write(b"bytes\n")
        self.assertEqual("Renée Çelik \U0001F600\nhalf, bytes\n".encode("utf-8"), self.logged())
        stderr = LineWriter(self.fd, "ascii", "backslashreplace")
        print("Renée", file=stderr)
        self.assertTrue(self.logged().endswith(b"Ren\\xe9e\n"))
        with self.assertRaises(TypeError):
            self.writer.write(b"not text")

    def test_it_looks_like_a_text_stream(self):
        self.assertEqual((self.fd, "utf-8", "strict", "<stdout>", True, True, False, False),
                         (self.writer.fileno(), self.writer.encoding, self.writer.errors, self.writer.name, self.writer.line_buffering,
                          self.writer.writable(), self.writer.readable(), self.writer.isatty()))
        self.assertIsInstance(self.writer, io.TextIOBase)
        self.writer.writelines(["a\n", "b\n"])
        self.assertEqual(b"a\nb\n", self.logged())

    def test_a_write_the_system_refuses_is_dropped_never_raised(self):
        self.recording.stop()
        with mock.patch.object(line_output.os, "write", side_effect=OSError(28, "No space left on device")):
            print("lost on a full disk", file=self.writer)
        self.recording.start()
        print("written once there is room", file=self.writer)
        self.assertEqual(b"written once there is room\n", self.logged())

    def interrupting(self, *handlers):
        """
        os.write recording what it is given, its first writes each interrupted by the next of handlers, as a signal handler runs in the
        thread it interrupts (post_worker_init's prints "Received cache flush instruction")
        """
        self.recording.stop()
        self.addCleanup(self.recording.start)
        real_write = os.write
        pending = list(handlers)

        def write(fd, data):
            self.writes.append(bytes(data))
            if pending:
                pending.pop(0)()
            return real_write(fd, data)
        return mock.patch.object(line_output.os, "write", side_effect=write)

    def test_a_signal_handler_printing_while_a_line_is_written_is_written_after_it_whole(self):
        with self.interrupting(lambda: print("Received cache flush instruction", file=self.writer)):
            print("SERVER ERROR X at y answered 500", file=self.writer)
        # One write per line, print()'s two pieces of the handler's line included, so no other process's write can land between them
        self.assertEqual([b"SERVER ERROR X at y answered 500\n", b"Received cache flush instruction\n"], self.writes)
        self.assertEqual(b"SERVER ERROR X at y answered 500\nReceived cache flush instruction\n", self.logged())

    def test_a_signal_handler_never_joins_the_line_not_yet_complete(self):
        with self.interrupting(lambda: print("Received cache flush instruction", file=self.writer)):
            self.writer.write("the line written\nthe line not yet complete")
            self.writer.write(", now complete\n")
        self.assertEqual([b"the line written\n", b"Received cache flush instruction\n", b"the line not yet complete, now complete\n"],
                         self.writes)
        self.assertEqual(b"the line written\nReceived cache flush instruction\nthe line not yet complete, now complete\n", self.logged())

    def test_a_signal_handler_interrupting_the_handler_s_own_write_is_written_too(self):
        first = lambda: print("from the first handler", "in pieces", file=self.writer)
        second = lambda: print("from the second", file=self.writer)
        with self.interrupting(first, second):
            print("the line being written", file=self.writer)
            print("the next line", file=self.writer)
        self.assertEqual([b"the line being written\n", b"from the first handler in pieces\n", b"from the second\n",
                          b"the next line\n"], self.writes)
        self.assertTrue(all(data.endswith(b"\n") for data in self.writes))

    @unittest.skipUnless(hasattr(os, "fork"), "needs fork")
    def test_a_forked_process_does_not_write_its_parent_s_line_not_complete(self):
        run_script(self, FORK, self.path)
        self.assertEqual(b"the child's line\nthe parent's line, ended by the parent\n", self.logged())


class TestInstall(unittest.TestCase):

    def streams(self):
        directory = tempfile.TemporaryDirectory(prefix="jaaql-lines-")
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "gunicorn.log")
        out = open(path, "a", encoding="utf-8")
        err = open(path, "a", encoding="utf-8", errors="backslashreplace")
        self.addCleanup(out.close)
        self.addCleanup(err.close)
        return path, out, err

    def test_install_replaces_stdout_and_stderr_on_their_file_descriptors_once_writing_what_they_held(self):
        path, out, err = self.streams()
        out.write("buffered before\n")
        with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            line_output.install()
            stdout, stderr = sys.stdout, sys.stderr
            self.assertIsInstance(stdout, LineWriter)
            self.assertIsInstance(stderr, LineWriter)
            self.assertEqual((out.fileno(), err.fileno(), "utf-8", "backslashreplace"),
                             (stdout.fileno(), stderr.fileno(), stdout.encoding, stderr.errors))
            line_output.install()
            self.assertIs(stdout, sys.stdout)
            print("printed after")
            print("Renée", file=sys.stderr)
        with open(path, encoding="utf-8") as file:
            self.assertEqual("buffered before\nprinted after\nRenée\n", file.read())

    def test_install_leaves_a_stream_without_a_file_descriptor(self):
        captured = io.StringIO()
        with mock.patch.object(sys, "stdout", captured), mock.patch.object(sys, "stderr", None):
            line_output.install()
            self.assertIs(captured, sys.stdout)
            self.assertIsNone(sys.stderr)

    @unittest.skipUnless(os.path.isfile(GUNICORN_CONFIG), "needs docker/gunicorn_config.py")
    def test_gunicorn_installs_it_in_the_master_on_starting(self):
        spec = importlib.util.spec_from_file_location("jaaql_gunicorn_config", GUNICORN_CONFIG)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        self.assertEqual((True, True), (config.preload_app, config.enable_stdio_inheritance))
        path, out, err = self.streams()
        with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
            config.on_starting(None)
            self.assertIsInstance(sys.stdout, LineWriter)
            self.assertIsInstance(sys.stderr, LineWriter)


@unittest.skipUnless(hasattr(os, "fork"), "needs fork")
class TestManyProcessesPrintingAtOnce(unittest.TestCase):

    def test_sixteen_processes_printing_at_once_lose_join_cut_and_reorder_no_line(self):
        # intact, damaged, out of order, and the parent's line not complete when it forked, once
        for unbuffered in (False, True):
            with self.subTest(unbuffered=unbuffered), tempfile.TemporaryDirectory(prefix="jaaql-lines-") as directory:
                answer = run_script(self, RACE, "fixed", os.path.join(directory, "gunicorn.log"), "16", "900", unbuffered=unbuffered)
                self.assertEqual([16 * 900, 0, 0, 1], [int(value) for value in answer.split()])


if __name__ == "__main__":
    unittest.main()
