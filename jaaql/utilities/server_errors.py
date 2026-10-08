"""
Server-error reports: a request that fails because of JAAQL or its infrastructure, never because of what the client sent, is printed as one
line and reported to Sentinel through jaaql.utilities.sentinel.

routed_function sees every failed request before Flask answers it (request_failed) and re-raises it unchanged. A request is reported for
- an exception JAAQL did not expect, answered 500;
- an explicit 5xx (a werkzeug HTTPException, an HttpStatusException or a JaaqlInterpretableHandledError): a connection lost for good, the pool
  exhausted, a compiled query missing from the cache, a failed COMMIT, a cloud procedure that crashed;
- a server fault noted while it ran, though it is answered as a client error: JAAQL's own SQL failing with an SQLSTATE that is not the
  client's, a bug in the interpreter running JAAQL's own SQL, the verifier's verdict timing out, a connection pool that cannot be made.
SQL the request supplied or named (client_sql: /submit, /execute, /call-proc, the security-event procedure, the email data view, /prepare)
counts only when the database server fails under it (a connection gone, a resource exhausted, an I/O error, corruption, a shutdown, a
connection lost after the SQL may have committed): nothing else it raises does. Neither does any 4xx, an exception marked as the client's
(client_fault: the refusal of an arbitrary query, an error a cloud procedure relays, what reading a malformed request raises), a client gone, a
request while JAAQL is not installed, or one on SERVER_ERROR__unreported_routes (Sentinel's ingest route, so a report never reports itself,
and the deploy-time routes). The auth verifier reports its own failures (background_failed); the Flask error handlers report what no routed
request saw (unrouted_failure); /exchange-auth-code, which answers every failure with its redirect, reports what of it is the server's.

A failed request makes at most one report, with exactly the keys Sentinel's ingest route binds. It names the account by its id only; the
inputs of a query route (SERVER_ERROR__routes_with_inputs) keep the values policy (values included, secrets <redacted>, encrypted literals
masked), every other route's inputs are named only, statements show their parameter names only, and URL query strings are removed from every
message. Each process reports an error (its file, line and class) at most once an hour, counting
its repeats into its next report, and makes at most SERVER_ERROR__max_reports_per_hour reports an hour, at most
SERVER_ERROR__max_reports_per_account_per_hour of them for one account, in a budget apart from the slow queries'. Nothing here raises or
waits: a failure to report is printed as one line
"""
import json
import os
import re
import sys
import traceback
import types
from datetime import datetime, timezone

import psycopg
from flask import has_request_context, request, current_app
from werkzeug.exceptions import HTTPException

import jaaql
from jaaql.constants import SERVER_ERROR__unreported_routes, SERVER_ERROR__max_reports_per_hour, \
    SERVER_ERROR__max_reports_per_account_per_hour, SERVER_ERROR__max_tracked_errors, SERVER_ERROR__max_faults, \
    SERVER_ERROR__routes_with_inputs, ROLE__jaaql, VERSION, KEY__parameters, KEY__query, ENDPOINT__oidc_get_token
from jaaql.exceptions.http_status_exception import HttpStatusException, JaaqlInterpretableHandledError, ConnectionLostError, \
    VerificationTimedOut, VerificationFailed, AuthorizationResponseError, ATTR__client_fault, ATTR__database_error, ATTR__outcome_unknown, \
    client_fault
from jaaql.exceptions.jaaql_interpretable_handled_errors import UserUnauthorized, UnhandledJaaqlServerError
from jaaql.utilities import sentinel, slow_queries

__all__ = ["configure", "request_failed", "background_failed", "unrouted_failure", "transform_failed", "commit_failed", "note_fault",
           "fresh_faults", "client_fault", "reading_request", "remote_procedure_crash", "authorization_response_failed", "reset_throttle",
           "FAULT__pool", "ANSWERED__oidc_exchange"]

ERR__report_failed = "Server error report failed: %s: %s"
LINE__server_error = "SERVER ERROR %s at %s (%s, %s) answered %s"
ANSWERED__oidc_exchange = "302, to the page the login started from or the application, not logged in"

# Set on an exception once request_failed or unrouted_failure has seen it, so the Flask error handlers never report it a second time
ATTR__seen = "jaaql_server_error_seen"
# Set on an exception whose report is filed under a name of its own rather than a file and line (a cloud procedure that crashed), with a
# detail line in place of what it printed
ATTR__report_source = "jaaql_report_source"
ATTR__report_detail = "jaaql_report_detail"

