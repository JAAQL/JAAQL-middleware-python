from http import HTTPStatus
from argparse import Namespace  # Used elsewhere

from jaaql.generated_constants import RESPONSE_CODE_LOOKUP

RESP__default_err_message = "We have encountered an error whilst processing your request!"
RESP__default_err_code = HTTPStatus.INTERNAL_SERVER_ERROR

ERR__connection_expired = "Connection expired"

ERR__already_installed = "JAAQL has already been installed!"
ERR__already_signed_up = "User has already signed up!"
ERR__non_node_connection_object = "Cannot request a list of databases for a non-node connection object"
ERR__passwords_do_not_match = "The supplied passwords do not match!"
ERR__cannot_override_db = "Cannot override DB"


class HttpStatusException(Exception):

    def __init__(self, message: str, response_code: int = HTTPStatus.UNPROCESSABLE_ENTITY):
        super().__init__(message)

        if response_code is None:
            response_code = HTTPStatus.UNPROCESSABLE_ENTITY

        self.message = message
        self.response_code = response_code


class HttpSingletonStatusException(HttpStatusException):
    def __init__(self, message: str, response_code: int = HTTPStatus.UNPROCESSABLE_ENTITY, actual_count: int = 1):
        super().__init__(message, response_code)

        self.actual_count = actual_count


class JaaqlInterpretableHandledError(Exception):
    def __init__(self, error_code: int, http_response_code: int,
                 table_name: str | None, index: int | None, message: str,
                 column_name: str | None, _set: str | None, descriptor):
        super().__init__(message)

        self.error_code = error_code
        self.message = message
        self.table_name = table_name
        self.index = index
        self.column_name = column_name
        self.descriptor = descriptor
        self.set = _set
        self.response_code = http_response_code

    @staticmethod
    def deserialize_from_json(obj):
        return JaaqlInterpretableHandledError(
            obj.get("error_code"), RESPONSE_CODE_LOOKUP.get(obj.get("error_code"), 422), obj.get("table_name"),
            obj.get("index"), obj.get("message"), obj.get("column_name"),
            obj.get("set"), obj.get("descriptor")
        )
