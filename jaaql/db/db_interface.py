import traceback
from abc import ABC, abstractmethod
from datetime import datetime
import logging
from jaaql.exceptions.http_status_exception import *
from typing import Optional
from jaaql.utilities.utils_no_project_imports import objectify
import queue

ERR__unknown_echo = "Unknown echo type '%s'. Please use either %s"

KEY_CONFIG__system = "SYSTEM"
KEY_CONFIG__logging = "logging"


RET__echo = "echo"
RET__columns = "columns"
RET__type_codes = "type_codes"
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

FILE__read = "r"
FILE__query_separator = ";"

ERR__missing_database = "The database name was missing from the connection"


class DBInterface(ABC):

    @abstractmethod
    def __init__(self, config, address: str, username: str):
        self.config = config
        self.output_exceptions = self.config["DEBUG"]["output_query_exceptions"].lower() == "true"
        self.logging = config.get(KEY_CONFIG__system, {KEY_CONFIG__logging: True}).get(KEY_CONFIG__logging, True)
        self.username = username
        self.address = address

    @staticmethod
    def fracture_uri(uri: str, allow_missing_database: bool = False) -> (str, int, str, str, str):
        if DIVIDER__protocol in uri:
            uri = uri.split(DIVIDER__protocol)[1]

        db_split = uri.split(DIVIDER__address)[-1].split(DIVIDER__db)
        address = db_split[0]
        db_name = db_split[1] if len(db_split) > 1 else None

        if not allow_missing_database and db_name is None:
            raise HttpStatusException(ERR__missing_database)

        username, password = DIVIDER__address.join(uri.split(DIVIDER__address)[:-1]).split(DIVIDER__password)
        address, port = address.split(DIVIDER__port)

        return address, port, db_name, username, password

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
            if isinstance(err, HttpStatusException) or isinstance(err, JaaqlInterpretableHandledError):
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

    def put_conn_handle_error(self, conn, err, echo=ECHO__none, skip_rollback_commit: bool = False):
        if not skip_rollback_commit:
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

    def execute_query_fetching_results(self, conn, query, parameters=None, echo=ECHO__none, as_objects=False, wait_hook: queue.Queue = None,
                                       requires_dba_check: bool = False):
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

            if requires_dba_check:
                self.check_dba(conn, wait_hook=wait_hook)
                if wait_hook:
                    wait_hook = None

            columns, type_codes, rows = self.execute_query(conn, query, new_parameters, wait_hook)

            ret = {
                RET__columns: columns,
                RET__rows: rows,
                RET__type_codes: type_codes
            }

        if echo != ECHO__none:
            ret[RET__echo] = query

        if as_objects:
            return objectify(ret)
        else:
            return ret

    def read_utf8(self, filename):
        with open(filename, 'rb') as file:
            # Read the first few bytes to check for BOM
            first_bytes = file.read(3)

            # Check for UTF-8-SIG (BOM)
            if first_bytes.startswith(b'\xef\xbb\xbf'):
                # Reopen with 'utf-8-sig' to properly handle BOM
                file = open(filename, FILE__read, encoding='utf-8-sig')
            else:
                # Reopen with 'utf-8' assuming no BOM
                file = open(filename, FILE__read, encoding='utf-8')

            return file

    def execute_script_file(self, conn, file_loc: str = None, as_content: str = None, as_individual=False, commit=True):
        ret = None
        err = None

        if as_individual:
            ret = []

        try:
            if as_content:
                queries = as_content
            else:
                with self.read_utf8(file_loc) as file:
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
            if self.output_exceptions:
                traceback.print_exc()
            err = ex

        if commit:
            self.handle_error(conn, err)
            return ret
        else:
            return ret, err

    @abstractmethod
    def check_dba(self, conn, wait_hook: queue.Queue = None):
        pass

    @abstractmethod
    def execute_query(self, conn, query, parameters: Optional[dict] = None, wait_hook: queue.Queue = None):
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