FAULT__internal_sql = "JAAQL's own query"
FAULT__internal = "JAAQL's own code, running its own query"
FAULT__commit = "the COMMIT of JAAQL's own query"
FAULT__database_server = "the database server, failing under the request's query"
FAULT__commit_database_server = "the database server, failing at the COMMIT of the request's query"
FAULT__outcome_unknown = "the connection, lost after %s may have committed"
FAULT__verification_timeout = "the wait for the authorization verifier's verdict"
FAULT__pool = "making the connection pool"
QUERY__own = "JAAQL's own query"
QUERY__requests = "the request's query"

SOURCE_FILE__max_length = 255
LOCATION__max_length = 512
ERROR_CONDENSED__max_length = 200
VERSION__max_length = 40
USER_AGENT__max_length = 512
LINE_NUMBER__max = 999999
STACKTRACE__max_length = 16000
REPORT__truncated = "\n[... report truncated ...]\n"
STATEMENT__max_length = 4000
INPUTS__max_length = 4000
# A redacted value shorter than this is not looked for in messages: it would replace parts of every number and word
SECRET__min_length = 3

VALUE__redacted = "<redacted>"
VALUE__encrypted = "<encrypted>"

# A database error with one of these SQLSTATE classes, or one of these codes, is the client's even when JAAQL's own SQL raised it: the data
# it was given (22, 23), a business rule of a jaaql function (JQ), a RAISE EXCEPTION (P0001)
SQLSTATE__clients_classes = ("22", "23", "JQ")
SQLSTATE__clients_codes = ("P0001",)
# Refused permission, the client's when the query ran as the requester (not as JAAQL)
SQLSTATE__insufficient_privilege = "42501"
# A database error with one of these SQLSTATE classes, or one of these codes, is the database server failing rather than refusing the SQL, so
# the server's whoever wrote the SQL: a connection gone (08), a resource exhausted (53: disk full, out of memory, too many connections), an I/O
# error (58), its configuration (F0), an internal error or corruption (XX), the server shutting down, crashing or starting (57P01-57P05; not
# 57014, a statement timeout). Not a read-only transaction (25006), which SQL can ask for
SQLSTATE__servers_classes = ("08", "53", "58", "F0", "XX")
SQLSTATE__servers_codes = ("57P01", "57P02", "57P03", "57P04", "57P05")
# Unless a PL/pgSQL RAISE raised it, which names any SQLSTATE the SQL asks for
SOURCE_FUNCTION__raise = "exec_stmt_raise"

# What code raises when what it reads is not of the shape it expects: a key missing, a value of another type
SHAPE_ERRORS = (TypeError, KeyError, AttributeError, IndexError, ValueError)

# The errors of an authorization response that the user causes: consent refused, a login not completed, a login page left open until it
# expired (Keycloak answers temporarily_unavailable described authentication_expired). Every other is the identity provider's or JAAQL's
OIDC__users_errors = frozenset({"access_denied", "login_required", "interaction_required", "consent_required", "account_selection_required"})
OIDC__users_descriptions = frozenset({"authentication_expired"})

# A request's inputs as a report names them, on a route that does not show their values
INPUT_NAMES__max = 50
INPUT_NAME__max_length = 60

ANSWERED__as_client_error = ", a server-side failure JAAQL answers as a client error"
ANSWERED__unexpected = UnhandledJaaqlServerError().error_code

REGEX__url_query = re.compile(r"((?:https?://|\burl: )[^\s?#'\"]*)\?[^\s'\")]*")
REGEX__file_line = re.compile(r'File "([^"]+)", line')
REGEX__parameter_name = re.compile(r"(?<![:\w]):([A-Za-z_][\w.\-]*)|(?<![#\w])#([A-Za-z_][\w.\-]*)")

_CLIENT_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)
_REPORTING_FILES = ("jaaql/utilities/server_errors.py", "jaaql/utilities/slow_queries.py")
# Where every routed request enters JAAQL
_ENTRY_FILE = "jaaql/mvc/base_controller.py"
# In the package, but never JAAQL's own code in a request
_TESTS = "jaaql/test/"
# The layers that run every query: the frame of interest for a fault in JAAQL's own query is the one that asked for it
_QUERY_LAYERS = ("jaaql/db/", "jaaql/interpreter/")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(jaaql.__file__)))


