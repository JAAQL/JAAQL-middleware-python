from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement
import json
import imaplib
import smtplib
from base64 import urlsafe_b64decode as b64d
from jaaql.constants import ENCODING__ascii
from typing import Union, List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from queue import Queue
import threading

QUERY__load_email_accounts = "SELECT * FROM jaaql__email_accounts WHERE deleted is null"

ERR__password_not_found = "Password not found for email account with name '%s'"
ERR__email_not_found = "Email account not found with name '%s'"

KEY__account_name = "name"
KEY__account_protocol = "protocol"
KEY__account_host = "host"
KEY__account_username = "username"
KEY__account_port = "port"
KEY__account_send_from = "send_from"

PROTOCOL__imap = "imap"
PROTOCOL__smtp = "smtp"

EMAIL__from = "From"
EMAIL__to = "To"
EMAIL__subject = "Subject"

REPLACEMENT__str = "{{%s}}"


class EmailAttachment:
    def __init__(self, content: bytes, filename: str):
        self.content = content
        self.filename = filename

    def build_attachment(self) -> MIMEApplication:
        attachment = MIMEApplication(self.content, _subtype=self.filename.split(".")[-1])
        attachment.add_header('Content-Disposition', 'attachment', filename=self.filename)
        return attachment


class Email:
    def __init__(self, from_account: str, to: Union[str, List[str]], subject: str = None, body: str = None,
                 attachments: Union[EmailAttachment, List[EmailAttachment]] = None, html_replacements: dict = None):
        self.from_account = from_account
        self.to = to
        self.subject = subject
        self.body = body
        self.attachments = attachments
        self.html_replacements = html_replacements


class EmailManager:

    def __init__(self, connection: DBInterface, email_credentials: Optional[str]):
        if email_credentials is None:
            self.email_credentials = None
        else:
            self.email_credentials = json.loads(b64d(email_credentials).decode(ENCODING__ascii))
        self.connection = connection
        self.accounts = execute_supplied_statement(connection, QUERY__load_email_accounts, as_objects=True)

        self.email_queues = {}

        for account in self.accounts:
            if account[KEY__account_name] not in self.email_credentials:
                raise Exception(ERR__password_not_found % account[KEY__account_name])
            cur_queue = Queue()
            self.email_queues[account[KEY__account_name]] = cur_queue
            method_args = [self.email_queues, cur_queue, self.email_credentials[account[KEY__account_name]]]
            threading.Thread(target=self.email_connection_thread, args=method_args, daemon=True).start()

    def construct_message(self, account: dict, email: Email) -> MIMEMultipart:
        send_body = email.body

        message = MIMEMultipart("alternative")

        if email.html_replacements is not None:
            for key, val in email.html_replacements:
                send_body = send_body.replace(REPLACEMENT__str % key, val)
            message.attach(MIMEText(email.body, 'html'))
        else:
            message.attach(MIMEText(email.body, 'plain'))

        message[EMAIL__to] = email.to
        message[EMAIL__from] = account[KEY__account_send_from]
        message[EMAIL__subject] = email.subject

        message_final = MIMEMultipart('mixed')
        message_final.attach(message)

        if email.attachments is not None:
            email_attachments = email.attachments
            if not isinstance(email_attachments, List):
                email_attachments = [email_attachments]
            for attachment in email_attachments:
                message_final.attach(attachment.build_attachment())

        return message_final

    def email_connection_thread(self, account: dict, queue: Queue, password: str):
        protocol = account[KEY__account_protocol]
        host = account[KEY__account_host]
        conn_lib = imaplib.IMAP4_SSL if protocol == PROTOCOL__imap else smtplib.SMTP_SSL
        conn = conn_lib(protocol + "." + host, port=account[KEY__account_port])

        conn.starttls()
        conn.login(account[KEY__account_username] + "@" + host, password)

        while True:
            email: Email = queue.get()
            conn.send_message(account[KEY__account_send_from], email.to,
                              self.construct_message(account, email).as_string())

    def send_email(self, email: Email):
        if email.from_account in self.email_queues:
            self.email_queues[email.from_account].put(email)
        else:
            raise Exception(ERR__email_not_found % email.from_account)
