"""
Slow-query reports: a JAAQL query request (one InterpretJAAQL.transform: its statements and its COMMIT) whose database time exceeds
SENTINEL_SLOW_QUERY_SECONDS (default 3) is printed as one line and reported to Sentinel through jaaql.utilities.sentinel.

What is timed: each statement from the moment the parallel verifier's verdict is in until its rows are fetched (DBPGInterface.execute_query),
plus the end of the transaction. Not timed: the wait for that verdict, connection checkout, and work in Python. The time is wall clock in the
worker: under gunicorn's gevent worker a statement whose answer arrives while other requests of the worker hold the CPU is only taken up
once they yield, so an overloaded worker can report a fast statement as slow.

Only a query run inside a scope is reported: a request scope, which routed_function opens for every route but the ones in
SLOW_QUERY__unreported_routes (Sentinel's ingest route, deploy and development tooling), or a background scope a long-running job opens on
purpose (the auth verifier). A request that names no application is not reported when it is on a route of
SLOW_QUERY__unreported_without_application (jaaql-monitor's /submit, however it logged in: deploy scripts, migrations, procedure test runs)
or authenticated with a bypass key. Install, migrations and anything else outside a scope never are.

The report is built in the request that ran the query, from that request's own values, and queued without waiting. It names the account
by its id only. Each process reports one query (Sentinel's source_file) at most once an hour, counting its slow runs in between into its
next report, and makes at most SLOW_QUERY__max_reports_per_hour reports an hour, at most SLOW_QUERY__max_reports_per_account_per_hour of
them for the queries of one account
"""
import contextvars
import hashlib
import json
import math
import os
import re
import socket
import threading
import time
from collections import deque, OrderedDict
from contextlib import contextmanager
from datetime import datetime, timezone
from itertools import islice
from urllib.parse import urlsplit

from jaaql.constants import ENVIRON__sentinel_slow_query_seconds, SLOW_QUERY__default_seconds, SLOW_QUERY__repeat_seconds, \
    SLOW_QUERY__max_reports_per_hour, SLOW_QUERY__max_reports_per_account_per_hour, SLOW_QUERY__max_tracked_queries, \
    SLOW_QUERY__redacted_key, SLOW_QUERY__unreported_without_application, REGEX__dmbs_procedure_name, KEY__application, VERSION
from jaaql.utilities import sentinel

WARN__threshold = "WARNING: %s=%r is not a number of seconds, using %s"
ERR__report_failed = "Slow query report failed: %s: %s"
LINE__slow_query = "SLOW QUERY %.2f s %s (%s, %s)"

SOURCE_FILE__prefix = "slow-query:"
SOURCE_FILE__max_length = 255
SOURCE_FILE__max_host_length = 60
LABEL__max_length = 200
LABEL__cut_length = 180
LOCATION__max_length = 512
ERROR_CONDENSED__max_length = 200
VERSION__max_length = 40
SOURCE_SYSTEM__max_length = 63
SOURCE_SYSTEM__fallback = "jaaql"
USER_AGENT__max_length = 512
STATEMENT__max_length = 8000
VALUE__max_length = 500
PARAMETERS__max_length = 4000
STATEMENTS__max_listed = 20
STACKTRACE__max_length = 16000
SQL_PREVIEW__length = 60
VALUE__max_depth = 32
HOUR = 3600
# A query not slow for this long is forgotten, with the slow runs not yet counted into a report
FORGET__seconds = 24 * HOUR

VALUE__redacted = "<redacted>"
VALUE__encrypted = "<encrypted>"
LITERAL__encrypted = "#'<encrypted>'"

REGEX__procedure_call = re.compile(r'\s*SELECT\s+\*\s+FROM\s+"([^"]+)"\s*\(', re.IGNORECASE)
REGEX__procedure_name = re.compile(REGEX__dmbs_procedure_name)
REGEX__source_system_unsafe = re.compile(r"[^a-z0-9-]+")
# An encrypted literal, #'...' with '' for a quote, as InterpretJAAQL.encrypt_literals finds it, without its nested repetition
REGEX__encrypted_literal = re.compile(r"#'(?:[^']|'')*'")


