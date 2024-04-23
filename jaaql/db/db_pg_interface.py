import uuid

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
    def put_conn_threaded(username: str, db_name: str, the_queue: queue.Queue):
        while True:
            try:
                conn, do_reset = the_queue.get()
                if do_reset:
                    with conn.cursor() as cursor:
                        cursor.execute("RESET ROLE;")
                        did_close = False
                        if hasattr(conn, "jaaql_reset_key"):
                            try:
                                cursor.execute("SELECT jaaql__reset_session_authorization('" + str(conn.jaaql_reset_key) + "');")
                            except:
                                did_close = True
                                conn.close()
                        if not did_close:
                            cursor.execute("RESET ALL;")
                            conn.commit()
                DBPGInterface.HOST_POOLS[username][db_name].putconn(conn)
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
                    the_pool = ConnectionPool(conn_str, min_size=PGCONN__min_conns, max_size=PGCONN__max_conns, max_lifetime=60 * 30)
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

    def _get_conn(self, allow_operational: bool = True):
        conn = DBPGInterface.HOST_POOLS[self.username][self.db_name].getconn(timeout=TIMEOUT)
        conn.jaaql_reset_key = str(uuid.uuid4())
        if self.role is not None or self.sub_role is not None:
            try:
                with conn.cursor() as cursor:
                    if self.role is not None:
                        try:
                            cursor.execute("SELECT jaaql__set_session_authorization('" + self.role + "', '" + conn.jaaql_reset_key + "');")
                        except InternalError as ex:
                            if str(ex).startswith("role \"") and str(ex).endswith("\" does not exist"):
                                raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
                            else:
                                traceback.print_exc()
                                raise ex
                        except UndefinedFunction:
                            raise HttpStatusException("Database '%s' has not been configured for usage with JAAQL. Please ask the dba to run 'configure_database_for_use_with_jaaql' from the jaaql database" % self.db_name)
                    if self.sub_role is not None:
                        cursor.execute("SET ROLE \"" + self.sub_role + "\"")
            except InvalidParameterValue:
                raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
            except OperationalError as ex:
                if allow_operational:
                    DBPGInterface.HOST_POOLS[self.username][self.db_name].close()
                    DBPGInterface.HOST_POOLS[self.username][self.db_name] = ConnectionPool(self.conn_str, min_size=PGCONN__min_conns,
                                                                                           max_size=PGCONN__max_conns, max_lifetime=60 * 30)
                    try:
                        DBPGInterface.HOST_POOLS[self.username][self.db_name].getconn(timeout=TIMEOUT)
                    except OperationalError:
                        self.close()
                        raise HttpStatusException("Database \"" + self.db_name + "\" does not exist",
                                                  CustomHTTPStatus.DATABASE_NO_EXIST)

                    conn = self._get_conn(False)
                else:
                    raise ex

        return conn

    def get_pool(self):
        if self.db_name not in DBPGInterface.HOST_POOLS[self.username]:
            DBPGInterface.HOST_POOLS[self.username][self.db_name] = ConnectionPool(self.conn_str, min_size=PGCONN__min_conns,
                                                                                   max_size=PGCONN__max_conns, max_lifetime=60 * 30)
        return DBPGInterface.HOST_POOLS[self.username][self.db_name]

    def get_conn(self, retry_closed_pool: bool = True):
        try:
            conn = self._get_conn()
        except PoolClosed as ex:
            # Jaaql has likely been reinstalled, this pool has been forcibly closed
            if retry_closed_pool:
                DBPGInterface.HOST_POOLS[self.username][self.db_name] = ConnectionPool(self.conn_str, min_size=PGCONN__min_conns,
                                                                                       max_size=PGCONN__max_conns, max_lifetime=60 * 30)
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
        columns, _, rows = self.execute_query(conn, QUERY__dba_query, parameters={KEY__database: self.db_name}, wait_hook=wait_hook)
        if not rows[0]:
            raise HttpStatusException(ERR__must_use_canned_query)

    def execute_query(self, conn, query, parameters=None, wait_hook: queue.Queue = None):
        x = 0
        err = None
        while x < PGCONN__max_conns:
            x += 1
            try:
                with conn.cursor() as cursor:
                    do_prepare = False

                    if wait_hook:
                        res, err, code = wait_hook.get()
                        if not res:
                            if code == 500:
                                raise Exception(err)
                            raise UserUnauthorized()

                    if parameters is None or len(parameters.keys()) == 0:
                        cursor.execute(query, prepare=do_prepare)
                    else:
                        cursor.execute(query, parameters, prepare=do_prepare)
                    if cursor.description is None:
                        return [], [], []
                    else:
                        return [desc[0] for desc in cursor.description], [desc.type_code for desc in cursor.description], cursor.fetchall()
            except OperationalError as ex:
                if ex.sqlstate is None or ex.sqlstate.startswith("08"):
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
