import unittest
from jaaql.test.components.component_utils import BASE_URL
from http import HTTPStatus
from .component_utils import *

BASE_INTERNAL_URL = BASE_URL + "/internal"

PASSWORD_JAAQL = "Abcdefg456"
PASSWORD_SUPERJAAQL = "Hijklmn123"


class BaseComponent(unittest.TestCase):
    pass