def parse_threshold(raw) -> float:
    if raw is None or raw.strip() == "":
        return float(SLOW_QUERY__default_seconds)
    try:
        value = float(raw)
        if math.isnan(value):
            raise ValueError(raw)
        return value
    except ValueError:
        print(WARN__threshold % (ENVIRON__sentinel_slow_query_seconds, raw, SLOW_QUERY__default_seconds))
        return float(SLOW_QUERY__default_seconds)


THRESHOLD_SECONDS = parse_threshold(os.environ.get(ENVIRON__sentinel_slow_query_seconds))

_public_url = None
_api_prefix = ""
_host = socket.gethostname()


def enabled() -> bool:
    return THRESHOLD_SECONDS > 0


def configure(public_url: str = None, is_container: bool = False):
    """
    Where the reports say they come from: the public URL of this JAAQL (config [SWAGGER] url, https://<SERVER_ADDRESS> in the container),
    behind which the container serves its routes under /api, and its host name, which keeps the same query on two boxes two queries
    """
    global _public_url, _api_prefix, _host
    _public_url = public_url.rstrip("/") if public_url else None
    _api_prefix = "/api" if is_container else ""
    host = urlsplit(_public_url).hostname if _public_url else None
    _host = host if host and host != "_" else socket.gethostname()


class Scope:
    """
    One request, or one background job: who asked and on which route. Shared with the server-error reports (jaaql/utilities/server_errors.py),
    which keep in it the request's inputs and the server faults noted while it runs; slow is whether its queries are timed for slow-query
    reports
    """
    __slots__ = ("route", "method", "path", "user_agent", "account_id", "application", "bypass", "background", "started", "slow", "faults",
                 "inputs")

    def __init__(self, route: str = None, method: str = None, path: str = None, user_agent: str = None, background: str = None,
                 slow: bool = True):
        self.route = route
        self.method = method
        self.path = path
        self.user_agent = user_agent
        self.account_id = None
        self.application = None
        self.bypass = False
        self.background = background
        self.started = time.perf_counter()
        self.slow = slow
        self.faults = []
        self.inputs = None


_scope = contextvars.ContextVar("jaaql_slow_query_scope", default=None)


def current_scope() -> Scope:
    return _scope.get()


@contextmanager
def request_scope(route: str, method: str, path: str, user_agent: str = None, slow: bool = True):
    token = _scope.set(Scope(route=route, method=method, path=path, user_agent=user_agent, slow=slow))
    try:
        yield
    finally:
        _scope.reset(token)


@contextmanager
def background(name: str):
    token = _scope.set(Scope(background=name))
    try:
        yield
    finally:
        _scope.reset(token)


def note_caller(account_id, bypass: bool):
    # The account by its id only: a username is an email address, which a report does not carry
    scope = _scope.get()
    if scope is not None:
        scope.account_id = account_id
        scope.bypass = bool(bypass)


def note_application(inputs):
    scope = _scope.get()
    if scope is not None and isinstance(inputs, dict):
        # Kept by reference, for a server-error report only: the model may change the inputs before one is made
        scope.inputs = inputs
        if isinstance(inputs.get(KEY__application), str):
            scope.application = inputs[KEY__application]


class Label:
    """
    What a query is, for the report and for Sentinel's cooldown: <kind>:<name>, or for /execute <kind>:<ref> for the compiled query that
    took longest of those that ran (refs: {query key: "<file>:<index>"}). A transform without one is labelled from its SQL
    """
    __slots__ = ("kind", "name", "refs")

    def __init__(self, kind: str, name: str = None, refs: dict = None):
        self.kind = kind
        self.name = name
        self.refs = refs


