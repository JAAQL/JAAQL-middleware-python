from jaaql.email.email_manager_service import EmailAttachment
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jwt_crypt_key
from jaaql.exceptions.http_status_exception import HttpStatusException, HTTPStatus, ERR__already_installed, ERR__already_signed_up
from jaaql.constants import *
from os.path import join
from jaaql.mvc.response import JAAQLResponse
from jaaql.db.db_interface import DBInterface, RET__rows
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.mvc.queries import *
from jaaql.utilities.utils import get_jaaql_root
from jaaql.db.db_utils import execute_supplied_statement, execute_supplied_statement_singleton, create_interface, jaaql__encrypt
from jaaql.utilities import crypt_utils
from io import BytesIO
from flask import send_file
import threading
from datetime import datetime, timedelta
from jaaql.mvc.base_model import JAAQLPivotInfo
from os.path import dirname
from jwt.utils import base64url_decode
import uuid
import json
import random
import os
from queue import Queue

ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__invalid_level = "Invalid level!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__email_template_not_installed = "Either email template does not exist or email template has not been attached to this application configuration"
ERR__lacking_permissions = "Only an administrator can perform this action!"
ERR__schema_invalid = "Schema invalid!"
ERR__cant_send_attachments = "Cannot send attachments to other people"
ERR__keep_alive_failed = "Keep alive failed"
ERR__template_not_signup = "One of the supplied templates is not suitable for signup"
ERR__unexpected_parameters = "Signup data not expected"
ERR__unexpected_validation_column = "Unexpected column in the input parameters '%s'"
ERR__data_validation_table_no_primary = "Data validation table has no primary key"
ERR__cant_find_sign_up = "Cannot locate sign up with key. The key is either incorrect, has expired or has not been activated with the emailed code"
ERR__invite_code_expired = "Invite code expired. Please use the link within the email"
ERR__incorrect_invite_code = "Incorrect invite code"
ERR__template_reset_password = "You cannot use this template to reset your password"
ERR__cant_find_reset = "Cannot locate reset with key. The key is either incorrect, has expired or has not been activated with the emailed code"
ERR__reset_code_expired = "Reset code expired. Please use the link within the email"
ERR__incorrect_reset_code = "Incorrect reset code"
ERR__as_attachment_unexpected = "Input 'as_attachment' unexpected as document is returned as a file link"
ERR__document_created_file = "Document is a file, cannot be downloaded in this way"

PG__default_connection_string = "postgresql://postgres:%s@localhost:5432/jaaql"
DIR__scripts = "scripts"

MODIFIER__allow_conflicts = " ON CONFLICT DO NOTHING"

ATTR__version = "version"
ATTR__count = "count"
ATTR__the_user = "the_user"
ATTR__data_lookup_json = "data_lookup_json"
ATTR__activated = "activated"
ATTR__code_attempts = "code_attempts"
ATTR__closed = "closed"
ATTR__created = "created"
ATTR__expiry_code_ms = "code_expiry_ms"
ATTR__used_key_a = "used_key_a"

SQL__err_duplicate_user = "duplicate key value violates unique constraint \"account_unq_email\""

RESEND__invite_max = 2
RESEND__invite_not_registered_max = 3
RESEND__reset_max = 2
RESET__not_started = 0
RESET__started = 1
RESET__completed = 2

CODE__letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CODE__invite_length = 5
CODE__max_attempts = 3
CODE__alphanumeric = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
CODE__reset_length = 8

SIGNUP__not_started = 0
SIGNUP__started = 1
SIGNUP__already_registered = 2
SIGNUP__completed = 3


