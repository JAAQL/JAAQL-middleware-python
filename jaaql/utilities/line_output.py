"""
One write for every line a gunicorn worker prints, so that the lines of workers printing at the same moment are never joined or cut in
gunicorn.log. Gunicorn's --capture-output points every process's stdout and stderr (file descriptors 1 and 2) at the log file, opened for
appending, and the master and each worker print into it with print() and traceback (a SERVER ERROR line, a webhook refused, a traceback).
Python's own sys.stdout does not write a line at once: writing to a file it buffers 8 KiB and writes the buffer when it is full, so a line
can be cut where the buffer ends, another worker's buffer landing in the cut, and the line is held until the buffer fills; unbuffered
(PYTHONUNBUFFERED) it writes each piece print() gives it as it comes, the text, then the separator and the newline, so two workers printing
at once write "A", "B", "\n", "\n" and their lines are joined into one, which a grep -c of SERVER ERROR then counts once.

install() replaces sys.stdout and sys.stderr with LineWriters on the same file descriptors: a LineWriter keeps what it is given until a
line is complete and then writes every complete line it holds in one write(), which the kernel appends to a file opened for appending as a
whole, never interleaved with another process's write. So every line lands whole and at once, and the lines of one process land in the
order it printed them. What a signal handler prints while the thread it interrupted is in a LineWriter's write is kept apart from that
thread's line and written once its write is done, in one write too; a handler that prints at any other moment, between print()'s text and
its newline for one, joins the line not yet complete, so gunicorn_config.py's post_worker_init has gevent's hub run the cache flush on
SIGUSR1, between greenlets, instead of a handler of signal.signal's. The limits: a line not yet complete is written by
flush() and when the process exits normally, until then it is held; one that grows past LINE__max_pending_bytes (1 MiB) is written as it
is, in pieces; to a pipe (LOG_TO_OUTPUT) the kernel keeps a write whole only up to PIPE_BUF (4,096 bytes), so a longer line can still be
cut there. A write the system refuses (a full disk) is dropped, never failing the code that printed. gunicorn_config.py's on_starting
installs it in the master once the app is loaded, and every worker forks with it; a process forked starts with a lock of its own and
nothing of its parent's pending line
"""
import io
import os
import select
import sys
import threading
import weakref

LINE__max_pending_bytes = 1024 * 1024
ENCODING__default = "utf-8"

_WRITERS = weakref.WeakSet()


def _write_all(fd: int, data: bytes):
    view = memoryview(data)
    while view:
        try:
            written = os.write(fd, view)
        except BlockingIOError:
            select.select([], [fd], [])
            continue
        except OSError:
            return
        view = view[written:]


def _forked():
    for writer in list(_WRITERS):
        writer._forked()


os.register_at_fork(after_in_child=_forked)


class _LineBuffer:
    """
    The binary side of a LineWriter (its .buffer), for code that writes bytes to sys.stdout.buffer: the same pending line
    """

    def __init__(self, writer):
        self._writer = writer

    def write(self, data) -> int:
        data = bytes(data)
        self._writer._write_bytes(data)
        return len(data)

    def flush(self):
        self._writer.flush()

    def fileno(self) -> int:
        return self._writer.fileno()

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return self._writer.isatty()


class LineWriter(io.TextIOBase):
    """
    A text stream on a file descriptor that writes the complete lines it is given at once, all of them in one write()
    """

    def __init__(self, fd: int, encoding: str = None, errors: str = None, name=None):
        super().__init__()
        self._fd = fd
        self._encoding = encoding or ENCODING__default
        self._errors = errors or "strict"
        self._name = name if name is not None else fd
        self._lock = threading.RLock()
        self._pending = bytearray()
        self._interrupted = bytearray()
        self._writing = False
        self.buffer = _LineBuffer(self)
        _WRITERS.add(self)

    def _forked(self):
        self._lock = threading.RLock()
        self._pending = bytearray()
        self._interrupted = bytearray()
        self._writing = False

    @property
    def encoding(self):
        return self._encoding

    @property
    def errors(self):
        return self._errors

    @property
    def name(self):
        return self._name

    @property
    def line_buffering(self) -> bool:
        return True

    @property
    def newlines(self):
        return None

    def fileno(self) -> int:
        return self._fd

    def isatty(self) -> bool:
        try:
            return os.isatty(self._fd)
        except OSError:
            return False

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def write(self, text) -> int:
        if not isinstance(text, str):
            raise TypeError("write() argument must be str, not %s" % type(text).__name__)
        self._write_bytes(text.encode(self._encoding, self._errors))
        return len(text)

    def _write_bytes(self, data: bytes):
        with self._lock:
            if self._writing:
                # A signal handler printing while this thread is in here: kept apart from the line being written, and written after it
                self._interrupted += data
                return
            self._writing = True
            try:
                self._pending += data
                end = self._pending.rfind(b"\n") + 1
                if end == 0 and len(self._pending) >= LINE__max_pending_bytes:
                    end = len(self._pending)
                if end > 0:
                    complete = bytes(self._pending[:end])
                    del self._pending[:end]
                    _write_all(self._fd, complete)
                self._write_interrupted()
            finally:
                self._writing = False

    def _write_interrupted(self):
        # What handlers printed while this thread was writing, all of it in one write (a handler has returned before the thread it
        # interrupted goes on), again while one prints during that write. Only what was taken is removed: a handler can print between the
        # taking and the removing, and its line is written on the next turn
        while self._interrupted:
            interrupted = bytes(self._interrupted)
            del self._interrupted[:len(interrupted)]
            _write_all(self._fd, interrupted)

    def flush(self):
        with self._lock:
            if self._writing or not (self._pending or self._interrupted):
                return
            self._writing = True
            try:
                pending = bytes(self._pending)
                self._pending.clear()
                if pending:
                    _write_all(self._fd, pending)
                self._write_interrupted()
            finally:
                self._writing = False

    def close(self):
        # The file descriptor stays open: it is the process's stdout or stderr
        try:
            self.flush()
        finally:
            super().close()


def install():
    """
    Replaces sys.stdout and sys.stderr with LineWriters on their file descriptors, unless they are already; what they still buffer is
    written first
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        if stream is None or isinstance(stream, LineWriter):
            continue
        try:
            fd = stream.fileno()
        except (AttributeError, OSError, ValueError):
            continue
        stream.flush()
        setattr(sys, name, LineWriter(fd, getattr(stream, "encoding", None), getattr(stream, "errors", None),
                                      getattr(stream, "name", fd)))
