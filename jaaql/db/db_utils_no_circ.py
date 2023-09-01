import os

from jaaql.mvc.exception_queries import QUERY__fetch_application_schemas, KG__application_schema__application, KG__application__is_live, \
    KG__application_schema__name, KEY__is_default
from queue import Queue
from jaaql.db.db_utils import execute_supplied_statement, create_interface_for_db, ERR__schema_invalid
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.constants import KEY__application, KEY__database, KEY__schema, KEY__role, DB__jaaql, \
    KEY__read_only, KEY__prevent_unused_parameters, KEY__debugging_account_id, ENVIRON__allow_debugging_users
from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils_no_project_imports import objectify


def submit(vault, config, db_crypt_key, jaaql_connection: DBInterface, inputs: dict, account_id: str, verification_hook: Queue = None,
           cached_canned_query_service = None, as_objects: bool = False, singleton: bool = False):
    if not isinstance(inputs, dict):
        raise HttpStatusException("Expected object or string input")

    if KEY__application in inputs:
        schemas = execute_supplied_statement(jaaql_connection, QUERY__fetch_application_schemas, {
            KG__application_schema__application: inputs[KEY__application]
        }, as_objects=True)
        if len(schemas) == 0:
            raise HttpStatusException("Application has no schemas!")
        if not schemas[0][KG__application__is_live]:
            raise HttpStatusException("Application is currently being deployed. Please wait a few minutes until deployment is complete")
        schemas = {itm[KG__application_schema__name]: itm for itm in schemas}

        found_db = None
        if KEY__schema in inputs:
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

    if os.environ.get(ENVIRON__allow_debugging_users) == "TRUE" and inputs.get(KEY__debugging_account_id) is not None:
        account_id = inputs.pop(KEY__debugging_account_id)

    required_db = create_interface_for_db(vault, config, account_id, inputs[KEY__database], sub_role)

    prevent_unused = inputs.pop(KEY__prevent_unused_parameters) if KEY__prevent_unused_parameters in inputs else True

    ret = InterpretJAAQL(required_db).transform(inputs, skip_commit=inputs.get(KEY__read_only), wait_hook=verification_hook,
                                                encryption_key=db_crypt_key,
                                                canned_query_service=cached_canned_query_service, prevent_unused_parameters=prevent_unused)

    if as_objects:
        ret = objectify(ret, singleton=singleton)

    return ret