class Measurement:
    __slots__ = ("scope", "label", "application", "database", "statements", "end_seconds", "ended_with", "failure")

    def __init__(self, scope: Scope, label: Label, application: str, database: str):
        self.scope = scope
        self.label = label
        self.application = application
        self.database = database
        # (query key, statement text as sent with its :parameters, {parameter: value}, names of the #parameters, seconds)
        self.statements = []
        self.end_seconds = 0.0
        self.ended_with = None
        self.failure = None

    def statement(self, query_key, text, parameters: dict, encrypted_names, timing: list):
        self.statements.append((query_key, text, parameters, encrypted_names, sum(timing) if timing else 0.0))

    def total(self) -> float:
        return sum(statement[4] for statement in self.statements) + self.end_seconds

    def finish(self):
        total = self.total()
        if total > THRESHOLD_SECONDS:
            try:
                _slow(self, total)
            except Exception as ex:
                print(ERR__report_failed % (type(ex).__name__, str(ex)[:200]))


def start(label: Label, operation, db_interface) -> Measurement:
    """
    A measurement for one transform, or None (nothing is timed) when slow-query reports are off or the transform runs outside a scope that
    times its queries
    """
    if not THRESHOLD_SECONDS > 0:
        return None
    scope = _scope.get()
    if scope is None or not scope.slow:
        return None
    application = operation.get(KEY__application) if isinstance(operation, dict) else None
    return Measurement(scope, label, application if isinstance(application, str) else None, getattr(db_interface, "db_name", None))


# Throttle -----------------------------------------------------------------------------------------------------------------------------

DECISION__report = "reported"
DECISION__repeat = "repeat, not reported"
DECISION__capped = "over %d reports this hour, not reported" % SLOW_QUERY__max_reports_per_hour
DECISION__account_capped = "over %d reports this hour for this account, not reported" % SLOW_QUERY__max_reports_per_account_per_hour


def _now() -> float:
    return time.monotonic()


class Throttle:
    """
    Which reports a process makes: one per identity an hour, counting its runs in between into its next report, at most max_per_hour reports
    an hour and max_per_account of them for one account, and at most max_tracked identities kept track of. limits() gives those three, read
    at every decision. Slow-query reports and server-error reports have one each, so neither spends the other's budget
    """

    def __init__(self, limits):
        self.limits = limits
        self.lock = threading.Lock()
        # identity -> [monotonic time of its last report or None (never reported), runs since, slowest of those, time of its last run],
        # the one longest not seen first
        self.identities = OrderedDict()
        # (monotonic time, account id or None) of each report in the last hour
        self.reported_at = deque()

    def reset(self):
        with self.lock:
            self.identities.clear()
            self.reported_at.clear()

    @staticmethod
    def _recently_reported(entry, now) -> bool:
        return entry[0] is not None and now - entry[0] < SLOW_QUERY__repeat_seconds

    def _forget(self, now, max_per_hour: int, max_tracked: int):
        # The identities not seen for a day, then beyond max_tracked the ones longest not seen, never one reported in the last hour (there
        # are at most max_per_hour of those), which would be reported again
        while self.identities:
            identity, entry = next(iter(self.identities.items()))
            if now - entry[3] < FORGET__seconds:
                break
            del self.identities[identity]
        excess = len(self.identities) - max_tracked
        if excess > 0:
            oldest = islice(self.identities.items(), excess + max_per_hour)
            for identity in [identity for identity, entry in oldest if not self._recently_reported(entry, now)][:excess]:
                del self.identities[identity]

    @staticmethod
    def _counted(entry, seconds: float, decision: str):
        entry[1] += 1
        entry[2] = max(entry[2], seconds)
        return decision, None

    def decide(self, identity: str, seconds: float = 0.0, account_id=None):
        """
        (DECISION__report, (runs since its last report, slowest of those)) when a report is to be made, else (the reason, None)
        """
        max_per_hour, max_per_account, max_tracked = self.limits()
        now = _now()
        with self.lock:
            entry = self.identities.pop(identity, None)
            if entry is None:
                entry = [None, 0, 0.0, now]
            entry[3] = now
            self.identities[identity] = entry
            self._forget(now, max_per_hour, max_tracked)
            if self._recently_reported(entry, now):
                return self._counted(entry, seconds, DECISION__repeat)
            while self.reported_at and now - self.reported_at[0][0] >= HOUR:
                self.reported_at.popleft()
            if len(self.reported_at) >= max_per_hour:
                return self._counted(entry, seconds, "over %d reports this hour, not reported" % max_per_hour)
            if account_id is not None and sum(1 for _, reported_for in self.reported_at if reported_for == account_id) >= max_per_account:
                return self._counted(entry, seconds, "over %d reports this hour for this account, not reported" % max_per_account)
            repeats = (entry[1], entry[2])
            entry[0], entry[1], entry[2] = now, 0, 0.0
            self.reported_at.append((now, account_id))
            return DECISION__report, repeats


