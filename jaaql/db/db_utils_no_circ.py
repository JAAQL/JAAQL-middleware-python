import re
from datetime import date
from http import HTTPStatus
from jaaql.mvc.exception_queries import QUERY__fetch_application_schemas, KG__application_schema__application, KG__application__is_live, \
    KG__application_schema__name, KEY__is_default
from queue import Queue
from jaaql.db.db_utils import execute_supplied_statement, create_interface_for_db, ERR__schema_invalid, CONN_LOST__max_attempts, \
    requested_database
from jaaql.exceptions.http_status_exception import HttpStatusException, ConnectionLostError
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL, KEY_autocommit
from jaaql.constants import KEY__application, KEY__database, KEY__schema, KEY__role, DB__jaaql, \
    KEY__read_only, KEY__prevent_unused_parameters, KEY__timelines, GUC__timeline_prefix, TIMELINES__max_count, TIMELINE__max_moment_length, \
    REGEX__timeline_name, REGEX__timeline_moment, ERR__timelines_malformed, ERR__timelines_too_many, ERR__timeline_name_invalid, \
    ERR__timeline_name_repeated, ERR__timeline_moment_invalid, ERR__timelines_with_autocommit
from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils_no_project_imports import objectify
from jaaql.mvc.generated_queries import application__select

ERROR_VALUE__max_length = 80


def get_jaaql_connection_to_db(vault, config, database: str, jaaql_connection: DBInterface):
    return create_interface_for_db(vault, config, jaaql_connection.role, database)


def _describe_rejected_value(value) -> str:
    # Client input quoted in an error message, cut short so a huge value cannot flood the response
    described = repr(value)
    return described if len(described) <= ERROR_VALUE__max_length else described[:ERROR_VALUE__max_length - 3] + "..."


def _is_timeline_moment(moment) -> bool:
    if not isinstance(moment, str) or len(moment) > TIMELINE__max_moment_length or re.fullmatch(REGEX__timeline_moment, moment) is None:
        return False
    try:
        # The pattern fixes the shape and every field's range; only the calendar can say whether the day exists (30 February).
        # Deliberately not datetime.fromisoformat on the whole value: what it accepts differs per Python version (24:00, Z)
        date.fromisoformat(moment[:10])
    except ValueError:
        return False
    return True


def pop_timeline_settings(inputs: dict):
    """
    Pops the optional 'timelines' key, {"<timeline>": "<ISO-8601 date or date-time>" | null}, and returns the transaction-local
    settings it asks for as {"timeline.<timeline>": "<moment>"}, or None when there are none. A null moment means the default
    (current versions) and is dropped. The client names timelines, never settings: every name is built here from the prefix.
    Everything is checked before any database work, so a bad request is a 400 rather than an error from the settings statement
    that is batched with, and would be reported against, the request's first query
    """
    timelines = inputs.pop(KEY__timelines, None)
    if timelines is None:
        return None

    if not isinstance(timelines, dict):
        raise HttpStatusException(ERR__timelines_malformed, HTTPStatus.BAD_REQUEST)
    if len(timelines) > TIMELINES__max_count:
        raise HttpStatusException(ERR__timelines_too_many % (len(timelines), TIMELINES__max_count), HTTPStatus.BAD_REQUEST)

    settings = {}
    named = set()
    for timeline, moment in timelines.items():
        name = timeline.lower() if isinstance(timeline, str) and timeline.isascii() else None
        if name is None or re.fullmatch(REGEX__timeline_name, name) is None:
            raise HttpStatusException(ERR__timeline_name_invalid % _describe_rejected_value(timeline), HTTPStatus.BAD_REQUEST)
        if name in named:
            raise HttpStatusException(ERR__timeline_name_repeated % name, HTTPStatus.BAD_REQUEST)
        named.add(name)

        if moment is None:
            continue
        if not _is_timeline_moment(moment):
            raise HttpStatusException(ERR__timeline_moment_invalid % (_describe_rejected_value(moment), name, TIMELINE__max_moment_length),
                                      HTTPStatus.BAD_REQUEST)
        settings[GUC__timeline_prefix + name] = moment

    if len(settings) == 0:
        return None

    # Under autocommit a transaction-local setting ends with the statement that set it, before the query runs
    if inputs.get(KEY_autocommit):
        raise HttpStatusException(ERR__timelines_with_autocommit, HTTPStatus.BAD_REQUEST)

    return settings


