import os
import traceback
import uuid

from http import HTTPStatus
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement, execute_supplied_statement_singleton
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.utilities.utils import load_config, await_jaaql_installation, get_jaaql_connection, time_delta_ms
from urllib.parse import quote
from jaaql.utilities.utils_no_project_imports import check_allowable_file_path
import json
import imaplib
import smtplib
import base64
from base64 import urlsafe_b64decode as b64d, urlsafe_b64encode as b64e
from typing import Union, List, Optional
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from queue import Queue, Empty
import threading
import ssl
import time
import sys
from flask import Flask, jsonify, request
from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.constants import VAULT_KEY__db_crypt_key, KEY__encrypted_password, KEY__id, KEY__template, KEY__sender, ENCODING__ascii, PORT__ems, \
    ENDPOINT__reload_accounts, ENDPOINT__send_email, KEY__attachment_name, KEY__parameters, KEY__url, KEY__oauth_token, \
    KEY__document_id, KEY__create_file, DIR__render_template, KEY__render_as, KEY__content, DIR__www, KEY__email_account_name, \
    KEY__email_account_send_name, KEY__email_account_protocol, KEY__email_account_host, KEY__email_account_port, KEY__email_account_username, \
    KEY__override_send_name, KEY__application, ENVIRON__install_path, KEY__artifact_base_uri, KEY__email_account_password, \
    KEY__email_account_whitelist

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

QUERY__mark_rendered_document_completed = "UPDATE rendered_document SET completed = current_timestamp, filename = :filename, content = :content WHERE document_id = :document_id"
QUERY__fetch_unrendered_document = "SELECT able.url, ac.artifact_base_uri, able.render_as, rd.document_id, rd.encrypted_parameters as parameters, rd.create_file, rd.encrypted_access_token as oauth_token FROM rendered_document rd INNER JOIN renderable_document able ON rd.document = able.name INNER JOIN application_configuration ac ON rd.configuration = ac.name AND rd.application = ac.application WHERE rd.completed is null ORDER BY rd.created LIMIT 1"
QUERY__update_email_account_password = "UPDATE email_account SET encrypted_password = :encrypted_password WHERE id = :id"
QUERY__load_email_accounts = "SELECT * FROM email_account"
QUERY__create_email_account = "INSERT INTO email_account (name, send_name, host, port, username, encrypted_password, whitelist) VALUES (:name, :send_name, :host, :port, :username, :password, :whitelist) ON CONFLICT ON CONSTRAINT email_account_pkey DO UPDATE SET send_name = excluded.send_name, host = excluded.host, port = excluded.port, username = excluded.username, encrypted_password = excluded.encrypted_password, whitelist = excluded.whitelist"
QUERY__ins_email_history = "INSERT INTO email_history (application, template, sender, encrypted_subject, encrypted_body, encrypted_attachments, encrypted_recipients, encrypted_recipients_keys, override_send_name) VALUES (:application, :template, :sender, :encrypted_subject, :encrypted_body, :encrypted_attachments, :encrypted_recipients, :encrypted_recipients_keys, :override_send_name)"
QUERY__fetch_email_template = "SELECT rd.url FROM renderable_document rd INNER JOIN renderable_document_template rdt ON rd.name = rdt.attachment WHERE rd.name = :name AND rdt.template = :template"
QUERY__purge_rendered_documents = "DELETE FROM rendered_document rd USING renderable_document able WHERE rd.document = able.name AND completed is not null and completed > current_timestamp + interval '5 minutes' RETURNING rd.document_id, rd.create_file, able.render_as"

KEY__email_account = "email_account"
KEY__encrypted_subject = "encrypted_subject"
KEY__encrypted_body = "encrypted_body"
KEY__encrypted_attachments = "encrypted_attachments"
KEY__encrypted_recipients = "encrypted_recipients"
KEY__encrypted_recipients_keys = "encrypted_recipients_keys"
KEY__artifact_base = "artifact_base"

ATTR__filename = "filename"

