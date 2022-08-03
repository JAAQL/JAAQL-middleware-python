from psycopg import OperationalError
from psycopg_pool import ConnectionPool

import traceback

from jaaql.db.db_interface import DBInterface, ECHO__none, CHAR__newline
from jaaql.exceptions.http_status_exception import *
from jaaql.constants import USERNAME__jaaql

ERR__connect_db = "Could not create connection to database!"

PGCONN__min_conns = 5
PGCONN__max_conns = 1
PGCONN__max_conns_jaaql_user = 10

ALLOWABLE_COMMANDS = ["SELECT ", "INSERT ", "UPDATE ", "DELETE "]

ERR__command_not_allowed = "Command not allowed. Please use one of " + str(ALLOWABLE_COMMANDS)


class DBPGInterface(DBInterface):

    def __init__(self, config: dict, pool: ConnectionPool, super_username: str, username: str):
        super().__init__(config, pool, super_username, username)

    def get_conn(self):
        try:
            conn = self.pool.getconn()
            if self.super_username != self.username:
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
        if self.super_username != self.username:
            with conn.cursor() as cursor:
                cursor.execute("RESET SESSION AUTHORIZATION;")
                self.commit(conn)
        return self.pool.putconn(conn)

    def close(self):
        print("Closing host pool")
        self.pool.close()

    def execute_query(self, conn, query, parameters=None):
        while True:
            try:
                with conn.cursor() as cursor:
                    do_prepare = False
                    if self.username != self.super_username:
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
                    self.pool.putconn(conn)
                    self.pool.check()
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
