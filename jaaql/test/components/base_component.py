import unittest
from http import HTTPStatus
from .component_utils import *

BASE_INTERNAL_URL = BASE_URL + "/internal"

PASSWORD_JAAQL = "Abcdefg456"
PASSWORD_SUPERJAAQL = "Hijklmn123"

HEADER_AUTH = "Authentication-Token"


class BaseComponent(unittest.TestCase):

    def get_jaaql_auth_header(self):
        res = requests.post(BASE_URL + "/oauth/token", json={
            "username": "jaaql",
            "password": PASSWORD_JAAQL
        })

        self.assertEqual(HTTPStatus.OK, res.status_code, "Expecting auth token")
        return res.json()
