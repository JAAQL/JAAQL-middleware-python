import re
import uuid

import psycopg
from psycopg import OperationalError
from psycopg.conninfo import make_conninfo
from psycopg.pq import TransactionStatus
from psycopg_pool import ConnectionPool, PoolClosed
import queue
from psycopg.errors import ProgrammingError, InvalidParameterValue, UndefinedFunction, InternalError
import threading
import traceback
from jaaql.constants import ERR__invalid_token

from jaaql.db.db_interface import DBInterface, ECHO__none, CHAR__newline
from jaaql.exceptions.http_status_exception import *
from jaaql.exceptions.custom_http_status import CustomHTTPStatus
from jaaql.exceptions.jaaql_interpretable_handled_errors import UserUnauthorized, DatabaseOperationalError, handled_error_from_database_error, \
    database_error_descriptor
from jaaql.constants import KEY__database

ERR__connect_db = "Could not create connection to database!"
ERR__commit_outcome_unknown = "The connection was lost during COMMIT, so whether the transaction was persisted is unknown: "

PGCONN__min_conns = 5
PGCONN__max_conns = 10

TIMEOUT = 2.5

# Upper bound on how long a request waits for the parallel auth verifier's verdict before failing
# closed. Kept below the nginx proxy read timeout so the worker unwinds and returns its connection
# rather than the request dying at the proxy while the worker hangs on holding an open transaction.
WAIT_HOOK__timeout = 30
ERR__verification_timed_out = "Authorization verification timed out"

# libpq TCP keepalives: detect a peer that vanishes (DB reboot, network drop) within ~25s so the
# socket errors instead of a read blocking indefinitely. Without this the single serial
# auth-verification thread can wedge forever on a dead connection and, via the wait below, take
# every authenticated request down with it. Ignored by libpq for unix-socket connections.
CONN_STR__keepalives = " keepalives=1 keepalives_idle=10 keepalives_interval=5 keepalives_count=3"

ERR__invalid_role = "Role not allowed, invalid format!"
ERR__must_use_canned_query = "Must use canned query as you are not an admin!"

QUERY__dba_query = "SELECT pg_has_role(datdba::regrole, 'MEMBER') FROM pg_database WHERE datname = %(database)s;"
QUERY__dba_query_external = "SELECT pg_has_role(datdba::regrole, 'MEMBER') FROM pg_database WHERE datname = current_database();"
# Applies an interface's session_settings in one statement however many there are, names and values bound as parameters.
# is_local = true: they end with the request's transaction (COMMIT or ROLLBACK), so they never reach a later checkout
QUERY__apply_session_settings = "SELECT set_config(s.n, s.v, true) FROM unnest(%s::text[], %s::text[]) AS s(n, v)"

try:
    # Pipeline mode needs libpq >= 14. create_app refuses to boot when this is False so a server
    # can never silently degrade; the sequential fallback in execute_query exists only for
    # non-server tooling that imports this module directly
    PIPELINE_SUPPORTED = psycopg.Pipeline.is_supported()
except Exception:
    PIPELINE_SUPPORTED = False


def _execute_pending_statement(cursor, statement):
    # A pending statement is SQL text, or a (SQL, parameters) pair when it carries client-supplied values
    if isinstance(statement, tuple):
        cursor.execute(statement[0], statement[1])
    else:
        cursor.execute(statement)


