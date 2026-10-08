"""
The sender of every report JAAQL makes to Sentinel's ingest route (POST <SENTINEL_URL>/api/sentinel/reporting/error): the slow-query reports
and the server-error reports (jaaql/utilities/slow_queries.py, jaaql/utilities/server_errors.py).

send() never waits and never raises: a report goes into a bounded queue, or is dropped and counted when the queue is full. One daemon
sender per process takes it from there, with a connect and a read timeout and one attempt, so a Sentinel that is down, slow or refusing costs
a printed line and never a request. The sender is started on the first send() of each process: gunicorn builds the app in its master
(preload_app) and forks the workers afterwards, and a thread started in the master does not run in a worker
"""
import os
import queue
import threading
import time
import traceback

import requests

from jaaql.constants import ENDPOINT__report_sentinel_error, SENTINEL__queue_size, SENTINEL__connect_timeout, SENTINEL__read_timeout

ERR__sentinel_failed = "Sentinel answered %d: %s"
ERR__sentinel_unreachable = "Sentinel report not delivered: %s: %s"
ERR__sentinel_queue_full = "Sentinel queue full, %d report(s) dropped so far in this process"

DROPPED__line_interval_seconds = 60

_lock = threading.Lock()
_url = None
_queue = None
_sender = None
_sender_pid = None
_dropped = 0
_dropped_line_at = None


def normalise_url(sentinel_url: str, base_url: str) -> (str, bool):
    """
    The ingest URL for the value of SENTINEL_URL, and whether it is this JAAQL itself ("_": the box's own base URL). A host or URL gains
    https:// when it names no scheme, then /api, then the ingest route, unless it already ends with them. None when it is unset
    """
    if not sentinel_url:
        return None, False
    if sentinel_url == "_":
        return base_url + ENDPOINT__report_sentinel_error, True
    if not sentinel_url.startswith("http"):
        sentinel_url = "https://" + sentinel_url
    if not sentinel_url.endswith("/api") and not sentinel_url.endswith(ENDPOINT__report_sentinel_error):
        sentinel_url = sentinel_url + "/api"
    if not sentinel_url.endswith(ENDPOINT__report_sentinel_error):
        sentinel_url = sentinel_url + ENDPOINT__report_sentinel_error
    return sentinel_url, False


def configure(sentinel_url: str, base_url: str) -> bool:
    """
    Sets where reports go from now on (None: nowhere, send() drops nothing and queues nothing). Returns whether that is this JAAQL itself
    """
    global _url
    _url, internal = normalise_url(sentinel_url, base_url)
    return internal


def is_configured() -> bool:
    return _url is not None


def send(payload: dict) -> bool:
    """
    Queues one report for the sender without waiting. False when Sentinel is not configured or the queue is full (the report is dropped)
    """
    if _url is None:
        return False
    the_queue = _ensure_sender()
    try:
        the_queue.put_nowait(payload)
        return True
    except queue.Full:
        _count_dropped()
        return False


def wait_idle(timeout: float) -> bool:
    """
    Waits until every queued report has been sent or given up on; True when that happened within timeout. For tests and shutdown only
    """
    deadline = time.monotonic() + timeout
    while True:
        the_queue = _queue
        if the_queue is None or the_queue.unfinished_tasks == 0:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)


def _ensure_sender() -> queue.Queue:
    global _queue, _sender, _sender_pid
    pid = os.getpid()
    if _sender_pid == pid:
        return _queue
    with _lock:
        if _sender_pid != pid:
            # A forked worker inherits the master's queue but not its sender: it starts its own, on a queue of its own
            _queue = queue.Queue(maxsize=SENTINEL__queue_size)
            _sender = threading.Thread(target=_send_forever, args=[_queue], daemon=True, name="sentinel-sender")
            _sender.start()
            _sender_pid = pid
        return _queue


def _count_dropped():
    global _dropped, _dropped_line_at
    _dropped += 1
    now = time.monotonic()
    if _dropped_line_at is None or now - _dropped_line_at >= DROPPED__line_interval_seconds:
        _dropped_line_at = now
        print(ERR__sentinel_queue_full % _dropped)


def _send_forever(the_queue: queue.Queue):
    while True:
        payload = the_queue.get()
        try:
            _post(payload)
        except Exception:
            traceback.print_exc()
        finally:
            the_queue.task_done()


def storable(payload: dict) -> dict:
    """
    The payload with every text one Sentinel's database can store: Postgres text holds no NUL character (shown as \\0) and only what UTF-8 can
    encode (a lone surrogate, which a decoded request can carry, becomes ?). Either would make the ingest route refuse the whole report
    """
    return {key: value.replace("\x00", "\\0").encode("utf-8", "replace").decode("utf-8") if isinstance(value, str) else value
            for key, value in payload.items()}


def _post(payload: dict):
    url = _url
    if url is None:
        return
    try:
        res = requests.post(url, json=storable(payload), timeout=(SENTINEL__connect_timeout, SENTINEL__read_timeout))
    except Exception as ex:
        print(ERR__sentinel_unreachable % (type(ex).__name__, str(ex)[:200]))
        return
    if res.status_code != 200:
        print(ERR__sentinel_failed % (res.status_code, res.text[:200]))
