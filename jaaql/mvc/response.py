from http import HTTPStatus


class JAAQLResponse:
    def __init__(self):
        self.response_code = HTTPStatus.OK
        self.account_id = None
        self.ip_id = None
        self.response_type = None
