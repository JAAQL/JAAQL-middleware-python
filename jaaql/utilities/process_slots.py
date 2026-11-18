"""
How many node processes of one kind one gunicorn worker runs at once. Every request to /webhook/<application>/<name> or
/secure/<application>/<name> starts a node process of its own (about 50 MB, for a fraction of a second), and so does every call of a public
cloud procedure (/remote_procedure, a procedure of access public); /webhook and public procedures need no login, and a gevent worker serves
up to 100 requests at once (worker_connections), so without a bound a flood of such requests from many addresses, which nginx's limit per
client address does not hold back, could start some 500 node processes on a box of 5 workers and run it out of memory, its database with it.
Webhooks (WEBHOOKS) and public procedures (PUBLIC_PROCEDURES) have places of their own, so that a flood of one never keeps the other out.
Private procedures are not bounded: they need a login, which is accountable and held back by nginx's limit per address, and Securium's,
which page through an outside API, can run longer than a request could wait for a place.

A Slots runs at most max_running() processes at once (WEBHOOKS: WEBHOOK_MAX_RUNNING, default WEBHOOK__default_max_running, 4;
PUBLIC_PROCEDURES: PUBLIC_PROCEDURE_MAX_RUNNING, default 4). A request asked for while that many run waits for a place, at most
SLOT__wait_seconds (5), and at most max_waiting() of them wait at once (WEBHOOK_MAX_WAITING, default WEBHOOK__default_max_waiting, 32;
PUBLIC_PROCEDURE_MAX_WAITING, default 32): a burst, such as a page loading many documents through one webhook, is served a few at a time
instead of refused. The waiting are served in the order they came: a place given back goes straight to the one that
has waited longest, and a newcomer takes a free place only when nobody waits. A request that finds as many waiting, or that waits in vain,
is not started and is answered 503 with Retry-After (SLOT__retry_after_seconds), never as a server error, and a webhook sender retries a
503; the bound on waiting keeps a flood from holding the worker's connections, which the app's other routes need. Both settings are read at
every request; a max_running() of 0 lifts the bound, and a max_waiting() of 0 refuses at once. A box runs at most GUNICORN_WORKERS
(default 5) times as many. The webhooks in use, Sentinel's gateway heartbeat (one every 5 minutes) and Securium's document downloads, never
come near it, and no app in use has a public procedure (thewashingforecast's, deprecated, is the only one). A refusal is printed, at most once a minute for each kind, with the number refused since the line before
"""
import collections
import os
import threading
import time

from jaaql.constants import ENVIRON__webhook_max_running, ENVIRON__webhook_max_waiting, WEBHOOK__default_max_running, \
    WEBHOOK__default_max_waiting, SLOT__wait_seconds, ENVIRON__public_procedure_max_running, ENVIRON__public_procedure_max_waiting, \
    PUBLIC_PROCEDURE__default_max_running, PUBLIC_PROCEDURE__default_max_waiting

LINE__refused = "%s %s/%s answered 503: this worker already runs %d %s processes (%s) and %s; %d refused since the last line"
REASON__queue_full = "%d more wait (%s)"
REASON__waited = "no place came free in %g s"
REFUSALS__print_seconds = 60


def _now() -> float:
    return time.monotonic()


def _setting(name: str, default: int) -> int:
    try:
        return max(int(os.environ.get(name, default)), 0)
    except (TypeError, ValueError):
        return default


class _Waiter:
    # One request waiting for a place. A released place is handed to it under the lock (granted), and the event wakes it
    __slots__ = ("event", "granted")

    def __init__(self):
        self.event = threading.Event()
        self.granted = False


class Slots:

    def __init__(self, title: str, noun: str, environ_max_running: str, environ_max_waiting: str, default_max_running: int,
                 default_max_waiting: int):
        self.title = title
        self.noun = noun
        self.environ_max_running = environ_max_running
        self.environ_max_waiting = environ_max_waiting
        self.default_max_running = default_max_running
        self.default_max_waiting = default_max_waiting
        self.wait_seconds = SLOT__wait_seconds
        self._lock = threading.Lock()
        self._running = 0
        self._waiters = collections.deque()
        self._refused = 0
        self._printed_at = None

    def max_running(self) -> int:
        """
        The processes one process may run at once, 0 when that is not bounded
        """
        return _setting(self.environ_max_running, self.default_max_running)

    def max_waiting(self) -> int:
        """
        The requests that may wait for a place at once, 0 when none may
        """
        return _setting(self.environ_max_waiting, self.default_max_waiting)

    def running(self) -> int:
        with self._lock:
            return self._running

    def waiting(self) -> int:
        with self._lock:
            return len(self._waiters)

    def _refuse(self, application: str, name: str, limit: int, reason: str) -> bool:
        with self._lock:
            self._refused += 1
            now = _now()
            if self._printed_at is not None and now - self._printed_at < REFUSALS__print_seconds:
                return False
            self._printed_at = now
            refused, self._refused = self._refused, 0
        print(LINE__refused % (self.title, application, name, limit, self.noun, self.environ_max_running, reason, refused))
        return False

    def _stop_waiting(self, waiter: _Waiter) -> bool:
        # True when a place was handed to the waiter, which then holds it; otherwise it leaves the queue
        with self._lock:
            if not waiter.granted and waiter in self._waiters:
                self._waiters.remove(waiter)
            return waiter.granted

    def claim(self, application: str, name: str) -> bool:
        """
        Takes a place for one process of application/name, which must be registered (its name may be printed), waiting for one as above.
        False when there is none: nothing is taken then, and the refusal is counted and perhaps printed
        """
        limit = self.max_running()
        with self._lock:
            if limit == 0 or (self._running < limit and not self._waiters):
                self._running += 1
                return True
            already = len(self._waiters)
            full = already >= self.max_waiting()
            if not full:
                waiter = _Waiter()
                self._waiters.append(waiter)
        if full:
            return self._refuse(application, name, limit, REASON__queue_full % (already, self.environ_max_waiting))
        try:
            waiter.event.wait(self.wait_seconds)
        except BaseException:
            if self._stop_waiting(waiter):
                self.release()
            raise
        if self._stop_waiting(waiter):
            return True
        return self._refuse(application, name, limit, REASON__waited % self.wait_seconds)

    def release(self):
        """
        Gives back the place a successful claim took: to the one that has waited longest, if any waits, which then runs in it
        """
        with self._lock:
            if self._waiters:
                waiter = self._waiters.popleft()
                waiter.granted = True
                waiter.event.set()
            else:
                self._running = max(self._running - 1, 0)

    def reset(self):
        # For the tests: none running or waiting, no refusal counted or printed, the wait as it is
        with self._lock:
            for waiter in self._waiters:
                waiter.event.set()
            self._running = 0
            self._waiters.clear()
            self._refused = 0
            self._printed_at = None
        self.wait_seconds = SLOT__wait_seconds


WEBHOOKS = Slots("Webhook", "webhook", ENVIRON__webhook_max_running, ENVIRON__webhook_max_waiting, WEBHOOK__default_max_running,
                 WEBHOOK__default_max_waiting)
PUBLIC_PROCEDURES = Slots("Public procedure", "public procedure", ENVIRON__public_procedure_max_running, ENVIRON__public_procedure_max_waiting,
                          PUBLIC_PROCEDURE__default_max_running, PUBLIC_PROCEDURE__default_max_waiting)