_slow_query_throttle = Throttle(lambda: (SLOW_QUERY__max_reports_per_hour, SLOW_QUERY__max_reports_per_account_per_hour,
                                         SLOW_QUERY__max_tracked_queries))
_identities = _slow_query_throttle.identities
_reported_at = _slow_query_throttle.reported_at


def reset_throttle():
    _slow_query_throttle.reset()


def _throttle(identity: str, seconds: float, account_id=None):
    return _slow_query_throttle.decide(identity, seconds, account_id)


# The report ---------------------------------------------------------------------------------------------------------------------------

def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()


def _collapse(text: str) -> str:
    return " ".join(str(text).split())


def _masked(text: str) -> str:
    # An encrypted literal is in the statement as the request wrote it; the database only ever saw it encrypted
    return REGEX__encrypted_literal.sub(LITERAL__encrypted, text) if "#'" in text else text


def _printable(text: str) -> str:
    # One line of printable characters, whatever a request named its procedure, template or application
    return "".join(ch if ch.isprintable() else "?" for ch in _collapse(text))


def _ref_of(label: Label, query_key):
    return label.refs.get(query_key) if label is not None and label.refs else None


def label_of(measurement: Measurement) -> str:
    return _printable(_label_of(measurement))


def _label_of(measurement: Measurement) -> str:
    label = measurement.label
    if label is not None and label.refs:
        # The compiled query that took longest: a request picks which ones it runs, so naming them all would make every combination a
        # query of its own
        slowest = None
        for statement in measurement.statements:
            ref = label.refs.get(statement[0])
            if ref is not None and (slowest is None or statement[4] > slowest[1]):
                slowest = (ref, statement[4])
        return label.kind + ":" + (slowest[0] if slowest is not None else next(iter(label.refs.values())))
    if label is not None and label.name is not None:
        return label.kind + ":" + str(label.name)
    texts = [_masked(str(statement[1])) for statement in measurement.statements]
    if len(texts) == 1:
        match = REGEX__procedure_call.match(texts[0])
        if match is not None and REGEX__procedure_name.fullmatch(match.group(1)) is not None:
            return "proc:" + match.group(1)
    return "sql:" + _sha1("\n;\n".join(_collapse(text) for text in texts))[:12]


def source_system_of(application) -> str:
    return REGEX__source_system_unsafe.sub("-", (application or "").lower())[:SOURCE_SYSTEM__max_length] or SOURCE_SYSTEM__fallback


def short_label(label: str) -> str:
    # The label goes into source_file (varchar 255) with the prefix and the host: a long one is cut and keeps a hash of the whole
    room = SOURCE_FILE__max_length - len(SOURCE_FILE__prefix) - 1 - len(_host[:SOURCE_FILE__max_host_length])
    if len(label) <= min(LABEL__max_length, room):
        return label
    return label[:min(LABEL__cut_length, room - 13)] + "~" + _sha1(label)[:12]


def source_file_of(label: str) -> str:
    return SOURCE_FILE__prefix + short_label(label) + "@" + _host[:SOURCE_FILE__max_host_length]


def _ascii(text: str) -> str:
    return "".join(ch if " " <= ch <= "~" else "?" for ch in text)


def _where(scope: Scope) -> str:
    return scope.background if scope.background is not None else (scope.method or "") + " " + (scope.path or scope.route or "")


def _location(scope: Scope) -> str:
    if scope.background is not None:
        return (_public_url or _host) + " (" + scope.background + ")"
    return (_public_url or "") + _api_prefix + (scope.path or scope.route or "")


def _seconds(value: float) -> str:
    return "%.2f s" % value


