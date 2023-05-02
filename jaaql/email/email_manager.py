import re

from typing import Callable
from jaaql.email.email_manager_service import Email
import requests
from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.constants import *
from urllib.parse import quote
from jaaql.utilities.utils_no_project_imports import load_artifact
from typing import Optional
from jaaql.mvc.handmade_queries import *
from jaaql.db.db_utils_no_circ import submit
from jaaql.interpreter.interpret_jaaql import KEY_query, KEY_parameters, KEY_assert, ASSERT_one

REGEX__object_name = r'^[0-9a-zA-Z_]{1,63}$'

ERR__invalid_object_name = "Object name '%s' is invalid. Must match regex: " + REGEX__object_name

REGEX__email_parameter = r'({{)([a-zA-Z0-9_\-]+)(}})'
REGEX__email_uri_encoded_parameter = r'(\[\[)([a-zA-Z0-9_\-]+)(\]\])'
REPLACE__str = "{{%s}}"
REPLACE__uri_encoded_str = "[[%s]]"
ERR__missing_parameter = "Missing parameter from template '%s'"
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

    def send_email(self, vault, config, db_crypt_key, jaaql_connection, application: str, template: str, application_artifacts_source: str,
                   application_base_url: str, account_id: str, parameters: dict = None, parameter_id: str = None, none_sanitized_parameters: dict = None):
        if none_sanitized_parameters is None:
            none_sanitized_parameters = {}

        account = account__select(jaaql_connection, db_crypt_key, account_id)
        template = email_template__select(jaaql_connection, application, template)

        if parameters is not None and len(parameters) == 0:
            parameters = None

        if template[KG__email_template__validation_schema] is None and parameters is not None:
            raise HttpStatusException(ERR__unexpected_parameters)
        if template[KG__email_template__validation_schema] is not None and parameters is None:
            raise HttpStatusException(ERR__expected_parameters)

        if parameters is not None:
            ins_query = "INSERT INTO %s (%s) VALUES (%s) RETURNING id"

            if parameter_id is not None:
                parameters[KEY__id] = parameter_id

            for col, _ in parameters.items():
                if not re.match(REGEX__object_name, col):
                    raise HttpStatusException(ERR__invalid_object_name % col)

            cols = ", ".join(['"' + key + '"' for key in parameters.keys()])
            vals = ", ".join([':' + key for key in parameters.keys()])

            ins_query = ins_query % (template[KG__email_template__data_validation_table], cols, vals)
            submit(vault, config, db_crypt_key, jaaql_connection, {
                KEY__application: application,
                KEY__schema: template[KG__email_template__validation_schema],
                KEY_query: ins_query,
                KEY_parameters: parameters,
                KEY_assert: ASSERT_one
            }, account_id)
            parameter_id = execute_supplied_statement_singleton(jaaql_connection, ins_query, parameters, as_objects=True)[KEY__id]

            sel_table = \
                template[KG__email_template__data_validation_table] if template[KG__email_template__data_validation_view] is None \
                else template[KG__email_template__data_validation_view]

            sel_query = "SELECT * FROM %s WHERE id = :id" % sel_table
            submit(vault, config, db_crypt_key, jaaql_connection, {
                KEY__application: application,
                KEY__schema: template[KG__email_template__validation_schema],
                KEY_query: sel_query,
                KEY_parameters: parameters,
                KEY_assert: ASSERT_one
            }, account_id)
            parameters = execute_supplied_statement_singleton(jaaql_connection, sel_query, {KEY__id: parameter_id}, as_objects=True)
        else:
            parameters = {}

        none_sanitized_parameters[EMAIL_PARAM__app_url] = application_base_url
        none_sanitized_parameters[EMAIL_PARAM__email_address] = account[KG__account__username]
        parameters = {**parameters, **none_sanitized_parameters}

        self.construct_and_send_email(application_artifacts_source, template[KG__email_template__dispatcher], template,
                                      account[KG__account__username], parameters)

    def construct_and_send_email(self, application_artifacts_source: Optional[str], dispatcher: str, template: dict, to_email: str,
                                 parameters: Optional[dict], attachments=None, attachment_access_token: str = None):
        loaded_template = load_artifact(self.is_container, application_artifacts_source, template[KG__email_template__content_url])

        loaded_template = self.perform_replacements(loaded_template, REPLACE__str, str, REGEX__email_parameter, parameters)
        loaded_template = self.perform_replacements(loaded_template, REPLACE__uri_encoded_str, EmailManager.uri_encode_replace,
                                                    REGEX__email_uri_encoded_parameter, parameters)

        first_line = loaded_template.split("\n")[0].strip()
        if SUBJECT_MARKER not in first_line:
            raise HttpStatusException("Email template does not have a subject on the first line denoted by 'Subject: '")
        subject = first_line.split(SUBJECT_MARKER)[1].strip()
        body = "\n".join(loaded_template.split("\n")[1:]).strip()

        if template[KG__email_template__content_url].lower().endswith(".htmlbody"):
            body = EMAIL_HTML__start + body + EMAIL_HTML__end

        if attachments is not None:
            attachment_list = attachments
            if not isinstance(attachment_list, list):
                attachment_list = [attachment_list]
            for attachment in attachment_list:
                attachment.format_attachment_url(application_artifacts_source, self.is_container)

        self._send_email(Email(template[KEY__application], template[KG__email_template__name], dispatcher, to_email, subject, body,
                               attachments=attachments, attachment_access_token=attachment_access_token))

    def perform_replacements(self, html_template: str, replace_str: str, replace_func: Callable, replace_regex: str, args: dict = None):
        if args is None:
            args = {}

        for key, val in args.items():
            html_template = html_template.replace(replace_str % key.upper(), replace_func(val))

        matched = re.findall(replace_regex, html_template)
        if len(matched) != 0:
            raise HttpStatusException(ERR__missing_parameter % matched[0][1])

        return html_template
