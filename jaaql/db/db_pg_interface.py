import uuid

import psycopg
from psycopg import OperationalError
from psycopg_pool import ConnectionPool, PoolClosed
import queue
from psycopg.errors import ProgrammingError, InvalidParameterValue, UndefinedFunction, InternalError
import threading
import traceback
from jaaql.constants import ERR__invalid_token

from jaaql.db.db_interface import DBInterface, ECHO__none, CHAR__newline
from jaaql.exceptions.http_status_exception import *
from jaaql.exceptions.custom_http_status import CustomHTTPStatus
from jaaql.exceptions.jaaql_interpretable_handled_errors import UserUnauthorized
from jaaql.constants import KEY__database

ERR__connect_db = "Could not create connection to database!"

PGCONN__min_conns = 5
PGCONN__max_conns = 10

TIMEOUT = 2.5

ERR__invalid_role = "Role not allowed, invalid format!"
ERR__must_use_canned_query = "Must use canned query as you are not an admin!"

QUERY__dba_query = "SELECT pg_has_role(datdba::regrole, 'MEMBER') FROM pg_database WHERE datname = %(database)s;"
QUERY__dba_query_external = "SELECT pg_has_role(datdba::regrole, 'MEMBER') FROM pg_database WHERE datname = current_database();"

try:
    # Pipeline mode needs libpq >= 14. create_app refuses to boot when this is False so a server
    # can never silently degrade; the sequential fallback in execute_query exists only for
    # non-server tooling that imports this module directly
    PIPELINE_SUPPORTED = psycopg.Pipeline.is_supported()
except Exception:
    PIPELINE_SUPPORTED = False


class JaaqlPGConnection(psycopg.Connection):
    """
    Connection whose per-checkout session-authorization statements (jaaql__set_session_authorization
    / SET ROLE) are deferred at checkout and sent pipelined with the first real query, saving a
    network round trip per checkout.

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
                        flush_cursor.execute(statement)
            finally:
                self._jaaql_flushing = False
        return super().cursor(*args, **kwargs)


def _statement_is_preparable(query: str) -> bool:
    # Server-side PREPARE accepts a single statement only. A ';' anywhere except trailing means the
    # text may hold multiple statements (a ';' inside a string literal merely skips the
    # optimisation, which is the safe direction)
    return ";" not in query.rstrip().rstrip(";")


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
    def _process_returned_conn(username: str, db_name: str, conn, do_reset: bool):
        if isinstance(conn, JaaqlPGConnection) and conn.jaaql_has_pending_auth():
            # The deferred authorization statements were never sent, so the session still runs as
            # the pool user and there is nothing to reset. Clearing them here also stops the
            # cursor() below from flushing them
            conn.jaaql_take_pending_auth()
            do_reset = False
        if do_reset:
            with conn.cursor() as cursor:
                cursor.execute("RESET ROLE;")
                did_close = False
                if hasattr(conn, "jaaql_reset_key"):
                    try:
                        cursor.execute("SELECT jaaql_extension.jaaql__reset_session_authorization('" + str(conn.jaaql_reset_key) + "');")
                    except:
                        did_close = True
                        conn.close()
                if not did_close:
                    cursor.execute("RESET ALL;")
                    conn.commit()
        DBPGInterface.HOST_POOLS[username][db_name].putconn(conn)

    @staticmethod
    def put_conn_threaded(username: str, db_name: str, the_queue: queue.Queue):
        while True:
            try:
                conn, do_reset = the_queue.get()
                DBPGInterface._process_returned_conn(username, db_name, conn, do_reset)
            except Exception:
                pass  # Ignore, pool has likely been wiped

    def __init__(self, config, host: str, port: int, db_name: str, username: str, role: str = None, password: str = None, sub_role: str = None):
        super().__init__(config, host, username)

        self.role = role
        self.sub_role = sub_role
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
                conn_str = "user=" + username + " password=" + password + " dbname=" + db_name
                # Important we don't list the host as this will force a unix socket
                if host is not None and host not in ['localhost', '127.0.0.1']:
                    conn_str += " host=" + host

                if str(port) != "5432":
                    conn_str += " port=" + str(port)

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
        if self.role is not None or self.sub_role is not None:
            # Deferred: sent pipelined with the first query by execute_query, or flushed eagerly by
            # JaaqlPGConnection.cursor() if the connection is used rawly. Errors these statements
            # raise are translated by _translate_session_auth_error at execution time; dead pool
            # connections, previously detected here, are recycled by execute_query's
            # OperationalError retry loop
            pending = []
            if self.role is not None:
                pending.append("SELECT jaaql_extension.jaaql__set_session_authorization('" + self.role + "', '" + conn.jaaql_reset_key + "');")
            if self.sub_role is not None:
                pending.append("SET ROLE \"" + self.sub_role + "\"")
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

    def execute_query(self, conn, query, parameters=None, wait_hook: queue.Queue = None, prepare: bool = False):
        x = 0
        err = None
        while x < PGCONN__max_conns:
            x += 1
            try:
                cursor_factory = conn.jaaql_raw_cursor if isinstance(conn, JaaqlPGConnection) else conn.cursor
                with cursor_factory() as cursor:
                    do_prepare = prepare and _statement_is_preparable(query)

                    if wait_hook:
                        res, err, code = wait_hook.get()
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
                            if PIPELINE_SUPPORTED:
                                with conn.pipeline():
                                    for statement in pending_auth:
                                        auth_cursor.execute(statement)
                                    execute_main_query()
                            else:
                                for statement in pending_auth:
                                    auth_cursor.execute(statement)
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
                        return [desc[0] for desc in cursor.description], [desc.type_code for desc in cursor.description], cursor.fetchall()
            except OperationalError as ex:
                if ex.sqlstate is None or ex.sqlstate.startswith("08") or ex.sqlstate.startswith("57"):
                    if isinstance(conn, JaaqlPGConnection):
                        # This putconn bypasses the reset queue, so make sure no unsent
                        # authorization statements ride back into the pool where check() or a
                        # later checkout could flush them as the wrong user
                        conn.jaaql_take_pending_auth()
                    DBPGInterface.HOST_POOLS[self.username][self.db_name].putconn(conn)
                    DBPGInterface.HOST_POOLS[self.username][self.db_name].check()
                    conn = self.get_conn()
                    err = ex
                else:
                    raise ex
            except Exception as ex:
                if self.output_query_exceptions:
                    traceback.print_exc()
                raise ex

        if err:
            raise err

    def commit(self, conn):
        conn.commit()

    def rollback(self, conn):
        conn.rollback()

    def handle_db_error(self, err, echo):
        if isinstance(err, ProgrammingError) and hasattr(err, 'pgresult'):
            err = err.pgresult.error_message.decode("UTF-8")

        err = str(err)
        if echo != ECHO__none:
            err += CHAR__newline + echo
        raise HttpStatusException(err, HTTPStatus.UNPROCESSABLE_ENTITY)
