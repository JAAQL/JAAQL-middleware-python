from .base_component import *
import requests
from jaaql.constants import *


class ApplicationComponent(BaseComponent):

    def test_application_endpoints(self):
        auth_header = {HEADER_AUTH: self.get_jaaql_auth_header()}
        self.test_create_application(auth_header)
        self.test_update_application(auth_header)
        self.test_fetch_applications(auth_header)
        self.test_delete_application(auth_header)

    def test_create_application(self, auth_header):
        resp = requests.post(BASE_INTERNAL_URL + "/applications", json={
            "name": "CTP-App",
            "description": "The CTP App",
            "url": "apps/ctp",
            "public_username": "ctp_app"
        }, headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Create app successful")
        resp = requests.get(BASE_URL + "/applications/public-user")
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Fetch public user successful")
        resp = self.get_jaaql_auth_header("ctp_app", resp.json()[KEY__password])
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Login public user account successful")

        requests.post(BASE_INTERNAL_URL + "/applications", json={
            "name": "App1",
            "description": "The app called 1",
            "url": "apps/app1"
        }, headers=auth_header)
        resp = requests.get(BASE_URL + "/applications/public-user")
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Fetch non-existent public user failing")

        requests.post(BASE_INTERNAL_URL + "/applications", json={
            "name": "App2",
            "description": "The app called 2",
            "url": "apps/app2"
        }, headers=auth_header)

    def test_update_application(self, auth_header):
        resp = requests.put(BASE_INTERNAL_URL + "/applications", json={
            "name": "App1",
            "new_name": "App1Updated",
            "new_description": "App 1 but updated",
            "new_url": "{{DEFAULT_URL}}/app1"
        }, headers=auth_header)
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Update application successful")

    def test_delete_application(self, auth_header):
        resp = requests.delete(BASE_INTERNAL_URL + "/applications", json={
            "name": "App2"
        }, headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Deletion first step")
        resp = requests.delete(BASE_INTERNAL_URL + "/applications/confirm-deletion", json=resp.json(), headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Deletion second step")

    def test_fetch_applications(self, auth_header):
        resp = requests.get(BASE_INTERNAL_URL + "/applications?sort=name%20ASC", headers=auth_header)
        data = resp.json()[KEY__data]
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Returned applications")
        self.assertEqual(2, len(data), "Records returned count")

        self.assertEqual("CTP-App", data[0][KEY__application_name])
        self.assertEqual("The CTP App", data[0][KEY__application_description])
        self.assertEqual("apps/ctp", data[0][KEY__application_url])
        self.assertEqual("App1Updated", data[1][KEY__application_name])
        self.assertEqual("App 1 but updated", data[1][KEY__application_description])
        self.assertEqual("http://127.0.0.1/app1", data[1][KEY__application_url])
