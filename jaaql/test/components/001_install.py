from .base_component import *

KEY_INSTALL_KEY = "install_key"
PATH_INSTALL = "/install"


class InstallComponent(BaseComponent):

    def test_install(self):
        install_data = {
          "password": PASSWORD_JAAQL,
          "use_mfa": False,
          KEY_INSTALL_KEY: "the wrong install key",
          "superjaaql_password": PASSWORD_SUPERJAAQL
        }

        install_key = None
        with open("log/gunicorn.log", "r") as log_handle:
            install_key = log_handle.read().split("INSTALL KEY: ")[1].split("\n")[0].strip()

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status_code, "Wrong install key expected")

        install_data[KEY_INSTALL_KEY] = install_key
        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Correct install key")

        time.sleep(20)

        wait_for_service()

        resp = requests.post(BASE_INTERNAL_URL + PATH_INSTALL, json=install_data)
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Already installed expected")