class JaaqlPGConnection(psycopg.Connection):
    """
    Connection whose per-checkout session-authorization statements (jaaql__set_session_authorization
    / SET ROLE, then the transaction-local session settings) are deferred at checkout and sent
    pipelined with the first real query, saving a network round trip per checkout.

    Safety property: authorization must never be skippable. Any cursor obtained through the normal
    cursor() call while statements are still pending executes them eagerly first, so raw connection
    usage cannot run as the pool user. execute_query claims the statements via
    jaaql_take_pending_auth and is then responsible for sending them before (or batched with) the
    query it executes.
    """

    _jaaql_pending_auth = None
    _jaaql_flushing = False

    def jaaql_set_pending_auth(self, statements: list):
        self._jaaql_pending_auth = statements

    def jaaql_has_pending_auth(self) -> bool:
        return self._jaaql_pending_auth is not None

    def jaaql_take_pending_auth(self):
        pending, self._jaaql_pending_auth = self._jaaql_pending_auth, None
        return pending

    def jaaql_raw_cursor(self, *args, **kwargs):
        # Bypasses the pending-authorization flush; the caller has taken responsibility for
        # executing the pending statements itself
        return super().cursor(*args, **kwargs)

    def cursor(self, *args, **kwargs):
        if self._jaaql_pending_auth is not None and not self._jaaql_flushing:
            self._jaaql_flushing = True
            try:
                pending = self.jaaql_take_pending_auth()
                with super().cursor() as flush_cursor:
                    for statement in pending:
                        _execute_pending_statement(flush_cursor, statement)
            finally:
                self._jaaql_flushing = False
        return super().cursor(*args, **kwargs)


def _statement_is_preparable(query: str) -> bool:
    # Server-side PREPARE accepts a single statement only. A ';' anywhere except trailing means the
    # text may hold multiple statements (a ';' inside a string literal merely skips the
    # optimisation, which is the safe direction)
    return ";" not in query.rstrip().rstrip(";")


REGEX__word = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
STATEMENTS__ending_transaction = {"COMMIT", "END", "ROLLBACK", "ABORT"}


def _leading_word(query: str, i: int = 0) -> (str, int):
    # The first word at or after i, upper-cased, and where it ends. Whitespace, -- comments and /* */ comments, which nest, are
    # skipped as Postgres skips them
    n = len(query)
    while i < n:
        if query[i].isspace():
            i += 1
        elif query.startswith("--", i):
            while i < n and query[i] not in "\r\n":
                i += 1
        elif query.startswith("/*", i):
            depth = 0
            while i < n:
                if query.startswith("/*", i):
                    depth += 1
                    i += 2
                elif query.startswith("*/", i):
                    depth -= 1
                    i += 2
                    if depth == 0:
                        break
                else:
                    i += 1
        else:
            break
    match = REGEX__word.match(query, i)
    return (match.group(0).upper(), match.end()) if match is not None else ("", i)


def _statement_may_end_transaction(query: str) -> bool:
    # True when running the text may end the transaction it runs in, persisting what ran before it: several statements, any of
    # which may (a ';' in a literal counts too, erring towards True), or one COMMIT, END, ROLLBACK, ABORT or PREPARE TRANSACTION
    if not _statement_is_preparable(query):
        return True
    word, end = _leading_word(query)
    return word in STATEMENTS__ending_transaction or (word == "PREPARE" and _leading_word(query, end)[0] == "TRANSACTION")


def _escape_unescaped_percent(query: str) -> str:
    # psycopg3 scans every '%' in the SQL when parameters are supplied and
    # rejects anything that isn't a placeholder or '%%'. JAAQL uses named
    # parameters only (:parameter -> %(name)s), so positional %s/%b/%t must
    # never survive: any '%s' in author SQL is a literal inside a string
    # (LIKE '%saas%', LIKE '%twynstra%', etc.), not a placeholder. Escape
    # everything except '%%' and '%(name)X'.
    out = []
    i = 0
    n = len(query)
    while i < n:
        if query[i] != '%':
            out.append(query[i])
            i += 1
            continue

        nxt = query[i + 1] if i + 1 < n else ''
        if nxt == '%':
            out.append('%%')
            i += 2
        elif nxt == '(':
            close = query.find(')', i + 2)
            if close == -1 or close + 1 >= n:
                out.append('%%')
                i += 1
            else:
                out.append(query[i:close + 2])
                i = close + 2
        else:
            out.append('%%')
            i += 1
    return ''.join(out)


