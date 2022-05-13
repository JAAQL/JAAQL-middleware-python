from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement
from jaaql.utilities.utils import load_config, await_jaaql_installation, get_jaaql_connection
import json
import imaplib
import smtplib
from base64 import urlsafe_b64decode as b64d, urlsafe_b64encode as b64e
from jaaql.constants import ENCODING__ascii
from typing import Union, List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from queue import Queue
import threading
import ssl
import sys
from flask import Flask, jsonify, request
from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.constants import VAULT_KEY__jaaql_lookup_connection, VAULT_KEY__db_crypt_key

QUERY__load_email_accounts = "SELECT * FROM jaaql__email_accounts WHERE deleted is null"

KEY__email_account = "email_account"
KEY__encrypted_subject = "encrypted_subject"
KEY__encrypted_body = "encrypted_body"
KEY__encrypted_attachments = "encrypted_attachments"
KEY__encrypted_recipients = "encrypted_recipients"
QUERY__ins_email_history = "INSERT INTO jaaql__email_history (email_account, encrypted_subject, encrypted_body, encrypted_attachments, encrypted_recipients) VALUES (:email_account, :encrypted_subject, :encrypted_body, :encrypted_attachments, :encrypted_recipients)"

ERR__password_not_found = "Password not found for email account with name '%s'"
ERR__email_not_found = "Email account not found with name '%s'"

KEY__account_name = "account_name"
KEY__account_protocol = "protocol"
KEY__account_host = "host"
KEY__account_username = "username"
KEY__account_port = "port"
KEY__account_send_from = "send_name"

PROTOCOL__imap = "imap"
PROTOCOL__smtp = "smtp"

EMAIL__from = "From"
EMAIL__from_email = "From_Email"
EMAIL__to = "To"
EMAIL__subject = "Subject"

REPLACEMENT__str = "{{%s}}"

PORT__ems = 6061


class EmailAttachment:
    def __init__(self, content: bytes, filename: str):
        self.content = content
        self.filename = filename

    def build_attachment(self) -> MIMEApplication:
        attachment = MIMEApplication(self.content, _subtype=self.filename.split(".")[-1])
        attachment.add_header('Content-Disposition', 'attachment', filename=self.filename)
        return attachment

    def repr_json(self):
        return dict(content=b64e(self.content).decode(ENCODING__ascii), filename=self.filename)

    @staticmethod
    def deserialize(attachment: dict):
        return EmailAttachment(b64d(attachment["content"]), attachment["filename"])


TYPE__email_attachments = Union[EmailAttachment, List[EmailAttachment]]


class Email:
    def __init__(self, from_account: str, to: Union[str, List[str]], subject: str = None, body: str = None,
                 attachments: TYPE__email_attachments = None, html_replacements: dict = None):
        self.from_account = from_account
        self.to = to
        self.subject = subject
        self.body = body
        self.attachments = attachments
        if not isinstance(self.attachments, List) and self.attachments is not None:
            self.attachments = [attachments]
        self.html_replacements = html_replacements

    def repr_json(self):
        return dict(from_account=self.from_account, to=self.to, subject=self.subject, body=self.body,
                    attachments=[attachment.repr_json() for attachment in self.attachments],
                    html_replacements=self.html_replacements)

    @staticmethod
    def deserialize(email: dict):
        attachments = None
        if email["attachments"] is not None:
            attachments = [EmailAttachment.deserialize(attachment) for attachment in email["attachments"]]
        return Email(email["from_account"], email["to"], email["subject"], email["body"], attachments,
                     email["html_replacements"])


