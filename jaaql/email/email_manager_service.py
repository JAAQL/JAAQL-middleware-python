import traceback
import uuid
import time
from http import HTTPStatus
from urllib.parse import urlparse

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime

from selenium.webdriver.support.wait import WebDriverWait

from jaaql.constants import *
from urllib.parse import quote
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.utilities.utils import load_config, await_jaaql_installation, get_jaaql_connection
from jaaql.utilities.utils_no_project_imports import check_allowable_file_path, time_delta_ms
from email.utils import formatdate, make_msgid
from smtplib import SMTP, SMTPException, SMTPAuthenticationError
import base64
from base64 import urlsafe_b64encode as b64e
from typing import Union, List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from queue import Queue, Empty
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

ATTR__finished_request = "data-jaaql-finished-request"
ATTR__finished_request_success = "data-jaaql-finished-request-success"

ERR__email_not_found = "Email account not found with name '%s'"
ERR__invalid_call_to_internal_email_service = "Invalid call to internal email service"
ERR__attachment_timeout = "Could not send email! Attachment took too long to render!"
ERR__attachment_timeout_render = "Could not send email! Attachment timed out whilst rendering!"
ERR__attachment_error = "Could not send email! Attachment rendering received error: '%s'"

PROTOCOL__imap = "imap"
PROTOCOL__smtp = "smtp"

EMAIL__from = "From"
EMAIL__from_email = "From_Email"
EMAIL__to = "To"
EMAIL__subject = "Subject"
EMAIL__date = "Date"
EMAIL__message_id = "Message-ID"

SPLIT__address = ", "

TIMEOUT__attachment = 90000
TIMEOUT__attachment_render = 60000
TIMEOUT__page_load = 20
TIMEOUT__pdf_generation = 60

REGEX__html_tags = r'<(\/[a-zA-Z]+|(!?[a-zA-Z]+((\s)*((\"?[^(\">)]*\"?)|[a-zA-Z]*\s*=\s*\"[^\"]*\"))*))>'

HTTP_ARG__oauth_token = "oauth_token"

KEY__attachment_name = "name"
KEY__attachment_application = "application"
KEY__template_base = "template_base"


QUERY__purge_rendered_documents = "DELETE FROM document_request rd USING document_template able WHERE rd.template = able.name AND completed is not null and completed > current_timestamp + interval '5 minutes' RETURNING rd.uuid as document_id, rd.create_file, 'pdf' as render_as"
QUERY__fetch_unrendered_document = "SELECT able.content_path as url, a.base_url, 'pdf' as render_as, rd.uuid as document_id, rd.encrypted_parameters as parameters, rd.create_file, rd.encrypted_access_token as oauth_token FROM document_request rd INNER JOIN document_template able ON rd.template = able.name INNER JOIN application a ON rd.application = a.name WHERE rd.completed is null ORDER BY rd.request_timestamp LIMIT 1"
QUERY__mark_rendered_document_completed = "UPDATE document_request SET completed = current_timestamp, file_name = :file_name, content = :content WHERE uuid = :document_id"
QUERY__mark_rendered_document_completed_with_error = "UPDATE document_request SET completed = current_timestamp WHERE uuid = :document_id"