def _normalised(path: str) -> str:
    return os.path.normcase(os.path.abspath(path)).replace("\\", "/")


_ROOT_NORMALISED = _normalised(_ROOT).rstrip("/") + "/"

_application_of = None

_throttle = slow_queries.Throttle(lambda: (SERVER_ERROR__max_reports_per_hour, SERVER_ERROR__max_reports_per_account_per_hour,
                                           SERVER_ERROR__max_tracked_errors))


def configure(application_of=None):
    """
    application_of() names the application this box serves (its query cache's), under which an error of a request that names none is filed
    """
    global _application_of
    _application_of = application_of


def reset_throttle():
    _throttle.reset()


class Fault:
    """
    A server fault noted while a request ran, though what it answers may be a client error: the exception, the stack above the frame that
    caught it (its own traceback starts there), and for a query the statement, its query key, its database and whether the request wrote it
    """
    __slots__ = ("kind", "exception", "outer", "statement", "query_key", "database", "clients")

    def __init__(self, kind: str, exception, outer, statement, query_key, database, clients: bool = False):
        self.kind = kind
        self.exception = exception
        self.outer = outer
        self.statement = statement
        self.query_key = query_key
        self.database = database
        self.clients = clients

    def frames(self) -> list:
        return list(self.outer) + list(traceback.extract_tb(self.exception.__traceback__))


# Classifying -------------------------------------------------------------------------------------------------------------------------

def sqlstate_of(ex):
    diag = getattr(ex, "diag", None)
    return (getattr(diag, "sqlstate", None) if diag is not None else None) or getattr(ex, "sqlstate", None)


def is_clients_sqlstate(sqlstate, db_interface, ex=None) -> bool:
    """
    Whether a database error JAAQL's own SQL raised is still the client's: the data or the identity it was given. One raised by psycopg on
    the client side has no SQLSTATE and is the client's only when it is about the data (a NUL byte in a parameter)
    """
    if sqlstate is None:
        return isinstance(ex, (psycopg.DataError, psycopg.IntegrityError))
    if sqlstate[:2] in SQLSTATE__clients_classes or sqlstate in SQLSTATE__clients_codes:
        return True
    if sqlstate == SQLSTATE__insufficient_privilege:
        # As the requester's role (the interface's role is an account), not on the lookup connection or as the jaaql role
        role = getattr(db_interface, "role", None)
        return role is not None and role != ROLE__jaaql
    return False


def is_servers_failure(ex) -> bool:
    """
    Whether a database error is the database server failing under the SQL rather than refusing it (SQLSTATE__servers_classes and _codes), so
    the server's whoever wrote the SQL. Not when a PL/pgSQL RAISE raised it: SQL can raise any SQLSTATE it names
    """
    sqlstate = sqlstate_of(ex)
    if sqlstate is None or not (sqlstate[:2] in SQLSTATE__servers_classes or sqlstate in SQLSTATE__servers_codes):
        return False
    diag = getattr(ex, "diag", None)
    return getattr(diag, "source_function", None) != SOURCE_FUNCTION__raise


def status_of(ex) -> int:
    if isinstance(ex, HTTPException):
        return ex.code or 500
    if isinstance(ex, (HttpStatusException, JaaqlInterpretableHandledError)):
        try:
            return int(ex.response_code)
        except (TypeError, ValueError):
            return 500
    # Answered by the Exception handler with UnhandledJaaqlServerError
    return 500


def answered_of(ex) -> str:
    status = status_of(ex)
    if isinstance(ex, JaaqlInterpretableHandledError):
        return "%d (error_code %s)" % (status, ex.error_code)
    if isinstance(ex, (HTTPException, HttpStatusException)):
        return str(status)
    return "%d (error_code %s)" % (status, ANSWERED__unexpected)


def is_server_error(ex) -> bool:
    return status_of(ex) >= 500


def is_clients(ex) -> bool:
    return isinstance(ex, _CLIENT_GONE) or getattr(ex, ATTR__client_fault, False) is True


def _mark_seen(ex):
    try:
        setattr(ex, ATTR__seen, True)
    except Exception:
        pass


def _failed(ex):
    try:
        print(ERR__report_failed % (type(ex).__name__, str(ex)[:200]))
    except Exception:
        pass


# Noting faults ------------------------------------------------------------------------------------------------------------------------

def fresh_faults():
    # A background scope reused for job after job (the verifier) starts each with none noted
    scope = slow_queries.current_scope()
    if scope is not None:
        scope.faults = []


