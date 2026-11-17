"""
A rendered document (POST /documents) is kept 5 minutes after it completed, as the route's documentation says, and then the email
service's purge loop deletes its row from document_request (the PDF, its encrypted access token and its parameters) and, for a
create_file document, its file under www/rendered_documents. A document that completed less than 5 minutes ago, or that has not been
rendered yet, stays.

    python -m unittest jaaql.test.test_rendered_document_purge

It runs one pass of the real DrivenChrome.purge_rendered_documents through a DBPGInterface against document_template and document_request
as the jaaql install creates them (01.install_domains and the two tables from 04.install_jaaql_data_structures) on a scratch Postgres;
it runs only when JAAQL_TEST_POSTGRES_URI is set to postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops,
the database jaaql_test_documents. All documents here are synthetic
"""
import os
import re
import shutil
import tempfile
import unittest
from os.path import dirname, join
from types import SimpleNamespace
from unittest import mock

import psycopg

from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface
from jaaql.email import email_manager_service
from jaaql.email.email_manager_service import DrivenChrome

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_documents"
CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}
SCRIPTS = join(dirname(dirname(__file__)), "scripts")
APPLICATION = "docs-app"
TEMPLATE = "invoice"


def install_script(name):
    with open(join(SCRIPTS, name), encoding="utf-8") as file:
        return file.read()


def table_definition(script, table):
    return re.search(r"create table " + table + r" \(.*?\);", script, re.DOTALL).group(0)


class EndOfPass(Exception):
    pass


def end_of_pass(_seconds):
    raise EndOfPass()


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), "set " + ENVIRON__test_postgres_uri + " to run against a scratch Postgres")
class TestPurgeRenderedDocuments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
        address, port, _, cls.pool_user, password = DBInterface.fracture_uri(uri)
        cls.test_uri = uri.rsplit("/", 1)[0] + "/" + TEST_DATABASE
        with psycopg.connect(uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("CREATE DATABASE " + TEST_DATABASE)
        structures = install_script("04.install_jaaql_data_structures.generated.sql")
        with psycopg.connect(cls.test_uri, autocommit=True) as conn:
            conn.execute(install_script("01.install_domains.generated.sql"))
            conn.execute(table_definition(structures, "document_template"))
            conn.execute(table_definition(structures, "document_request"))
            conn.execute("INSERT INTO document_template (application, name, content_path) VALUES (%s, %s, 'invoice/print')",
                         (APPLICATION, TEMPLATE))
        cls.lookup = create_interface(CONFIG, address, int(port), TEST_DATABASE, cls.pool_user, password=password)

    @classmethod
    def tearDownClass(cls):
        pool = DBPGInterface.HOST_POOLS.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        DBPGInterface.HOST_POOLS_QUEUES.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        if pool is not None:
            pool.close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")

    def setUp(self):
        self.admin("TRUNCATE document_request")
        self.rendered_documents = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.rendered_documents)

    def admin(self, sql, params=None):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def document(self, completed_ago, create_file=False):
        completed = None if completed_ago is None else "now() - interval '" + completed_ago + "'"
        document_id = str(self.admin(
            "INSERT INTO document_request (application, template, request_timestamp, encrypted_access_token, encrypted_parameters, "
            "create_file, file_name, content, completed) VALUES (%s, %s, now() - interval '1 day', 'encrypted-token', 'encrypted-parameters', "
            "%s, 'invoice.pdf', %s, " + ("NULL" if completed is None else completed) + ") RETURNING uuid",
            (APPLICATION, TEMPLATE, create_file, None if create_file else b"%PDF-1.7"))[0][0])
        if create_file and completed_ago is not None:
            with open(self.file_of(document_id), "wb") as file:
                file.write(b"%PDF-1.7")
        return document_id

    def file_of(self, document_id):
        return join(self.rendered_documents, document_id + ".pdf")

    def purge_once(self):
        chrome = DrivenChrome.__new__(DrivenChrome)
        chrome.db_interface = self.lookup
        chrome.template_dir_path = self.rendered_documents
        with mock.patch.object(email_manager_service, "time", SimpleNamespace(sleep=end_of_pass)):
            with self.assertRaises(EndOfPass):
                chrome.purge_rendered_documents()

    def kept(self):
        return {str(row[0]) for row in self.admin("SELECT uuid FROM document_request")}

    def test_documents_completed_over_5_minutes_ago_are_deleted_with_their_files(self):
        self.document("6 minutes")
        old_file = self.document("6 minutes", create_file=True)
        self.document("400 days")
        young_content = self.document("4 minutes")
        young_file = self.document("4 minutes", create_file=True)
        unrendered = self.document(None)
        unrendered_file = self.document(None, create_file=True)

        self.purge_once()

        self.assertEqual({young_content, young_file, unrendered, unrendered_file}, self.kept())
        self.assertFalse(os.path.exists(self.file_of(old_file)))
        self.assertTrue(os.path.exists(self.file_of(young_file)))

    def test_a_document_goes_once_its_5_minutes_are_over(self):
        document_id = self.document("4 minutes 50 seconds", create_file=True)
        self.purge_once()
        self.assertEqual({document_id}, self.kept())

        self.admin("UPDATE document_request SET completed = now() - interval '5 minutes 10 seconds'")
        self.purge_once()
        self.assertEqual(set(), self.kept())
        self.assertFalse(os.path.exists(self.file_of(document_id)))

    def test_a_file_already_gone_does_not_stop_the_purge(self):
        gone = self.document("10 minutes", create_file=True)
        os.remove(self.file_of(gone))
        after_it = self.document("10 minutes", create_file=True)

        self.purge_once()

        self.assertEqual(set(), self.kept())
        self.assertFalse(os.path.exists(self.file_of(after_it)))


if __name__ == "__main__":
    unittest.main()
