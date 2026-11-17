"""
A dispatcher sends from its from_address when it has one, and otherwise from its username, the address JAAQL always sent from: a transactional
mail service logs in with a generated username that is not an address. The From header is the display name, or the email's
override_send_name, with that address, made by email.utils.formataddr, and the envelope's MAIL FROM is that address too, where it used to be
the display name (MAIL FROM:<LesBij>). The SMTP login stays username and password. POST /internal/dispatchers takes from_address as an
optional argument, so a request without it, as jaaql-monitor sends for a credentials file of three lines, works as before and leaves the
stored value as it is. When the 15-second reload brings a dispatcher with other settings, its thread closes the connection it still has open
with the old login and logs in again before the next email, where it used to send over the old connection for as long as the server kept it.

    python -m unittest jaaql.test.test_email_from_address

The unit tests need only the package's requirements: SMTP is a mock or a stub server on 127.0.0.1 that records the login and the envelope.
TestDispatcherFromAddressAgainstPostgres runs the generated email_dispatcher queries against the install DDL, and the 4.33.13 migration against
a table that has the column and one that has not; it runs only when JAAQL_TEST_POSTGRES_URI is set to
postgresql://<superuser>:<password>@<host>:<port>/<database> and creates, then drops, the database jaaql_test_from_address
"""
import base64
import contextlib
import email as email_parser
import functools
import io
import os
import re
import smtplib
import socketserver
import threading
import unittest
from email import policy
from email.utils import make_msgid
from os.path import join
from queue import Queue
from types import SimpleNamespace
from unittest import mock

import psycopg

from jaaql.db.db_interface import DBInterface
from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.db.db_utils import create_interface
from jaaql.documentation.documentation_internal import DOCUMENTATION__dispatchers
from jaaql.email import email_manager_service
from jaaql.email.email_manager_service import Email, EmailManagerService, ParameterisedLock, ThreadsafeQueueInitialiser
from jaaql.mvc import generated_queries
from jaaql.mvc.base_controller import BaseJAAQLController
from jaaql.mvc.generated_queries import *
from jaaql.mvc.model import JAAQLModel
from jaaql.utilities.utils import get_jaaql_root

ENVIRON__test_postgres_uri = "JAAQL_TEST_POSTGRES_URI"
TEST_DATABASE = "jaaql_test_from_address"
CONFIG = {"DEBUG": {"output_query_exceptions": "false"}, "DATABASE": {"interface": "postgres"}, "SYSTEM": {"logging": False}}
CRYPT_KEY = b"k" * 32

APPLICATION = "lesbij"
DISPATCHER = "default"
DISPATCHER_KEY = APPLICATION + ":" + DISPATCHER
FROM_ADDRESS = "no-reply@relay-systems.com"
MAILBOX_LOGIN = "no-reply@relay-systems.com"
SERVICE_LOGIN = "tes-7f3c9a2b"
PASSWORD = "not-a-real-password"


MESSAGE_ID = mock.patch.object(email_manager_service, "make_msgid", functools.partial(make_msgid, domain="jaaql.test"))


def setUpModule():
    # make_msgid looks up the host's FQDN for every message, which takes a second on some Windows machines
    MESSAGE_ID.start()


def tearDownModule():
    MESSAGE_ID.stop()


def dispatcher(username: str, **extra) -> dict:
    # A row of email_dispatcher as email_dispatcher__select_all returns it (password decrypted)
    info = {
        KG__email_dispatcher__application: APPLICATION,
        KG__email_dispatcher__name: DISPATCHER,
        KG__email_dispatcher__display_name: "LesBij",
        KG__email_dispatcher__protocol: None,
        KG__email_dispatcher__url: "send.simplemailservice.eu",
        KG__email_dispatcher__port: 587,
        KG__email_dispatcher__username: username,
        KG__email_dispatcher__password: PASSWORD,
        KG__email_dispatcher__whitelist: None
    }
    info.update(extra)
    return info


def an_email(to="ann@example.com", **kwargs) -> Email:
    return Email(APPLICATION, "template", DISPATCHER, to, "Your lesson", "<p>See you on Monday</p>", **kwargs)


def a_service(is_gunicorn: bool = True) -> EmailManagerService:
    # Without __init__, which starts the dispatcher manager thread and Chrome
    service = EmailManagerService.__new__(EmailManagerService)
    service.is_gunicorn = is_gunicorn
    service.driven_chrome = None
    service.dispatchers = {}
    service.dispatcher_blacklist = {}
    service.parameterised_lock = ParameterisedLock()
    service.threadsafe_queue_initialiser = ThreadsafeQueueInitialiser()
    return service