def note_fault(ex, kind: str, statement: str = None, query_key=None, database: str = None, catcher=None, clients: bool = False):
    """
    Notes a server fault in the current scope for its report, should the request fail. catcher is the frame that caught ex (by default the
    caller's), above which its traceback does not reach; clients, that the statement is the request's own SQL
    """
    try:
        scope = slow_queries.current_scope()
        if scope is None or len(scope.faults) >= SERVER_ERROR__max_faults:
            return
        catcher = catcher if catcher is not None else sys._getframe(1)
        outer = traceback.extract_stack(catcher)[:-1]
        # From where the request enters JAAQL (its route), or for a background job from its first frame of JAAQL's, without the server's
        # and Flask's frames above
        paths = [short_path(frame.filename) for frame in outer]
        first = next((idx for idx, path in enumerate(paths) if path == _ENTRY_FILE),
                     next((idx for idx, path in enumerate(paths) if _is_jaaqls(path)), 0))
        outer = outer[first:]
        scope.faults.append(Fault(kind, ex, outer, None if statement is None else str(statement), query_key, database, clients))
    except Exception as report_ex:
        _failed(report_ex)


def transform_failed(raised, answer, client_sql: bool, db_interface, query_key=None, statement=None):
    """
    For InterpretJAAQL.transform, whose statement raised raised and which answers with answer: notes the server fault, if it is one. Whoever
    wrote the SQL: the verifier's timeout, a connection lost after the SQL may have committed (answer marked ATTR__outcome_unknown), and the
    database server failing under it (is_servers_failure). For JAAQL's own SQL (client_sql False) also a database error whose SQLSTATE is not
    the client's and an exception that is no answer of JAAQL's (a bug). A lost connection whose request is re-run is not: it is reported once
    the attempts run out
    """
    try:
        if isinstance(raised, VerificationTimedOut):
            kind = FAULT__verification_timeout
        elif getattr(answer, ATTR__outcome_unknown, False) is True:
            kind = FAULT__outcome_unknown % (QUERY__requests if client_sql else QUERY__own)
        elif isinstance(answer, ConnectionLostError):
            return
        elif isinstance(raised, psycopg.Error) and is_servers_failure(raised):
            kind = FAULT__database_server if client_sql else FAULT__internal_sql
        elif client_sql:
            return
        elif isinstance(raised, psycopg.Error):
            if is_clients_sqlstate(sqlstate_of(raised), db_interface, raised):
                return
            kind = FAULT__internal_sql
        elif isinstance(raised, (HttpStatusException, JaaqlInterpretableHandledError, VerificationFailed)):
            return
        elif isinstance(raised, Exception):
            kind = FAULT__internal
        else:
            return
        note_fault(raised, kind, statement=statement, query_key=query_key, database=getattr(db_interface, "db_name", None),
                   catcher=sys._getframe(1), clients=client_sql)
    except Exception as report_ex:
        _failed(report_ex)


def commit_failed(raised, client_sql: bool, db_interface, query_key=None):
    """
    For InterpretJAAQL.transform, whose COMMIT was refused or lost and answered with raised, translated as a statement's error would be: notes
    the database error behind it when the connection was lost in flight or the database server failed, whoever wrote the SQL, and for JAAQL's
    own SQL also when its SQLSTATE is not the client's. A COMMIT that failed otherwise is answered 500 and reported as such
    """
    try:
        database_error = getattr(raised, ATTR__database_error, None)
        if not isinstance(raised, JaaqlInterpretableHandledError) or not isinstance(database_error, psycopg.Error):
            return
        if getattr(raised, ATTR__outcome_unknown, False) is True:
            kind = FAULT__outcome_unknown % (QUERY__requests if client_sql else QUERY__own)
        elif is_servers_failure(database_error):
            kind = FAULT__commit_database_server if client_sql else FAULT__commit
        elif client_sql or is_clients_sqlstate(sqlstate_of(database_error), db_interface, database_error):
            return
        else:
            kind = FAULT__commit
        note_fault(raised, kind, query_key=query_key, database=getattr(db_interface, "db_name", None), catcher=sys._getframe(1),
                   clients=client_sql)
    except Exception as report_ex:
        _failed(report_ex)


