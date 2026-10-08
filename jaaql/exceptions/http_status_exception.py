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


class ConnectionLostError(HttpStatusException):
    # Raised when a database operation failed because its connection was lost (e.g. the backend was
    # terminated by \wipe dbms's pg_terminate_backend) BEFORE anything committed: during a statement of
    # a transaction, or before its COMMIT was sent. Nothing persisted, so a self-contained operation may
    # safely be retried on a fresh connection. Subclasses HttpStatusException so that if retries are
    # exhausted it still surfaces as a clean 500.
    def __init__(self, message: str):
        super().__init__("Connection lost, transaction not persisted: " + message, HTTPStatus.INTERNAL_SERVER_ERROR)


class VerificationTimedOut(Exception):
    # The parallel verifier gave no verdict in time. Answered as the plain Exception it replaces; a server fault whatever SQL waited for it
    # (jaaql/utilities/server_errors.py)
    pass


class VerificationFailed(Exception):
    # The parallel verifier failed with a server error. Answered as the plain Exception it replaces; the verifier reports it itself, the
    # requests waiting for its verdict do not
    pass


class AuthorizationResponseError(Exception):
    # The identity provider answered a login's authorization request with an error of its own (a JARM response carrying error=...). Never
    # raised: the login is answered with its redirect, and the error reported unless the user caused it (jaaql/utilities/server_errors.py)
    pass


# An exception carrying this attribute set to True is the client's, whatever its status: it is never reported as a server error
ATTR__client_fault = "jaaql_client_fault"
# The database error a refused COMMIT raised, on the error it is answered with (translated as a statement's would be)
ATTR__database_error = "jaaql_database_error"
# Set to True on the error a request is answered with when its connection was lost after its SQL may have committed (a COMMIT lost in
# flight, a connection gone after the request's own COMMIT): the outcome is unknown, whoever wrote the SQL, which is the server's to answer for
ATTR__outcome_unknown = "jaaql_outcome_unknown"


def outcome_unknown(ex):
    setattr(ex, ATTR__outcome_unknown, True)
    return ex


def client_fault(ex):
    setattr(ex, ATTR__client_fault, True)
    return ex


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
        # An error a cloud procedure relays from its output, whatever its code: the procedure's own requests to JAAQL report their own
        # server faults
        return client_fault(JaaqlInterpretableHandledError(
            obj.get("error_code"), RESPONSE_CODE_LOOKUP.get(obj.get("error_code"), 422), obj.get("table_name"),
            obj.get("index"), obj.get("message"), obj.get("column_name"),
            obj.get("set"), obj.get("descriptor")
        ))
