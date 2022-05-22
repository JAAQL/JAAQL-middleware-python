import unittest
import inspect
from http import HTTPStatus
from .component_utils import *

BASE_INTERNAL_URL = BASE_URL + "/internal"

PASSWORD_JAAQL = "Abcdefg456"
PASSWORD_SUPERJAAQL = "Hijklmn123"

HEADER_AUTH = "Authentication-Token"


class BaseComponent(unittest.TestCase):

    def get_jaaql_auth_header(self, username: str = "jaaql", password: str = PASSWORD_JAAQL, run_test: bool = True):
        res = requests.post(BASE_URL + "/oauth/token", json={
            "username": username,
            "password": password
        })

        if run_test:
            self.assertEqual(HTTPStatus.OK, res.status_code, "Expecting auth token")
            return res.json()
        else:
            return res

    def assertEqual(self, first, second, msg=None):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        print("\033[36m\033[1mASSERTION:\033[0m \033[33m\033[1m" + calframe[1][3] + "\033[0m " + msg)
        super().assertEqual(first, second, msg)