class _ReadingRequest:
    # reading_request's context: one that marks what it sees as the client's, one that marks nothing, each made once
    __slots__ = ("clients",)

    def __init__(self, clients: bool):
        self.clients = clients

    def __enter__(self):
        return self

    def __exit__(self, exc_type, ex, tb):
        if self.clients and isinstance(ex, SHAPE_ERRORS):
            try:
                client_fault(ex)
            except Exception as report_ex:
                _failed(report_ex)
        return False


_READING__clients = _ReadingRequest(True)
_READING__own = _ReadingRequest(False)


def reading_request(clients: bool = True):
    """
    Around code that reads what the request sent: an exception it raises because a key is missing or a value is of another type than expected
    (SHAPE_ERRORS, answered 500 as ever) is the client's, never a server error, and is raised on unchanged. With clients False (JAAQL built
    what is read) it marks nothing
    """
    return _READING__clients if clients else _READING__own


def remote_procedure_crash(ex, application, name, returncode, stdout, stderr):
    """
    Files ex, the answer to a cloud procedure or webhook that crashed, under remote-procedure:<application>/<name>, with its exit code and the
    length of what it printed: never the output itself, which can hold anyone's data. Returns ex
    """
    try:
        setattr(ex, ATTR__report_source, slow_queries._printable("remote-procedure:%s/%s" % (application, name)))
        setattr(ex, ATTR__report_detail, "the remote procedure exited with code %s, printing %d characters to stdout and %d to stderr (not shown)"
                % (returncode, len(stdout or ""), len(stderr or "")))
    except Exception as report_ex:
        _failed(report_ex)
    return ex


# Deciding -----------------------------------------------------------------------------------------------------------------------------

def request_failed(ex, route: str, installed: bool, answered: str = None):
    """
    For routed_function, with the exception a request failed with, before Flask answers it: reports it when it is a server error (5xx or
    unexpected), else the last server fault noted while the request ran, if any. answered overrides what the report says the client got
    """
    try:
        if not isinstance(ex, Exception):
            # A worker shutting down (GreenletExit, SystemExit)
            return
        _mark_seen(ex)
        if route in SERVER_ERROR__unreported_routes or not installed or is_clients(ex):
            return
        scope = slow_queries.current_scope()
        faults = list(scope.faults) if scope is not None else []
        if is_server_error(ex):
            _report(scope, ex, None, faults, answered or answered_of(ex))
        elif faults:
            _report(scope, ex, faults[-1], faults[:-1], answered or answered_of(ex) + ANSWERED__as_client_error)
    except Exception as report_ex:
        _failed(report_ex)


def background_failed(ex, answered: str):
    """
    For a background job in its own scope (the auth verifier): reports any failure but a refused login, by the last server fault it noted
    when there is one
    """
    try:
        if not isinstance(ex, Exception) or isinstance(ex, UserUnauthorized) or is_clients(ex):
            return
        _mark_seen(ex)
        scope = slow_queries.current_scope()
        faults = list(scope.faults) if scope is not None else []
        if faults:
            _report(scope, ex, faults[-1], faults[:-1], answered)
        else:
            _report(scope, ex, None, [], answered)
    except Exception as report_ex:
        _failed(report_ex)


def unrouted_failure(ex):
    """
    For the Flask error handlers: reports by the same rule an exception no routed request saw, as a route added to the app directly raises it
    """
    try:
        if not isinstance(ex, Exception):
            return
        original = getattr(ex, "original_exception", None)
        if getattr(ex, ATTR__seen, False) or getattr(original, ATTR__seen, False):
            return
        _mark_seen(ex)
        failed = original if isinstance(original, Exception) else ex
        if not has_request_context():
            return
        route = request.url_rule.rule if request.url_rule is not None else request.path
        installed = bool(getattr(getattr(current_app, "model", None), "has_installed", True))
        if route in SERVER_ERROR__unreported_routes or not installed or is_clients(failed) or not is_server_error(failed):
            return
        scope = slow_queries.Scope(route=route, method=request.method, path=request.path, user_agent=request.headers.get("User-Agent"),
                                   slow=False)
        _report(scope, failed, None, [], answered_of(failed))
    except Exception as report_ex:
        _failed(report_ex)


