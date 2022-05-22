import os

from .base_component import *
from jaaql.constants import *
from base64 import b64decode as b64d
from pyzbar.pyzbar import decode, ZBarSymbol
import pyotp
from PIL import Image
from io import BytesIO

KEY_INSTALL_KEY = "install_key"
PATH_INSTALL = "/install"
PATH_UNINSTALL = "/uninstall"

ENVIRON__fast_jaaql_component_tests = "FAST_TESTS"


class InstallComponent(BaseComponent):

    def test_install(self):
        if not bool(os.environ.get(ENVIRON__fast_jaaql_component_tests, False)):
            self.run_test_install()
            self.run_test_install_mfa()
        else:
            print("Skipping full install tests as fast tests activated")
        self.run_test_install_superjaaql()

    def get_uninstall_data(self, db_user_password: str, uninstall_key: str):
        return {
            KEY__db_super_user_password: db_user_password,
            KEY__uninstall_key: uninstall_key
        }

    def run_test_install(self):
        resp = self.get_jaaql_auth_header(run_test=False)
        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, resp.status_code, "Not yet installed")

        resp = requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password],
                                                                                              self.fetch_uninstall_key()))
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Not yet installed, uninstall")

        install_data = {
            "password": PASSWORD_JAAQL,
            "use_mfa": False,
            KEY_INSTALL_KEY: "wrong_install_key"
        }
        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Wrong install key")

        install_data = {
            "password": PASSWORD_JAAQL,
            "use_mfa": False,
            KEY_INSTALL_KEY: self.fetch_install_key(),
            "allow_uninstall": True
        }

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Correct install key")
        self.assertEqual(None, resp.json()[KEY__jaaql_otp_uri], "Otp URI missing")
        self.assertEqual(None, resp.json()[KEY__jaaql_otp_qr], "Otp QR missing")
        self.assertEqual(None, resp.json()[KEY__superjaaql_otp_uri], "Superjaaql OTP URI missing")
        self.assertEqual(None, resp.json()[KEY__superjaaql_otp_qr], "Superjaaql OTP QR missing")

        time.sleep(20)
        wait_for_service()

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Already installed")

        resp = self.get_jaaql_auth_header(run_test=False)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "JAAQL can login")
        resp = self.get_jaaql_auth_header(password="thewrongpassword", run_test=False)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Jaaql can't login with the incorrect password")
        resp = self.get_jaaql_auth_header(username="superjaaql", password=PASSWORD_SUPERJAAQL, run_test=False)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Superjaaql can't login")

        resp = requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data("wrong password", self.fetch_uninstall_key()))
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Uninstall was unsuccessful, wrong db password")
        resp = requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password], "wrong uninstall key"))
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Uninstall was unsuccessful, wrong uninstall key")
        resp = requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password],
                                                                                              self.fetch_uninstall_key()))
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Uninstall was successful")

        time.sleep(20)
        wait_for_service()

        resp = requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password],
                                                                                              self.fetch_uninstall_key()))
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Not yet installed, after uninstall")

    def run_test_install_mfa(self):
        install_data = {
            "password": PASSWORD_JAAQL,
            "use_mfa": True,
            KEY_INSTALL_KEY: self.fetch_install_key(),
            "allow_uninstall": True
        }

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Correct install key")
        self.assertEqual(True, resp.json()[KEY__jaaql_otp_uri] is not None, "Otp URI present")
        self.assertEqual(True, resp.json()[KEY__jaaql_otp_qr] is not None, "Otp QR present")
        self.assertEqual(None, resp.json()[KEY__superjaaql_otp_uri], "Superjaaql OTP URI missing")
        self.assertEqual(None, resp.json()[KEY__superjaaql_otp_qr], "Superjaaql OTP QR missing")
        otp_uri = resp.json()[KEY__jaaql_otp_uri]

        time.sleep(20)
        wait_for_service()

        self.assertEqual(otp_uri, self.decode_b64_qr(resp.json()[KEY__jaaql_otp_qr]), "QR decodes jaaql")
        resp = self.get_jaaql_auth_header(run_test=False)
        self.assertEqual(HTTPStatus.ACCEPTED, resp.status_code, "Pre auth check")
        resp_app = requests.get(BASE_URL + "/applications", headers={HEADER_AUTH: resp.json()})
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp_app.status_code, "Pre auth denied")
        resp_mfa = requests.post(BASE_URL + "/oauth/token", json={"mfa_key": "123456", "pre_auth_key": resp.json()})
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp_mfa.status_code, "Wrong MFA key")
        gen_mfa_key = self.gen_mfa_key(otp_uri)
        resp_mfa = requests.post(BASE_URL + "/oauth/token", json={"mfa_key": gen_mfa_key, "pre_auth_key": resp.json()})
        self.assertEqual(HTTPStatus.OK, resp_mfa.status_code, "Correct MFA key")
        resp = self.get_jaaql_auth_header(run_test=False)
        resp = requests.post(BASE_URL + "/oauth/token", json={"mfa_key": gen_mfa_key, "pre_auth_key": resp.json()})
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Cannot reuse mfa key")

        requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password], self.fetch_uninstall_key()))
        time.sleep(20)
        wait_for_service()

        install_data = {
            "password": PASSWORD_JAAQL,
            "superjaaql_password": PASSWORD_SUPERJAAQL,
            "use_mfa": True,
            KEY_INSTALL_KEY: self.fetch_install_key(),
            "allow_uninstall": True
        }

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Correct install key")
        self.assertEqual(True, resp.json()[KEY__jaaql_otp_uri] is not None, "Otp URI present")
        self.assertEqual(True, resp.json()[KEY__jaaql_otp_qr] is not None, "Otp QR present")
        self.assertEqual(True, resp.json()[KEY__superjaaql_otp_uri] is not None, "Superjaaql OTP URI present")
        self.assertEqual(True, resp.json()[KEY__superjaaql_otp_qr] is not None, "Superjaaql OTP QR present")
        otp_uri = resp.json()[KEY__superjaaql_otp_uri]

        time.sleep(20)
        wait_for_service()

        self.assertEqual(otp_uri, self.decode_b64_qr(resp.json()[KEY__superjaaql_otp_qr]), "QR decodes superjaaql")
        resp = self.get_jaaql_auth_header(username="superjaaql", password=PASSWORD_SUPERJAAQL, run_test=False)
        self.assertEqual(HTTPStatus.ACCEPTED, resp.status_code, "Pre auth check")
        gen_mfa_key = self.gen_mfa_key(otp_uri)
        resp_mfa = requests.post(BASE_URL + "/oauth/token", json={"mfa_key": gen_mfa_key, "pre_auth_key": resp.json()})
        self.assertEqual(HTTPStatus.OK, resp_mfa.status_code, "Correct MFA key")

        requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password], self.fetch_uninstall_key()))
        time.sleep(20)
        wait_for_service()

    def run_test_install_superjaaql(self):
        install_data = {
            "password": PASSWORD_JAAQL,
            "superjaaql_password": PASSWORD_SUPERJAAQL,
            "use_mfa": False,
            KEY_INSTALL_KEY: self.fetch_install_key()
        }

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(None, resp.json()[KEY__jaaql_otp_uri], "Otp URI missing")
        self.assertEqual(None, resp.json()[KEY__jaaql_otp_qr], "Otp QR missing")
        self.assertEqual(None, resp.json()[KEY__superjaaql_otp_uri], "Superjaaql OTP URI missing")
        self.assertEqual(None, resp.json()[KEY__superjaaql_otp_qr], "Superjaaql OTP QR missing")

        time.sleep(20)
        wait_for_service()

        resp = self.get_jaaql_auth_header(run_test=False)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "JAAQL can login")
        resp = self.get_jaaql_auth_header(password="thewrongpassword", run_test=False)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Jaaql can't login with the incorrect password")
        resp = self.get_jaaql_auth_header(username="superjaaql", password=PASSWORD_SUPERJAAQL, run_test=False)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Superjaaql can login")
        resp = self.get_jaaql_auth_header(username="superjaaql", password="wrongsuperjaaqlpassword", run_test=False)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Superjaaql can't login with the incorrect password")

        resp = requests.post(BASE_INTERNAL_URL + PATH_UNINSTALL, json=self.get_uninstall_data(os.environ[PG_ENV__password],
                                                                                              self.fetch_uninstall_key()))
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Uninstall not allowed")

    def fetch_install_key(self):
        install_key = None
        with open("log/gunicorn.log", "r") as log_handle:
            install_key = log_handle.read().split("INSTALL KEY: ")[-1].split("\n")[0].strip()
        return install_key

    def fetch_uninstall_key(self):
        uninstall_key = ""
        with open("log/gunicorn.log", "r") as log_handle:
            try:
                uninstall_key = log_handle.read().split("UNINSTALL KEY: ")[-1].split("\n")[0].strip()
            except:
                pass
        return uninstall_key

    def decode_b64_qr(self, b64_qr: str):
        qr = b64d(b64_qr.split(HTML__base64_png)[1].encode("ASCII"))
        qr = Image.open(BytesIO(qr))
        return decode(qr, symbols=[ZBarSymbol.QRCODE])[0].data.decode("ASCII")

    def gen_mfa_key(self, otp_uri: str):
        totp_iv = otp_uri.split("secret=")[1].split("&")[0]
        return pyotp.TOTP(totp_iv).now()
