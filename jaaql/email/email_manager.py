import os
import re
import threading

from typing import Callable
from jaaql.email.email_manager_service import Email, TYPE__email_attachments
import requests
from os.path import join
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.constants import *
from urllib.parse import quote
from jaaql.utilities.utils_no_project_imports import load_artifact
import time

REGEX__email_parameter = r'({{)([a-zA-Z0-9_\-]+)(}})'
REGEX__email_uri_encoded_parameter = r'(\[\[)([a-zA-Z0-9_\-]+)(\]\])'
REPLACE__str = "{{%s}}"
REPLACE__uri_encoded_str = "[[%s]]"
ERR__missing_parameter = "Missing parameter from template '%s'"
ERR__unexpected_parameter_in_template = "Unexpected parameter in template '%s'"


class EmailManager:

    def __init__(self, is_container: bool):
        self.is_container = is_container

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

    def construct_and_send_email(self, artifact_base_uri: str, template: dict, sender: str, to_email: str, to_name: str,
                                 parameters: dict = None, optional_parameters: dict = None, attachments: TYPE__email_attachments = None,
                                 attachment_access_token: str = None):
        loaded_template = load_artifact(self.is_container, artifact_base_uri, template[KEY__app_relative_path])
        if loaded_template is None:
            return

        optional_parameters["EMAIL_ADDRESS"] = to_email
        subject, loaded_template = self.perform_replacements(template[KEY__subject], loaded_template, REPLACE__str, str, REGEX__email_parameter,
                                                             parameters, optional_parameters)
        subject, loaded_template = self.perform_replacements(subject, loaded_template, REPLACE__uri_encoded_str, EmailManager.uri_encode_replace,
                                                             REGEX__email_uri_encoded_parameter, parameters, optional_parameters)

        if attachments is not None:
            attachment_list = attachments
            if not isinstance(attachment_list, list):
                attachment_list = [attachment_list]
            for attachment in attachment_list:
                attachment.format_attachment_url(artifact_base_uri, self.is_container)

        self.send_email(Email(str(sender), template[KEY__application], str(template[KEY__email_template_name]), str(template[KEY__account]),
                              to_email, to_name, subject=subject, body=loaded_template, is_html=True, attachments=attachments,
                              attachment_access_token=attachment_access_token, override_send_name=template[KEY__override_send_name]))

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
