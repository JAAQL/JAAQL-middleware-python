from jaaql.mvc.exception_queries import QUERY__fetch_application_schemas, KG__application_schema__application, KG__application__is_live, \
    KG__application_schema__name, KEY__is_default
from queue import Queue
from jaaql.db.db_utils import execute_supplied_statement, create_interface_for_db, ERR__schema_invalid
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.constants import KEY__application, KEY__database, KEY__schema, KEY__role, DB__jaaql, \
    KEY__read_only, KEY__prevent_unused_parameters
from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils_no_project_imports import objectify
from jaaql.mvc.generated_queries import application__select


def get_jaaql_connection_to_db(vault, config, database: str, jaaql_connection: DBInterface):
    return create_interface_for_db(vault, config, jaaql_connection.role, database)


def get_required_db(vault, config, jaaql_connection: DBInterface, inputs: dict, account_id: str, conn=None, interface: DBInterface = None, db_cache=None):
    if not isinstance(inputs, dict):
        raise HttpStatusException("Expected object or string input")

    if conn is None:
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

        if KEY__database not in inputs:
            inputs[KEY__database] = DB__jaaql

        sub_role = inputs.pop(KEY__role) if KEY__role in inputs else None

        required_db = create_interface_for_db(vault, config, account_id, inputs[KEY__database], sub_role)
    else:
        if interface is None:
            raise Exception("Must supply interface is connection is supplied!")

        required_db = interface

    return required_db


def submit(vault, config, db_crypt_key, jaaql_connection: DBInterface, inputs: dict, account_id: str, verification_hook: Queue = None,
           cached_canned_query_service=None, as_objects: bool = False, singleton: bool = False, keep_alive_conn: bool = False,
           conn=None, interface: DBInterface = None, db_cache=None):
    if not isinstance(inputs, dict):
        raise HttpStatusException("Expected object or string input")

    required_db = get_required_db(vault, config, jaaql_connection, inputs, account_id, conn, interface, db_cache=db_cache)

    prevent_unused = inputs.pop(KEY__prevent_unused_parameters) if KEY__prevent_unused_parameters in inputs else True

    ret = InterpretJAAQL(required_db, jaaql_connection
                         ).transform(inputs, skip_commit=inputs.get(KEY__read_only), wait_hook=verification_hook,
                                     encryption_key=db_crypt_key, conn=conn,
                                     canned_query_service=cached_canned_query_service, prevent_unused_parameters=prevent_unused,
                                     and_return_connection_mid_transaction=keep_alive_conn)

    if as_objects:
        ret = objectify(ret, singleton=singleton)

    return ret