class StubSMTP:
    """
    An SMTP server on 127.0.0.1 that offers AUTH PLAIN and no STARTTLS and records each login and each message's envelope and data. on_message
    runs before a message's 250 reply, so a sender that waits for that reply sees the message recorded
    """

    def __init__(self):
        self.logins = []
        self.messages = []
        self.connections = []
        self.on_message = None
        stub = self

        class Handler(socketserver.StreamRequestHandler):
            def reply(self, text):
                self.wfile.write((text + "\r\n").encode("ascii"))

            def handle(self):
                envelope = {"mail_from": None, "rcpt_to": []}
                self.reply("220 stub ESMTP")
                for line in self.rfile:
                    command = line.decode("ascii").rstrip("\r\n")
                    verb = command.split(" ", 1)[0].upper()
                    if verb == "EHLO":
                        self.reply("250-stub")
                        self.reply("250 AUTH PLAIN")
                    elif verb == "AUTH":
                        _, user, password = base64.b64decode(command.split(" ")[2]).decode("utf-8").split("\0")
                        stub.logins.append((user, password))
                        self.reply("235 2.7.0 Authentication successful")
                    elif verb == "MAIL":
                        envelope["mail_from"] = command[len("MAIL FROM:"):]
                        self.reply("250 OK")
                    elif verb == "RCPT":
                        envelope["rcpt_to"].append(command[len("RCPT TO:"):])
                        self.reply("250 OK")
                    elif verb == "DATA":
                        self.reply("354 End data with <CR><LF>.<CR><LF>")
                        data = []
                        for data_line in self.rfile:
                            if data_line == b".\r\n":
                                break
                            data.append(data_line)
                        envelope["message"] = email_parser.message_from_bytes(b"".join(data), policy=policy.default)
                        stub.messages.append(envelope)
                        envelope = {"mail_from": None, "rcpt_to": []}
                        if stub.on_message is not None:
                            stub.on_message()
                        self.reply("250 OK")
                    elif verb == "QUIT":
                        self.reply("221 Bye")
                        return
                    else:
                        self.reply("250 OK")

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            block_on_close = False

        self.server = Server(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        for connection in self.connections:
            connection.close()
        self.server.shutdown()
        self.server.server_close()

    def smtp_class(self):
        # Stands in for smtplib.SMTP in email_manager_service: whatever host it is given, it connects to the stub, and STARTTLS is a no-op
        stub_port = self.port
        connections = self.connections

        class StubbedSMTP(smtplib.SMTP):
            def __init__(self, host="", port=0, timeout=30, **kwargs):
                super().__init__("127.0.0.1", port=stub_port, timeout=10)
                connections.append(self)

            def starttls(self, *args, **kwargs):
                return 220, b"Ready to start TLS"

        return StubbedSMTP


class TestFromHeader(unittest.TestCase):

    def from_header(self, info: dict, **email_kwargs):
        _, message = a_service().construct_message(info, an_email(**email_kwargs))
        return message[email_manager_service.EMAIL__from]

    def test_without_from_address_the_username_is_the_address(self):
        # A row read before the 4.33.13 migration has no from_address key at all
        self.assertEqual("LesBij <" + MAILBOX_LOGIN + ">", self.from_header(dispatcher(MAILBOX_LOGIN)))
        self.assertEqual("LesBij <" + MAILBOX_LOGIN + ">", self.from_header(dispatcher(MAILBOX_LOGIN, from_address=None)))
        self.assertEqual("LesBij <" + MAILBOX_LOGIN + ">", self.from_header(dispatcher(MAILBOX_LOGIN, from_address="")))

    def test_from_address_replaces_the_username(self):
        self.assertEqual("LesBij <" + FROM_ADDRESS + ">", self.from_header(dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS)))

    def test_override_send_name_keeps_the_from_address(self):
        self.assertEqual("Hoogewierde <" + FROM_ADDRESS + ">",
                         self.from_header(dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS), override_send_name="Hoogewierde"))

    def test_display_names_are_quoted_and_encoded(self):
        header = self.from_header(dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS, display_name="Relay, Systems"))
        self.assertEqual('"Relay, Systems" <' + FROM_ADDRESS + ">", header)
        header = self.from_header(dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS, display_name="Leerlingbijles Één"))
        self.assertTrue(header.isascii(), header)
        parsed = email_parser.message_from_string("From: " + header + "\n\n", policy=policy.default)["From"].addresses[0]
        self.assertEqual(("Leerlingbijles Één", FROM_ADDRESS), (parsed.display_name, parsed.addr_spec))


