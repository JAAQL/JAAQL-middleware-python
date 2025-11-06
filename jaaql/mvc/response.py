from http import HTTPStatus
from wsgiref.handlers import format_date_time
from jaaql.utilities.utils_no_project_imports import format_cookie, COOKIE_ATTR_EXPIRES


class JAAQLResponse:
    def __init__(self):
        self.response_code = HTTPStatus.OK
        self.account_id = None
        self.ip_id = None
        self.response_type = None
        self.raw_response = None
        self.raw_headers = {}
        self.is_binary = False

        self.cookies = {}

    def set_cookie(self, name, value, attributes, is_https):
        if name in self.cookies:
            raise Exception("Cookie '%s' already exists" % name)
        self.cookies[name] = format_cookie(name, value, attributes, is_https)

    def delete_cookie(self, cookie, is_https):
        self.set_cookie(cookie, "", attributes={COOKIE_ATTR_EXPIRES: format_date_time(0)}, is_https=is_https)