def _redacted(value, secrets: set, depth: int = 0):
    """
    The value with the value of every entry whose name matches SLOW_QUERY__redacted_key replaced by <redacted>, at any depth and inside
    JSON text; each scalar replaced is added to secrets
    """
    if depth > VALUE__max_depth:
        return VALUE__redacted
    if isinstance(value, dict):
        redacted = {}
        for key, inner in value.items():
            if SLOW_QUERY__redacted_key.search(str(key)):
                _collect(inner, secrets, depth + 1)
                redacted[key] = VALUE__redacted
            else:
                redacted[key] = _redacted(inner, secrets, depth + 1)
        return redacted
    if isinstance(value, (list, tuple)):
        return [_redacted(inner, secrets, depth + 1) for inner in value]
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError):
            return value
        if isinstance(parsed, (dict, list)):
            redacted = _redacted(parsed, secrets, depth + 1)
            if redacted != parsed:
                return json.dumps(redacted, ensure_ascii=False)
    return value


def _collect(value, secrets: set, depth: int):
    if depth > VALUE__max_depth or value is None or isinstance(value, bool):
        return
    if isinstance(value, dict):
        for inner in value.values():
            _collect(inner, secrets, depth + 1)
    elif isinstance(value, (list, tuple)):
        for inner in value:
            _collect(inner, secrets, depth + 1)
    elif str(value) != "":
        secrets.add(str(value))


def _secrets_of(measurement: Measurement) -> set:
    secrets = set()
    for statement in measurement.statements:
        _redacted(statement[2] or {}, secrets)
    return secrets


def _outcome(failure, secrets: set) -> str:
    if failure is None:
        return "completed"
    message = getattr(failure, "message", None)
    if message is None:
        message = str(failure)
    elif not isinstance(message, str):
        message = json.dumps(message, default=str)
    lines = str(message).strip().splitlines()
    first = lines[0] if lines else ""
    # A database error can quote the value it refused, which may be one the parameters show as <redacted>
    for secret in sorted(secrets, key=len, reverse=True):
        first = first.replace(secret, VALUE__redacted)
    return "failed - " + type(failure).__name__ + ": " + first[:200]


def _value(key: str, value, encrypted: bool) -> str:
    if SLOW_QUERY__redacted_key.search(key):
        return json.dumps(VALUE__redacted)
    if encrypted:
        return json.dumps(VALUE__encrypted)
    value = _redacted(value, set())
    try:
        rendered = json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        rendered = json.dumps(str(value), ensure_ascii=False)
    return rendered if len(rendered) <= VALUE__max_length else rendered[:VALUE__max_length] + "..."


def _parameters(parameters: dict, encrypted_names) -> str:
    entries = [(key, value, False) for key, value in (parameters or {}).items()] + [(key, None, True) for key in (encrypted_names or ())]
    if len(entries) == 0:
        return ""
    block = "\tParameters:\n\t{\n" + ",\n".join("\t\t" + json.dumps(str(key), ensure_ascii=False) + ": " + _value(str(key), value, encrypted)
                                               for key, value, encrypted in entries) + "\n\t}\n"
    return block if len(block) <= PARAMETERS__max_length else block[:PARAMETERS__max_length] + "\n\t[parameters truncated]\n"


def _statement_text(text) -> str:
    text = _masked(str(text))
    if len(text) > STATEMENT__max_length:
        text = text[:STATEMENT__max_length] + "\n[statement truncated]"
    return "".join("\t" + line + "\n" for line in text.strip("\r\n").splitlines())


