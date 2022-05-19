from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.constants import ENCODING__utf
from typing import Union
import jaaql.utilities.crypt_utils as crypt_utils
from jaaql.db.db_pg_interface import DBPGInterface

ERR__encryption_key_required = "Encryption key required. Check internal function calls"
ERR__duplicated_encrypt_parameter = "Duplicated value in encrypt_parameters list"
ERR__duplicated_decrypt_column = "Duplicated value in decrypt_columns list"
ERR__missing_encrypt_parameter = "Encrypted parameter is not found '%s'"
ERR__duplicated_encryption_salt = "Duplicated value in encryption_salts list"
ERR__missing_decrypt_column = "Decrypted column '%s' not found in the result set"
ERR__expected_single_row = "Expected single row response but received '%d' rows"
ERR__unsupported_interface = "Unsupported interface '%s'. We only support %s"


KEY_CONFIG__db = "DATABASE"
KEY_CONFIG__interface = "interface"
INTERFACE__postgres_key = "postgres"
INTERFACE__postgres_class = "DBPGInterface"


def jaaql__encrypt(dec_input: str, encryption_key: bytes, salt: bytes = None) -> str:
    return crypt_utils.encrypt_raw(encryption_key, dec_input, salt)


def jaaql__decrypt(enc_input: str, encryption_key: bytes) -> str:
    return crypt_utils.decrypt__raw(encryption_key, enc_input)


def try_encode(salt: Union[str, bytes]) -> bytes:
    if isinstance(salt, str):
        salt = salt.encode(ENCODING__utf)
    return salt


def create_interface(config, address: str, port: int, database: str, username: str, password: str,
                     is_jaaql_user: bool = False, dev_mode: bool = False):
    interface = config[KEY_CONFIG__db][KEY_CONFIG__interface]
    supported = {
        INTERFACE__postgres_key: INTERFACE__postgres_class
    }

    if interface not in supported.keys():
        raise Exception(ERR__unsupported_interface % (interface, ", ".join(supported.keys())))

    # interface_class = getattr(db, supported[interface])  To implement later for accessing non postgres databases
    interface_class = DBPGInterface
    instance = interface_class(config, address, port, database, username, password, is_jaaql_user, dev_mode)

    return instance


def execute_supplied_statement(db_interface, query: str, parameters: dict = None,
                               as_objects: bool = False, encrypt_parameters: list = None,
                               decrypt_columns: list = None, encryption_key: bytes = None,
                               encryption_salts: dict = None):
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
        "parameters": parameters
    }

    data = InterpretJAAQL(db_interface).transform(statement)

    missing = [param for param in decrypt_columns if param not in data["columns"]]
    if len(missing) != 0:
        raise HttpStatusException(ERR__missing_decrypt_column % missing)

    if len(decrypt_columns) != 0:
        data["rows"] = [
            [jaaql__decrypt(
                val, encryption_key) if col in decrypt_columns and val is not None else val for val, col in
             zip(row, data["columns"])] for row in data["rows"]]

    if as_objects:
        data = db_interface.objectify(data)

    return data


def force_singleton(data, as_objects: bool = False, singleton_code: int = None):
    was_no_singleton = False
    if as_objects:
        if len(data) != 1:
            was_no_singleton = True
    else:
        if len(data["rows"]) != 1:
            was_no_singleton = True
        if len(data["rows"]) != 0:
            data["rows"] = data["rows"][0]

    if was_no_singleton:
        raise HttpStatusException(ERR__expected_single_row % len(data), singleton_code)

    return data[0] if as_objects else data


def execute_supplied_statement_singleton(db_interface, query, parameters: dict = None,
                                         as_objects: bool = False, encrypt_parameters: list = None,
                                         decrypt_columns: list = None, encryption_key: bytes = None,
                                         encryption_salts: dict = None, singleton_code: int = None):
    data = execute_supplied_statement(db_interface, query, parameters, as_objects, encrypt_parameters,
                                      decrypt_columns, encryption_key, encryption_salts)

    return force_singleton(data, as_objects, singleton_code)


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
        data = [db_interface.objectify(obj) for obj in data]

    return data