class TestEnvelope(unittest.TestCase):

    def test_envelope_sender_is_the_sender_address(self):
        for info, expected in [(dispatcher(MAILBOX_LOGIN), MAILBOX_LOGIN),
                               (dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS), FROM_ADDRESS)]:
            conn = mock.Mock()
            a_service().send_email_with_connection(conn, an_email(), DISPATCHER_KEY, info)
            message, from_addr, to_addrs = conn.send_message.call_args[0]
            self.assertEqual(expected, from_addr)
            self.assertEqual(["ann@example.com"], to_addrs)
            self.assertEqual("LesBij <" + expected + ">", message[email_manager_service.EMAIL__from])

    def test_whitelist_still_filters_recipients(self):
        conn = mock.Mock()
        info = dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS, whitelist="*@example.com, bob@elsewhere.org")
        recipients = ["ann@example.com", "carl@elsewhere.org", "bob+test@elsewhere.org"]
        with mock.patch.dict(os.environ, {"JAAQL_USE_EMAIL_WHITELIST": "TRUE"}), contextlib.redirect_stderr(io.StringIO()) as err:
            a_service().send_email_with_connection(conn, an_email(to=recipients, recipient_names=recipients), DISPATCHER_KEY, info)
        message, from_addr, to_addrs = conn.send_message.call_args[0]
        self.assertEqual(FROM_ADDRESS, from_addr)
        self.assertEqual(["ann@example.com", "bob+test@elsewhere.org"], to_addrs)
        self.assertEqual("ann@example.com, bob+test@elsewhere.org", message[email_manager_service.EMAIL__to])
        self.assertIn("'carl@elsewhere.org' rejected by whitelist", err.getvalue())

    def test_outside_gunicorn_the_email_is_printed_with_its_sender(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            a_service(is_gunicorn=False).send_email_with_connection(None, an_email(), DISPATCHER_KEY,
                                                                     dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS))
        self.assertIn("\nLesBij\n" + FROM_ADDRESS + "\n['ann@example.com']\n", out.getvalue())

    def test_login_is_username_and_password(self):
        with mock.patch.object(email_manager_service, "SMTP") as smtp:
            a_service().fetch_conn(DISPATCHER_KEY, "send.simplemailservice.eu", 587, SERVICE_LOGIN, PASSWORD)
        smtp.assert_called_once_with("send.simplemailservice.eu", port=587, timeout=30)
        smtp.return_value.starttls.assert_called_once()
        smtp.return_value.login.assert_called_once_with(SERVICE_LOGIN, PASSWORD)


class TestOnTheWire(unittest.TestCase):
    """
    The dispatcher thread end to end against the stub server: it logs in, sends one queued email and stops once the dispatcher is gone
    """

    def setUp(self):
        self.stub = StubSMTP()
        self.addCleanup(self.stub.close)

    def send(self, *infos: dict):
        # One email per row in turn: once a message is in, the dispatcher becomes the next row, as the manager thread's reload every 15
        # seconds makes it, and the next email is queued; after the last one the dispatcher is gone
        service = a_service()
        queue = Queue()
        service.dispatchers = {DISPATCHER_KEY: (infos[0], queue)}
        queue.put(an_email())

        def on_message():
            if len(self.stub.messages) < len(infos):
                service.dispatchers[DISPATCHER_KEY] = (infos[len(self.stub.messages)], queue)
                queue.put(an_email())
            else:
                service.dispatchers.pop(DISPATCHER_KEY)

        self.stub.on_message = on_message
        with mock.patch.object(email_manager_service, "SMTP", self.stub.smtp_class()):
            thread = threading.Thread(target=service.dispatcher_thread, args=[DISPATCHER_KEY, infos[0]])
            thread.start()
            thread.join(20)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(infos), len(self.stub.messages))
        return self.stub.logins, self.stub.messages

    def send_one(self, info: dict):
        logins, messages = self.send(info)
        return logins, messages[0]

    def test_three_line_credentials_send_from_the_mailbox(self):
        logins, sent = self.send_one(dispatcher(MAILBOX_LOGIN))
        self.assertEqual([(MAILBOX_LOGIN, PASSWORD)], logins)
        self.assertEqual("<" + MAILBOX_LOGIN + ">", sent["mail_from"])
        self.assertEqual(["<ann@example.com>"], sent["rcpt_to"])
        self.assertEqual("LesBij <" + MAILBOX_LOGIN + ">", sent["message"]["From"])

    def test_four_line_credentials_log_in_with_the_username_and_send_from_the_address(self):
        logins, sent = self.send_one(dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS))
        self.assertEqual([(SERVICE_LOGIN, PASSWORD)], logins)
        self.assertEqual("<" + FROM_ADDRESS + ">", sent["mail_from"])
        self.assertEqual(["<ann@example.com>"], sent["rcpt_to"])
        self.assertEqual("LesBij <" + FROM_ADDRESS + ">", sent["message"]["From"])

    def test_a_switched_dispatcher_logs_in_again_before_its_next_email(self):
        # The connection still open from the old login must not carry the first email after the switch
        logins, sent = self.send(dispatcher(MAILBOX_LOGIN, url="mail-server.nl"), dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS))
        self.assertEqual([(MAILBOX_LOGIN, PASSWORD), (SERVICE_LOGIN, PASSWORD)], logins)
        self.assertEqual(["<" + MAILBOX_LOGIN + ">", "<" + FROM_ADDRESS + ">"], [message["mail_from"] for message in sent])
        self.assertEqual(2, len(self.stub.connections))

    def test_an_unchanged_dispatcher_keeps_its_connection(self):
        logins, sent = self.send(dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS), dispatcher(SERVICE_LOGIN, from_address=FROM_ADDRESS))
        self.assertEqual([(SERVICE_LOGIN, PASSWORD)], logins)
        self.assertEqual(["<" + FROM_ADDRESS + ">"] * 2, [message["mail_from"] for message in sent])
        self.assertEqual(1, len(self.stub.connections))


