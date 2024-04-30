import re

from typing import Callable
from jaaql.email.email_manager_service import Email
import requests
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.constants import *
from urllib.parse import quote
from jaaql.utilities.utils_no_project_imports import load_template
from typing import Optional
from jaaql.mvc.handmade_queries import *

REGEX__html_entities = r'<.*?>'
REGEX__object_name = r'^[0-9a-zA-Z_]{1,63}$'

ERR__invalid_object_name = "Object name '%s' is invalid. Must match regex: " + REGEX__object_name

REGEX__email_parameter = r'({{)([a-zA-Z0-9_\-]+)(}})'
REGEX__email_uri_encoded_parameter = r'(\[\[)([a-zA-Z0-9_\-]+)(\]\])'
REPLACE__str = "{{%s}}"
REPLACE__uri_encoded_str = "[[%s]]"
ERR__missing_parameter = "Missing replacement parameter '%s' found in template but not in replacement variables. Available variables are: %s"
ERR__unexpected_parameter_in_template = "Unexpected parameter in template '%s'"

EMAIL_HTML__start = "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">\r\n<html xmlns=\"http://www.w3.org/1999/xhtml\" lang=\"en\">\r\n<body>\r\n"
EMAIL_HTML__end = "\r\n</body>\r\n</html>"

SUBJECT_MARKER = "Subject: "

ERR__unexpected_parameters = "Email parameters were not expected"
ERR__expected_parameters = "Email parameters were expected"


class EmailManager:

    def __init__(self, is_container: bool):
        self.is_container = is_container

    def _send_email(self, email: Email):
        requests.post("http://127.0.0.1:" + str(PORT__ems) + ENDPOINT__send_email, json=email.repr_json())

    @staticmethod
    def uri_encode_replace(val):
        return quote(str(val))

    @staticmethod
    def replace_html_tags(val):
        return re.sub(REGEX__html_entities, "", val)

    @staticmethod
    def replace_tags_then_encode(val):
        return EmailManager.uri_encode_replace(EmailManager.replace_html_tags(val))

    def construct_and_send_email(self, application_templates_source: Optional[str], dispatcher: str, template: dict, to_email: str,
                                 parameters: Optional[dict], attachments=None, attachment_access_token: str = None,
                                 attachment_base_url: str = ""):
        loaded_template = load_template(self.is_container, application_templates_source, template[KG__email_template__content_url])

        loaded_template = self.perform_replacements(loaded_template, REPLACE__str, EmailManager.replace_html_tags, REGEX__email_parameter, parameters)
        loaded_template = self.perform_replacements(loaded_template, REPLACE__uri_encoded_str, EmailManager.replace_tags_then_encode,
                                                    REGEX__email_uri_encoded_parameter, parameters)

        first_line = loaded_template.split("\n")[0].strip()
        if SUBJECT_MARKER not in first_line:
            raise HttpStatusException("Email template does not have a subject on the first line denoted by 'Subject: '")
        subject = first_line.split(SUBJECT_MARKER)[1].strip()
        body = "\n".join(loaded_template.split("\n")[1:]).strip()

        if template[KG__email_template__content_url].lower().endswith(".template"):
            body = EMAIL_HTML__start + body + EMAIL_HTML__end

        if attachments is not None:
            attachment_list = attachments
            if not isinstance(attachment_list, list):
                attachment_list = [attachment_list]
            for attachment in attachment_list:
                attachment.format_attachment_url(attachment_base_url, self.is_container)

        self._send_email(Email(template[KEY__application], template[KG__email_template__name], dispatcher, to_email, subject, body,
                               attachments=attachments, attachment_access_token=attachment_access_token))

    def perform_replacements(self, html_template: str, replace_str: str, replace_func: Callable, replace_regex: str, args: dict = None):
        if args is None:
            args = {}

        for key, val in args.items():
            replace_val = str(val)
            html_template = html_template.replace(replace_str % key.upper(), replace_func(replace_val))

        matched = re.findall(replace_regex, html_template)
        if len(matched) != 0:
            raise HttpStatusException(ERR__missing_parameter % (matched[0][1], str(list(args.keys()))))

        return html_template