class EmailManagerService:

    def __init__(self, connection: DBInterface, email_credentials: Optional[str], db_crypt_key: bytes):
        if email_credentials is None:
            self.email_credentials = None
        else:
            self.email_credentials = json.loads(b64d(email_credentials).decode(ENCODING__ascii))
        self.db_crypt_key = db_crypt_key
        self.connection = connection
        self.accounts = execute_supplied_statement(connection, QUERY__load_email_accounts, as_objects=True)

        self.email_queues = {}

        for account in self.accounts:
            if account[KEY__account_name] not in self.email_credentials:
                raise Exception(ERR__password_not_found % account[KEY__account_name])
            cur_queue = Queue()
            self.email_queues[account[KEY__account_name]] = cur_queue
            method_args = [account, cur_queue, self.email_credentials[account[KEY__account_name]]]
            threading.Thread(target=self.email_connection_thread, args=method_args, daemon=True).start()

    def construct_message(self, account: dict, email: Email) -> (str, MIMEMultipart):
        send_body = email.body

        message = MIMEMultipart("alternative")

        if email.html_replacements is not None:
            for key, val in email.html_replacements.items():
                send_body = send_body.replace(REPLACEMENT__str % key, val)
            message.attach(MIMEText(send_body, 'html'))
        else:
            message.attach(MIMEText(send_body, 'plain'))

        message_final = MIMEMultipart('mixed')
        message_final.attach(message)
        message_final[EMAIL__to] = email.to
        message_final[EMAIL__from] = account[KEY__account_send_from] + " <" + account[KEY__account_username] + ">"
        message_final[EMAIL__subject] = email.subject

        if email.attachments is not None:
            email_attachments = email.attachments
            for attachment in email_attachments:
                message_final.attach(attachment.build_attachment())

        return send_body, message_final

    def is_connected(self, conn: smtplib.SMTP):
        try:
            status = conn.noop()[0]
        except Exception as ex:
            status = -1
        return True if status == 250 else False

    def fetch_conn(self, conn_lib, account: dict, password: str):
        conn = conn_lib(account[KEY__account_host], port=account[KEY__account_port])

        context = ssl.SSLContext(ssl.PROTOCOL_TLS)

        if conn_lib == smtplib.SMTP_SSL:
            conn.ehlo()
        conn.starttls(context=context)
        if conn_lib == smtplib.SMTP_SSL:
            conn.ehlo()
        conn.login(account[KEY__account_username], password)

        return conn

    def format_attachments_for_storage(self, attachments: TYPE__email_attachments):
        if attachments is None:
            return None
        if not isinstance(attachments, list):
            attachments = [attachments]
        attachments = "::".join([b64e(attachment.content).decode(ENCODING__ascii) for attachment in attachments])
        return attachments

    def email_connection_thread(self, account: dict, queue: Queue, password: str):
        conn_lib = imaplib.IMAP4 if account[KEY__account_protocol] == PROTOCOL__imap else smtplib.SMTP
        conn = self.fetch_conn(conn_lib, account, password)

        while True:
            email: Email = queue.get()
            if not self.is_connected(conn):
                conn = self.fetch_conn(conn_lib, account, password)
            send_to = email.to
            if not isinstance(send_to, list):
                send_to = [send_to]
            send_to = ", ".join(send_to)
            formatted_body, to_send = self.construct_message(account, email)
            conn.send_message(to_send, account[KEY__account_username], send_to)
            execute_supplied_statement(self.connection, QUERY__ins_email_history, {
                    KEY__email_account: account[KEY__account_name],
                    KEY__encrypted_subject: email.subject,
                    KEY__encrypted_body: formatted_body,
                    KEY__encrypted_attachments: self.format_attachments_for_storage(email.attachments),
                    KEY__encrypted_recipients: send_to
                }, encryption_key=self.db_crypt_key, encrypt_parameters=[
                    KEY__encrypted_subject,
                    KEY__encrypted_body,
                    KEY__encrypted_attachments,
                    KEY__encrypted_recipients
                ]
            )

    def send_email(self, email: Email):
        if email.from_account in self.email_queues:
            self.email_queues[email.from_account].put(email)
        else:
            raise Exception(ERR__email_not_found % email.from_account)


def create_app(ems: EmailManagerService):

    app = Flask(__name__, instance_relative_config=True)

    @app.route("/send-email", methods=["POST"])
    def send_email():
        ems.send_email(Email.deserialize(request.json))

        return jsonify("OK")

    return app


def create_flask_app(vault_key=None, email_credentials=None, is_gunicorn: bool = False):
    config = load_config(is_gunicorn)
    await_jaaql_installation(config, is_gunicorn)
    vault = Vault(vault_key, DIR__vault)
    jaaql_lookup_connection = get_jaaql_connection(config, vault)
    db_crypt_key = vault.get_obj(VAULT_KEY__db_crypt_key)

    flask_app = create_app(EmailManagerService(jaaql_lookup_connection, email_credentials, db_crypt_key))
    print("Created email manager app host, running flask", file=sys.stderr)
    flask_app.run(port=PORT__ems, host="0.0.0.0", threaded=True)
