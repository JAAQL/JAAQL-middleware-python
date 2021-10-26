from jaaql.exceptions.http_status_exception import HttpStatusException
from http import HTTPStatus

ERR__not_yet_implemented = "Not yet implemented!"


class NotYetImplementedException(HttpStatusException):

    def __init__(self):
        super().__init__(ERR__not_yet_implemented, HTTPStatus.NOT_IMPLEMENTED)
