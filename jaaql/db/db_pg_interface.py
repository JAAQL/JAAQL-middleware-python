from psycopg import OperationalError
from psycopg_pool import ConnectionPool, NullConnectionPool

import logging
import traceback

from jaaql.db.db_interface import DBInterface, ECHO__none, CHAR__newline
from jaaql.exceptions.http_status_exception import *
from jaaql.exceptions.custom_http_status import CustomHTTPStatus

ERR__connect_db = "Could not create connection to database!"

PGCONN__min_conns = 5
PGCONN__max_conns = 1
PGCONN__max_conns_jaaql_user = 40


class DBPGInterface(DBInterface):

    def __init__(self, config, host: str, port: int, db_name: str, username: str, password: str, is_jaaql_user: bool,
                 dev_mode: bool):
        super().__init__(config, host, username, dev_mode)

        # Created connection pool, allowing for 1 connection for this specific user
        # Allows for the lookup of multiple users at the same time when providing jaaql user
        try:
            conn_str = "user=" + username + " password=" + password + " dbname=" + db_name

            # Important we don't list the host as this will force a unix socket
            if host not in ['localhost', '127.0.0.1']:
                conn_str += " host=" + host
            if str(port) != "5432":
                conn_str += " port=" + str(port)

            if is_jaaql_user:
                self.pg_pool = ConnectionPool(conn_str, min_size=PGCONN__min_conns, max_size=PGCONN__max_conns_jaaql_user, max_lifetime=60 * 30)
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

            if conn is None:
                raise Exception
        except Exception as ex:
            traceback.print_exc()
            logging.critical(ex, exc_info=True)
            raise HttpStatusException(ERR__connect_db, HTTPStatus.INTERNAL_SERVER_ERROR)

        return conn

    def put_conn(self, conn):
        return self.pg_pool.putconn(conn)

    def close(self):
        self.pg_pool.close()

    def execute_query(self, conn, query, parameters=None):
        while True:
            try:
                with conn.cursor() as cursor:
                    if parameters is None or len(parameters.keys()) == 0:
                        cursor.execute(query)
                    else:
                        cursor.execute(query, parameters)
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