def authorization_response_failed(error, description, installed: bool):
    """
    For /exchange-auth-code, whose authorization response from the identity provider (verified, so the provider's) carries error, described
    by description, and which answers it with its redirect: reports it unless the user caused it (OIDC__users_errors), as a failure raised
    where this is called
    """
    try:
        if error in OIDC__users_errors or description in OIDC__users_descriptions:
            return
        caller = sys._getframe(1)
        failure = AuthorizationResponseError(slow_queries._printable("%s: %s" % (error, description)))
        failure = failure.with_traceback(types.TracebackType(None, caller, caller.f_lasti, caller.f_lineno))
        request_failed(failure, ENDPOINT__oidc_get_token, installed, answered=ANSWERED__oidc_exchange)
    except Exception as report_ex:
        _failed(report_ex)


# The report ---------------------------------------------------------------------------------------------------------------------------

def short_path(path: str) -> str:
    """
    A frame's file as a report names it, without the box's install path: jaaql/... from the folder that holds the package, site-packages/...,
    else its folder and name
    """
    if not path:
        return "?"
    if path.startswith("<"):
        return path
    absolute = os.path.abspath(path).replace("\\", "/")
    normalised = _normalised(path)
    at = normalised.rfind("/site-packages/")
    if at >= 0:
        return absolute[at + 1:]
    if normalised.startswith(_ROOT_NORMALISED):
        return absolute[len(_ROOT_NORMALISED):]
    return "/".join(absolute.split("/")[-2:])


def _is_jaaqls(path: str) -> bool:
    return path.startswith("jaaql/") and not path.startswith(_TESTS) and path not in _REPORTING_FILES


def _frame_of(frames, above_query_layers: bool):
    # The deepest frame of JAAQL's own code; for a fault in JAAQL's own query the deepest above the layers that run every query, which is
    # the code that asked for it
    own = [(frame, short_path(frame.filename)) for frame in frames]
    own = [(frame, path) for frame, path in own if _is_jaaqls(path)]
    if above_query_layers:
        above = [(frame, path) for frame, path in own if not path.startswith(_QUERY_LAYERS)]
        if above:
            return above[-1]
    if own:
        return own[-1]
    if frames:
        return frames[-1], short_path(frames[-1].filename)
    return None, None


def message_of(ex) -> str:
    message = getattr(ex, "message", None) if isinstance(ex, (HttpStatusException, JaaqlInterpretableHandledError)) else None
    if isinstance(message, dict):
        # A dict query's wrapper, {error, set, query, parameters}: the error only
        message = message.get("error")
    if message is not None and not isinstance(message, str):
        message = json.dumps(message, default=str)
    if message is None:
        message = str(ex)
    lines = [line for line in str(message).strip().splitlines() if line.strip()]
    return lines[0].strip() if lines else ""


def condensed_of(ex) -> str:
    # A refused COMMIT by the database error behind its answer
    database_error = getattr(ex, ATTR__database_error, None)
    ex = database_error if isinstance(database_error, psycopg.Error) else ex
    sqlstate = sqlstate_of(ex) if isinstance(ex, psycopg.Error) else None
    return type(ex).__name__ + (" " + sqlstate if sqlstate else "") + ": " + message_of(ex)


def scrub(text: str, secrets) -> str:
    """
    text without the query string of any URL (Keycloak's and requests' errors put the email there) and, on the lines that are not a
    traceback's file and code lines, without any redacted value or the value of an encrypted literal (#'...', which the database only ever
    sees encrypted, as the request's inputs and a message quoting its SQL hold it)
    """
    text = REGEX__url_query.sub(r"\1?" + VALUE__redacted, text)
    secrets = sorted([secret for secret in secrets if len(secret) >= SECRET__min_length], key=len, reverse=True)
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if not line.startswith("  "):
            line = slow_queries._masked(line)
            for secret in secrets:
                line = line.replace(secret, VALUE__redacted)
            lines[idx] = line
    return "\n".join(lines)


def _traceback_text(ex, outer=None) -> str:
    te = traceback.TracebackException(type(ex), ex, ex.__traceback__, compact=True)
    if outer:
        te.stack = traceback.StackSummary.from_list(list(outer) + list(te.stack))
    return REGEX__file_line.sub(lambda match: 'File "%s", line' % short_path(match.group(1)), "".join(te.format()))


def _encrypted_names(inputs: dict) -> set:
    # The parameters a request's SQL takes as #name, which the database only ever sees encrypted
    names = set()
    pending = [inputs.get(KEY__query)]
    while pending:
        query = pending.pop()
        if isinstance(query, str):
            names.update(match.group(2) for match in REGEX__parameter_name.finditer(query) if match.group(2))
        elif isinstance(query, dict):
            pending.extend(query.values())
        elif isinstance(query, (list, tuple)):
            pending.extend(query)
    return names


