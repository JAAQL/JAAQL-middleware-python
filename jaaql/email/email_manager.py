import re

from jaaql.email.email_manager_service import Email, TYPE__email_attachments
import requests
from os.path import join
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.constants import *

REGEX__email_parameter = r'({{)([a-zA-Z0-9_\-]+)(}})'
REPLACE__str = "{{%s}}"
ERR__missing_parameter = "Missing parameter from template '%s'"
ERR__unexpected_parameter_in_template = "Unexpected parameter in template '%s'"


class EmailManager:

    def send_email(self, email: Email):
        requests.post("http://127.0.0.1:" + str(PORT__ems) + "/send-email", json=email.repr_json())

    def reload_service(self):
        requests.post("http://127.0.0.1:" + str(PORT__ems) + "/" + ENDPOINT__reload_accounts)

    def construct_and_send_email(self, base_url: str, app_url: str, template: dict, sender: str, to_email: str, to_name: str,
                                 parameters: dict = None, optional_parameters: dict = None, attachments: TYPE__email_attachments = None):
        loaded_template = self.load_template(base_url, app_url, template[KEY__app_relative_path])
        if loaded_template is None:
            return

        subject, loaded_template = self.perform_replacements(template[KEY__subject], loaded_template, parameters, optional_parameters)

        self.send_email(Email(sender, template[KEY__id], template[KEY__account], to_email, to_name, subject=subject, body=loaded_template,
                              is_html=True, attachments=attachments))

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

    def perform_replacements(self, subject: str, html_template: str, args: dict = None, optional_args: dict = None):
        if args is None:
            args = {}
        if optional_args is None:
            optional_args = {}

        for key, val in args.items():
            new_template = html_template.replace(REPLACE__str % key.upper(), str(val))
            new_subject = subject.replace(REPLACE__str % key.upper(), str(val))
            if new_template == html_template and subject == new_subject:
                raise HttpStatusException(ERR__unexpected_parameter_in_template % key)
            html_template = new_template
            subject = new_subject

        for key, val in optional_args.items():
            subject = subject.replace(REPLACE__str % key.upper(), str(val))
            html_template = html_template.replace(REPLACE__str % key.upper(), str(val))

        matched = re.findall(REGEX__email_parameter, html_template)
        matched = matched + re.findall(REGEX__email_parameter, subject)
        if len(matched) != 0:
            raise HttpStatusException(ERR__missing_parameter % matched[0][1])

        return subject, html_template