def stacktrace_of(measurement: Measurement, total: float, label: str, application: str, repeats) -> str:
    scope = measurement.scope
    statements = measurement.statements
    statement_seconds = sum(statement[4] for statement in statements)
    ended_with = measurement.ended_with or "end of transaction"
    if scope.background is not None:
        route = "Background: " + scope.background + " on " + (_public_url or _host)
        account = ""
        so_far = ""
    else:
        route = "Route: " + _printable(_where(scope)) + " on " + (_public_url or _host)
        account = " | account: " + (str(scope.account_id) if scope.account_id is not None else "-")
        so_far = "; request time so far " + _seconds(time.perf_counter() - scope.started)
    lines = [
        "Slow query: " + _seconds(total) + ", over the %g s threshold" % THRESHOLD_SECONDS,
        "Query: " + label,
        "Outcome: " + _outcome(measurement.failure, _secrets_of(measurement)),
        route,
        "Application: " + _printable(application or "-") + " | database: " + (measurement.database or "-") + account,
        "At: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") + " | JAAQL " + VERSION + " | worker pid " + str(os.getpid()),
        "Database time: " + _seconds(total) + " = statements " + _seconds(statement_seconds) + " + " + ended_with + " " +
        _seconds(measurement.end_seconds),
        "  (wall clock in this worker, to which its other requests add while they hold it; not counted: authorization verification and "
        "connection checkout" + so_far + ")",
    ]
    if repeats is not None and repeats[0] > 0:
        lines.append("Repeats: %d more slow run%s of this query in this worker since its last report, slowest %s" % (
            repeats[0], "" if repeats[0] == 1 else "s", _seconds(repeats[1])))
    text = "\n".join(lines) + "\n"
    for idx, (query_key, statement_text, parameters, encrypted_names, seconds) in enumerate(statements[:STATEMENTS__max_listed]):
        ref = _ref_of(measurement.label, query_key)
        text += "\nStatement %d of %d | query key %s%s | %s\n" % (idx + 1, len(statements), query_key,
                                                                 "" if ref is None else ", compiled query " + _printable(ref), _seconds(seconds))
        text += _statement_text(statement_text) + _parameters(parameters, encrypted_names)
    if len(statements) > STATEMENTS__max_listed:
        rest = statements[STATEMENTS__max_listed:]
        text += "\n... and %d more statements, %s together\n" % (len(rest), _seconds(sum(statement[4] for statement in rest)))
    # Without the trailing newline, which Sentinel's ingest route strips
    return (text if len(text) <= STACKTRACE__max_length else text[:STACKTRACE__max_length] + "\n[report truncated]").rstrip("\n")


def condensed_of(total: float, label: str, measurement: Measurement) -> str:
    condensed = "Slow query: " + _seconds(total) + " " + label
    if label.startswith("sql:") and measurement.statements:
        condensed += " " + _printable(_masked(str(measurement.statements[0][1])))[:SQL_PREVIEW__length]
    return condensed[:ERROR_CONDENSED__max_length]


def payload_of(measurement: Measurement, total: float, label: str, application: str, repeats) -> dict:
    # Exactly the keys Sentinel's ingest route binds, all of them: it refuses a report with any other key
    user_agent = measurement.scope.user_agent
    return {
        "location": _location(measurement.scope)[:LOCATION__max_length],
        "source_file": source_file_of(label),
        "error_condensed": condensed_of(total, short_label(label), measurement),
        "file_line_number": None,
        "file_col_number": None,
        "version": ("JAAQL " + VERSION)[:VERSION__max_length],
        "source_system": source_system_of(application),
        "stacktrace": stacktrace_of(measurement, total, label, application, repeats),
        # Encrypted at rest by Sentinel, which encodes ASCII only
        "user_agent": _ascii(user_agent)[:USER_AGENT__max_length] if user_agent else "JAAQL/" + VERSION,
    }


def is_tooling(scope: Scope, application: str = None) -> bool:
    # Admin tooling, not the application: a request whose queries name no application, on jaaql-monitor's route or with a bypass key
    return scope.background is None and not (application or scope.application) and \
        (scope.bypass or scope.route in SLOW_QUERY__unreported_without_application)


def _slow(measurement: Measurement, total: float):
    scope = measurement.scope
    application = measurement.application or scope.application
    if is_tooling(scope, application):
        return
    label = label_of(measurement)
    # One line, whatever the request named its application or path
    line = LINE__slow_query % (total, label, _printable(_where(scope)), _printable(application or "-"))
    if not sentinel.is_configured():
        print(line)
        return
    decision, repeats = _throttle(source_system_of(application) + ":" + source_file_of(label), total, scope.account_id)
    if decision == DECISION__report and not sentinel.send(payload_of(measurement, total, label, application, repeats)):
        decision = "Sentinel queue full, not reported"
    print(line + " - " + decision)