def _email_addresses(value, secrets: set, depth: int = 0):
    # Every value in inputs whose values a report does not show that holds an @, looked for in its messages: the account is named by its
    # id only, and a login names it by its email address
    if depth > slow_queries.VALUE__max_depth:
        return
    if isinstance(value, dict):
        for inner in value.values():
            _email_addresses(inner, secrets, depth + 1)
    elif isinstance(value, (list, tuple)):
        for inner in value:
            _email_addresses(inner, secrets, depth + 1)
    elif isinstance(value, str) and "@" in value:
        secrets.add(value)


def _inputs_text(scope, secrets: set) -> (str, str):
    """
    The heading and the text of the request's inputs in a report, adding to secrets the values to remove from its messages: on a query route
    (SERVER_ERROR__routes_with_inputs) the inputs with their values (secrets <redacted>, # parameters <encrypted>), on every other route their
    names only
    """
    inputs = scope.inputs if scope is not None else None
    if not isinstance(inputs, dict) or len(inputs) == 0:
        return None, ""
    shown = slow_queries._redacted(inputs, secrets)
    if scope.route not in SERVER_ERROR__routes_with_inputs:
        _email_addresses(inputs, secrets)
        names = [slow_queries._printable(str(name))[:INPUT_NAME__max_length] for name in inputs]
        text = ", ".join(names[:INPUT_NAMES__max]) + ("" if len(names) <= INPUT_NAMES__max else " and %d more" % (len(names) - INPUT_NAMES__max))
        return "Request inputs (names only, values not shown)", text
    parameters = shown.get(KEY__parameters)
    if isinstance(parameters, dict):
        for name in _encrypted_names(inputs) & set(parameters):
            if parameters[name] is not None:
                parameters[name] = VALUE__encrypted
    try:
        text = json.dumps(shown, default=str, ensure_ascii=False)
    except Exception:
        text = str(shown)
    # The encrypted literals of the request's SQL masked before it is cut, which could leave one without its closing quote
    text = slow_queries._masked(text)
    if len(text) > INPUTS__max_length:
        text = text[:INPUTS__max_length] + "..."
    return "Request inputs", text


def _parameter_names(statement: str) -> list:
    names = []
    for match in REGEX__parameter_name.finditer(statement):
        name = match.group(1) or match.group(2)
        if name not in names:
            names.append(name)
    return names


def _statement_text(fault: Fault) -> str:
    statement = slow_queries._masked(fault.statement)
    if len(statement) > STATEMENT__max_length:
        statement = statement[:STATEMENT__max_length] + "\n[statement truncated]"
    names = _parameter_names(fault.statement)
    return "".join("\t" + line + "\n" for line in statement.strip("\r\n").splitlines()) + \
        ("\tParameters: " + ", ".join(names) + " (values not shown)\n" if names else "")


def _where_of(frame, path: str) -> str:
    if frame is None:
        return path or "?"
    return "%s:%s in %s" % (path, frame.lineno, frame.name)


