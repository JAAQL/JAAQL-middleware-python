"""
The code exchange of a login through the identity provider (/exchange-auth-code, exchange_auth_code) sends its token request straight to
Keycloak (the backchannel, KEYCLOAK_URL) but signs a client assertion whose audience is the token endpoint as the realm's discovery document
advertises it, on the host the realm's frontendUrl names, as the PAR's assertion does. Keycloak refuses any other audience with
"Invalid token audience" (invalid_client), so the exchange found no id_token and every such login landed logged out.

    python -m unittest jaaql.test.test_token_client_assertion

Needs only the package's requirements: the jaaql lookups, the discovery document, the JARM check and the identity provider are replaced
"""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.response import JAAQLResponse

FRONTEND = "http://localhost"
BACKCHANNEL = "http://host.docker.internal:8080"
TOKEN_PATH = "/realms/MfaTest/protocol/openid-connect/token"
CLIENT_ID = "f7144911-54da-4c8d-b16d-28395444922c"


class TokenRequestSent(Exception):
    pass


class TestTokenClientAssertion(unittest.TestCase):

    def exchange(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jaaql_model = JAAQLModel.__new__(JAAQLModel)
        jaaql_model.use_easyauth = False
        jaaql_model.use_oidc_basic = False
        jaaql_model.use_fapi_advanced = False
        jaaql_model.is_https = False
        jaaql_model.jaaql_lookup_connection = None
        jaaql_model.vault = SimpleNamespace(get_obj=lambda key_name: "k" * 32)
        jaaql_model.get_db_crypt_key = lambda: b"k" * 32
        jaaql_model.fapi_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        jaaql_model.jwks = {"keys": [{"kid": "k1"}]}
        jaaql_model.fetch_discovery_content = lambda *args: {
            "issuer": FRONTEND + "/realms/MfaTest",
            "token_endpoint": FRONTEND + TOKEN_PATH,
            "id_token_signing_alg_values_supported": ["PS256", "RS256"]
        }
        jaaql_model.fetch_jwks_client = lambda *args: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key="unused"))
        sent = {}

        def post(url, data=None, **kwargs):
            sent["url"] = url
            sent["data"] = data
            raise TokenRequestSent()

        jaaql_model.idp_session = SimpleNamespace(post=post)
        oidc_state = {"application": "mfatest", "provider": "Relay Systems", "tenant": "default", "database": "db", "code_verifier": "v" * 50,
                      "state": "s1", "nonce": "n1", "redirect_uri": FRONTEND + "/person__browse.html"}
        with mock.patch.dict(os.environ, {"KEYCLOAK_URL": BACKCHANNEL, "OIDC_ISSUER": ""}), \
                mock.patch.object(model.crypt_utils, "jwt_decode", return_value=oidc_state), \
                mock.patch.object(model, "jaaql__decrypt", side_effect=lambda value, key: value), \
                mock.patch.object(model, "application__select", return_value={"default_schema": "default", "base_url": FRONTEND}), \
                mock.patch.object(model, "user_registry__select", return_value={"discovery_url": BACKCHANNEL + "/realms/MfaTest"}), \
                mock.patch.object(model, "database_user_registry__select", return_value={"client_id": CLIENT_ID}), \
                mock.patch.object(model.jwt, "decode", return_value={"state": "s1", "code": "the-code"}):
            with self.assertRaises(TokenRequestSent):
                jaaql_model.exchange_auth_code({"response": "jarm"}, "oidc-cookie", "127.0.0.1", JAAQLResponse())
        return sent, key

    def test_the_token_request_goes_to_the_backchannel(self):
        sent, _ = self.exchange()
        self.assertEqual(BACKCHANNEL + TOKEN_PATH, sent["url"])
        self.assertEqual("the-code", sent["data"]["code"])
        self.assertEqual("urn:ietf:params:oauth:client-assertion-type:jwt-bearer", sent["data"]["client_assertion_type"])

    def test_the_client_assertion_names_the_advertised_token_endpoint(self):
        sent, key = self.exchange()
        assertion = sent["data"]["client_assertion"]
        self.assertEqual({"alg": "PS256", "kid": "k1", "typ": "JWT"}, jwt.get_unverified_header(assertion))
        claims = jwt.decode(assertion, key.public_key(), algorithms=["PS256"], audience=FRONTEND + TOKEN_PATH)
        self.assertEqual(FRONTEND + TOKEN_PATH, claims["aud"])
        self.assertEqual(CLIENT_ID, claims["iss"])
        self.assertEqual(CLIENT_ID, claims["sub"])
        with self.assertRaises(jwt.InvalidAudienceError):
            jwt.decode(assertion, key.public_key(), algorithms=["PS256"], audience=BACKCHANNEL + TOKEN_PATH)


if __name__ == "__main__":
    unittest.main()