class DBPGInterface(DBInterface):

    HOST_POOLS = {}
    HOST_POOLS_QUEUES = {}

    @staticmethod
    def close_all_pools():
        for _, user_pool_dict in DBPGInterface.HOST_POOLS.items():
            for _, pool in user_pool_dict.items():
                pool.close()
        DBPGInterface.HOST_POOLS = {}
        DBPGInterface.HOST_POOLS_QUEUES = {}

    @staticmethod
    def check_all_pools():
        # Force a synchronous liveness check of every pooled connection, discarding and replacing any
        # that are broken. clean() reboots Postgres, and background activity (the per-minute cron, the
        # auth verifier) can re-open pools DURING the reboot/reinstall window, caching connections to
        # the old postmaster. psycopg_pool only detects those lazily, so the first real request after
        # the wipe (e.g. \register @dba) gets handed a dead connection whose commit then fails "the
        # connection is lost". Calling this once Postgres is stable makes the refresh deterministic.
        for _, user_pool_dict in DBPGInterface.HOST_POOLS.items():
            for _, pool in user_pool_dict.items():
                try:
                    pool.check()
                except Exception:
                    pass

    @staticmethod
    def _process_returned_conn(username: str, db_name: str, conn, do_reset: bool):
        if isinstance(conn, JaaqlPGConnection) and conn.jaaql_has_pending_auth():
            # The deferred authorization statements were never sent, so the session still runs as
            # the pool user and there is nothing to reset. Clearing them here also stops the
            # cursor() below from flushing them
            conn.jaaql_take_pending_auth()
            do_reset = False
        if do_reset:
            try:
                if conn.info.transaction_status != TransactionStatus.IDLE:
                    # Whatever the request left open is not the putback's to persist (a read_only request, a caller that
                    # returned a connection mid-transaction): the commit below is for the reset statements alone
                    conn.rollback()
                with conn.cursor() as cursor:
                    cursor.execute("RESET ROLE;")
                    if hasattr(conn, "jaaql_reset_key"):
                        cursor.execute("SELECT jaaql_extension.jaaql__reset_session_authorization('" + str(conn.jaaql_reset_key) + "');")
                    cursor.execute("RESET ALL;")
                conn.commit()
            except Exception:
                # A connection that could not be reset must never serve another request, and must not be kept from the pool
                # either: closed, putconn discards it and the pool opens a replacement
                conn.close()
        DBPGInterface.HOST_POOLS[username][db_name].putconn(conn)

    @staticmethod
    def put_conn_threaded(username: str, db_name: str, the_queue: queue.Queue):
        while True:
            conn, do_reset = the_queue.get()
            try:
                DBPGInterface._process_returned_conn(username, db_name, conn, do_reset)
            except Exception:
                # The pool has likely been wiped or replaced. Close the connection so it cannot linger outside any pool
                try:
                    conn.close()
                except Exception:
                    pass

    def __init__(self, config, host: str, port: int, db_name: str, username: str, role: str = None, password: str = None, sub_role: str = None,
                 session_settings: dict = None):
        super().__init__(config, host, username)

        self.role = role
        self.sub_role = sub_role
        # {setting name: value}, applied transaction-locally after the authorization statements. Built server side (see
        # pop_timeline_settings), never named by the client
        self.session_settings = session_settings
        if sub_role is not None:
            if len([ch for ch in sub_role if not ch.isalnum() and ch not in ['_', '-']]) != 0:
                raise HttpStatusException(ERR__invalid_role, HTTPStatus.UNAUTHORIZED)

        self.output_query_exceptions = config["DEBUG"]["output_query_exceptions"].lower() == "true"
        self.username = username
        self.db_name = db_name

        if self.username not in DBPGInterface.HOST_POOLS:
            DBPGInterface.HOST_POOLS[self.username] = {}
            DBPGInterface.HOST_POOLS_QUEUES[self.username] = {}

        user_pool = DBPGInterface.HOST_POOLS[self.username]

        self.conn_str = None
        the_pool = None

        if password is not None:
            try:
                conn_params = {"user": username, "password": password, "dbname": db_name}
                # Important we don't list the host as this will force a unix socket
                if host is not None and host not in ['localhost', '127.0.0.1']:
                    conn_params["host"] = host

                if str(port) != "5432":
                    conn_params["port"] = str(port)

                # make_conninfo quotes every value, so no value can add a setting of its own (a database named
                # "x host=elsewhere" would otherwise send the superuser credentials to that host)
                conn_str = make_conninfo(CONN_STR__keepalives.strip(), **conn_params)

                self.conn_str = conn_str

                if self.db_name not in user_pool:
                    the_pool = ConnectionPool(conn_str, min_size=PGCONN__min_conns, max_size=PGCONN__max_conns, max_lifetime=60 * 30,
                                              connection_class=JaaqlPGConnection)
                    the_pool.getconn(timeout=TIMEOUT)
                    user_pool[self.db_name] = the_pool
                    the_queue = queue.Queue()
                    DBPGInterface.HOST_POOLS_QUEUES[self.username][self.db_name] = the_queue
                    threading.Thread(target=DBPGInterface.put_conn_threaded, args=[self.username, self.db_name, the_queue], daemon=True).start()
            except OperationalError as ex:
                if the_pool is not None:
                    the_pool.close()
                if "does not exist" in str(ex).split("\"")[-1] or "couldn't get a connection after" in str(ex):
                    raise HttpStatusException("Database \"" + self.db_name + "\" does not exist",
                                              CustomHTTPStatus.DATABASE_NO_EXIST)
                else:
                    raise HttpStatusException(str(ex))

    def _get_conn(self):
        conn = DBPGInterface.HOST_POOLS[self.username][self.db_name].getconn(timeout=TIMEOUT)
        conn.jaaql_reset_key = str(uuid.uuid4())
        if isinstance(conn, JaaqlPGConnection):
            # Discard any pending authorization left by a previous checkout that was returned
            # without executing (defensive: every return path should already have cleared it).
            # Without this a later checkout could execute a previous user's authorization
            conn.jaaql_take_pending_auth()
        if conn.autocommit:
            # A request that asked for autocommit hands its connection back still in autocommit and
            # psycopg_pool does not reset it, so the next request to land on it would run statement by
            # statement: a multi-query submit no longer atomic, a transaction-local setting gone before
            # the query it was meant for. transform() applies autocommit again for requests that ask.
            # The pool only hands out idle connections, so this cannot fail on an open transaction
            conn.autocommit = False
        if self.role is not None or self.sub_role is not None or self.session_settings:
            # Deferred: sent pipelined with the first query by execute_query, or flushed eagerly by
            # JaaqlPGConnection.cursor() if the connection is used rawly. Errors these statements
            # raise are translated by _translate_session_auth_error at execution time; a dead pool
            # connection, previously detected here, surfaces at that first query, and the request
            # is re-run on a fresh connection (InterpretJAAQL.transform, ConnectionLostError)
            pending = []
            if self.role is not None:
                pending.append("SELECT jaaql_extension.jaaql__set_session_authorization('" + self.role + "', '" + conn.jaaql_reset_key + "');")
            if self.sub_role is not None:
                pending.append("SET ROLE \"" + self.sub_role + "\"")
            if self.session_settings:
                # After the authorization statements, so the settings are applied as the user and only once the
                # parallel verifier has accepted the request
                pending.append((QUERY__apply_session_settings, (list(self.session_settings.keys()), list(self.session_settings.values()))))
            conn.jaaql_set_pending_auth(pending)
        return conn

    def get_pool(self):
        if self.db_name not in DBPGInterface.HOST_POOLS[self.username]:
            DBPGInterface.HOST_POOLS[self.username][self.db_name] = ConnectionPool(self.conn_str, min_size=PGCONN__min_conns,
                                                                                   max_size=PGCONN__max_conns, max_lifetime=60 * 30,
                                                                                   connection_class=JaaqlPGConnection)
        return DBPGInterface.HOST_POOLS[self.username][self.db_name]

    def get_conn(self, retry_closed_pool: bool = True):
        try:
            conn = self._get_conn()
        except PoolClosed as ex:
            # Jaaql has likely been reinstalled, this pool has been forcibly closed
            if retry_closed_pool:
                DBPGInterface.HOST_POOLS[self.username][self.db_name] = ConnectionPool(self.conn_str, min_size=PGCONN__min_conns,
                                                                                       max_size=PGCONN__max_conns, max_lifetime=60 * 30,
                                                                                       connection_class=JaaqlPGConnection)
                conn = self.get_conn(retry_closed_pool=False)
                if not conn:
                    raise ex
            else:
                return False
        except HttpStatusException as ex:
            raise ex
        except Exception:
            traceback.print_exc()
            raise HttpStatusException(ERR__connect_db, HTTPStatus.INTERNAL_SERVER_ERROR)

        return conn

    def put_conn(self, conn):
        DBPGInterface.HOST_POOLS_QUEUES[self.username][self.db_name].put((conn, self.role is not None))

    def close(self):
        DBPGInterface.HOST_POOLS[self.username].pop(self.db_name).close()
        DBPGInterface.HOST_POOLS_QUEUES[self.username].pop(self.db_name)

    def check_dba(self, conn, wait_hook: queue.Queue = None):
        columns, _, rows = self.execute_query(conn, QUERY__dba_query, parameters={KEY__database: self.db_name}, wait_hook=wait_hook, prepare=True)
        if not rows[0]:
            raise HttpStatusException(ERR__must_use_canned_query)

    def _translate_session_auth_error(self, ex):
        """
        The deferred session-authorization statements execute batched with the first query, so
        their errors surface during execute_query rather than at checkout. This translates them to
        the same exceptions the eager checkout path used to raise. Returns None when the error is
        not recognisably from the authorization statements (the caller re-raises it untouched, so
        a query's own error keeps its normal handling)
        """
        if isinstance(ex, InternalError):
            if str(ex).startswith("role \"") and str(ex).endswith("\" does not exist"):
                return HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
        if isinstance(ex, UndefinedFunction) and "jaaql__set_session_authorization" in str(ex):
            return HttpStatusException("Database '%s' has not been configured for usage with JAAQL. Please ask the dba to run 'configure_database_for_use_with_jaaql' from the jaaql database" % self.db_name)
        if isinstance(ex, InvalidParameterValue) and "role" in str(ex).lower():
            return HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
        return None

    def execute_query(self, conn, query, parameters=None, wait_hook: queue.Queue = None, prepare: bool = False,
                      capture_provenance: list = None):
        try:
            cursor_factory = conn.jaaql_raw_cursor if isinstance(conn, JaaqlPGConnection) else conn.cursor
            with cursor_factory() as cursor:
                do_prepare = prepare and _statement_is_preparable(query)

                if wait_hook:
                    try:
                        verdict = wait_hook.get(timeout=WAIT_HOOK__timeout)
                    except queue.Empty:
                        # The parallel verifier never delivered a verdict (its single serial thread
                        # wedged, e.g. on a connection killed by a DB reboot). Fail closed and let
                        # the worker unwind - without this bound the worker blocks forever holding
                        # an open transaction, and enough of them starve the pool into nginx 504s.
                        raise Exception(ERR__verification_timed_out)
                    # The verdict belongs to the request, not to this attempt at it: left on the hook, a
                    # request re-run on a fresh connection after losing its first one reads it again
                    # instead of waiting out WAIT_HOOK__timeout for a second verdict that never comes
                    wait_hook.put(verdict)
                    res, err, code = verdict
                    if not res:
                        if code == 500:
                            raise Exception(err)
                        raise UserUnauthorized()

                def execute_main_query():
                    if parameters is None or len(parameters.keys()) == 0:
                        cursor.execute(query, prepare=do_prepare)
                    else:
                        cursor.execute(_escape_unescaped_percent(query), parameters, prepare=do_prepare)

                # Claimed only now, after the wait_hook: if verification rejects the request,
                # the statements remain pending and the putback thread discards them unsent
                pending_auth = conn.jaaql_take_pending_auth() if isinstance(conn, JaaqlPGConnection) else None

                if pending_auth:
                    auth_cursor = conn.jaaql_raw_cursor()
                    try:
                        # Pipeline mode is unsafe for two kinds of statement, so restrict it to
                        # single-command queries on transactional (non-autocommit) connections;
                        # everything else falls back to sequential execution:
                        #  - it forces the extended protocol on every execute, which rejects a
                        #    multi-command string ("cannot insert multiple commands into a
                        #    prepared statement"); the sequential fallback runs the main query
                        #    under the simple protocol that permits several commands.
                        #  - it wraps statements in an implicit transaction, which statements
                        #    that cannot run in a transaction block (CREATE DATABASE, VACUUM,
                        #    CREATE INDEX CONCURRENTLY, ...) reject. JAAQL runs those with
                        #    autocommit=True, so skipping the pipeline there keeps them standalone.
                        if PIPELINE_SUPPORTED and _statement_is_preparable(query) and not conn.autocommit:
                            with conn.pipeline():
                                for statement in pending_auth:
                                    _execute_pending_statement(auth_cursor, statement)
                                execute_main_query()
                        else:
                            for statement in pending_auth:
                                _execute_pending_statement(auth_cursor, statement)
                            execute_main_query()
                    except (InternalError, UndefinedFunction, InvalidParameterValue) as ex:
                        translated = self._translate_session_auth_error(ex)
                        if translated is not None:
                            raise translated
                        if isinstance(ex, InternalError):
                            traceback.print_exc()
                        raise ex
                    finally:
                        try:
                            auth_cursor.close()
                        except Exception:
                            pass
                else:
                    execute_main_query()

                if cursor.description is None:
                    return [], [], []
                else:
                    if capture_provenance is not None:
                        capture_provenance.clear()
                        pgresult = cursor.pgresult
                        capture_provenance.extend(
                            (pgresult.ftype(idx), pgresult.ftable(idx), pgresult.ftablecol(idx))
                            for idx in range(pgresult.nfields))
                    return [desc[0] for desc in cursor.description], [desc.type_code for desc in cursor.description], cursor.fetchall()
        except Exception as ex:
            if isinstance(ex, OperationalError) and conn.closed:
                # The connection is gone and the transaction on it with it. The query is not retried here on
                # another connection: the caller holds this one and would go on to commit and return it, so
                # the request is re-run as a whole by the owner of its connection (InterpretJAAQL.transform,
                # ConnectionLostError). A database restart leaves every idle pooled connection dead, so have
                # the pool replace those before that re-run checks one out
                try:
                    DBPGInterface.HOST_POOLS[self.username][self.db_name].check()
                except Exception:
                    pass
            if self.output_query_exceptions:
                traceback.print_exc()
            raise ex

    def commit(self, conn):
        conn.commit()

    def rollback(self, conn):
        conn.rollback()

    def is_connection_closed(self, conn) -> bool:
        # True once psycopg has seen the connection fail (backend terminated by \wipe dbms or a restart, network
        # loss) or it was closed. Whatever transaction was open on it can no longer commit
        return conn.closed

    def statement_may_end_transaction(self, query: str) -> bool:
        return _statement_may_end_transaction(query)

    def has_ended_transaction(self, conn) -> bool:
        return not conn.autocommit and conn.info.transaction_status == TransactionStatus.IDLE

    def translate_commit_error(self, conn, commit_err, error_set: str = None):
        if not isinstance(commit_err, psycopg.Error):
            return None
        if conn.closed:
            # Lost while the COMMIT was in flight: the server may have committed before the connection went (a crash
            # after the commit record was flushed, a network loss before the reply). The outcome is unknown, so this
            # is reported as it stands and never re-run, which could apply the request twice
            return DatabaseOperationalError(message=ERR__commit_outcome_unknown + str(commit_err), descriptor=database_error_descriptor(commit_err))
        # The server refused the COMMIT (a deferred constraint, a serialization failure, ...), so the transaction
        # was rolled back: the error maps exactly as it does when a statement raises it
        return handled_error_from_database_error(commit_err, error_set)

    def handle_db_error(self, err, echo):
        if isinstance(err, ProgrammingError) and hasattr(err, 'pgresult'):
            err = err.pgresult.error_message.decode("UTF-8")

        err = str(err)
        if echo != ECHO__none:
            err += CHAR__newline + echo
        raise HttpStatusException(err, HTTPStatus.UNPROCESSABLE_ENTITY)
