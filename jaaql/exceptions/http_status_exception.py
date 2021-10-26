from http import HTTPStatus

RESP__default_err_message = "We have encountered an error whilst processing your request!"
RESP__default_err_code = HTTPStatus.INTERNAL_SERVER_ERROR


class HttpStatusException(Exception):

    def __init__(self, message: str, response_code: int = HTTPStatus.UNPROCESSABLE_ENTITY):
        super().__init__(message)

        self.message = message
        self.response_code = response_code
