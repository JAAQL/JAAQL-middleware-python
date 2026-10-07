"""
The oidc and oidc_return cookies that /oidc-redirect-url (fetch_redirect_uri) sets to carry a login through the identity provider live as
long as the OIDC session token they carry (oidc_login_expiry_ms, 1800 s with the shipped configuration), not the 900 s of an inactivity
cookie; their other attributes are unchanged.

    python -m unittest jaaql.test.test_oidc_cookies

Needs only the package's requirements: the jaaql lookups and the discovery document are replaced, so no database or identity provider
is reached
"""
import unittest
from types import SimpleNamespace
from unittest import mock

import jwt

from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.response import JAAQLResponse
from jaaql.utilities import crypt_utils
from jaaql.utilities.utils_no_project_imports import COOKIE_OIDC, COOKIE_OIDC_RETURN

JWT_KEY = "jwt-secret"
BASE_URL = "http://localhost"


def attributes(cookie):
    name_value, *rest = cookie.split("; ")
    return name_value.split("=", 1), rest


class TestOidcCookies(unittest.TestCase):

    def redirect(self, oidc_login_expiry_ms=1800000, is_container=True, is_https=False):
        jaaql_model = JAAQLModel.__new__(JAAQLModel)
        jaaql_model.use_easyauth = False
        jaaql_model.use_oidc_basic = True
        jaaql_model.jaaql_lookup_connection = None
        jaaql_model.vault = SimpleNamespace(get_obj=lambda key: JWT_KEY if key == model.VAULT_KEY__jwt_crypt_key else "k" * 32)
        jaaql_model.oidc_login_expiry_ms = oidc_login_expiry_ms
        jaaql_model.is_container = is_container
        jaaql_model.is_https = is_https
        jaaql_model.fetch_discovery_content = lambda *args: {"authorization_endpoint": "http://localhost:8080/realms/MfaTest/protocol/openid-connect/auth"}
        response = JAAQLResponse()
        with mock.patch.object(model, "application__select", return_value={"default_schema": "default", "base_url": BASE_URL}), \
                mock.patch.object(model, "application_schema__select", return_value={"database": "mfatest_db"}), \
                mock.patch.object(model, "user_registry__select", return_value={"discovery_url": "http://localhost:8080/realms/MfaTest"}), \
                mock.patch.object(model, "database_user_registry__select", return_value={"client_id": "mfatest", "federation_procedure": "_system.federate"}), \
                mock.patch.object(model, "fetch_parameters_for_federation_procedure", return_value=[]):
            jaaql_model.fetch_redirect_uri({"application": "mfatest", "provider": "Relay Systems", "tenant": "default", "redirect_uri": "person__browse.html"},
                                           response)
        return response

    def test_both_cookies_live_as_long_as_the_oidc_login(self):
        response = self.redirect()
        for name in [COOKIE_OIDC, COOKIE_OIDC_RETURN]:
            with self.subTest(cookie=name):
                (cookie_name, _), rest = attributes(response.cookies[name])
                self.assertEqual(name, cookie_name)
                self.assertEqual(["HttpOnly", "SameSite=Lax", "Path=/api", "Max-Age=1800"], rest)
        self.assertEqual(302, response.response_code)
        self.assertTrue(response.raw_headers["Location"].startswith(BASE_URL + "/realms/MfaTest/protocol/openid-connect/auth?"))

    def test_the_max_age_follows_oidc_login_expiry_ms_and_matches_the_token_in_the_cookie(self):
        response = self.redirect(oidc_login_expiry_ms=600000)
        (_, token), rest = attributes(response.cookies[COOKIE_OIDC])
        self.assertIn("Max-Age=600", rest)
        self.assertEqual(BASE_URL + "/person__browse.html", crypt_utils.jwt_decode(JWT_KEY, token, model.JWT_PURPOSE__oidc)["redirect_uri"])
        expires_at = jwt.decode(token, JWT_KEY, algorithms=[crypt_utils.JWT__algo])[crypt_utils.JWT__exp]
        self.assertAlmostEqual(600000, expires_at - crypt_utils.fetch_epoch_ms(), delta=5000)
        (_, return_url), rest = attributes(response.cookies[COOKIE_OIDC_RETURN])
        self.assertEqual(BASE_URL + "/person__browse.html", return_url)
        self.assertIn("Max-Age=600", rest)

    def test_the_other_attributes_are_unchanged(self):
        response = self.redirect(is_container=False, is_https=True)
        for name in [COOKIE_OIDC, COOKIE_OIDC_RETURN]:
            with self.subTest(cookie=name):
                self.assertEqual(["HttpOnly", "Secure", "SameSite=Lax", "Path=/", "Max-Age=1800"], attributes(response.cookies[name])[1])


if __name__ == "__main__":
    unittest.main()
