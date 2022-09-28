from psycopg import OperationalError
from psycopg_pool import ConnectionPool
import queue
from psycopg.errors import ProgrammingError, InvalidParameterValue
import threading
import traceback
from jaaql.constants import ERR__invalid_token

from jaaql.db.db_interface import DBInterface, ECHO__none, CHAR__newline
from jaaql.exceptions.http_status_exception import *
from jaaql.exceptions.custom_http_status import CustomHTTPStatus

ERR__connect_db = "Could not create connection to database!"

PGCONN__min_conns = 5
PGCONN__max_conns = 10

ALLOWABLE_COMMANDS = ["SELECT ", "INSERT ", "UPDATE ", "DELETE "]

ERR__command_not_allowed = "Command not allowed. Please use one of " + str(ALLOWABLE_COMMANDS)
ERR__invalid_role = "Role not allowed, invalid format!"


class DBPGInterface(DBInterface):

    HOST_POOLS = {}
    HOST_POOLS_QUEUES = {}

    @staticmethod
    def put_conn_threaded(username: str, db_name: str, the_queue: queue.Queue):
        while True:
            try:
                conn, do_reset = the_queue.get()
                if do_reset:
                    with conn.cursor() as cursor:
                        cursor.execute("RESET ROLE; RESET SESSION AUTHORIZATION;")
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
                    user_pool[self.db_name] = ConnectionPool(conn_str, min_size=PGCONN__min_conns, max_size=PGCONN__max_conns, max_lifetime=60 * 30)
                    the_queue = queue.Queue()
                    DBPGInterface.HOST_POOLS_QUEUES[self.username][self.db_name] = the_queue
                    threading.Thread(target=DBPGInterface.put_conn_threaded, args=[self.username, self.db_name, the_queue], daemon=True).start()
            except OperationalError as ex:
                if "does not exist" in str(ex).split("\"")[-1]:
                    raise HttpStatusException(str(ex), CustomHTTPStatus.DATABASE_NO_EXIST)
                else:
                    raise HttpStatusException(str(ex))

        self.pg_pool = user_pool[self.db_name]

    def _get_conn(self, allow_operational: bool = True):
        conn = self.pg_pool.getconn()
        if self.role is not None or self.sub_role is not None:
            try:
                with conn.cursor() as cursor:
                    if self.role is not None:
                        cursor.execute("SET SESSION AUTHORIZATION \"" + self.role + "\";")
                    if self.sub_role is not None:
                        cursor.execute("SET ROLE \"" + self.sub_role + "\"")
            except InvalidParameterValue:
                raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
            except OperationalError as ex:
                if allow_operational:
                    self.pg_pool.close()
                    DBPGInterface.HOST_POOLS[self.username][self.db_name] = ConnectionPool(self.conn_str, min_size=PGCONN__min_conns,
                                                                                           max_size=PGCONN__max_conns, max_lifetime=60 * 30)
                    self.pg_pool = DBPGInterface.HOST_POOLS[self.username][self.db_name]
                    conn = self._get_conn(False)
                else:
                    raise ex

        return conn

    def get_conn(self):
        try:
            conn = self._get_conn()
        except HttpStatusException as ex:
            raise ex
        except Exception:
            traceback.print_exc()
            raise HttpStatusException(ERR__connect_db, HTTPStatus.INTERNAL_SERVER_ERROR)

        return conn

    def put_conn(self, conn):
        DBPGInterface.HOST_POOLS_QUEUES[self.username][self.db_name].put((conn, self.role is not None))

    def close(self):
        DBPGInterface.HOST_POOLS[self.username].pop(self.db_name)
        DBPGInterface.HOST_POOLS_QUEUES[self.username].pop(self.db_name)
        self.pg_pool.close()

    def execute_query(self, conn, query, parameters=None, wait_hook: queue.Queue = None):
        x = 0
        err = None
        while x < 5:
            x += 1
            try:
                with conn.cursor() as cursor:
                    do_prepare = False

                    # if self.role is not None:
                    #     do_prepare = True
                    #     if not any([query.upper().startswith(ok_command) for ok_command in ALLOWABLE_COMMANDS]):
                    #         raise HttpStatusException(ERR__command_not_allowed)

                    if wait_hook:
                        res, err, code = wait_hook.get()
                        if not res:
                            if code == 500:
                                raise Exception(err)
                            raise HttpStatusException(err, code)

                    if parameters is None or len(parameters.keys()) == 0:
                        cursor.execute(query, prepare=do_prepare)
                    else:
                        cursor.execute(query, parameters, prepare=do_prepare)
                    if cursor.description is None:
                        return [], []
                    else:
                        return [desc[0] for desc in cursor.description], cursor.fetchall()
            except OperationalError as ex:
                if ex.sqlstate is not None and ex.sqlstate.startswith("08"):
                    self.pg_pool.putconn(conn)
                    self.pg_pool.check()
                    conn = self.get_conn()
                    err = ex
                else:
                    if self.output_query_exceptions:
                        traceback.print_exc()
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
            err = err.pgresult.error_message.decode("ASCII")

        err = str(err)
        if echo != ECHO__none:
            err += CHAR__newline + echo
        raise HttpStatusException(err, HTTPStatus.UNPROCESSABLE_ENTITY)
