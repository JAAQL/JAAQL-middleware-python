from .base_component import *
import requests
from jaaql.constants import *


class ApplicationComponent(BaseComponent):

    def test_application_endpoints(self):
        auth_header = {HEADER_AUTH: self.get_jaaql_auth_header()}
        self.run_test_create_application(auth_header)
        self.run_test_update_application(auth_header)
        self.run_test_delete_application(auth_header)
        self.run_test_fetch_applications(auth_header)

    def run_test_create_application(self, auth_header):
        resp = requests.post(BASE_INTERNAL_URL + "/applications", json={
            "name": "CTP-App",
            "description": "The CTP App",
            "url": "apps/ctp",
            "public_username": "ctp_app"
        }, headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Create app")
        resp = requests.get(BASE_URL + "/applications/public-user?application=CTP-App")
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Fetch public user")
        resp = self.get_jaaql_auth_header("ctp_app", resp.json()[KEY__password], run_test=False)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Login public user account")

        requests.post(BASE_INTERNAL_URL + "/applications", json={
            "name": "App1",
            "description": "The app called 1",
            "url": "apps/app1"
        }, headers=auth_header)
        resp = requests.get(BASE_URL + "/applications/public-user?application=App1")
        self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, resp.status_code, "Fail fetching non-existent public user")

        requests.post(BASE_INTERNAL_URL + "/applications", json={
            "name": "App2",
            "description": "The app called 2",
            "url": "apps/app2"
        }, headers=auth_header)

    def run_test_update_application(self, auth_header):
        resp = requests.put(BASE_INTERNAL_URL + "/applications", json={
            "name": "App1",
            "new_name": "App1Updated",
            "new_description": "App 1 but updated",
            "new_url": "{{DEFAULT}}/app1"
        }, headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Update application")

    def run_test_delete_application(self, auth_header):
        resp = requests.delete(BASE_INTERNAL_URL + "/applications?name=App2", headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Deletion first step")
        resp = requests.post(BASE_INTERNAL_URL + "/applications/confirm-deletion", json=resp.json(), headers=auth_header)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Deletion second step")

    def run_test_fetch_applications(self, auth_header):
        resp = requests.get(BASE_INTERNAL_URL + "/applications?sort=name%20ASC", headers=auth_header)
        data = resp.json()[KEY__data]
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Returned applications")

        self.assertEqual(5, len(data), "Records returned count")

        self.assertEqual("App1Updated", data[0][KEY__application_name], "Match second name")
        self.assertEqual("App 1 but updated", data[0][KEY__description], "Match second description")
        self.assertEqual("http://127.0.0.1/apps/app1", data[0][KEY__application_url], "Match second url")
        self.assertEqual("CTP-App", data[2][KEY__application_name], "Match first name")
        self.assertEqual("The CTP App", data[2][KEY__description], "Match first description")
        self.assertEqual("apps/ctp", data[2][KEY__application_url], "Match first url")