class JAAQLModel(BaseJAAQLModel):

    VERIFICATION_QUEUE = None
    LOG_QUEUE = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        JAAQLModel.LOG_QUEUE = Queue()
        threading.Thread(target=self.log_thread, args=[JAAQLModel.LOG_QUEUE])

    def check_is_internal_admin(self, connection: DBInterface):
        execute_supplied_statement(connection, QUERY__fetch_internal_admin)

    def log(self, user_id: str, occurred: datetime, duration_ms: int, exception: str, contr_input: str, ip: str, status: int, endpoint: str):
        JAAQLModel.LOG_QUEUE.put({
            KEY__user_id: user_id,
            KEY__occurred: occurred.isoformat(),
            KEY__duration_ms: duration_ms,
            KEY__exception: exception,
            KEY__input: contr_input,
            KEY__ip: ip,
            KEY__status: int(status),
            KEY__endpoint: endpoint
        })

    def log_thread(self, log_queue: Queue):
        while True:
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__log_ins, log_queue.get())

    def drop_email_account(self, connection: DBInterface, name: str):
        execute_supplied_statement(connection, QUERY__drop_email_account, {KEY__name: name})
        self.email_manager.reload_service()

    def redeploy(self, connection: DBInterface):
        self.check_is_internal_admin(connection)

        if self.is_container:
            f = open("/JAAQL-middleware-python/redeploy", "w")
        else:
            f = open(join(dirname(get_jaaql_root()), "redeploy"), "w")
        f.write("Will be detected and redeployment will now happen")
        f.close()

        print("Redeploying JAAQL")

        threading.Thread(target=self.exit_jaaql, daemon=True).start()

    def add_account_password(self, user_id: str, password: str):
        crypt_utils.validate_password(password)
        salt = self.get_repeatable_salt(user_id)
        password = crypt_utils.hash_password(password, salt)
        password_id = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__add_password,
                                                           {KEY__account: user_id, KEY__password_hash: password},
                                                           encryption_key=self.get_db_crypt_key(), encryption_salts={KEY__password_hash: salt},
                                                           encrypt_parameters=[KEY__password_hash], as_objects=True)[KEY__id]
        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__add_password_cache, {KEY__account: user_id, KEY__password: password_id})

    def add_my_account_password(self, user_id: str, username: str, ip_address: str, old_password: str, password: str):
        res = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_recent_passwords_with_account, {KEY__user_id: user_id},
                                                   decrypt_columns=[KEY__password_hash], encryption_key=self.get_db_crypt_key())
        if not crypt_utils.verify_password_hash(res[KEY__password_hash], old_password, salt=self.get_repeatable_salt(user_id)):
            raise HttpStatusException(ERR__incorrect_credentials)
        self.add_account_password(password, user_id)
        return self.get_auth_token(password=password, ip_address=ip_address, username=username)

    def fetch_user_from_username(self, username: str, singleton_message: str = None, singleton_code: int = None):
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_user_from_username, {KEY__username: username},
                                                    encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__username],
                                                    encryption_salts={KEY__username: self.get_repeatable_salt()}, as_objects=True,
                                                    singleton_code=singleton_code, singleton_message=singleton_message)[KEY__user_id]

    def fetch_user_record_from_username(self, username: str):
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_user_record_from_username, {KEY__username: username},
                                                    encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__username],
                                                    encryption_salts={KEY__username: self.get_repeatable_salt()}, as_objects=True)

    def select_from_data_validation_table(self, connection: DBInterface, val_table: str, pkey_vals: dict):
        val_table_esc = '"%s"' % val_table
        pkeys_where = " AND ".join(['"' + col + '" = :' + col for col in pkey_vals.keys()])
        sel_query = "SELECT * FROM " + val_table_esc + " WHERE " + pkeys_where
        sanitized_params = execute_supplied_statement_singleton(connection, sel_query, pkey_vals, as_objects=True)

        return {key: value for key, value in sanitized_params.items() if key not in pkey_vals}

    def fetch_sanitized_email_params(self, connection: DBInterface, template: dict, params: dict):
        val_table = template[KEY__data_validation_table]
        val_cols = execute_supplied_statement(connection, QUERY__fetch_table_columns,
                                              {KEY__table_name: val_table}, as_objects=True)
        primary_cols = [val_col[KEY__column_name] for val_col in val_cols if val_col[KEY__is_primary]]
        val_cols = [val_col[KEY__column_name] for val_col in val_cols]

        for col in params.keys():
            if col not in val_cols:
                raise HttpStatusException(ERR__unexpected_validation_column % col)

        cols = ", ".join(['"' + col + '"' for col in val_cols if col in params.keys()])
        ins = ", ".join([':' + col for col in val_cols if col in params.keys()])
        pkeys = ", ".join(['"' + col + '"' for col in primary_cols])
        if len(pkeys) == 0:
            raise HttpStatusException(ERR__data_validation_table_no_primary)
        val_table_esc = '"%s"' % val_table
        ins_query = "INSERT INTO " + val_table_esc + " (" + cols + ") VALUES (" + ins + ") RETURNING " + pkeys
        pkey_vals = execute_supplied_statement_singleton(connection, ins_query, params, as_objects=True)
        pkey_vals = {key: str(val) if isinstance(val, uuid.UUID) else val for key, val in pkey_vals.items()}
        select_table = template[KEY__data_validation_view] if template[KEY__data_validation_view] is not None else val_table
        return self.select_from_data_validation_table(connection, select_table, pkey_vals), pkey_vals

    def user_invite(self, user_id: str, application: str = None, configuration: str = None, email_template: str = None,
                    template_lookup: dict = None):
        if template_lookup is not None:
            template_lookup = json.dumps(template_lookup)

        params = {
            ATTR__data_lookup_json: template_lookup,
            ATTR__the_user: user_id,
            KEY__application: application,
            KEY__configuration: configuration,
            KEY__email_template: email_template,
            KEY__invite_code: "".join([CODE__letters[random.randint(0, len(CODE__letters) - 1)] for _ in range(CODE__invite_length)])
        }
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_insert, params, as_objects=True)

    def fetch_interface(self, application: str, configuration: str, schema: str):
        """
        TODO this won't work. Used for emails, needs to be the database admin user for a database
        :param application:
        :param configuration:
        :param schema:
        :return:
        """
        schemas = self.fetch_pivoted_application_schemas()
        db_name = schemas[application][configuration][schema][KEY__database]
        return self.create_interface_for_db(ROLE__jaaql, db_name)

    def request_signup(self, inputs: dict):
        template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url, {
            KEY__name: inputs[KEY__email_template],
            KEY__configuration: inputs[KEY__configuration],
            KEY__application: inputs[KEY__application]
        }, as_objects=True, singleton_message=ERR__email_template_not_installed)
        template_already_exists = execute_supplied_statement_singleton(
            self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url, {
                KEY__name: inputs[KEY__already_signed_up_email_template],
                KEY__configuration: inputs[KEY__configuration],
                KEY__application: inputs[KEY__application]
            }, as_objects=True, singleton_message=ERR__email_template_not_installed)
        artifact_url = template.pop(KEY__artifact_base_uri)
        app_url = template.pop(KEY__application_url)

        if not template[KEY__allow_signup] or not template_already_exists[KEY__allow_confirm_signup_attempt]:
            raise HttpStatusException(ERR__template_not_signup)

        user_existed = False
        try:
            user_id = self.create_account(self.jaaql_lookup_connection, {KEY__username: inputs[KEY__email]})
        except HttpStatusException as hs:
            if not hs.message.startswith(SQL__err_duplicate_user):
                raise hs  # Unrelated exception, raise it

            res = self.fetch_user_recent_password(inputs[KEY__email])
            if len(res) == 0:
                user_id = self.fetch_user_from_username(inputs[KEY__email])
            else:
                user_id = res[0][KEY__user_id]
                user_existed = True

        attempts = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_count, {KEY__user_id: user_id},
                                                        as_objects=True)[ATTR__count]
        if user_existed and attempts >= RESEND__invite_max or attempts >= RESEND__invite_not_registered_max:
            raise HttpStatusException(ERR__too_many_signup_attempts, HTTPStatus.TOO_MANY_REQUESTS)

        params = inputs[KEY__parameters]
        if params is not None and len(params) != 0 and template[KEY__data_validation_table] is None:
            raise HttpStatusException(ERR__unexpected_parameters)
        if params is not None and len(params) == 0:
            params = None
        if params is None and template[KEY__data_validation_table] is not None:
            params = {}

        template = template_already_exists if user_existed else template

        sanitized_params = {}
        pkey_vals = None
        if template[KEY__data_validation_table] is not None:
            if EMAIL_PARAM__signup_key in params:
                raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__signup_key)
            if EMAIL_PARAM__invite_code in params:
                raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__invite_code)
            if EMAIL_PARAM__app_url in params:
                raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__app_url)

            interface = self.fetch_interface(template[KEY__application], inputs[KEY__configuration], template[KEY__schema])
            sanitized_params, pkey_vals = self.fetch_sanitized_email_params(interface, template, params)

        invite_keys = self.user_invite(user_id, inputs[KEY__application], inputs[KEY__configuration], template[KEY__name], pkey_vals)
        optional_params = {EMAIL_PARAM__signup_key: invite_keys[KEY__invite_key], EMAIL_PARAM__invite_code: invite_keys[KEY__invite_code],
                           EMAIL_PARAM__app_url: app_url}
        optional_params = {**optional_params, **sanitized_params}

        self.email_manager.construct_and_send_email(artifact_url, template, user_id, inputs[KEY__email], None, {}, optional_params)

        return {KEY__invite_key: invite_keys[KEY__invite_poll_key]}

    def signup_status(self, inputs: dict):
        select_param = {KEY__invite_or_poll_key: inputs[KEY__invite_or_poll_key]}
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_poll, parameters=select_param, as_objects=True,
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    singleton_message=ERR__cant_find_sign_up)

        res = self.fetch_user_recent_password(resp[KEY__email])
        existed = len(res) != 0

        is_invite_key = str(resp[KEY__invite_key]) == inputs[KEY__invite_or_poll_key]

        if not is_invite_key and not resp[ATTR__activated] and resp[ATTR__code_attempts] >= CODE__max_attempts:
            raise HttpStatusException(ERR__too_many_code_attempts, HTTPStatus.LOCKED)

        status = SIGNUP__not_started

        invite_code_match = inputs.get(KEY__invite_code) == resp[KEY__invite_code]
        timezone = resp[ATTR__created].tzinfo
        invite_code_expired = resp[ATTR__created] + timedelta(milliseconds=resp[ATTR__expiry_code_ms]) < datetime.now(timezone)

        if is_invite_key or resp[ATTR__activated] or (invite_code_match and not invite_code_expired):
            if invite_code_match and not resp[ATTR__activated]:
                execute_supplied_statement(self.jaaql_lookup_connection, QUERY__sign_up_upd, {KEY__invite_key: resp[KEY__invite_key]})
            elif not resp[ATTR__used_key_a]:
                execute_supplied_statement(self.jaaql_lookup_connection, QUERY__sign_up_upd_used, {KEY__invite_key: resp[KEY__invite_key]})

            if resp[ATTR__closed]:
                status = SIGNUP__completed
            elif existed:
                status = SIGNUP__already_registered
            elif resp[ATTR__activated] or resp[ATTR__used_key_a]:
                status = SIGNUP__started

        elif invite_code_match:
            raise HttpStatusException(ERR__invite_code_expired)
        else:
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__sign_up_increment_attempts, {KEY__invite_key: resp[KEY__invite_key]})
            raise HttpStatusException(ERR__incorrect_invite_code)

        return {KEY__invite_key_status: status}

    def fetch_user_recent_password(self, username: str):
        res = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_recent_passwords, {
            KEY__enc_username: username
        }, encryption_salts={KEY__enc_username: self.get_repeatable_salt()}, decrypt_columns=[KEY__password_hash, KEY__username],
                                         encrypt_parameters=[KEY__enc_username], encryption_key=self.get_db_crypt_key(), as_objects=True)
        return res

    def sign_up_user_with_token(self, token: str, password: str):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_fetch, parameters={KEY__invite_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)

        username = resp[KEY__email]

        res = self.fetch_user_recent_password(username)

        if len(res) != 0:
            raise HttpStatusException(ERR__already_signed_up, response_code=HTTPStatus.CONFLICT)

        self.add_account_password(self.fetch_user_from_username(username), password)

        return {KEY__email: username}

    def fetch_signup(self, token: str):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_fetch, parameters={KEY__invite_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)

        res = {}
        if resp[KEY__email_template] and resp[ATTR__data_lookup_json]:
            template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url,
                                                            {KEY__name: resp[KEY__email_template],
                                                             KEY__configuration: resp[KEY__configuration], KEY__application: resp[KEY__application]},
                                                            as_objects=True)
            interface = self.fetch_interface(template[KEY__application], resp[KEY__configuration], template[KEY__schema])
            res[KEY__parameters] = self.select_from_data_validation_table(interface, template[KEY__data_validation_table],
                                                                          json.loads(resp[ATTR__data_lookup_json]))

        return res

    def delete_from_data_validation_table(self, connection: DBInterface, val_table: str, pkey_vals: dict):
        val_table_esc = '"%s"' % val_table
        pkeys_where = " AND ".join(['"' + col + '" = :' + col for col in pkey_vals.keys()])
        pkeys_returning = ",".join(['"' + col + '"' for col in pkey_vals.keys()])
        del_query = "DELETE FROM " + val_table_esc + " WHERE " + pkeys_where + " RETURNING " + pkeys_returning
        execute_supplied_statement_singleton(connection, del_query, pkey_vals)

    def finish_signup(self, token: str):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_fetch, parameters={KEY__invite_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)

        if resp[KEY__email_template] and resp[ATTR__data_lookup_json]:
            template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url,
                                                            {KEY__name: resp[KEY__email_template],
                                                             KEY__configuration: resp[KEY__configuration]},
                                                            as_objects=True)[KEY__data_validation_table]
            interface = self.fetch_interface(template[KEY__application], resp[KEY__configuration], template[KEY__schema])
            self.delete_from_data_validation_table(interface, template, json.loads(resp[ATTR__data_lookup_json]))

        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__sign_up_close, {KEY__invite_key: resp[KEY__invite_key]})

    def send_reset_password_email(self, inputs: dict):
        template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url, {
            KEY__name: inputs[KEY__email_template],
            KEY__configuration: inputs[KEY__configuration],
            KEY__application: inputs[KEY__application]
        }, as_objects=True, singleton_message=ERR__email_template_not_installed)
        app_url = template.pop(KEY__application_url)
        artifact_url = template.pop(KEY__artifact_base_uri)

        if not template[KEY__allow_reset_password]:
            raise HttpStatusException(ERR__template_reset_password)

        user_exists = True
        user = None
        try:
            user = self.fetch_user_record_from_username(inputs[KEY__email])
        except HttpStatusException:
            user_exists = False

        if user_exists and user[KEY__application] is not None:
            raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)

        if user_exists:
            attempts = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_count, {ATTR__the_user: user[KEY__user_id]},
                                                            as_objects=True)[ATTR__count]
        else:
            attempts = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fake_reset_count,
                                                            {KEY__email: inputs[KEY__email]},
                                                            encryption_key=self.get_db_crypt_key(),
                                                            encryption_salts={KEY__email: self.get_repeatable_salt()},
                                                            encrypt_parameters=[KEY__email], as_objects=True)[ATTR__count]
        if attempts >= RESEND__reset_max:
            raise HttpStatusException(ERR__too_many_reset_requests, HTTPStatus.TOO_MANY_REQUESTS)

        if user_exists:
            params = inputs[KEY__parameters]
            if params is not None and template[KEY__data_validation_table] is None:
                raise HttpStatusException(ERR__unexpected_parameters)
            if params is None and template[KEY__data_validation_table] is not None:
                params = {}

            sanitized_params = {}
            pkey_vals = None

            if template[KEY__data_validation_table] is not None:
                if EMAIL_PARAM__reset_key in params:
                    raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__reset_key)
                if EMAIL_PARAM__reset_code in params:
                    raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__reset_code)
                if EMAIL_PARAM__app_url in params:
                    raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__app_url)

                interface = self.fetch_interface(template[KEY__application], inputs[KEY__configuration], template[KEY__schema])
                sanitized_params, pkey_vals = self.fetch_sanitized_email_params(interface, template, params)

            template_lookup = None
            if pkey_vals is not None:
                template_lookup = json.dumps(pkey_vals)
            params = {
                ATTR__data_lookup_json: template_lookup,
                ATTR__the_user: user[KEY__user_id],
                KEY__email_template: template[KEY__name],
                KEY__configuration: inputs[KEY__configuration],
                KEY__application: inputs[KEY__application],
                KEY__reset_code: "".join([CODE__alphanumeric[random.randint(0, len(CODE__alphanumeric) - 1)] for _ in range(CODE__reset_length)])
            }

            reset_keys = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_insert, params, as_objects=True)
            optional_params = {EMAIL_PARAM__reset_key: reset_keys[KEY__reset_key], EMAIL_PARAM__reset_code: reset_keys[KEY__reset_code],
                               EMAIL_PARAM__app_url: app_url}
            optional_params = {**optional_params, **sanitized_params}

            self.email_manager.construct_and_send_email(artifact_url, template, user[KEY__user_id], inputs[KEY__email], None, {}, optional_params)
        else:
            params = {
                KEY__email: inputs[KEY__email],
            }
            reset_keys = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fake_reset_insert, params,
                                                              encryption_key=self.get_db_crypt_key(),
                                                              encryption_salts={KEY__email: self.get_repeatable_salt()},
                                                              encrypt_parameters=[KEY__email], as_objects=True)

        return {KEY__reset_key: reset_keys[KEY__reset_poll_key]}

    def reset_password_status(self, inputs: dict):
        select_param = {KEY__reset_or_poll_key: inputs[KEY__reset_or_poll_key]}
        was_fake = False

        try:
            resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_poll, parameters=select_param, as_objects=True,
                                                        decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                        singleton_message=ERR__cant_find_reset)
        except HttpStatusException as se:
            if se.response_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fake_reset_poll, parameters=select_param,
                                                            decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                            as_objects=True, singleton_message=ERR__cant_find_reset)
                was_fake = True
            else:
                raise se

        is_reset_key = str(resp[KEY__reset_key]) == inputs[KEY__reset_or_poll_key]

        if not is_reset_key and not resp[ATTR__activated] and resp[ATTR__code_attempts] >= CODE__max_attempts:
            raise HttpStatusException(ERR__too_many_code_attempts, HTTPStatus.LOCKED)

        status = RESET__not_started

        reset_code_match = inputs.get(KEY__reset_code) == resp[KEY__reset_code]
        timezone = resp[ATTR__created].tzinfo
        reset_code_expired = resp[ATTR__created] + timedelta(milliseconds=resp[ATTR__expiry_code_ms]) < datetime.now(timezone)

        if is_reset_key or resp[ATTR__activated] or (reset_code_match and not reset_code_expired):
            if reset_code_match and not resp[ATTR__activated]:
                execute_supplied_statement(self.jaaql_lookup_connection, QUERY__reset_upd, {KEY__reset_key: resp[KEY__reset_key]})
            elif not resp[ATTR__used_key_a]:
                execute_supplied_statement(self.jaaql_lookup_connection, QUERY__reset_upd_used, {KEY__reset_key: resp[KEY__reset_key]})

            if resp[ATTR__closed]:
                status = RESET__completed
            elif resp[ATTR__activated] or resp[ATTR__used_key_a]:
                status = RESET__started

        elif reset_code_match:
            raise HttpStatusException(ERR__reset_code_expired)
        else:
            if was_fake:
                execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fake_reset_increment_attempts,
                                           {KEY__reset_key: inputs[KEY__reset_or_poll_key]})
            else:
                execute_supplied_statement(self.jaaql_lookup_connection, QUERY__reset_increment_attempts, {KEY__reset_key: resp[KEY__reset_key]})
            raise HttpStatusException(ERR__incorrect_reset_code)

        return {KEY__reset_key_status: status}

    def fetch_document(self, inputs: dict, response: JAAQLResponse):
        res = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_rendered_document,
                                                   {KEY__document_id: inputs[KEY__document_id]}, singleton_message=ERR__document_id_not_found,
                                                   as_objects=True)

        if not res[KEY__completed]:
            raise HttpStatusException(ERR__document_still_rendering, HTTPStatus.TOO_EARLY)

        if res[KEY__create_file]:
            if inputs[KEY__as_attachment] is not None:
                raise HttpStatusException(ERR__as_attachment_unexpected)
            response.response_code = HTTPStatus.CREATED
            return self.url + "/" + DIR__render_template + "/" + res[KEY__document_id] + "." + res[KEY__render_as]
        else:
            return self.url + "/api/rendered_documents/" + res[KEY__document_id]

    def fetch_document_stream(self, inputs: dict):
        res = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_rendered_document,
                                                   {KEY__document_id: inputs[KEY__document_id]}, singleton_message=ERR__document_id_not_found,
                                                   as_objects=True)

        if not res[KEY__completed]:
            raise HttpStatusException(ERR__document_still_rendering, HTTPStatus.TOO_EARLY)

        if res[KEY__create_file]:
            raise HttpStatusException(ERR__document_created_file)
        else:
            content = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__purge_rendered_document,
                                                           {KEY__document_id: inputs[KEY__document_id]}, as_objects=True)[KEY__content]
            as_attachment = False
            if inputs[KEY__as_attachment]:
                as_attachment = True

            buffer = BytesIO()
            buffer.write(content)
            buffer.seek(0)

            return send_file(buffer, as_attachment=as_attachment, download_name=res[KEY__filename])

    def render_document(self, inputs: dict, auth_token: str, ip_address: str):
        inputs[KEY__oauth_token] = self.refresh_auth_token(auth_token, ip_address)
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__ins_rendered_document, inputs,
                                                    encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__parameters, KEY__oauth_token],
                                                    as_objects=True)

    def send_email(self, inputs: dict, auth_token: str, user_id: str, ip_address: str, username: str):
        if inputs[KEY__recipient] is not None:
            raise HttpStatusException(HTTPStatus.NOT_IMPLEMENTED.description, HTTPStatus.NOT_IMPLEMENTED.value)

        if inputs[KEY__recipient] is not None and inputs[KEY__attachments] is not None:
            raise HttpStatusException(ERR__cant_send_attachments)

        template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url, {
            KEY__name: inputs[KEY__email_template],
            KEY__configuration: inputs[KEY__configuration],
            KEY__application: inputs[KEY__application]
        }, as_objects=True)
        app_url = template.pop(KEY__application_url)
        artifact_url = template.pop(KEY__artifact_base_uri)

        params = inputs[KEY__parameters]
        if params is not None and template[KEY__data_validation_table] is None:
            raise HttpStatusException(ERR__unexpected_parameters)
        if template[KEY__data_validation_table] is not None and params is None:
            params = {}
        if template[KEY__data_validation_table] is not None:
            if EMAIL_PARAM__app_url in params:
                raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__app_url)

            interface = self.fetch_interface(template[KEY__application], inputs[KEY__configuration], template[KEY__schema])
            params, _ = self.fetch_sanitized_email_params(interface, template, params)

        optional_params = {EMAIL_PARAM__app_url: app_url}
        optional_params = {**optional_params, **params}

        recipients = inputs[KEY__recipient]
        if recipients is None:
            recipients = username

        if inputs[KEY__attachments] is not None:
            for attachment in inputs[KEY__attachments]:
                attachment[KEY__application] = inputs[KEY__application]
                attachment[KEY__configuration] = inputs[KEY__configuration]

        self.email_manager.construct_and_send_email(artifact_url, template, user_id, recipients, None, {}, optional_params,
                                                    attachments=EmailAttachment.deserialize_list(inputs[KEY__attachments], template[KEY__name],
                                                                                                 app_url),
                                                    attachment_access_token=self.refresh_auth_token(auth_token, ip_address))

    def reset_password_perform_reset(self, inputs: dict):
        token = inputs[KEY__reset_key]
        password = inputs[KEY__password]

        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_fetch, parameters={KEY__reset_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)
        self.add_account_password(str(resp[ATTR__the_user]), password)
        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__reset_close, parameters={KEY__reset_key: token})

        res = {
            KEY__email: resp[KEY__email]
        }
        if resp[KEY__email_template] and resp[ATTR__data_lookup_json]:
            template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_with_app_url,
                                                            {KEY__name: resp[KEY__email_template],
                                                             KEY__application: resp[KEY__application], KEY__configuration: resp[KEY__configuration]},
                                                            as_objects=True)
            interface = self.fetch_interface(template[KEY__application], resp[KEY__configuration], template[KEY__schema])
            res[KEY__parameters] = self.select_from_data_validation_table(interface, template[KEY__data_validation_table],
                                                                          json.loads(resp[ATTR__data_lookup_json]))

        return res

    def create_account(self, connection: DBInterface, inputs: dict, is_public: bool = False):
        if inputs.get(KEY__password) is not None and not is_public:
            crypt_utils.validate_password(inputs[KEY__password])

        inputs[KEY__is_public] = is_public
        password = inputs.pop(KEY__password, None)

        if KEY__attach_as not in inputs:
            inputs[KEY__attach_as] = None

        account_id = execute_supplied_statement_singleton(connection, QUERY__create_account, inputs,
                                                          encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__username],
                                                          encryption_salts={KEY__username: self.get_repeatable_salt()})[RET__rows][0]

        if password:
            self.add_account_password(account_id, password)

        return account_id

    def is_installed(self, response: JAAQLResponse):
        if not self.has_installed:
            response.response_code = HTTPStatus.UNPROCESSABLE_ENTITY
            return ERR__not_yet_installed

    def is_alive(self):
        version = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__postgres_version, as_objects=True)[ATTR__version]
        if "PostgreSQL " not in version:
            raise HttpStatusException(ERR__keep_alive_failed)

    def install(self, db_connection_string: str, jaaql_password: str, super_db_password: str, install_key: str, allow_uninstall: bool):
        if self.jaaql_lookup_connection is None:
            if allow_uninstall:
                self.vault.insert_obj(VAULT_KEY__allow_jaaql_uninstall, True)

            if install_key != self.install_key:
                raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)

            if db_connection_string is None:
                db_connection_string = PG__default_connection_string % os.environ[PG_ENV__password]

            address, port, _, username, db_password = DBInterface.fracture_uri(db_connection_string)

            super_interface = create_interface(self.config, address, port, DB__jaaql, username, db_password)
            conn = super_interface.get_conn()
            super_interface.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "install_1.sql"))
            resp = super_interface.execute_query(conn, QUERY__setup_jaaql_role)
            jaaql_db_password = resp[1][0][0]
            super_interface.commit(conn)
            super_interface.put_conn(conn)
            super_interface.close()

            self.jaaql_lookup_connection = create_interface(self.config, address, port, DB__jaaql, ROLE__jaaql, jaaql_db_password)
            conn = self.jaaql_lookup_connection.get_conn()
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "install_2.sql"))
            self.jaaql_lookup_connection.commit(conn)
            self.jaaql_lookup_connection.put_conn(conn)

            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__setup_system)

            execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__attach_account, {
                KEY__user_id: ROLE__jaaql,
                KEY__enc_username: USERNAME__jaaql
            }, encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__enc_username],
                                                 encryption_salts={KEY__enc_username: self.get_repeatable_salt()})
            execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__attach_account, {
                KEY__user_id: ROLE__postgres,
                KEY__enc_username: USERNAME__super_db
            }, encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__enc_username],
                                                 encryption_salts={KEY__enc_username: self.get_repeatable_salt()})

            self.add_account_password(ROLE__postgres, super_db_password)
            self.add_account_password(ROLE__jaaql, jaaql_password)

            self.create_account(self.jaaql_lookup_connection, {KEY__username: USERNAME__public, KEY__password: PASSWORD__public})

            self.jaaql_lookup_connection.close()

            super_conn_str = PROTOCOL__postgres + username + ":" + db_password + "@" + address + ":" + str(port) + "/"
            self.vault.insert_obj(VAULT_KEY__super_db_credentials, super_conn_str)
            jaaql_lookup_str = PROTOCOL__postgres + ROLE__jaaql + ":" + jaaql_db_password + "@" + address + ":" + str(port) + "/" + DB__jaaql
            self.vault.insert_obj(VAULT_KEY__jaaql_lookup_connection, jaaql_lookup_str)

            print("Rebooting to allow JAAQL config to be shared among workers")
            threading.Thread(target=self.exit_jaaql).start()
        else:
            raise HttpStatusException(ERR__already_installed)

    def verification_thread(self, the_queue: Queue):
        print("Starting auth verification thread")
        while True:
            auth_token, ip_address, complete = the_queue.get()
            try:
                self.verify_auth_token(auth_token, ip_address)
                complete.put((True, None, None))
            except HttpStatusException as ex:
                complete.put((False, ex.message, ex.response_code))
            except Exception as ex:
                complete.put((False, str(ex), 500))

    def verify_auth_token_threaded(self, auth_token: str, ip_address: str, complete: Queue):
        try:
            if JAAQLModel.VERIFICATION_QUEUE is None:
                JAAQLModel.VERIFICATION_QUEUE = Queue()
                threading.Thread(target=self.verification_thread, args=[JAAQLModel.VERIFICATION_QUEUE], daemon=True).start()
            JAAQLModel.VERIFICATION_QUEUE.put((auth_token, ip_address, complete))
            payload = json.loads(base64url_decode(auth_token.split(".")[1].encode("UTF-8")).decode())
            return payload[KEY__user_id], payload[KEY__username], payload[KEY__ip_id], payload[KEY__is_public]
        except Exception:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

    def verify_auth_token(self, auth_token: str, ip_address: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth)
        if not decoded or decoded[KEY__address] != ip_address:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
        lookup = {KEY__user_id: decoded[KEY__user_id], KEY__password: decoded[KEY__password_id]}
        execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_matching_recent_passwords_with_account, lookup,
                                             singleton_message=ERR__invalid_token, singleton_code=HTTPStatus.UNAUTHORIZED, skip_commit=True)

        return decoded[KEY__user_id], decoded[KEY__username], decoded[KEY__ip_id], decoded[KEY__is_public]

    def refresh_cached_canned_query_service(self, connection: DBInterface, application: str, configuration: str):
        self.check_is_internal_admin(connection)

        self.cached_canned_query_service.refresh_configuration(self.is_container, self.jaaql_lookup_connection, application, configuration)

    def refresh_auth_token(self, auth_token: str, ip_address: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth, allow_expired=True)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        if datetime.fromisoformat(decoded[KEY__created]) + timedelta(milliseconds=self.refresh_expiry_ms) < datetime.now():
            raise HttpStatusException(ERR__refresh_expired, HTTPStatus.UNAUTHORIZED)

        return self.get_auth_token(decoded[KEY__username], ip_address)

    def get_auth_token(self, username: str, ip_address: str, password: str = None, response: JAAQLResponse = None):
        incorrect_credentials = False
        user_id = None
        res = None
        encrypted_ip = None

        try:
            user_id = self.fetch_user_from_username(username, singleton_code=HTTPStatus.UNAUTHORIZED)
        except HttpStatusException as exc:
            if exc.response_code == HTTPStatus.UNAUTHORIZED:
                incorrect_credentials = True
            else:
                raise exc

        if not incorrect_credentials:
            salt_user = self.get_repeatable_salt(user_id)

            encrypted_ip = jaaql__encrypt(ip_address, self.get_db_crypt_key(), salt_user)

            the_kwargs = {
                "encryption_salts": {KEY__enc_username: self.get_repeatable_salt()},
                "decrypt_columns": [KEY__password_hash, KEY__username],
                "encrypt_parameters": [KEY__enc_username],
                "encryption_key": self.get_db_crypt_key(),
                "as_objects": True
            }

            res = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_recent_passwords_with_ips, {
                KEY__enc_username: username,
                KEY__encrypted_address: encrypted_ip,
            }, **the_kwargs)

            if len(res) == 0 and password is not None:
                res = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_recent_passwords, {
                    KEY__enc_username: username
                }, **the_kwargs)

            if len(res) == 1:
                res = res[0]
                if password is not None and not crypt_utils.verify_password_hash(res[KEY__password_hash], password,
                                                                                 salt=self.get_repeatable_salt(res[KEY__user_id])):
                    incorrect_credentials = True
            else:
                incorrect_credentials = True

        if incorrect_credentials:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        address = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY__add_or_update_ip,
                                                       {KEY__account: res[KEY__user_id], KEY__encrypted_address: encrypted_ip},
                                                       as_objects=True)[KEY__address]

        jwt_data = {
            KEY__user_id: str(res[KEY__user_id]),
            KEY__password_id: str(res[KEY__password_id]),
            KEY__username: res[KEY__username],
            KEY__address: ip_address,
            KEY__ip_id: str(address),
            KEY__created: datetime.now().isoformat(),
            KEY__is_public: res[KEY__username] == USERNAME__public
        }

        if response is not None:
            response.user_id = str(res[KEY__user_id]),
            response.ip_id = str(address)

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

    def fetch_pivoted_application_schemas(self):
        data = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_application_schemas, as_objects=True, skip_commit=True)

        return self.group(self.pivot(data,
                          [JAAQLPivotInfo(KEY__configuration, "name", "configuration_name"),
                           JAAQLPivotInfo(KEY__schema, "configuration_name", "schema_name")]), KEY__name)

    def create_interface_for_db(self, user_id: str, database: str, sub_role: str = None):
        jaaql_uri = self.vault.get_obj(VAULT_KEY__super_db_credentials)
        address, port, _, username, password = DBInterface.fracture_uri(jaaql_uri)
        return create_interface(self.config, address, port, database, username, password=password, role=user_id, sub_role=sub_role)

    def submit(self, inputs: dict, user_id: str, verification_hook: Queue):
        if not isinstance(inputs, dict):
            raise HttpStatusException("Expected object or string input")

        if KEY__application in inputs:
            application_configs = self.fetch_pivoted_application_schemas()
            if inputs[KEY__application] not in application_configs:
                raise HttpStatusException("Application '%s' does not exist!" % inputs[KEY__application])
            app = application_configs[inputs[KEY__application]]

            if inputs[KEY__configuration] not in app:
                raise HttpStatusException("Configuration '%s' does not exist for application '%s'!" % (inputs[KEY__configuration],
                                                                                                       inputs[KEY__application]))
            config = app[inputs[KEY__configuration]]

            found_db = None
            if KEY__schema in inputs:
                found_db = config[inputs[KEY__schema]][KEY__database]
                inputs.pop(KEY__schema)
            else:
                if len(config) == 1:
                    found_db = config[list(config.keys())[0]][KEY__database]
                else:
                    found_dbs = [val[KEY__database] for _, val in config.items() if val[KEY__is_default]]
                    if len(found_dbs) == 1:
                        found_db = found_dbs[0]

            if not found_db:
                raise HttpStatusException(ERR__schema_invalid)

            inputs[KEY__database] = found_db

        if KEY__database not in inputs:
            inputs[KEY__database] = DB__jaaql

        sub_role = inputs.pop(KEY__role) if KEY__role in inputs else None
        required_db = self.create_interface_for_db(user_id, inputs[KEY__database], sub_role)

        return InterpretJAAQL(required_db).transform(inputs, skip_commit=inputs.get(KEY__read_only), wait_hook=verification_hook,
                                                     encryption_key=self.get_db_crypt_key(),
                                                     canned_query_service=self.cached_canned_query_service)