ELE__jaaql_filename = "jaaql_filename"

ERR__email_not_found = "Email account not found with name '%s'"
ERR__invalid_call_to_internal_email_service = "Invalid call to internal email service"
ERR__attachment_timeout = "Could not send email! Attachment rendering timed out!"
ERR__attachment_error = "Could not send email! Attachment rendering received error: '%s'"
ERR__attachment_filename = "Attachment did not render in time or could not find the file name for the attachment. Please check template. Expected " \
    "presence of element with id " + ELE__jaaql_filename + " to be present after page has finished loading"

PROTOCOL__imap = "imap"
PROTOCOL__smtp = "smtp"

EMAIL__from = "From"
EMAIL__from_email = "From_Email"
EMAIL__to = "To"
EMAIL__subject = "Subject"

SPLIT__address = ", "

TIMEOUT__attachment = 60000
TIMEOUT__filename = 15000


class DrivenChrome:
    def __init__(self, db_interface: DBInterface, db_key: bytes, is_deployed: bool):
        self.attachments = Queue()
        self.completed_attachments = set()
        self.errored_attachments = {}
        self.db_interface = db_interface
        self.chrome_lock = threading.Lock()
        self.driver = None
        self.is_deployed = is_deployed
        self.db_key = db_key
        self.template_dir_path = os.path.join(DIR__www, DIR__render_template)

        self.a4_params = {'landscape': False, 'paperWidth': 8.27, 'paperHeight': 11.69, 'printBackground': True}

        threading.Thread(target=self.start_chrome, daemon=True).start()
        threading.Thread(target=self.purge_rendered_documents, daemon=True).start()

    def parameters_to_get_str(self, access_token: str, parameters: dict):
        if parameters is None:
            parameters = {}
        parameters[KEY__oauth_token] = access_token

        return "?" + "&".join([key + "=" + quote(itm) for key, itm in parameters.items()])

    def chrome_page_to_pdf(self, url: str, access_token: str, parameters: dict):
        filename = None

        with self.chrome_lock:
            self.driver.get(url + self.parameters_to_get_str(access_token, parameters))
            start_time = datetime.now()
            while True:
                filename = self.driver.find_elements(By.ID, ELE__jaaql_filename)
                if len(filename) != 0:
                    file_text = filename[0].get_attribute("innerHTML")
                    if not file_text.endswith(".pdf"):
                        file_text += ".pdf"
                    filename = file_text
                    break
                else:
                    if time_delta_ms(start_time, datetime.now()) > TIMEOUT__filename:
                        raise HttpStatusException(ERR__attachment_filename)
                    time.sleep(0.25)

            return filename, base64.b64decode(self.driver.execute_cdp_cmd("Page.printToPDF", self.a4_params)["data"])

    def purge_rendered_documents(self):
        while True:
            resp = execute_supplied_statement(self.db_interface, QUERY__purge_rendered_documents, as_objects=True)
            for to_purge in resp:
                if to_purge[KEY__create_file]:
                    try:
                        os.remove(os.path.join(self.template_dir_path, str(to_purge[KEY__document_id]) + "." + to_purge[KEY__render_as]))
                    except FileNotFoundError:
                        pass
            time.sleep(5)

    def render_document_requests(self):
        while True:
            try:
                resp = execute_supplied_statement_singleton(self.db_interface, QUERY__fetch_unrendered_document, as_objects=True,
                                                            decrypt_columns=[KEY__parameters, KEY__oauth_token], encryption_key=self.db_key)
                parameters = {}
                if resp[KEY__parameters]:
                    parameters = json.loads(resp[KEY__parameters])

                base_uri = EmailAttachment.static_format_attached_url(resp[KEY__artifact_base_uri], self.is_deployed)
                filename, content = self.chrome_page_to_pdf(base_uri, resp[KEY__oauth_token], parameters)

                inputs = {KEY__document_id: resp[KEY__document_id], KEY__content: None, ATTR__filename: filename}
                if resp[KEY__create_file]:
                    if not os.path.exists(self.template_dir_path):
                        os.mkdir(self.template_dir_path)
                    with open(os.path.join(self.template_dir_path, str(resp[KEY__document_id]) + "." + resp[KEY__render_as]), "wb") as f:
                        f.write(content)
                else:
                    inputs[KEY__content] = content

                execute_supplied_statement(self.db_interface, QUERY__mark_rendered_document_completed, inputs)
            except HttpStatusException as ex:
                if ex.response_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                    time.sleep(0.25)
                else:
                    traceback.print_exc()

    def start_chrome(self):
        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.headless = True
        service_log_path = None

        if self.is_deployed:
            options.add_argument('--no-sandbox')
            service_log_path = "log/chromedriver.log"

        with webdriver.Chrome(options=options, service_log_path=service_log_path) as driver:
            self.driver = driver
            threading.Thread(target=self.render_document_requests, daemon=True).start()
            while True:
                current_attachment: 'EmailAttachment' = self.attachments.get()
                try:
                    url = execute_supplied_statement_singleton(self.db_interface, QUERY__fetch_email_template,
                                                               {KEY__attachment_name: current_attachment.name,
                                                                KEY__template: current_attachment.template}, as_objects=True)[KEY__url]
                    if not url.endswith(".html"):
                        url += ".html"
                    url = current_attachment.artifact_base + "/" + url
                    filename, content = self.chrome_page_to_pdf(url, current_attachment.access_token, current_attachment.parameters)
                    current_attachment.content = content
                    current_attachment.filename = filename
                except HttpStatusException as ex:
                    self.errored_attachments[current_attachment.id] = str(ex)
                    self.completed_attachments.add(current_attachment.id)
                except Exception as ex:
                    traceback.print_exc()
                    self.errored_attachments[current_attachment.id] = str(ex)
                    self.completed_attachments.add(current_attachment.id)
                self.completed_attachments.add(current_attachment.id)


