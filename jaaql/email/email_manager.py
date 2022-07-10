import re
import threading

from typing import Callable
from jaaql.email.email_manager_service import Email, TYPE__email_attachments
import requests
from os.path import join
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.constants import *
from urllib.parse import quote
import time

REGEX__email_parameter = r'({{)([a-zA-Z0-9_\-]+)(}})'
REGEX__email_uri_encoded_parameter = r'(\[\[)([a-zA-Z0-9_\-]+)(\]\])'
REPLACE__str = "{{%s}}"
REPLACE__uri_encoded_str = "[[%s]]"
ERR__missing_parameter = "Missing parameter from template '%s'"
ERR__unexpected_parameter_in_template = "Unexpected parameter in template '%s'"


class EmailManager:

    def send_email(self, email: Email):
        requests.post("http://127.0.0.1:" + str(PORT__ems) + ENDPOINT__send_email, json=email.repr_json())

    def wait_and_then_reload_service(self):
        time.sleep(0.5)
        requests.post("http://127.0.0.1:" + str(PORT__ems) + ENDPOINT__reload_accounts)

    def reload_service(self):
        threading.Thread(target=self.wait_and_then_reload_service).start()

    @staticmethod
    def uri_encode_replace(val):
        return quote(str(val))

    def construct_and_send_email(self, base_url: str, app_url: str, template: dict, sender: str, to_email: str, to_name: str,
                                 parameters: dict = None, optional_parameters: dict = None, attachments: TYPE__email_attachments = None,
                                 attachment_access_token: str = None):
        loaded_template = self.load_template(base_url, app_url, template[KEY__app_relative_path])
        if loaded_template is None:
            return

        subject, loaded_template = self.perform_replacements(template[KEY__subject], loaded_template, REPLACE__str, str, REGEX__email_parameter,
                                                             parameters, optional_parameters)
        subject, loaded_template = self.perform_replacements(subject, loaded_template, REPLACE__uri_encoded_str, EmailManager.uri_encode_replace,
                                                             REGEX__email_uri_encoded_parameter, parameters, optional_parameters)

        self.send_email(Email(str(sender), str(template[KEY__id]), str(template[KEY__account]), to_email, to_name, subject=subject,
                              body=loaded_template, is_html=True, attachments=attachments, attachment_access_token=attachment_access_token))

    def load_template(self, base_url: str, app_url: str, app_relative_path: str):
        if app_relative_path is None:
            return None

        if not app_relative_path.endswith(".html"):
            app_relative_path = app_relative_path + ".html"
        if app_url is None or app_url.startswith(base_url) or (
                not app_url.startswith("https://") and not app_url.startswith("http://")):
            return open(join("www", "templates", app_relative_path), "r").read()
        else:
            return requests.get("/".join(app_url.split("/")[:-1]) + "/templates/" + app_relative_path).text

    def perform_replacements(self, subject: str, html_template: str, replace_str: str, replace_func: Callable, replace_regex: str, args: dict = None,
                             optional_args: dict = None):
        if args is None:
            args = {}
        if optional_args is None:
            optional_args = {}

        for key, val in args.items():
            new_template = html_template.replace(replace_str % key.upper(), replace_func(val))
            new_subject = subject.replace(replace_str % key.upper(), replace_func(val))
            if new_template == html_template and subject == new_subject:
                raise HttpStatusException(ERR__unexpected_parameter_in_template % key)
            html_template = new_template
            subject = new_subject

        for key, val in optional_args.items():
            subject = subject.replace(replace_str % key.upper(), replace_func(val))
            html_template = html_template.replace(replace_str % key.upper(), replace_func(val))

        matched = re.findall(replace_regex, html_template)
        matched = matched + re.findall(replace_regex, subject)
        if len(matched) != 0:
            raise HttpStatusException(ERR__missing_parameter % matched[0][1])

        return subject, html_template
