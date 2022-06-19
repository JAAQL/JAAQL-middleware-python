from psycopg import OperationalError
from psycopg_pool import ConnectionPool

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


class DBPGInterface(DBInterface):

    HOST_POOL = None
    HOST_USER = None

    def __init__(self, config, host: str, port: int, db_name: str, username: str, password: str, is_jaaql_user: bool,
                 dev_mode: bool):
        super().__init__(config, host, username, dev_mode)

        self.output_query_exceptions = config["DEBUG"]["output_query_exceptions"].lower() == "true"

        # Created connection pool, allowing for 1 connection for this specific user
        # Allows for the lookup of multiple users at the same time when providing jaaql user
        try:
            conn_str = "user=" + username + " password=" + password + " dbname=" + db_name
            self.is_host_pool = False
            # Important we don't list the host as this will force a unix socket
            if host not in ['localhost', '127.0.0.1']:
                conn_str += " host=" + host
            else:
                self.is_host_pool = True
            if str(port) != "5432":
                conn_str += " port=" + str(port)

            self.username = username

            if self.is_host_pool:
                if DBPGInterface.HOST_POOL is None:
                    DBPGInterface.HOST_POOL = ConnectionPool(conn_str, min_size=PGCONN__min_conns, max_size=PGCONN__max_conns_jaaql_user,
                                                             max_lifetime=60 * 30)
                    DBPGInterface.HOST_USER = self.username
                self.pg_pool = DBPGInterface.HOST_POOL
            else:
                self.pg_pool = ConnectionPool(conn_str, min_size=1, max_size=5)
        except OperationalError as ex:
            if "does not exist" in str(ex).split("\"")[-1]:
                raise HttpStatusException(str(ex), CustomHTTPStatus.DATABASE_NO_EXIST)
            else:
                raise HttpStatusException(str(ex))

    def get_conn(self):
        try:
            conn = self.pg_pool.getconn()
            if DBPGInterface.HOST_USER != self.username and self.is_host_pool:
                with conn.cursor() as cursor:
                    cursor.execute("SET SESSION AUTHORIZATION '" + self.username + "';")
                    self.commit(conn)
            if conn is None:
                raise Exception
        except Exception as ex:
            traceback.print_exc()
            raise HttpStatusException(ERR__connect_db, HTTPStatus.INTERNAL_SERVER_ERROR)

        return conn

    def put_conn(self, conn):
        if self.is_host_pool and DBPGInterface.HOST_USER != self.username:
            with conn.cursor() as cursor:
                cursor.execute("RESET SESSION AUTHORIZATION;")
                self.commit(conn)
        return self.pg_pool.putconn(conn)

    def close(self, force: bool = False):
        if not self.is_host_pool or force:
            self.pg_pool.close()
            print("Closing host pool")

            if self.is_host_pool:
                DBPGInterface.HOST_POOL = None
                DBPGInterface.HOST_USER = None
                print("Wiping host pool")

    def execute_query(self, conn, query, parameters=None):
        while True:
            try:
                with conn.cursor() as cursor:
                    do_prepare = False
                    if DBPGInterface.HOST_USER != self.username and self.username != USERNAME__jaaql:
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
