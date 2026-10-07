"""
A database named by the request (a request without an application, /domains, /prepare) and the connection string built for it.

    python -m unittest jaaql.test.test_requested_database

Needs only the package's requirements: connections, pools and the vault are replaced, so no database is reached
"""
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

from psycopg.conninfo import conninfo_to_dict

from jaaql.constants import DB__jaaql
from jaaql.db import db_pg_interface, db_utils_no_circ
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import requested_database
from jaaql.db.db_utils_no_circ import get_required_db
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel

CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}

NAMES__plain = ["database", "jaaql", "postgres", "jaaql_test_lifecycle", "x" * 63]
NAMES__unsafe = ["x host=attacker.example", "x host=attacker.example port=5433", "database options='-csession_replication_role=replica'",
                 "dbname=x", "x' host='y", "database\n", " database", "", "x" * 64, "my-app", "a.b"]


class TestRequestedDatabase(unittest.TestCase):

    def test_plain_names_are_accepted(self):
        for name in NAMES__plain:
            self.assertEqual(name, requested_database(name))

    def test_anything_else_is_refused(self):
        for name in NAMES__unsafe + [None, 1, ["database"], {"dbname": "x"}]:
            with self.subTest(name=name):
                with self.assertRaises(HttpStatusException) as caught:
                    requested_database(name)
                self.assertEqual(HTTPStatus.UNPROCESSABLE_ENTITY, caught.exception.response_code)


class TestGetRequiredDb(unittest.TestCase):

    def required_db(self, inputs):
        with mock.patch.object(db_utils_no_circ, "create_interface_for_db", return_value="interface") as created:
            result = get_required_db(None, CONFIG, None, inputs, "account")
        return result, created

    def test_a_request_naming_an_unsafe_database_never_connects(self):
        for name in NAMES__unsafe:
            with self.subTest(name=name):
                with mock.patch.object(db_utils_no_circ, "create_interface_for_db") as created:
                    with self.assertRaises(HttpStatusException):
                        get_required_db(None, CONFIG, None, {"database": name, "query": "SELECT 1"}, "account")
                created.assert_not_called()

    def test_a_plain_database_is_connected_to(self):
        result, created = self.required_db({"database": "postgres", "query": "SELECT 1"})
        self.assertEqual("interface", result)
        self.assertEqual("postgres", created.call_args.args[3])

    def test_no_application_and_no_database_is_the_jaaql_database(self):
        _, created = self.required_db({"query": "SELECT 1"})
        self.assertEqual(DB__jaaql, created.call_args.args[3])


class FakePool:

    def __init__(self, conninfo, **kwargs):
        self.conninfo = conninfo
        FakePool.made.append(self)

    def getconn(self, timeout=None):
        return None

    def close(self):
        pass


class TestConnectionString(unittest.TestCase):

    def conninfo(self, host, port, db_name, password):
        FakePool.made = []
        user = "jaaql_test_conninfo_user"
        try:
            with mock.patch.object(db_pg_interface, "ConnectionPool", FakePool), mock.patch.object(db_pg_interface.threading, "Thread"):
                DBPGInterface(CONFIG, host, port, db_name, user, password=password)
        finally:
            DBPGInterface.HOST_POOLS.pop(user, None)
            DBPGInterface.HOST_POOLS_QUEUES.pop(user, None)
        self.assertEqual(1, len(FakePool.made))
        return conninfo_to_dict(FakePool.made[0].conninfo)

    def test_a_database_name_cannot_add_settings(self):
        for db_name in NAMES__unsafe[:5]:
            with self.subTest(db_name=db_name):
                parsed = self.conninfo("localhost", 5432, db_name, "secret")
                self.assertEqual({"keepalives": "1", "keepalives_idle": "10", "keepalives_interval": "5", "keepalives_count": "3",
                                  "user": "jaaql_test_conninfo_user", "password": "secret", "dbname": db_name}, parsed)

    def test_a_password_with_spaces_and_quotes_stays_one_value(self):
        self.assertEqual("p w'x \\ host=y", self.conninfo("localhost", 5432, "database", "p w'x \\ host=y")["password"])

    def test_a_remote_host_and_another_port_are_kept(self):
        parsed = self.conninfo("db.example", 5435, "database", "secret")
        self.assertEqual(("db.example", "5435", "database"), (parsed["host"], parsed["port"], parsed["dbname"]))

    def test_localhost_on_the_default_port_names_neither(self):
        parsed = self.conninfo("127.0.0.1", 5432, "database", "secret")
        self.assertNotIn("host", parsed)
        self.assertNotIn("port", parsed)


class TestDbaEndpoints(unittest.TestCase):

    def test_domains_and_prepare_refuse_an_unsafe_database_before_connecting(self):
        stub = SimpleNamespace(vault=None, config=CONFIG, is_dba=lambda connection: None)
        for method in [JAAQLModel.fetch_domains, JAAQLModel.prepare_queries]:
            with self.subTest(method=method.__name__):
                with mock.patch.object(model, "create_interface_for_db") as created:
                    with self.assertRaises(HttpStatusException):
                        method(stub, {"database": "x host=attacker.example", "queries": []}, "account")
                created.assert_not_called()


if __name__ == "__main__":
    unittest.main()