class EmailAttachment:
    def __init__(self, name: str, parameters: dict, template: str, artifact_base: str = None):
        self.name = name
        self.artifact_base = artifact_base
        self.parameters = parameters
        self.id = str(uuid.uuid4())
        self.filename = None
        self.content = None
        self.access_token = None
        self.template = str(template)

    @staticmethod
    def static_format_attached_url(artifact_base_uri: str, is_container: bool):
        if not artifact_base_uri.startswith("https://") and not artifact_base_uri.startswith("http://"):
            if is_container:
                if check_allowable_file_path(artifact_base_uri):
                    raise Exception("Illegal artifact base url")

            if artifact_base_uri.startswith("file:///"):
                return artifact_base_uri
            else:
                return "file://" + os.environ[ENVIRON__install_path] + "/www/" + artifact_base_uri
        else:
            return artifact_base_uri

    def format_attachment_url(self, artifact_base_uri: str, is_container: bool):
        self.artifact_base = EmailAttachment.static_format_attached_url(artifact_base_uri, is_container)

    def build_attachment(self, access_token: str, driven_chrome: DrivenChrome) -> MIMEApplication:
        self.access_token = access_token
        driven_chrome.attachments.put(self)

        start_time = datetime.now()
        while time_delta_ms(start_time, datetime.now()) < TIMEOUT__attachment:
            if self.id in driven_chrome.completed_attachments:
                break
            time.sleep(1)

        if self.id not in driven_chrome.completed_attachments:
            raise Exception(ERR__attachment_timeout)
        driven_chrome.completed_attachments.remove(self.id)

        if self.id in driven_chrome.errored_attachments:
            raise Exception(ERR__attachment_error % driven_chrome.errored_attachments.pop(self.id))

        attachment = MIMEApplication(self.content, _subtype=self.filename.split(".")[-1])
        attachment.add_header('Content-Disposition', 'attachment', filename=self.filename)

        return attachment

    def repr_json(self):
        return dict(name=self.name, parameters=self.parameters, template=self.template, artifact_base=self.artifact_base)

    @staticmethod
    def deserialize(attachment: dict, template: str = None, artiface_base_url: str = None):
        if template is not None:
            return EmailAttachment(attachment[KEY__attachment_name], attachment[KEY__parameters], template, artiface_base_url)
        else:
            return EmailAttachment(attachment[KEY__attachment_name], attachment[KEY__parameters], attachment[KEY__template],
                                   attachment[KEY__artifact_base])

    @staticmethod
    def deserialize_list(attachments: list, template: str, artiface_base_url: str):
        if attachments is None:
            return None
        else:
            return [EmailAttachment.deserialize(attachment, template, artiface_base_url) for attachment in attachments]

    def encode_filename(self):
        return b64e(self.filename.encode(ENCODING__ascii)).decode(ENCODING__ascii)

    def encode_content(self):
        return b64e(self.content).decode(ENCODING__ascii)