class TestDispatchersRoute(unittest.TestCase):
    """
    POST /internal/dispatchers as the controller validates it and the model stores it
    """

    def attach(self, body: dict):
        BaseJAAQLController.validate_data(DOCUMENTATION__dispatchers.methods[0], body)
        with mock.patch.object(generated_queries, "execute_supplied_statement") as execute:
            JAAQLModel.attach_dispatcher_credentials(SimpleNamespace(get_db_crypt_key=lambda: CRYPT_KEY), None, body)
        query, parameters = execute.call_args[0][1:3]
        self.assertEqual(QG__email_dispatcher_update, query)
        return parameters

    def body(self, **extra):
        body = {"application": APPLICATION, "name": DISPATCHER, "url": "send.simplemailservice.eu", "port": 587, "username": SERVICE_LOGIN,
                "password": PASSWORD}
        body.update(extra)
        return body

    def test_without_from_address_it_is_left_unchanged(self):
        parameters = self.attach(self.body())
        self.assertIn(KG__email_dispatcher__from_address, parameters)
        self.assertIsNone(parameters[KG__email_dispatcher__from_address])
        self.assertEqual(SERVICE_LOGIN, parameters[KG__email_dispatcher__username])
        self.assertIn("from_address = COALESCE(:from_address, from_address)", QG__email_dispatcher_update)

    def test_from_address_is_stored(self):
        parameters = self.attach(self.body(from_address=" " + FROM_ADDRESS + " "))
        self.assertEqual(FROM_ADDRESS, parameters[KG__email_dispatcher__from_address])

    def test_from_address_must_be_a_string(self):
        with self.assertRaises(Exception) as raised:
            BaseJAAQLController.validate_data(DOCUMENTATION__dispatchers.methods[0], self.body(from_address=["a", "b"]))
        self.assertIn("from_address", str(raised.exception))


