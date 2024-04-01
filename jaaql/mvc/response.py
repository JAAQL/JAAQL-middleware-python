from http import HTTPStatus
from jaaql.utilities.utils_no_project_imports import format_cookie


class JAAQLResponse:
    def __init__(self):
        self.response_code = HTTPStatus.OK
        self.account_id = None
        self.ip_id = None
        self.response_type = None
        self.raw_response = None
        self.raw_headers = {}

        self.cookies = {}

    def set_cookie(self, name, value, attributes, is_https):
        if name in self.cookies:
            raise Exception("Cookie '%s' already exists" % name)
        self.cookies[name] = format_cookie(name, value, attributes, is_https)
