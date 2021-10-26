import psycopg2
from psycopg2 import pool, OperationalError

from jaaql.db.db_interface import *
from jaaql.exceptions.http_status_exception import *

ERR__connect_db = "Could not create connection to database!"

PGCONN__min_conns = 1
PGCONN__max_conns = 1
PGCONN__max_conns_jaaql_user = 20


class DBPGInterface(DBInterface):

    def __init__(self, config, host: str, port: int, db_name: str, username: str, password: str, is_jaaql_user: bool,
                 dev_mode: bool):
        super().__init__(config, host, username, dev_mode)

        # Created connection pool, allowing for 1 connection for this specific user
        # Allows for the lookup of multiple users at the same time when providing jaaql user
        try:
            self.pg_pool = psycopg2.pool.ThreadedConnectionPool(
                PGCONN__min_conns,
                PGCONN__max_conns_jaaql_user if is_jaaql_user else PGCONN__max_conns,
                user=username,
                password=password,
                host=host,
                port=port,
                database=db_name
            )
        except OperationalError as ex:
            raise HttpStatusException(str(ex), HTTPStatus.UNAUTHORIZED)

    def get_conn(self):
        try:
            conn = self.pg_pool.getconn()
            if conn is None:
                raise Exception
        except Exception as ex:
            logging.critical(ex, exc_info=True)
            raise HttpStatusException(ERR__connect_db, HTTPStatus.INTERNAL_SERVER_ERROR)

        return conn

    def put_conn(self, conn):
        return self.pg_pool.putconn(conn)

    def close(self):
        self.pg_pool.closeall()

    def execute_query(self, conn, query, parameters):
        cursor = conn.cursor()
        if parameters is None or len(parameters.keys()) == 0:
            cursor.execute(query)
        else:
            cursor.execute(query, parameters)
        if cursor.description is None:
            return [], []
        else:
            return [desc[0] for desc in cursor.description], cursor.fetchall()

    def commit(self, conn):
        conn.commit()

    def rollback(self, conn):
        conn.rollback()

    def handle_db_error(self, err, echo):
        err = str(err)
        if echo != ECHO__none:
            err += CHAR__newline + echo
        raise HttpStatusException(str(err), HTTPStatus.BAD_REQUEST)
