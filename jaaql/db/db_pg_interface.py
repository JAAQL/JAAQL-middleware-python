from psycopg import OperationalError
from psycopg_pool import ConnectionPool, NullConnectionPool

import traceback

from jaaql.db.db_interface import DBInterface, ECHO__none, CHAR__newline
from jaaql.exceptions.http_status_exception import *
from jaaql.exceptions.custom_http_status import CustomHTTPStatus
from jaaql.constants import USERNAME__jaaql

ERR__connect_db = "Could not create connection to database!"

PGCONN__min_conns = 5
PGCONN__max_conns = 1
PGCONN__max_conns_jaaql_user = 10

ALLOWABLE_COMMANDS = ["SELECT ", "INSERT ", "UPDATE ", "DELETE "]

ERR__command_not_allowed = "Command not allowed. Please use one of " + str(ALLOWABLE_COMMANDS)

HOST__localhost = "localhost"
HOST__127 = "127.0.0.1"


class DBPGInterface(DBInterface):

    SUPER_POOLS = {}
    SUPER_USERS = {}

    def __init__(self, config, host: str, port: int, db_name: str, username: str, password: str, dev_mode: bool, pooled: bool = True):
        super().__init__(config, host, username, dev_mode)

        host = host.lower()
        self.output_query_exceptions = config["DEBUG"]["output_query_exceptions"].lower() == "true"

        # Created connection pool, allowing for 1 connection for this specific user
        # Allows for the lookup of multiple users at the same time when providing jaaql user
        try:
            conn_str = "user=" + username + " password=" + password + " dbname=" + db_name

            # Important we don't list the host as this will force a unix socket
            self.is_host_pool = True
            if host not in [HOST__localhost, HOST__127]:
                conn_str += " host=" + host
                self.is_host_pool = False

            self.host = host

            if host == HOST__localhost:
                host = HOST__127

            if str(port) != "5432":
                conn_str += " port=" + str(port)

            self.username = username

            self.lookup = host + "/" + db_name
            self.pooled = pooled
            if pooled:
                if host not in DBPGInterface.SUPER_USERS:
                    DBPGInterface.SUPER_POOLS[self.lookup] = ConnectionPool(conn_str, min_size=PGCONN__min_conns,
                                                                            max_size=PGCONN__max_conns_jaaql_user, max_lifetime=60 * 30)
                    DBPGInterface.SUPER_USERS[self.lookup] = self.username
                self.pg_pool = DBPGInterface.SUPER_POOLS[self.lookup]
            else:
                self.pg_pool = NullConnectionPool(conn_str)

        except OperationalError as ex:
            if "does not exist" in str(ex).split("\"")[-1]:
                raise HttpStatusException(str(ex), CustomHTTPStatus.DATABASE_NO_EXIST)
            else:
                raise HttpStatusException(str(ex))

    def get_conn(self):
        try:
            conn = self.pg_pool.getconn()
            if DBPGInterface.SUPER_USERS[self.lookup] != self.username:
                with conn.cursor() as cursor:
                    cursor.execute("SET ROLE '" + self.username + "';")
                    self.commit(conn)
            if conn is None:
                raise Exception
        except Exception as ex:
            traceback.print_exc()
            raise HttpStatusException(ERR__connect_db, HTTPStatus.INTERNAL_SERVER_ERROR)

        return conn

    def put_conn(self, conn):
        if DBPGInterface.SUPER_USERS[self.lookup] != self.username:
            with conn.cursor() as cursor:
                cursor.execute("RESET SESSION AUTHORIZATION;")
                self.commit(conn)
        return self.pg_pool.putconn(conn)

    @staticmethod
    def close_all():
        for _, pool in DBPGInterface.SUPER_POOLS.items():
            pool.pg_pool.close()

        DBPGInterface.SUPER_USERS = {}
        DBPGInterface.SUPER_POOLS = {}

    def close(self):
        self.pg_pool.close()
        if self.pooled:
            DBPGInterface.SUPER_USERS.pop(self.lookup)
            DBPGInterface.SUPER_POOLS.pop(self.lookup)

    def execute_query(self, conn, query, parameters=None):
        while True:
            try:
                with conn.cursor() as cursor:
                    do_prepare = False
                    if DBPGInterface.SUPER_USERS[self.lookup] != self.username and (self.username != USERNAME__jaaql or not self.is_host_pool):
                        do_prepare = True
                        if not any([query.upper().startswith(ok_command) for ok_command in ALLOWABLE_COMMANDS]):
                            raise HttpStatusException(ERR__command_not_allowed)

                    if parameters is None or len(parameters.keys()) == 0:
                        cursor.execute(query, prepare=do_prepare)
                    else:
                        cursor.execute(query, parameters, prepare=do_prepare)
                    if cursor.description is None:
                        return [], []
                    else:
                        return [desc[0] for desc in cursor.description], cursor.fetchall()
            except OperationalError as ex:
                if ex.sqlstate.startswith("08"):
                    traceback.print_exc()
                    self.pg_pool.putconn(conn)
                    self.pg_pool.check()
                    conn = self.get_conn()
                else:
                    if self.output_query_exceptions:
                        traceback.print_exc()
                    raise ex
            except Exception as ex:
                if self.output_query_exceptions:
                    traceback.print_exc()
                raise ex

    def commit(self, conn):
        conn.commit()

    def rollback(self, conn):
        conn.rollback()

    def handle_db_error(self, err, echo):
        err = str(err)
        if echo != ECHO__none:
            err += CHAR__newline + echo
        raise HttpStatusException(str(err), HTTPStatus.BAD_REQUEST)
