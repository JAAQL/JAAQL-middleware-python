from .base_component import *


class DatabaseComponent(BaseComponent):

    def test_database(self):
        default_auth = self.get_jaaql_auth_header_dict()
        self.run_test_add_database(default_auth)
        self.run_test_delete_database(default_auth)
        self.run_test_fetch_databases(default_auth)

    def run_test_add_database(self, default_auth: str):
        superjaaql_auth = self.get_jaaql_auth_header_dict("superjaaql", PASSWORD_SUPERJAAQL)
        resp = requests.post(BASE_INTERNAL_URL + "/databases", headers=superjaaql_auth, json={
            KEY__database_name: "ctp_db",
            KEY__node: "host",
            KEY__create: True
        })
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Can create the database")

        resp = requests.post(BASE_INTERNAL_URL + "/databases", headers=default_auth, json={
            KEY__database_name: "test_db_1",
            KEY__node: "host"
        })
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Can create the database, no actual create")

        resp = requests.post(BASE_INTERNAL_URL + "/databases", headers=default_auth, json={
            KEY__database_name: "test_db_2",
            KEY__node: "host",
            KEY__create: True
        })
        self.assertEqual(HTTPStatus.BAD_REQUEST, resp.status_code, "Can't create the database, lacking perms")

        resp = requests.post(BASE_INTERNAL_URL + "/databases", headers=superjaaql_auth, json={
            KEY__database_name: "test_db_3",
            KEY__node: "host",
            KEY__create: True
        })
        self.assertEqual(HTTPStatus.OK, resp.status_code, "DB Created")

    def run_test_delete_database(self, default_auth: str):
        resp = requests.delete(BASE_INTERNAL_URL + "/databases?node=host&name=test_db_1", headers=default_auth)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Fetched drop key")
        resp = requests.post(BASE_INTERNAL_URL + "/databases/confirm-deletion", headers=default_auth, json=resp.json())
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Can drop the DB, no actual drop")

        resp = requests.delete(BASE_INTERNAL_URL + "/databases?node=host&name=test_db_2&drop=true", headers=default_auth)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Fetched drop key")
        resp = requests.post(BASE_INTERNAL_URL + "/databases/confirm-deletion", headers=default_auth, json=resp.json())
        self.assertEqual(HTTPStatus.BAD_REQUEST, resp.status_code, "Can't drop the DB. No perms")

        superjaaql_auth = self.get_jaaql_auth_header_dict("superjaaql", PASSWORD_SUPERJAAQL)
        resp = requests.delete(BASE_INTERNAL_URL + "/databases?node=host&name=test_db_3&drop=true", headers=superjaaql_auth)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Fetched second drop key")
        resp = requests.post(BASE_INTERNAL_URL + "/databases/confirm-deletion", headers=superjaaql_auth, json=resp.json())
        self.assertEqual(HTTPStatus.OK, resp.status_code, "DB Dropped")

    def run_test_fetch_databases(self, default_auth: str):
        resp = requests.get(BASE_INTERNAL_URL + "/databases?sort=name%20ASC", headers=default_auth)
        self.assertEqual(HTTPStatus.OK, resp.status_code, "Fetched databases")
        data = resp.json()[KEY__data]
        self.assertEqual(3, len(data), "Expected number of databases")
        self.assertEqual(None, data[1][ATTR__deleted], "Isn't deleted")
        self.assertEqual("ctp_db", data[1][KEY__application_name], "Correct name")
        self.assertEqual("host", data[1][KEY__node], "Correct node")
