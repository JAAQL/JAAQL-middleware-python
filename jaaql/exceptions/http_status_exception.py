from http import HTTPStatus
from argparse import Namespace

RESP__default_err_message = "We have encountered an error whilst processing your request!"
RESP__default_err_code = HTTPStatus.INTERNAL_SERVER_ERROR

HTTP_STATUS_CONNECTION_EXPIRED = Namespace(value=419)
ERR__connection_expired = "Connection expired"

ERR__already_installed = "JAAQL has already been installed!"
ERR__already_signed_up = "User has already signed up!"
ERR__non_node_connection_object = "Cannot request a list of databases for a non-node connection object"
ERR__passwords_do_not_match = "The supplied passwords do not match!"
ERR__cannot_override_db = "Cannot override DB"


class HttpStatusException(Exception):

    def __init__(self, message: str, response_code: int = HTTPStatus.UNPROCESSABLE_ENTITY):
        super().__init__(message)

        self.message = message
        self.response_code = response_code
