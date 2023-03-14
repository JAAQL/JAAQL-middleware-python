import os
import traceback
import uuid
import time

from jaaql.constants import *
from jaaql.utilities.utils import load_config, await_jaaql_installation, get_jaaql_connection
from jaaql.utilities.utils_no_project_imports import check_allowable_file_path
from email.utils import formatdate, make_msgid
from smtplib import SMTP, SMTPException, SMTPAuthenticationError
from base64 import urlsafe_b64encode as b64e
from typing import Union, List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from queue import Queue, Empty
import re
import hashlib
import json
import ssl
import sys
import threading
from flask import Flask, jsonify, request
from jaaql.mvc.generated_queries import *
from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.constants import VAULT_KEY__db_crypt_key

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
EMAIL__date = "Date"
EMAIL__message_id = "Message-ID"

SPLIT__address = ", "

TIMEOUT__attachment = 60000
TIMEOUT__filename = 15000

REGEX__html_tags = r'<(\/[a-zA-Z]+|(!?[a-zA-Z]+((\s)*((\"?[^(\">)]*\"?)|[a-zA-Z]*\s*=\s*\"[^\"]*\"))*))>'

HTTP_ARG__oauth_token = "oauth_token"


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
    def static_format_attached_url(artifact_base_url: str, is_container: bool):
        if not artifact_base_url.startswith("https://") and not artifact_base_url.startswith("http://"):
            if is_container:
                if check_allowable_file_path(artifact_base_url):
                    raise Exception("Illegal artifact base url")

            if artifact_base_url.startswith("file:///"):
                return artifact_base_url
            else:
                return "file://" + os.environ[ENVIRON__install_path] + "/www/" + artifact_base_url
        else:
            return artifact_base_url

    def format_attachment_url(self, artifact_base_url: str, is_container: bool):
        self.artifact_base = EmailAttachment.static_format_attached_url(artifact_base_url, is_container)

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
    def __init__(self, application: str, template: str, dispatcher: str, to: Union[str, List[str]],
                 subject: str, body: str, attachments: TYPE__email_attachments = None, recipient_names: Union[str, List[str]] = None,
                 is_html: bool = True, attachment_access_token: str = None, override_send_name: str = None):
        self.application = application
        self.template = template
        self.dispatcher = dispatcher
        if recipient_names is None:
            recipient_names = to
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
        return dict(application=self.application, template=self.template, dispatcher=self.dispatcher,
                    to=self.to, recipient_names=self.recipient_names, subject=self.subject, body=self.body,
                    attachments=[attachment.repr_json() for attachment in self.attachments] if self.attachments is not None else None,
                    is_html=self.is_html, attachment_access_token=self.attachment_access_token, override_send_name=self.override_send_name)

    @staticmethod
    def deserialize(email: dict):
        attachments = None
        if email["attachments"] is not None:
            attachments = [EmailAttachment.deserialize(attachment) for attachment in email["attachments"]]
        return Email(email["application"], email["template"], email["dispatcher"], email["to"],
                     email["subject"], email["body"], attachments, email["recipient_names"], email["is_html"], email["attachment_access_token"],
                     email["override_send_name"])


class ParameterisedLock:
    def __init__(self):
        self.namespace_lock = threading.Lock()
        self._lock_dict = {}

    def acquire_lock(self, key: str, blocking: bool = False):
        if key not in self._lock_dict:
            with self.namespace_lock:
                if key not in self._lock_dict:
                    self._lock_dict[key] = threading.Lock()

        return self._lock_dict[key].acquire(blocking=blocking)

    def release_lock(self, key: str):
        self._lock_dict[key].release()

    def check_lock_held(self, key: str):
        if key not in self._lock_dict:
            return False
        else:
            return self._lock_dict[key].locked()


class ThreadsafeQueueInitialiser:
    def __init__(self):
        self.parameterised_lock = ParameterisedLock()
        self.queues = {}

    def fetch_queue(self, key: str):
        if key not in self.queues:
            self.parameterised_lock.acquire_lock(key, True)
            if key not in self.queues:
                self.queues[key] = Queue()
            self.parameterised_lock.release_lock(key)
        return self.queues[key]


