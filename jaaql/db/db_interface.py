from abc import ABC, abstractmethod
from datetime import datetime
import logging
from jaaql.exceptions.http_status_exception import *
from jaaql import db
from typing import Optional

ERR__unknown_echo = "Unknown echo type '%s'. Please use either %s"
ERR__unsupported_interface = "Unsupported interface '%s'. We only support %s"

KEY_CONFIG__db = "DATABASE"
KEY_CONFIG__system = "SYSTEM"
KEY_CONFIG__logging = "logging"
KEY_CONFIG__interface = "interface"

RET__echo = "echo"
RET__columns = "columns"
RET__rows = "rows"

DIVIDER__protocol = "://"
DIVIDER__db = "/"
DIVIDER__port = ":"
DIVIDER__password = ":"
DIVIDER__address = "@"

ECHO__none = False
ECHO__debug = "debug"
ECHO__execute = True
ECHO__allowed = [ECHO__none, ECHO__debug, ECHO__execute]

CHAR__newline = "\r\n"

INTERFACE__postgres_key = "postgres"
INTERFACE__postgres_class = "DBPGInterface"

FILE__read = "r"
FILE__query_separator = ";"


class DBInterface(ABC):

    @abstractmethod
    def __init__(self, config, address: str, username: str, dev_mode: bool = False):
        self.config = config
        self.logging = config.get(KEY_CONFIG__system, {KEY_CONFIG__logging: True}).get(KEY_CONFIG__logging, True)
        self.dev_mode = dev_mode
        self.username = username
        self.address = address

    @staticmethod
    def fracture_uri(uri: str) -> (str, int, str, str, str):
        if DIVIDER__protocol in uri:
            uri = uri.split(DIVIDER__protocol)[1]

        address, db_name = uri.split(DIVIDER__address)[-1].split(DIVIDER__db)
        username, password = DIVIDER__address.join(uri.split(DIVIDER__address)[:-1]).split(DIVIDER__password)
        address, port = address.split(DIVIDER__port)

        return address, port, db_name, username, password

    @staticmethod
    def create_interface(config, address: str, port: int, database: str, username: str, password: str,
                         is_jaaql_user: bool = False, dev_mode: bool = False) -> 'DBInterface':
        interface = config[KEY_CONFIG__db][KEY_CONFIG__interface]
        supported = {
            INTERFACE__postgres_key: INTERFACE__postgres_class
        }

        if interface not in supported.keys():
            raise Exception(ERR__unsupported_interface % (interface, ", ".join(supported.keys())))

        interface_class = getattr(db, supported[interface])
        instance: DBInterface = interface_class(config, address, port, database, username, password, is_jaaql_user,
                                                dev_mode)

        return instance

    @abstractmethod
    def get_conn(self):
        pass

    def log_warning(self, exc):
        if self.logging:
            logging.warning(exc, exc_info=False)

    def log_critical(self, exc):
        if self.logging:
            logging.warning(exc, exc_info=False)

    def __attempt_commit_rollback(self, conn, err):
        try:
            if err is None:
                self.commit(conn)
            else:
                self.rollback(conn)
        except Exception as ex:
            if err is None:
                self.log_warning(ex)  # error committing. User stuffed up the SQL
            else:
                self.log_critical(ex)  # error rolling back. It is serious

    def __err_to_exception(self, err, echo):
        if err is not None:
            if isinstance(err, HttpStatusException):
                self.log_warning(err)
                raise err
            else:
                ex = self.handle_db_error(err, echo)
                if ex.response_code in [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND, HTTPStatus.UNAUTHORIZED]:
                    self.log_warning(ex)  # Minor error. User made a bad request (bad query, unauthorised etc.)
                else:
                    self.log_warning(ex)  # Serious error, connection failure to db or similar
                raise ex

    def handle_error(self, conn, err, echo=ECHO__none):
        self.__attempt_commit_rollback(conn, err)
        self.__err_to_exception(err, echo)

    def put_conn_handle_error(self, conn, err, echo=ECHO__none):
        self.__attempt_commit_rollback(conn, err)

        try:
            self.put_conn(conn)
        except Exception as ex:
            self.log_warning(ex)

        self.__err_to_exception(err, echo)

    @abstractmethod
    def put_conn(self, conn):
        pass

    @abstractmethod
    def rollback(self, conn):
        pass

    def execute_query_fetching_results(self, conn, query, parameters=None, echo=ECHO__none, as_objects=False):
        if echo not in ECHO__allowed:
            allowed_echoes = ", ".join([str(allowed_echo) for allowed_echo in ECHO__allowed])
            raise HttpStatusException(ERR__unknown_echo % (str(echo), allowed_echoes), HTTPStatus.BAD_REQUEST)

        if parameters is None:
            parameters = {}

        if echo == ECHO__debug:
            ret = {}
        else:
            new_parameters = {}
            for key, value in parameters.items():
                if value is not None:
                    if isinstance(value, datetime):
                        new_parameters[key] = str(value)
                    else:
                        new_parameters[key] = value
            columns, rows = self.execute_query(conn, query, new_parameters)

            ret = {
                RET__columns: columns,
                RET__rows: rows
            }

        if echo != ECHO__none:
            ret[RET__echo] = query

        if as_objects:
            return self.objectify(ret)
        else:
            return ret

    def objectify(self, data):
        return [dict(zip(data['columns'], row)) for row in data['rows']]

    def execute_script_file(self, conn, file_loc, as_individual=False, commit=True):
        ret = None
        err = None

        if as_individual:
            ret = []

        try:
            with open(file_loc, FILE__read) as file:
                queries = file.read()

                if as_individual:
                    queries = queries.split(FILE__query_separator)
                else:
                    queries = [queries]

                for query in queries:
                    if len(query.strip()) != 0:
                        query = query.strip()
                        resp = self.execute_query_fetching_results(conn, query, {}, ECHO__execute)

                        if as_individual:
                            ret.append(resp)
                        else:
                            ret = resp

        except Exception as ex:
            err = ex

        if commit:
            self.handle_error(conn, err)
            return ret
        else:
            return ret, err

    @abstractmethod
    def execute_query(self, conn, query, parameters: Optional[dict] = None):
        pass

    @abstractmethod
    def commit(self, conn):
        pass

    @abstractmethod
    def handle_db_error(self, err, echo) -> HttpStatusException:
        pass

    @abstractmethod
    def close(self):
        pass