def _cut(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[:length - 13] + "~" + slow_queries._sha1(text)[:12]


def _box_application():
    try:
        application = _application_of() if _application_of is not None else None
    except Exception:
        application = None
    return application if isinstance(application, str) else None


def _report(scope, ex, fault, earlier, answered: str):
    primary = fault.exception if fault is not None else ex
    frames = fault.frames() if fault is not None else list(traceback.extract_tb(primary.__traceback__))
    frame, path = _frame_of(frames, fault is not None)
    source = getattr(primary, ATTR__report_source, None)
    if source is not None:
        source_file, line, column = _cut(source, SOURCE_FILE__max_length), None, None
    else:
        source_file = _cut(path or "?", SOURCE_FILE__max_length)
        line = frame.lineno if frame is not None and isinstance(frame.lineno, int) and 0 <= frame.lineno <= LINE_NUMBER__max else None
        colno = getattr(frame, "colno", None) if frame is not None else None
        column = colno + 1 if isinstance(colno, int) and 0 <= colno < LINE_NUMBER__max else None
    application = (scope.application if scope is not None else None) or _box_application()
    # One line, whatever the request named its application or path
    route = slow_queries._printable(slow_queries._where(scope)) if scope is not None else "-"
    line_text = LINE__server_error % (type(primary).__name__, source_file + ("" if line is None else ":%d" % line), route,
                                      slow_queries._printable(application or "-"), answered)
    if not sentinel.is_configured():
        print(line_text)
        return
    source_system = slow_queries.source_system_of(application)
    decision, repeats = _throttle.decide(source_system + ":" + source_file + ":" + str(line) + ":" + type(primary).__name__, 0.0,
                                         scope.account_id if scope is not None else None)
    if decision == slow_queries.DECISION__report:
        payload = payload_of(scope, primary, fault, earlier, answered, frame, path, source_file, line, column, application, repeats)
        if not sentinel.send(payload):
            decision = "Sentinel queue full, not reported"
    print(line_text + " - " + decision)


def stacktrace_of(scope, primary, fault, earlier, answered, frame, path, application, repeats, secrets: set) -> str:
    inputs_heading, inputs = _inputs_text(scope, secrets)
    where = _where_of(frame, path)
    if fault is not None:
        where += " (" + fault.kind + ")"
    if scope is not None and scope.background is not None:
        route = "Background: " + scope.background + " on " + (slow_queries._public_url or slow_queries._host)
        account = ""
    else:
        route = "Route: " + (slow_queries._printable(slow_queries._where(scope)) if scope is not None else "-") + " on " + \
                (slow_queries._public_url or slow_queries._host)
        account = " | account: " + (str(scope.account_id) if scope is not None and scope.account_id is not None else "-")
    lines = [
        "Server error: " + condensed_of(primary),
        "Answered: " + answered,
        "Where: " + where,
    ]
    detail = getattr(primary, ATTR__report_detail, None)
    if detail is not None:
        lines.append("Detail: " + detail)
    lines += [
        route,
        "Application: " + slow_queries._printable(application or "-") + " | database: " +
        ((fault.database if fault is not None else None) or "-") + account,
        "At: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") + " | JAAQL " + VERSION + " | worker pid " + str(os.getpid()),
    ]
    if repeats is not None and repeats[0] > 0:
        lines.append("Repeats: %d more in this worker since its last report" % repeats[0])
    text = "\n".join(lines) + "\n"
    if fault is not None and fault.statement is not None:
        text += "\nStatement (%s%s):\n" % ("the request's" if fault.clients else "JAAQL's own",
                                           "" if fault.query_key is None else ", query key " + str(fault.query_key)) + _statement_text(fault)
    if earlier:
        text += "\nAlso noted in this request:\n" + "".join(
            "\t%s, %s: %s\n" % (noted.kind, _where_of(*_frame_of(noted.frames(), True)), condensed_of(noted.exception)) for noted in earlier)
    if inputs:
        text += "\n" + inputs_heading + ":\n\t" + inputs + "\n"
    text += "\n" + _traceback_text(primary, fault.outer if fault is not None else None)
    text = scrub(text, secrets)
    if len(text) > STACKTRACE__max_length:
        # The head (what failed, where, the statement, the inputs) and the tail (the exception itself), without the middle of the traceback
        head = STACKTRACE__max_length // 2
        text = text[:head] + REPORT__truncated + text[-(STACKTRACE__max_length - head - len(REPORT__truncated)):]
    # Without the trailing newline, which Sentinel's ingest route strips
    return text.rstrip("\n")


def payload_of(scope, primary, fault, earlier, answered, frame, path, source_file, line, column, application, repeats) -> dict:
    # Exactly the keys Sentinel's ingest route binds, all of them: it refuses a report with any other key
    secrets = set()
    stacktrace = stacktrace_of(scope, primary, fault, earlier, answered, frame, path, application, repeats, secrets)
    user_agent = scope.user_agent if scope is not None else None
    if scope is not None:
        location = slow_queries._location(scope)
    else:
        location = slow_queries._public_url or slow_queries._host
    return {
        "location": location[:LOCATION__max_length],
        "source_file": source_file,
        "error_condensed": scrub(condensed_of(primary), secrets)[:ERROR_CONDENSED__max_length],
        "file_line_number": line,
        "file_col_number": column,
        "version": ("JAAQL " + VERSION)[:VERSION__max_length],
        "source_system": slow_queries.source_system_of(application),
        "stacktrace": stacktrace,
        # Encrypted at rest by Sentinel, which encodes ASCII only
        "user_agent": slow_queries._ascii(user_agent)[:USER_AGENT__max_length] if user_agent else "JAAQL/" + VERSION,
    }