class EmailManagerService:

    def __init__(self, connection: DBInterface, db_crypt_key: bytes, is_gunicorn: bool):
        self.connection = connection
        self.db_crypt_key = db_crypt_key
        self.is_gunicorn = is_gunicorn
        self.dispatchers = {}
        self.dispatcher_blacklist = {}
        self.parameterised_lock = ParameterisedLock()
        self.threadsafe_queue_initialiser = ThreadsafeQueueInitialiser()
        threading.Thread(target=self.dispatcher_manager_thread, daemon=True).start()

    def construct_message(self, dispatcher_info: dict, email: Email) -> (str, MIMEMultipart):
        send_body = email.body

        message = MIMEMultipart("alternative")

        if email.is_html:
            message.attach(MIMEText(re.sub(REGEX__html_tags, "", send_body).strip()))
            message.attach(MIMEText(send_body, 'html'))
        else:
            message.attach(MIMEText(send_body, 'plain'))

        message_final = MIMEMultipart('mixed')
        message_final.attach(message)
        message_final[EMAIL__to] = SPLIT__address.join(email.to)
        send_name = dispatcher_info[KG__email_dispatcher__display_name]
        if email.override_send_name is not None:
            send_name = email.override_send_name
        message_final[EMAIL__from] = send_name + " <" + dispatcher_info[KG__email_dispatcher__username] + ">"
        message_final[EMAIL__subject] = email.subject
        message_final[EMAIL__date] = formatdate()
        message_final[EMAIL__message_id] = make_msgid()

        if email.attachments is not None:
            email_attachments = email.attachments
            for attachment in email_attachments:
                pass  # TODO set up attachments

        return send_body, message_final

    def is_connected(self, conn: SMTP):
        try:
            status = conn.noop()[0]
        except Exception:
            status = -1
        return True if status == 250 else False

    def try_close_conn(self, conn):
        try:
            conn.close()
        except:
            pass

    def fetch_conn(self, dispatcher_key: str, host: str, port: int, username: str, password: str):
        if not self.is_gunicorn:
            return None

        conn = SMTP(host, port=port, timeout=30)
        if conn is None:
            raise Exception("Could not connect to email dispatcher '%s' with address '%s:%d'" % dispatcher_key, host, port)

        context = ssl.SSLContext(ssl.PROTOCOL_TLS)

        conn.starttls(context=context)
        conn.login(username, password)

        return conn

    def form_dispatcher_key(self, application: str, name: str):
        return application + ":" + name

    def fetch_dispatchers_from_db(self):
        return {
            self.form_dispatcher_key(dispatcher[KG__email_dispatcher__application], dispatcher[KG__email_dispatcher__name]): (
                dispatcher,
                self.get_dispatcher_queue_from_key(self.form_dispatcher_key(dispatcher[KG__email_dispatcher__application],
                                                                            dispatcher[KG__email_dispatcher__name]))
            )
            for dispatcher in email_dispatcher__select_all(self.connection, self.db_crypt_key)
        }

    def update_dispatchers(self):
        new_dispatchers = self.fetch_dispatchers_from_db()
        potentially_require_threads = {key: val for key, val in new_dispatchers.items() if not self.parameterised_lock.check_lock_held(key)}
        self.dispatchers = new_dispatchers
        for dispatcher_key, dispatcher_info in potentially_require_threads.items():
            threading.Thread(target=self.dispatcher_thread, args=[dispatcher_key, dispatcher_info]).start()

    def get_dispatcher_queue_from_key(self, dispatcher_key: str):
        return self.dispatchers.get(dispatcher_key, (None, self.threadsafe_queue_initialiser.fetch_queue(dispatcher_key)))[1]

    def get_dispatcher_info_from_key(self, dispatcher_key: str):
        return self.dispatchers.get(dispatcher_key, (None, None))[0]

    def dispatcher_manager_thread(self):
        printed = False
        while True:
            try:
                self.update_dispatchers()
                if printed:
                    print("Successfully refreshed dispatchers after downtime")
                printed = False
            except Exception:
                if not printed:
                    print("Could not update dispatchers. Is db disconnected?")
                    traceback.print_exc()
                printed = True

            time.sleep(15)

    def send_email_with_connection(self, conn: SMTP, email: Email, dispatcher_key: str, dispatcher_info: dict):
        send_to = email.to
        send_recipients = email.recipient_names
        whitelist = dispatcher_info[KG__email_dispatcher__whitelist]

        if whitelist is not None and whitelist != "":
            send_to = []
            send_recipients = []
            for to, recipient in zip(email.to, email.recipient_names):
                if "@" not in to:
                    raise Exception("Email address '%s' was invalid" % to)
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
                    print("Address '%s' rejected by whitelist for account '%s'" % (to, dispatcher_key), file=sys.stderr)

        if len(send_to) == 0:
            return

        email.to = send_to
        email.recipient_names = send_recipients
        formatted_body, to_send = self.construct_message(dispatcher_info, email)

        if self.is_gunicorn:
            conn.send_message(to_send, dispatcher_info[KG__email_dispatcher__display_name], send_to)
        else:
            print("==============================================")
            print("Sending Email from '" + dispatcher_key + "'")
            print(email.subject)
            print(email.body)
            print(dispatcher_info[KG__email_dispatcher__display_name])
            print(send_to)
            print("==============================================")

    def hash_dispatcher_info(self, dispatcher_info):
        return hashlib.md5(json.dumps(dispatcher_info, default=str).encode()).hexdigest()

    def dispatcher_thread(self, dispatcher_key: str, dispatcher_info: dict):
        did_acquire = self.parameterised_lock.acquire_lock(dispatcher_key)
        if not did_acquire:
            return  # Did not acquire the thread lock. Another thread is operating

        queue = self.get_dispatcher_queue_from_key(dispatcher_key)
        email = None

        if self.dispatcher_blacklist.get(dispatcher_key, None) != self.hash_dispatcher_info(dispatcher_info):
            if dispatcher_key in self.dispatcher_blacklist:
                self.dispatcher_blacklist.pop(dispatcher_key)

            try:
                conn = None
                while (dispatcher_key in self.dispatchers or queue.qsize() != 0) and dispatcher_key not in self.dispatcher_blacklist:
                    try:
                        # The dispatcher has been removed from the database AND all emails in the queue have been removed
                        email = queue.get(timeout=10)
                        new_dispatcher_info = self.get_dispatcher_info_from_key(dispatcher_key)
                        if new_dispatcher_info is not None:
                            dispatcher_info = new_dispatcher_info
                        else:
                            new_dispatcher_info = dispatcher_info  # Done for hashing purposes

                        if self.hash_dispatcher_info(dispatcher_info) != self.hash_dispatcher_info(new_dispatcher_info):
                            self.try_close_conn(conn)

                        if not self.is_connected(conn):
                            conn = self.fetch_conn(dispatcher_key, dispatcher_info[KG__email_dispatcher__url],
                                                   dispatcher_info[KG__email_dispatcher__port], dispatcher_info[KG__email_dispatcher__username],
                                                   dispatcher_info[KG__email_dispatcher__password])

                        self.send_email_with_connection(conn, email, dispatcher_key, dispatcher_info)
                    except Empty:
                        pass  # Nothing wrong here. There were simply no emails received in the 10 seconds of queue wait time
                    except SMTPAuthenticationError as ex:
                        raise ex  # Caught in outer loop, we want to break free
                    except SMTPException as ex:
                        print("Issue sending email " + str(ex), file=sys.stderr)

            except SMTPAuthenticationError:
                queue.put(email)
                print("Incorrect credentials for email dispatcher with key '%s'" % dispatcher_key, file=sys.stderr)
                self.dispatcher_blacklist[dispatcher_key] = self.hash_dispatcher_info(dispatcher_info)
            except Exception:
                print("Unhandled email dispatcher exception", file=sys.stderr)
                traceback.print_exc()

        self.parameterised_lock.release_lock(dispatcher_key)

    def send_email(self, email: Email):
        dispatcher_key = self.form_dispatcher_key(email.application, email.dispatcher)
        if dispatcher_key not in self.dispatchers:
            self.update_dispatchers()
            if dispatcher_key not in self.dispatchers:
                raise Exception("Unable to find dispatcher with key '" + dispatcher_key + "'")
        self.get_dispatcher_queue_from_key(dispatcher_key).put(email)


def create_app(ems: EmailManagerService):

    app = Flask(__name__, instance_relative_config=True)

    @app.route(ENDPOINT__send_email, methods=["POST"])
    def send_email():
        ems.send_email(Email.deserialize(request.json))

        return jsonify("OK")

    @app.route("/", methods=["GET"])
    def is_alive():
        return jsonify("OK")

    return app


def create_flask_app(vault_key=None, is_gunicorn: bool = False):
    config = load_config(is_gunicorn)
    await_jaaql_installation(config, is_gunicorn)
    vault = Vault(vault_key, DIR__vault)
    jaaql_lookup_connection = get_jaaql_connection(config, vault)
    db_crypt_key = vault.get_obj(VAULT_KEY__db_crypt_key).encode(ENCODING__ascii)

    flask_app = create_app(EmailManagerService(jaaql_lookup_connection, db_crypt_key, is_gunicorn))
    print("Created email manager app host, running flask", file=sys.stderr)
    flask_app.run(port=PORT__ems, host="0.0.0.0", threaded=True)