CHROME_DEBUGGING = False


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

        self.chrome_restart_lock = threading.Lock()
        self.chrome_restart_count = 0
        self.max_chrome_restarts = 5
        self.chrome_restart_cooldown = {}
        self.last_progress_log = None

        self.a4_params = {
            "landscape": False,          # Portrait
            "paperWidth": 8.27,          # A-4 inches
            "paperHeight": 11.69,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "scale": 0.8,                # 80 %
            "printBackground": True,     # keep the dark frame
            "preferCSSPageSize": True    # honour @page if you ever add one
            # "displayHeaderFooter": False   # (default) – no extra header/footer
        }

        self.page_load_timeout = TIMEOUT__page_load
        self.pdf_generation_timeout = TIMEOUT__pdf_generation
        self.render_timeout = TIMEOUT__attachment_render / 1000  # Convert to seconds

        threading.Thread(target=self.start_chrome, daemon=True).start()
        threading.Thread(target=self.purge_rendered_documents, daemon=True).start()

    def initialize_chrome_driver(self):
        """Initialize Chrome driver with all settings"""
        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--force-color-profile=srgb")
        options.add_argument("--font-render-hinting=none")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--headless=new")

        # Add options to handle long-running JavaScript
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")

        if CHROME_DEBUGGING:
            options.add_argument("--enable-logging=stderr")
            options.add_argument("--v=1")
            options.set_capability(
                "goog:loggingPrefs",
                {"browser": "ALL", "performance": "ALL"}
            )

        if self.is_deployed:
            options.add_argument('--no-sandbox')

        service_args = []

        self.driver = webdriver.Chrome(options=options, service=Service(service_args=service_args))

        self.driver.set_page_load_timeout(self.page_load_timeout)
        self.driver.set_script_timeout(self.render_timeout)

        print(
            f"Chrome driver initialized with {self.page_load_timeout}s page load timeout, {self.render_timeout}s render timeout")

    def restart_chrome(self, reason="unspecified"):
        """Safely restart Chrome driver"""
        with self.chrome_restart_lock:
            # Check if we're restarting too frequently
            current_time = datetime.now()
            recent_restarts = [
                t for t in self.chrome_restart_cooldown.values()
                if (current_time - t).seconds < 300  # 5 minute window
            ]

            if len(recent_restarts) >= self.max_chrome_restarts:
                print(f"ERROR: Too many Chrome restarts ({len(recent_restarts)}) in 5 minutes. Not restarting.")
                raise Exception("Chrome restart limit exceeded")

            print(f"Restarting Chrome driver. Reason: {reason}")

            # Acquire the main chrome lock to ensure no operations are in progress
            with self.chrome_lock:
                # Try to quit existing driver
                if hasattr(self, 'driver') and self.driver:
                    try:
                        self.driver.quit()
                    except Exception as e:
                        print(f"Error quitting Chrome driver: {e}")

                    # Small delay to ensure Chrome process is fully terminated
                    time.sleep(2)

                # Initialize new Chrome instance
                try:
                    self.initialize_chrome_driver()
                    self.chrome_restart_count += 1
                    self.chrome_restart_cooldown[self.chrome_restart_count] = current_time

                    # Clean old restart records
                    self.chrome_restart_cooldown = {
                        k: v for k, v in self.chrome_restart_cooldown.items()
                        if (current_time - v).seconds < 3600  # Keep last hour
                    }

                except Exception as e:
                    print(f"CRITICAL: Failed to restart Chrome: {e}")
                    traceback.print_exc()
                    raise

    def parameters_to_get_str(self, access_token: str, parameters: dict):
        if parameters is None:
            parameters = {}
        parameters[KEY__oauth_token] = access_token

        return "?" + "&".join([key + "=" + quote(itm if isinstance(itm, bytes) else str(itm).encode("UTF-8")) for key, itm in parameters.items()])

    def chrome_page_to_pdf(self, url: str, access_token: str, parameters: dict, document_id: str):
        with self.chrome_lock:
            try:
                origin = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))
                self.driver.execute_cdp_cmd(
                    "Storage.clearDataForOrigin",
                    {
                        "origin": origin,
                        "storageTypes": "local_storage,session_storage"
                    }
                )

                old_handle = self.driver.current_window_handle
                self.driver.switch_to.new_window('tab')
                self.driver.switch_to.window(old_handle)
                self.driver.close()
                survivor_handles = [h for h in self.driver.window_handles if h != old_handle]
                self.driver.switch_to.window(survivor_handles[0])

                full_url = url + self.parameters_to_get_str(access_token, parameters) + "&BS_document_id=" + document_id
                try:
                    self.driver.get(full_url)
                except TimeoutException:
                    raise Exception(
                        f"Page load timeout after {self.page_load_timeout}s for document {document_id}")

                start_time = datetime.now()
                filename = ""
                error_message = None

                print(f"Waiting up to {self.render_timeout}s for document {document_id} to render...")

                # Use explicit wait with custom condition
                def check_render_completion(driver):
                    try:
                        # First check if body exists
                        body = driver.find_element(By.TAG_NAME, "body")
                        if body is None:
                            return False

                        finished = body.get_attribute(ATTR__finished_request)
                        finished_success = body.get_attribute(ATTR__finished_request_success)

                        if finished_success is not None:
                            # Success case
                            return True
                        elif finished is not None:
                            # Error case - also return True to stop waiting
                            return True

                        elapsed = time_delta_ms(start_time, datetime.now()) / 1000
                        current_second = int(elapsed)

                        # Only log every 10 seconds, and only once per second
                        if current_second % 10 == 0 and current_second > 0:
                            if self.last_progress_log is None or \
                                    self.last_progress_log < current_second:
                                print(f"Still waiting for document {document_id}... {elapsed:.0f}s elapsed")
                                self.last_progress_log = current_second

                        return False
                    except NoSuchElementException:
                        # Body not found yet
                        return False
                    except Exception as e:
                        print(f"Error checking render completion: {e}")
                        return False

                try:
                    # Wait up to render_timeout seconds
                    wait = WebDriverWait(self.driver, self.render_timeout, poll_frequency=0.25)
                    wait.until(check_render_completion)

                    # Check what happened
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    finished = body.get_attribute(ATTR__finished_request)
                    finished_success = body.get_attribute(ATTR__finished_request_success)

                    if finished_success is not None:
                        # Success
                        if finished_success != ATTR__finished_request_success:
                            filename = finished_success
                    elif finished is not None:
                        # Error
                        error_message = base64.b64decode(finished).decode("UTF-8")
                        raise HttpStatusException(f"Application level exception: '{error_message}'")

                    elapsed = time_delta_ms(start_time, datetime.now()) / 1000
                    print(f"Document {document_id} rendered successfully in {elapsed:.1f}s")

                except TimeoutException:
                    elapsed = time_delta_ms(start_time, datetime.now()) / 1000
                    # Log any console errors before failing
                    print(f"Timeout after {elapsed:.1f}s waiting for document {document_id}")
                    for log in self.driver.get_log('browser'):
                        print(f"CHROMEFAILURE: {log if isinstance(log, str) else json.dumps(log)}")
                    raise Exception(f"Render timeout after {elapsed:.1f}s (limit: {self.render_timeout}s)")

                # Process filename
                if len(filename) == 0:
                    filename = url.split("/")[-1].split(".html")[0]
                if not filename.endswith(".pdf"):
                    filename += ".pdf"

                # Generate PDF with timeout
                print(f"Generating PDF for document {document_id}...")
                pdf_start = datetime.now()

                try:
                    # Set timeout for CDP commands
                    self.driver.execute_cdp_cmd(
                        "Emulation.setEmulatedMedia",
                        {"media": "print"}
                    )

                    # Generate PDF - this can also take time for complex documents
                    pdf_result = self.driver.execute_cdp_cmd("Page.printToPDF", self.a4_params)
                    pdf_data = base64.b64decode(pdf_result["data"])

                    pdf_elapsed = (datetime.now() - pdf_start).total_seconds()
                    print(f"PDF generated for document {document_id} in {pdf_elapsed:.1f}s")

                    if pdf_elapsed > self.pdf_generation_timeout:
                        print(
                            f"WARNING: PDF generation took {pdf_elapsed:.1f}s, exceeding timeout of {self.pdf_generation_timeout}s")

                except Exception as e:
                    pdf_elapsed = (datetime.now() - pdf_start).total_seconds()
                    raise Exception(f"PDF generation failed after {pdf_elapsed:.1f}s: {str(e)}")

                # Clean up
                self.driver.execute_cdp_cmd("HeapProfiler.collectGarbage", {})

                total_elapsed = time_delta_ms(start_time, datetime.now()) / 1000
                print(f"Total time for document {document_id}: {total_elapsed:.1f}s")

                return filename, pdf_data

            except Exception as e:
                if not isinstance(e, HttpStatusException):  # This is an application level error. Chrome is fine!
                    # Try to recover the Chrome instance
                    self.attempt_chrome_recovery()
                raise

    def attempt_chrome_recovery(self):
        """Try to recover Chrome to a good state, restart if needed"""
        try:
            # First, try simple recovery
            handles = self.driver.window_handles
            if len(handles) > 1:
                # Close all tabs except one
                for handle in handles[1:]:
                    try:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    except:
                        pass  # Tab might already be closed

                self.driver.switch_to.window(handles[0])

            # Navigate to blank page to clear any bad state
            self.driver.get("about:blank")

            # Test if Chrome is responsive
            test_result = self.driver.execute_script("return 1+1")
            if test_result != 2:
                raise Exception("Chrome JavaScript execution failed")

        except Exception as e:
            # Recovery failed, restart Chrome
            print(f"Chrome recovery failed: {e}. Initiating restart...")
            self.restart_chrome(reason=f"Recovery failed: {str(e)}")

    def purge_rendered_documents(self):
        while True:
            resp = execute_supplied_statement(self.db_interface, QUERY__purge_rendered_documents, as_objects=True)
            for to_purge in resp:
                if to_purge[KEY__create_file]:
                    try:
                        os.remove(os.path.join(self.template_dir_path,
                                               str(to_purge[KEY__document_id]) + "." + to_purge[KEY__render_as]))
                    except FileNotFoundError:
                        pass
            time.sleep(5)

    def render_document_requests(self):
        consecutive_failures = 0
        max_consecutive_failures = 5
        last_resp = None

        while True:
            resp = None

            try:
                resp = last_resp if last_resp is not None else execute_supplied_statement_singleton(
                    self.db_interface, QUERY__fetch_unrendered_document,
                    as_objects=True,
                    decrypt_columns=[KEY__parameters, KEY__oauth_token],
                    encryption_key=self.db_key)
                last_resp = None
                parameters = {}
                if resp[KEY__parameters]:
                    parameters = json.loads(resp[KEY__parameters])

                base_url = EmailAttachment.static_format_attached_url(resp[KG__application__base_url] + "/" + resp["url"], self.is_deployed)

                filename, content = self.chrome_page_to_pdf(base_url, resp[KEY__oauth_token], parameters, str(resp[KEY__document_id]))

                inputs = {KEY__document_id: resp[KEY__document_id], KEY__content: None, KG__document_request__file_name: filename}
                if resp[KEY__create_file]:
                    if not os.path.exists(self.template_dir_path):
                        os.mkdir(self.template_dir_path)
                    with open(os.path.join(self.template_dir_path,
                                           str(resp[KEY__document_id]) + "." + resp[KEY__render_as]), "wb") as f:
                        f.write(content)
                else:
                    inputs[KEY__content] = content

                execute_supplied_statement(self.db_interface, QUERY__mark_rendered_document_completed, inputs)

                consecutive_failures = 0
            except HttpStatusException as ex:
                consecutive_failures = 0  # This is a properly handled exception

                if ex.response_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                    # When there are no rendered documents, we end up here with a null resp
                    if resp is not None:
                        execute_supplied_statement(self.db_interface,
                            QUERY__mark_rendered_document_completed_with_error,
                            { KEY__document_id: resp[KEY__document_id] })

                    time.sleep(0.25)
                else:
                    traceback.print_exc()
            except Exception as ex:
                consecutive_failures += 1
                print(f"Error in render_document_requests: {ex}")

                if consecutive_failures == 1:
                    # We will now retry the same resp
                    last_resp = resp

                if consecutive_failures >= max_consecutive_failures:
                    print(f"Too many consecutive failures ({consecutive_failures}), attempting Chrome restart")
                    try:
                        self.restart_chrome(reason=f"{consecutive_failures} consecutive failures")
                        consecutive_failures = 0  # Reset after restart
                    except Exception as restart_error:
                        print(f"Failed to restart Chrome: {restart_error}")
                        # Sleep longer if restart fails
                        time.sleep(30)
                else:
                    # Regular error handling
                    time.sleep(min(consecutive_failures * 2, 10))

    def start_chrome(self):
        try:
            self.initialize_chrome_driver()
        except Exception as e:
            print(f"Failed to start Chrome initially: {e}")
            traceback.print_exc()
            # Try once more after a delay
            time.sleep(5)
            self.initialize_chrome_driver()

        # Start the document rendering thread
        threading.Thread(target=self.render_document_requests, daemon=True).start()

        while True:
            current_attachment: 'EmailAttachment' = self.attachments.get()
            try:
                template = document_template__select(self.db_interface, current_attachment.application, current_attachment.name)
                content_path = template[KG__document_template__content_path]
                if not content_path.endswith(".html"):
                    content_path += ".html"
                content_path = current_attachment.template_base + "/" + content_path
                filename, content = self.chrome_page_to_pdf(content_path, current_attachment.access_token, current_attachment.parameters, str(uuid.uuid4()))
                current_attachment.content = content
                current_attachment.filename = filename
            except HttpStatusException as ex:
                self.errored_attachments[current_attachment.id] = str(ex)
            except Exception as ex:
                traceback.print_exc()
                self.errored_attachments[current_attachment.id] = str(ex)
            self.completed_attachments.add(current_attachment.id)