@unittest.skipUnless(os.environ.get(ENVIRON__test_postgres_uri), ENVIRON__test_postgres_uri + " is not set")
class TestDispatcherFromAddressAgainstPostgres(unittest.TestCase):
    """
    The domains of 01, email_dispatcher as 04 creates it in public, and in schema before_4_33_13 the same table without from_address, as
    every install before 4.33.13 has it
    """

    @classmethod
    def setUpClass(cls):
        uri = os.environ[ENVIRON__test_postgres_uri]
        cls.admin_uri = uri
        address, port, _, cls.pool_user, password = DBInterface.fracture_uri(uri)
        cls.test_uri = uri.rsplit("/", 1)[0] + "/" + TEST_DATABASE
        scripts = join(get_jaaql_root(), "scripts")
        with open(join(scripts, "01.install_domains.generated.sql"), encoding="utf-8") as file:
            domains = file.read()
        with open(join(scripts, "04.install_jaaql_data_structures.generated.sql"), encoding="utf-8") as file:
            table = re.search(r"^create table email_dispatcher \(.*?\);$", file.read(), re.S | re.M).group(0)
        cls.old_table = table.replace("\tfrom_address email_server_username,\n", "")
        assert cls.old_table != table
        with open(join(get_jaaql_root(), "migrations", "scripts", "4.33.13.jaaql"), encoding="utf-8") as file:
            cls.migration = file.read().replace("\\g", "")
        with psycopg.connect(uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")
            admin.execute("CREATE DATABASE " + TEST_DATABASE)
        with psycopg.connect(cls.test_uri, autocommit=True) as conn:
            conn.execute(domains)
            conn.execute(table)
        cls.lookup = create_interface(CONFIG, address, int(port), TEST_DATABASE, cls.pool_user, password=password)

    @classmethod
    def tearDownClass(cls):
        pool = DBPGInterface.HOST_POOLS.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        DBPGInterface.HOST_POOLS_QUEUES.get(cls.pool_user, {}).pop(TEST_DATABASE, None)
        if pool is not None:
            pool.close()
        with psycopg.connect(cls.admin_uri, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS " + TEST_DATABASE + " WITH (FORCE)")

    def admin(self, sql, params=None, schema="public"):
        with psycopg.connect(self.test_uri, autocommit=True) as conn:
            conn.execute("SET search_path TO " + schema + ", public")
            cursor = conn.execute(sql, params)
            return cursor.fetchall() if cursor.description is not None else None

    def from_address_columns(self, schema: str):
        return self.admin("SELECT domain_name, is_nullable FROM information_schema.columns WHERE table_schema = %s AND "
                          "table_name = 'email_dispatcher' AND column_name = 'from_address'", (schema,))

    def test_install_ddl_has_a_nullable_from_address(self):
        self.assertEqual([("email_server_username", "YES")], self.from_address_columns("public"))

    def test_migration_adds_the_column_to_an_old_table_and_can_run_again(self):
        self.admin("DROP SCHEMA IF EXISTS before_4_33_13 CASCADE; CREATE SCHEMA before_4_33_13")
        self.admin(self.old_table, schema="before_4_33_13")
        self.admin("INSERT INTO email_dispatcher (application, name, display_name, username) VALUES ('lesbij', 'default', 'LesBij', %s)",
                   (MAILBOX_LOGIN,), schema="before_4_33_13")
        self.assertEqual([], self.from_address_columns("before_4_33_13"))
        self.admin(self.migration, schema="before_4_33_13")
        self.admin(self.migration, schema="before_4_33_13")
        self.assertEqual([("email_server_username", "YES")], self.from_address_columns("before_4_33_13"))
        self.assertEqual([("LesBij", MAILBOX_LOGIN, None)],
                         self.admin("SELECT display_name, username, from_address FROM email_dispatcher", schema="before_4_33_13"))

    def test_migration_leaves_an_installed_table_alone(self):
        self.admin(self.migration)
        self.assertEqual([("email_server_username", "YES")], self.from_address_columns("public"))

    def test_generated_queries_store_from_address(self):
        self.admin("TRUNCATE email_dispatcher")
        email_dispatcher__insert(self.lookup, CRYPT_KEY, APPLICATION, DISPATCHER, "LesBij", username=MAILBOX_LOGIN, password=PASSWORD)
        [row] = email_dispatcher__select_all(self.lookup, CRYPT_KEY)
        self.assertIsNone(row[KG__email_dispatcher__from_address])
        self.assertEqual(MAILBOX_LOGIN, EmailManagerService.sender_address(row))

        email_dispatcher__update(self.lookup, CRYPT_KEY, APPLICATION, DISPATCHER, username=SERVICE_LOGIN, from_address=FROM_ADDRESS)
        row = email_dispatcher__select(self.lookup, CRYPT_KEY, APPLICATION, DISPATCHER)
        self.assertEqual((SERVICE_LOGIN, PASSWORD, FROM_ADDRESS),
                         (row[KG__email_dispatcher__username], row[KG__email_dispatcher__password], row[KG__email_dispatcher__from_address]))
        self.assertEqual(FROM_ADDRESS, EmailManagerService.sender_address(row))

        # A credentials file of three lines sends no from_address, which leaves the stored one as it is
        email_dispatcher__update(self.lookup, CRYPT_KEY, APPLICATION, DISPATCHER, url="send.simplemailservice.eu", port=587,
                                 username=SERVICE_LOGIN, password=PASSWORD, from_address=None)
        row = email_dispatcher__select(self.lookup, CRYPT_KEY, APPLICATION, DISPATCHER)
        self.assertEqual(FROM_ADDRESS, row[KG__email_dispatcher__from_address])


if __name__ == "__main__":
    unittest.main()
