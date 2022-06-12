from http import HTTPStatus


class JAAQLResponse:
    def __init__(self):
        self.response_code = HTTPStatus.OK
        self.user_id = None
        self.ip_id = None
        self.response_type = None