class EmailAttachment:
    def __init__(self, name: str, application: str, parameters: dict, template: str, template_base: str = None):
        self.name = name
        self.application = application
        self.template_base = template_base
        self.parameters = parameters
        self.id = str(uuid.uuid4())
        self.filename = None
        self.content = None
        self.access_token = None
        self.template = str(template)

    @staticmethod
    def static_format_attached_url(template_base_url: str, is_container: bool):
        if not template_base_url.startswith("https://") and not template_base_url.startswith("http://"):
            if is_container:
                if check_allowable_file_path(template_base_url):
                    raise Exception("Illegal template base url: '" + template_base_url + "'")

            if template_base_url.startswith("file:///"):
                return template_base_url
            else:
                return "file://" + os.environ.get(ENVIRON__install_path, os.getcwd().replace("\\", "/")) + "/www" + template_base_url
        else:
            return template_base_url

    def format_attachment_url(self, template_base_url: str, is_container: bool):
        self.template_base = EmailAttachment.static_format_attached_url(template_base_url, is_container)

    def repr_json(self):
        return dict(name=self.name, application=self.application, parameters=self.parameters,
                    template=self.template, template_base=self.template_base)

    @staticmethod
    def deserialize(attachment: dict, template: str = None, artiface_base_url: str = None):
        if template is not None:
            return EmailAttachment(attachment[KEY__attachment_name], attachment[KEY__attachment_application], attachment[KEY__parameters],
                                   template, artiface_base_url)
        else:
            return EmailAttachment(attachment[KEY__attachment_name], attachment[KEY__attachment_application], attachment[KEY__parameters],
                                   attachment[KEY__template], attachment[KEY__template_base])

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

    def build_attachment(self, access_token: str, driven_chrome: DrivenChrome, is_gunicorn: bool) -> MIMEApplication:
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

        if not is_gunicorn:
            os.makedirs("rendered_templates", exist_ok=True)
            with open("rendered_templates/" + self.filename, "wb") as f:
                f.write(self.content)

        return attachment


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

        self.driven_chrome = DrivenChrome(connection, self.db_crypt_key, self.is_gunicorn)

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
                message_final.attach(attachment.build_attachment(email.attachment_access_token, self.driven_chrome, self.is_gunicorn))

        return send_body, message_final

    def is_connected(self, conn: SMTP):
        try:
            status = conn.noop()[0]
        except:
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

        context = ssl.create_default_context()

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
        for dispatcher_key, dispatcher_tuple in potentially_require_threads.items():
            threading.Thread(target=self.dispatcher_thread, args=[dispatcher_key, dispatcher_tuple[0]]).start()

    def get_dispatcher_queue_from_key(self, dispatcher_key: str) -> Queue:
        _, ret = self.dispatchers.get(dispatcher_key, (None, self.threadsafe_queue_initialiser.fetch_queue(dispatcher_key)))
        return ret

    def get_dispatcher_info_from_key(self, dispatcher_key: str) -> Union[dict, None]:
        info, _ = self.dispatchers.get(dispatcher_key, (None, None))
        return info

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

        if whitelist is not None and whitelist != "" and os.environ.get("JAAQL_USE_EMAIL_WHITELIST") == "TRUE":
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
