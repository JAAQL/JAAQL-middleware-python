from jaaql.exceptions.http_status_exception import HttpStatusException, HttpSingletonStatusException
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.constants import ENCODING__utf, VAULT_KEY__super_db_credentials
from typing import Union
import jaaql.utilities.crypt_utils as crypt_utils
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_interface import DBInterface
from jaaql.utilities.utils_no_project_imports import objectify

ERR__encryption_key_required = "Encryption key required. Check internal function calls"
ERR__duplicated_encrypt_parameter = "Duplicated value in encrypt_parameters list"
ERR__duplicated_decrypt_column = "Duplicated value in decrypt_columns list"
ERR__missing_encrypt_parameter = "Encrypted parameter is not found '%s'"
ERR__duplicated_encryption_salt = "Duplicated value in encryption_salts list"
ERR__expected_single_row = "Expected single row response but received '%d' rows"
ERR__unsupported_interface = "Unsupported interface '%s'. We only support %s"
ERR__schema_invalid = "Schema invalid!"

KEY_CONFIG__db = "DATABASE"
KEY_CONFIG__interface = "interface"
INTERFACE__postgres_key = "postgres"
INTERFACE__postgres_class = "DBPGInterface"


def jaaql__encrypt(dec_input: str, encryption_key: bytes, salt: bytes = None) -> str:
    return crypt_utils.encrypt_raw(encryption_key, dec_input, salt)


def jaaql__decrypt(enc_input: str, encryption_key: bytes) -> str:
    return crypt_utils.decrypt_raw(encryption_key, enc_input)


def try_encode(salt: Union[str, bytes]) -> bytes:
    if isinstance(salt, str):
        salt = salt.encode(ENCODING__utf)
    return salt


def create_interface(config, address: str, port: int, database: str, username: str, password: str = None, role: str = None, sub_role: str = None):
    interface = config[KEY_CONFIG__db][KEY_CONFIG__interface]
    supported = {
        INTERFACE__postgres_key: INTERFACE__postgres_class
    }

    if interface not in supported.keys():
        raise Exception(ERR__unsupported_interface % (interface, ", ".join(supported.keys())))

    # interface_class = getattr(db, supported[interface])  To implement later for accessing non postgres databases
    interface_class = DBPGInterface
    instance = interface_class(config, address, port, database, username, role=role, password=password, sub_role=sub_role)

    return instance


def execute_supplied_statement(db_interface, query: str, parameters: dict = None,
                               as_objects: bool = False, encrypt_parameters: list = None,
                               decrypt_columns: list = None, encryption_key: bytes = None,
                               encryption_salts: dict = None, skip_commit: bool = False,
                               autocommit: bool = False, do_prepare_only: str = None,
                               attempt_fetch_domain_types: bool = False, psql: list = None,
                               pre_psql: str = None):
    if parameters is None:
        parameters = {}

    if (
            decrypt_columns is not None or encrypt_parameters is not None or encryption_salts is not None
    ) and encryption_key is None:
        raise HttpStatusException(ERR__encryption_key_required)

    if decrypt_columns is None:
        decrypt_columns = []

    if encrypt_parameters is None:
        encrypt_parameters = []

    if encryption_salts is None:
        encryption_salts = {}

    if len(encrypt_parameters) != len(set(encrypt_parameters)):
        raise HttpStatusException(ERR__duplicated_encrypt_parameter)

    if len(encrypt_parameters) != len(set(encrypt_parameters)):
        raise HttpStatusException(ERR__duplicated_decrypt_column)

    for key, val in encryption_salts.items():
        if key not in encrypt_parameters:
            raise HttpStatusException(ERR__missing_encrypt_parameter % key)

    if len(encryption_salts.keys()) != len(set(encryption_salts.keys())):
        raise HttpStatusException(ERR__duplicated_encryption_salt)

    missing = [param for param in encrypt_parameters if param not in parameters.keys()]
    if len(missing) != 0:
        raise HttpStatusException(ERR__missing_encrypt_parameter % missing)

    for col in encrypt_parameters:
        if parameters[col] is not None:
            parameters[col] = jaaql__encrypt(parameters[col], encryption_key,
                                             try_encode(encryption_salts.get(col, None)))

    statement = {
        "query": query,
        "parameters": parameters,
        "decrypt": decrypt_columns
    }

    data = InterpretJAAQL(db_interface).transform(statement, skip_commit=skip_commit, encryption_key=encryption_key, autocommit=autocommit,
                                                  do_prepare_only=do_prepare_only, attempt_fetch_domain_types=attempt_fetch_domain_types,
                                                  psql=psql, pre_psql=pre_psql)

    if as_objects:
        data = objectify(data)

    return data


def force_singleton(data, as_objects: bool = False, singleton_code: int = None, singleton_message: str = None):
    was_no_singleton = False
    original_count = 1
    if as_objects:
        if len(data) != 1:
            original_count = len(data)
            was_no_singleton = True
    else:
        if len(data["rows"]) != 1:
            original_count = len(data["rows"])
            was_no_singleton = True
        if len(data["rows"]) != 0:
            data["rows"] = data["rows"][0]

    if was_no_singleton:
        err = ERR__expected_single_row % len(data)
        if singleton_message is not None:
            err = singleton_message
        raise HttpSingletonStatusException(err, singleton_code, original_count)

    return data[0] if as_objects else data


def execute_supplied_statement_singleton(db_interface, query, parameters: dict = None,
                                         as_objects: bool = False, encrypt_parameters: list = None,
                                         decrypt_columns: list = None, encryption_key: bytes = None,
                                         encryption_salts: dict = None, singleton_code: int = None,
                                         singleton_message: str = None, skip_commit: bool = False,
                                         do_prepare_only: bool = False):
    data = execute_supplied_statement(db_interface, query, parameters, as_objects, encrypt_parameters,
                                      decrypt_columns, encryption_key, encryption_salts, skip_commit=skip_commit,
                                      do_prepare_only=do_prepare_only)

    return force_singleton(data, as_objects, singleton_code, singleton_message)


def execute_supplied_statements(db_interface, queries: Union[str, list],
                                parameters: Union[dict, list] = None, as_objects: bool = False):
    if not isinstance(queries, list):
        queries = [queries]
    if not isinstance(parameters, list) and parameters is not None:
        parameters = [parameters]

    if parameters is None:
        parameters = [{}] * len(queries)

    statement = [
        {
            "query": query,
            "parameters": parameter_set
        }
        for query, parameter_set in zip(queries, parameters)
    ]

    data = InterpretJAAQL(db_interface).transform(statement)

    if as_objects:
        data = [objectify(obj) for obj in data]

    return data


def create_interface_for_db(vault, config, user_id: str, database: str, sub_role: str = None):
    jaaql_uri = vault.get_obj(VAULT_KEY__super_db_credentials)
    address, port, _, username, password = DBInterface.fracture_uri(jaaql_uri)
    return create_interface(config, address, port, database, username, password=password, role=user_id, sub_role=sub_role)
