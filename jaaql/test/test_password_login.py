"""
A password login (/oauth/token, get_auth_token) on an account without an api_key, such as one that only ever logs in through its
identity provider, is refused as wrong credentials (401) instead of failing in decrypt (500); accounts with an api_key log in as before.

    python -m unittest jaaql.test.test_password_login

Needs only the package's requirements: the account lookup and the validated_ip_address write are replaced, so no database is reached
"""
import os
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

from jaaql.db.db_utils import jaaql__encrypt
from jaaql.exceptions.jaaql_interpretable_handled_errors import UserUnauthorized
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel

CRYPT_KEY = b"k" * 32
EMAIL = "ann@example.com"


def stub_model():
    return SimpleNamespace(jaaql_lookup_connection=None, get_db_crypt_key=lambda: CRYPT_KEY, get_repeatable_salt=lambda addition=None: b"salt",
                           _check_email_confirmation_grace_period=lambda account, email=None: None,
                           vault=SimpleNamespace(get_obj=lambda key: "jwt-secret"), token_expiry_ms=1800000, vigilant_sessions=False,
                           is_container=True, is_https=False)


def account(api_key):
    return {"id": "account-ann", "username": EMAIL, "api_key": api_key, "email_verified": True}


class TestPasswordLogin(unittest.TestCase):

    def login(self, api_key, password):
        environ = {key: value for key, value in os.environ.items() if key != "JAAQL_ACCEPTANCE_PASSWORD"}
        with mock.patch.dict(os.environ, environ, clear=True), \
                mock.patch.object(model, "fetch_account_from_username", return_value=account(api_key)), \
                mock.patch.object(model, "execute_supplied_statement_singleton", return_value={"uuid": "ip-uuid"}) as validated:
            try:
                return JAAQLModel.get_auth_token(stub_model(), EMAIL, "127.0.0.1", password=password), validated
            except UserUnauthorized as unauthorized:
                return unauthorized, validated

    def assertRefused(self, outcome):
        result, validated = outcome
        self.assertIsInstance(result, UserUnauthorized)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, result.response_code)
        validated.assert_not_called()

    def test_an_account_without_an_api_key_is_refused_as_wrong_credentials(self):
        for password in ["anything", "", None]:
            with self.subTest(password=password):
                self.assertRefused(self.login(None, password))

    def test_an_account_with_an_api_key_logs_in_with_its_password_only(self):
        api_key = jaaql__encrypt("s3cret-Password", CRYPT_KEY)
        self.assertRefused(self.login(api_key, "wrong"))
        self.assertRefused(self.login(api_key, None))
        token, validated = self.login(api_key, "s3cret-Password")
        self.assertIsInstance(token, str)
        validated.assert_called_once()


if __name__ == "__main__":
    unittest.main()