def get_required_db(vault, config, jaaql_connection: DBInterface, inputs: dict, account_id: str, conn=None, interface: DBInterface = None, db_cache=None):
    if not isinstance(inputs, dict):
        raise HttpStatusException("Expected object or string input")

    if conn is None:
        # Validated first, so a bad request does no database work at all (not even the application lookup)
        session_settings = pop_timeline_settings(inputs)

        if KEY__application in inputs:
            schemas = db_cache
            if schemas is None:
                schemas = execute_supplied_statement(jaaql_connection, QUERY__fetch_application_schemas, {
                    KG__application_schema__application: inputs[KEY__application]
                }, as_objects=True)
                if len(schemas) == 0:
                    application__select(jaaql_connection, inputs[KEY__application],
                                        singleton_message=f"Application '{inputs[KEY__application]}' does not exist. Are you sure you have installed it?")
                    raise HttpStatusException("Application has no schemas!")
                if not schemas[0][KG__application__is_live]:
                    raise HttpStatusException("Application is currently being deployed. Please wait a few minutes until deployment is complete")
                schemas = {itm[KG__application_schema__name]: itm for itm in schemas}

            found_db = None
            if KEY__schema in inputs and inputs[KEY__schema] is not None:
                found_db = schemas[inputs[KEY__schema]][KEY__database]
                inputs.pop(KEY__schema)
            else:
                if len(schemas) == 1:
                    found_db = schemas[list(schemas.keys())[0]][KEY__database]
                else:
                    found_dbs = [val[KEY__database] for _, val in schemas.items() if val[KEY__is_default]]
                    if len(found_dbs) == 1:
                        found_db = found_dbs[0]

            if not found_db:
                raise HttpStatusException(ERR__schema_invalid)

            inputs[KEY__database] = found_db
        elif KEY__database in inputs:
            requested_database(inputs[KEY__database])

        if KEY__database not in inputs:
            inputs[KEY__database] = DB__jaaql

        sub_role = inputs.pop(KEY__role) if KEY__role in inputs else None

        required_db = create_interface_for_db(vault, config, account_id, inputs[KEY__database], sub_role, session_settings=session_settings)
    else:
        if interface is None:
            raise Exception("Must supply interface is connection is supplied!")

        required_db = interface

    return required_db


def submit(vault, config, db_crypt_key, jaaql_connection: DBInterface, inputs: dict, account_id: str, verification_hook: Queue = None,
           cached_canned_query_service=None, as_objects: bool = False, singleton: bool = False, keep_alive_conn: bool = False,
           conn=None, interface: DBInterface = None, db_cache=None, prepare_statements: bool = False):
    if not isinstance(inputs, dict):
        raise HttpStatusException("Expected object or string input")

    required_db = get_required_db(vault, config, jaaql_connection, inputs, account_id, conn, interface, db_cache=db_cache)

    prevent_unused = inputs.pop(KEY__prevent_unused_parameters) if KEY__prevent_unused_parameters in inputs else True

    # A lost connection committed nothing, so re-running on a fresh connection is safe. \wipe dbms kills
    # pooled connections, so a request landing on one dies at commit ("the connection is lost") - retry
    # it. Only when transform owns the connection (conn is None); otherwise the caller manages the
    # transaction and must handle the loss itself.
    attempts = 0
    while True:
        attempts += 1
        try:
            ret = InterpretJAAQL(required_db, jaaql_connection
                                 ).transform(inputs, skip_commit=inputs.get(KEY__read_only), wait_hook=verification_hook,
                                             encryption_key=db_crypt_key, conn=conn,
                                             canned_query_service=cached_canned_query_service, prevent_unused_parameters=prevent_unused,
                                             and_return_connection_mid_transaction=keep_alive_conn, prepare_statements=prepare_statements)
            break
        except ConnectionLostError:
            if conn is not None or attempts >= CONN_LOST__max_attempts:
                raise

    if as_objects:
        ret = objectify(ret, singleton=singleton)

    return ret