TYPE__email_attachments = Union[EmailAttachment, List[EmailAttachment]]


class Email:
    def __init__(self, sender: str, application: str, template: str, from_account: str, to: Union[str, List[str]],
                 recipient_names: Union[str, List[str]], subject: str = None, body: str = None, attachments: TYPE__email_attachments = None,
                 is_html: bool = True, attachment_access_token: str = None, override_send_name: str = None):
        self.sender = sender
        self.application = application
        self.template = template
        self.from_account = from_account
        if isinstance(to, list) != isinstance(recipient_names, list):
            raise Exception(ERR__invalid_call_to_internal_email_service)
        if not isinstance(to, list):
            to = [to]
            recipient_names = [recipient_names]
        if len(to) != len(recipient_names):
            raise Exception(ERR__invalid_call_to_internal_email_service)
        recipient_names = [to[idx] if itm is None else itm for idx, itm in zip(range(len(recipient_names)), recipient_names)]
        self.to = to
        self.recipient_names = recipient_names
        self.subject = subject
        self.body = body
        self.attachments = attachments
        self.override_send_name = override_send_name
        if not isinstance(self.attachments, List) and self.attachments is not None:
            self.attachments = [attachments]
        self.is_html = is_html
        self.attachment_access_token = attachment_access_token

    def repr_json(self):
        return dict(sender=self.sender, application=self.application, template=self.template, from_account=self.from_account,
                    to=self.to, recipient_names=self.recipient_names, subject=self.subject, body=self.body,
                    attachments=[attachment.repr_json() for attachment in self.attachments] if self.attachments is not None else None,
                    is_html=self.is_html, attachment_access_token=self.attachment_access_token, override_send_name=self.override_send_name)

    @staticmethod
    def deserialize(email: dict):
        attachments = None
        if email["attachments"] is not None:
            attachments = [EmailAttachment.deserialize(attachment) for attachment in email["attachments"]]
        return Email(email["sender"], email["application"], email["template"], email["from_account"], email["to"],
                     email["recipient_names"], email["subject"], email["body"], attachments, email["is_html"], email["attachment_access_token"],
                     email["override_send_name"])


