from http import HTTPStatus

COOKIE_JAAQL_AUTH = "jaaql_auth"
COOKIE_FLAG_HTTP_ONLY = "HttpOnly"
COOKIE_FLAG_SECURE = "Secure"
COOKIE_ATTR_SAME_SITE = "SameSite"
COOKIE_ATTR_EXPIRES = "Expires"
COOKIE_ATTR_MAX_AGE = "Max-Age"
COOKIE_VAL_STRICT = "Strict"
COOKIE_VAL_INACTIVITY_15_MINUTES = "900"
COOKIE_EXPIRY_90_DAYS = 90

DEFAULT_COOKIE_FLAGS = [COOKIE_FLAG_SECURE, COOKIE_FLAG_HTTP_ONLY, COOKIE_FLAG_SECURE]


class JAAQLResponse:
    def __init__(self):
        self.response_code = HTTPStatus.OK
        self.account_id = None
        self.ip_id = None
        self.response_type = None

        self.cookies = {}

    def set_cookie(self, name, value, attributes):
        if name in self.cookies:
            raise Exception("Cookie '%s' already exists" % name)
        self.cookies[name] = ("; ".join([name + "=" + value] + DEFAULT_COOKIE_FLAGS + [key + "=" + val for key, val in attributes.items()]))