class EmailManagerService:

    def __init__(self, connection: DBInterface, email_accounts: Optional[str], db_crypt_key: bytes, is_gunicorn: bool):
        if email_accounts is None:
            self.email_accounts = {}
        else:
            self.email_accounts = json.loads(b64d(email_accounts).decode(ENCODING__ascii))
        self.db_crypt_key = db_crypt_key
        self.connection = connection

        self.email_queues = {}

        self.is_gunicorn = is_gunicorn

        self.reload_lock = threading.Lock()
        self.reload_accounts()

        self.driven_chrome = DrivenChrome(connection, self.db_crypt_key, self.is_gunicorn)

    def reload_accounts(self):
        with self.reload_lock:
            supplied_accounts_formatted = [
                {
                    KEY__email_account_name: name,
                    KEY__email_account_host: account[KEY__email_account_host],
                    KEY__email_account_port: account[KEY__email_account_port],
                    KEY__email_account_username: account[KEY__email_account_username],
                    KEY__email_account_password: account[KEY__email_account_password],
                    KEY__email_account_send_name: account[KEY__email_account_send_name],
                    KEY__email_account_whitelist: account[KEY__email_account_whitelist]
                }
                for name, account in self.email_accounts.items()
            ]

            for account in supplied_accounts_formatted:
                execute_supplied_statement(self.connection, QUERY__create_email_account, account, encryption_key=self.db_crypt_key,
                                           encrypt_parameters=[KEY__email_account_password])

            accounts = execute_supplied_statement(self.connection, QUERY__load_email_accounts, as_objects=True,
                                                  decrypt_columns=[KEY__encrypted_password], encryption_key=self.db_crypt_key)
            email_queues = {}

            for account in accounts:
                cur_queue = Queue()

                if str(account[KEY__email_account_name]) not in self.email_queues:
                    email_queues[str(account[KEY__email_account_name])] = cur_queue
                    password = account[KEY__encrypted_password]
                    method_args = [account, cur_queue, password]
                    threading.Thread(target=self.email_connection_thread, args=method_args, daemon=True).start()
                else:
                    email_queues[str(account[KEY__email_account_name])] = self.email_queues[str(account[KEY__email_account_name])]

            self.email_queues = email_queues

    def construct_message(self, account: dict, email: Email) -> (str, MIMEMultipart):
        send_body = email.body

        message = MIMEMultipart("alternative")

        if email.is_html:
            message.attach(MIMEText(send_body, 'html'))
        else:
            message.attach(MIMEText(send_body, 'plain'))

        message_final = MIMEMultipart('mixed')
        message_final.attach(message)
        message_final[EMAIL__to] = SPLIT__address.join(email.to)
        send_name = account[KEY__email_account_send_name]
        if email.override_send_name is not None:
            send_name = email.override_send_name
        message_final[EMAIL__from] = send_name + " <" + account[KEY__email_account_username] + ">"
        message_final[EMAIL__subject] = email.subject

        if email.attachments is not None:
            email_attachments = email.attachments
            for attachment in email_attachments:
                message_final.attach(attachment.build_attachment(email.attachment_access_token, self.driven_chrome))

        return send_body, message_final

    def is_connected(self, conn: smtplib.SMTP):
        try:
            status = conn.noop()[0]
        except Exception:
            status = -1
        return True if status == 250 else False

    def fetch_conn(self, conn_lib, account: dict, password: str):
        conn = conn_lib(account[KEY__email_account_host], port=account[KEY__email_account_port], timeout=30)
        if conn is None:
            raise Exception("Could not connect to email account '%s' with address '%s:%d'" % (account[KEY__email_account_name],
                                                                                              account[KEY__email_account_host],
                                                                                              account[KEY__email_account_port]))

        context = ssl.SSLContext(ssl.PROTOCOL_TLS)

        if conn_lib == smtplib.SMTP_SSL:
            conn.ehlo()
        conn.starttls(context=context)
        if conn_lib == smtplib.SMTP_SSL:
            conn.ehlo()
        conn.login(account[KEY__email_account_username], password)

        return conn

    def format_attachments_for_storage(self, attachments: TYPE__email_attachments):
        if attachments is None:
            return None
        if not isinstance(attachments, list):
            attachments = [attachments]
        attachments = "::".join([attachment.encode_filename() + ":" + attachment.encode_content() for attachment in attachments])
        return attachments

    def email_connection_thread(self, account: dict, queue: Queue, password: str):
        conn_lib = None
        conn = None
        try:
            if True:
                conn_lib = imaplib.IMAP4 if account[KEY__email_account_protocol] == PROTOCOL__imap else smtplib.SMTP
                conn = self.fetch_conn(conn_lib, account, password)
        except Exception as ex:
            traceback.print_exc()
            raise ex

        while True:
            try:
                email: Email = queue.get(timeout=10)
                if True:
                    if not self.is_connected(conn):
                        conn = self.fetch_conn(conn_lib, account, password)
                send_to = email.to
                send_recipients = email.recipient_names
                whitelist = account[KEY__email_account_whitelist]
                if whitelist is not None and whitelist != "":
                    send_to = []
                    for to, recipient in zip(email.to, email.recipient_names):
                        start_len = len(send_to)

                        for check in whitelist.split(","):
                            check = check.strip()
                            domain = check.split("@")[1].lower()
                            to_domain = to.strip().split("@")[1].lower()
                            if check.startswith("*@"):
                                if domain == to_domain:
                                    send_to.append(to)
                                    send_recipients.append(recipient)
                                    break
                            elif domain == to_domain:
                                person = check.split("@")[0].lower()
                                to_person = to.strip().split("@")[0].lower().split("+")[0]
                                if person == to_person:
                                    send_to.append(to)
                                    send_recipients.append(recipient)
                                    break

                        if len(send_to) == start_len:
                            print("Address '%s' rejected by whitelist for account '%s'" % (to, account[KEY__email_account_name]))

                email.to = send_to
                email.recipient_names = send_recipients
                formatted_body, to_send = self.construct_message(account, email)

                if len(send_to) != 0:
                    if True:
                        conn.send_message(to_send, account[KEY__email_account_username], send_to)
                    else:
                        print("SENDING EMAIL")
                        print(email.subject)
                        print(email.body)
                        print(account[KEY__email_account_username])
                        print(send_to)

                    execute_supplied_statement(self.connection, QUERY__ins_email_history, {
                            KEY__application: email.application,
                            KEY__template: email.template,
                            KEY__sender: email.sender,
                            KEY__override_send_name: email.override_send_name,
                            KEY__encrypted_subject: email.subject,
                            KEY__encrypted_body: formatted_body,
                            KEY__encrypted_attachments: self.format_attachments_for_storage(email.attachments),
                            KEY__encrypted_recipients: SPLIT__address.join(send_to),
                            KEY__encrypted_recipients_keys: SPLIT__address.join(send_recipients)
                        }, encryption_key=self.db_crypt_key, encrypt_parameters=[
                            KEY__encrypted_subject,
                            KEY__encrypted_body,
                            KEY__encrypted_attachments,
                            KEY__encrypted_recipients,
                            KEY__encrypted_recipients_keys
                        ]
                    )
            except Empty:
                if account[KEY__email_account_name] not in self.email_queues:
                    break
            except Exception:
                traceback.print_exc()  # Something went wrong

        try:
            conn.quit()
        except Exception:
            pass

    def send_email(self, email: Email):
        if email.from_account in self.email_queues:
            self.email_queues[email.from_account].put(email)
        else:
            self.reload_accounts()
            if email.from_account in self.email_queues:
                self.email_queues[email.from_account].put(email)
            else:
                raise Exception(ERR__email_not_found % email.from_account)


def create_app(ems: EmailManagerService):

    app = Flask(__name__, instance_relative_config=True)

    @app.route(ENDPOINT__send_email, methods=["POST"])
    def send_email():
        ems.send_email(Email.deserialize(request.json))

        return jsonify("OK")

    @app.route(ENDPOINT__reload_accounts, methods=["POST"])
    def refresh_accounts():
        ems.reload_accounts()

        return jsonify("OK")

    @app.route("/", methods=["GET"])
    def is_alive():
        return jsonify("OK")

    return app


def create_flask_app(vault_key=None, email_accounts=None, is_gunicorn: bool = False):
    config = load_config(is_gunicorn)
    await_jaaql_installation(config, is_gunicorn)
    vault = Vault(vault_key, DIR__vault)
    jaaql_lookup_connection = get_jaaql_connection(config, vault)
    db_crypt_key = vault.get_obj(VAULT_KEY__db_crypt_key).encode(ENCODING__ascii)

    flask_app = create_app(EmailManagerService(jaaql_lookup_connection, email_accounts, db_crypt_key, is_gunicorn))
    print("Created email manager app host, running flask", file=sys.stderr)
    flask_app.run(port=PORT__ems, host="0.0.0.0", threaded=True)
