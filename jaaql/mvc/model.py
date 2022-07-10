import random
import platform

from jaaql.db.db_interface import DBInterface, RET__rows
from jaaql.email.email_manager_service import EmailAttachment
from jaaql.mvc.base_model import BaseJAAQLModel, CONFIG_KEY__security, CONFIG_KEY_SECURITY__mfa_label, \
    CONFIG_KEY_SECURITY__mfa_issuer, VAULT_KEY__jwt_obj_crypt_key, VAULT_KEY__jwt_crypt_key, DIR__apps, SEPARATOR__dir
from jaaql.exceptions.http_status_exception import HttpStatusException, HTTPStatus, ERR__connection_expired, \
    HTTP_STATUS_CONNECTION_EXPIRED, ERR__already_installed, ERR__passwords_do_not_match, ERR__cannot_override_db, \
    ERR__already_signed_up

from typing import Union
from base64 import urlsafe_b64decode as b64d
from jaaql.mvc.queries import *
from jaaql.db.db_utils import execute_supplied_statement, execute_supplied_statement_singleton, create_interface, jaaql__encrypt
from jaaql.mvc.response import JAAQLResponse
from collections import Counter
from os.path import dirname
from jaaql.utilities import crypt_utils
from flask import send_file
import uuid
import os
import json
import pyotp
import qrcode
from base64 import b64encode as b64e, b32encode as b32e
from io import BytesIO
from datetime import datetime, timedelta
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL, KEY_query
from jaaql.constants import *
from os.path import join
from jaaql.utilities.utils import get_jaaql_root, Profiler
import threading
import re

TOKEN__pre_auth_reduction_factor = 15

ERR__empty_username = "Username cannot be empty"
ERR__cant_revoke_system_user = "Can't revoke system user"
ERR__invalid_username = "Invalid signup username. Expected an email address"
ERR__invalid_username_internal = "Invalid username. Expected something simple (letters, numbers, underscore and dash)"
ERR__document_created_file = "Document is a file, cannot be downloaded in this way"
ERR__as_attachment_unexpected = "Input 'as_attachment' unexpected as document is returned as a file link"
ERR__incorrect_invite_code = "Incorrect invite code"
ERR__incorrect_reset_code = "Incorrect reset code"
ERR__invite_code_expired = "Invite code expired. Please use the link within the email"
ERR__reset_code_expired = "Reset code expired. Please use the link within the email"
ERR__not_signed_up = "Not signed up"
ERR__recipient_not_allowed = "Recipient not allowed"
ERR__cant_send_attachments = "Cannot send attachments to other people"
ERR__template_not_signup = "One of the supplied templates is not suitable for signup"
ERR__template_reset_password = "You cannot use this template to reset your password"
ERR__please_sign_in = "Please sign in, this user already exists and is signed up!"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__password_incorrect = "Your password is incorrect!"
ERR__invalid_token = "Invalid token!"
ERR__new_ip = "Token being used from an ip address not associated with these credentials. Please refresh it"
ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__duplicated_database = "User %s has a duplicate database precedence with databases '%s'"
ERR__not_sole_owner = "You are not the sole owner of this connection"
ERR__mfa_must_be_enabled = "MFA must be turned on!"
ERR__cannot_self_sign_up = "Cannot self sign up. Must be invited to the platform"
ERR__unexpected_mfa_token = "MFA is disabled but user provided"
ERR__cannot_make_user_public = "Cannot make user with this username public"
ERR__unexpected_parameters = "Signup data not expected"
ERR__unexpected_validation_column = "Unexpected column in the input parameters '%s'"
ERR__user_does_not_exist = "The user does not exist, cannot resend the email"
ERR__data_validation_table_no_primary = "Data validation table has no primary key"
ERR__uninstallation_not_allowed = "Uninstallation not allowed"
ERR__password_required = "Password required"
ERR__cant_find_sign_up = "Cannot locate sign up with key. The key is either incorrect, has expired or has not been activated with the emailed code"
ERR__cant_find_reset = "Cannot locate reset with key. The key is either incorrect, has expired or has not been activated with the emailed code"
ERR__invalid_default_role = "Invalid default role '%s'"
ERR__keep_alive_failed = "Keep alive failed"

SQL__err_duplicate_user = "duplicate key value violates unique constraint \"jaaql__user_unq_email\""

USERNAME__superjaaql = "superjaaql"
USERNAME__postgres = "postgres"

APPLICATION__console = "console"
APPLICATION__playground = "playground"
APPLICATION__manager = "manager"
CONFIGURATION__host = "host"

FUNC__jaaql_create_node = "jaaql__create_node"

CODE__letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CODE__alphanumeric = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
CODE__invite_length = 5
CODE__reset_length = 8
CODE__max_attempts = 3
RESEND__invite_max = 2
RESEND__invite_not_registered_max = 3
RESEND__reset_max = 2

ATTR__version = "version"
ATTR__count = "count"
ATTR__ip_id = "ip_id"
ATTR__expiry_code_ms = "code_expiry_ms"
ATTR__used_key_a = "used_key_a"
ATTR__email = "email"
ATTR__public_credentials = "public_credentials"
ATTR__mobile = "mobile"
ATTR__the_user = "the_user"
ATTR__existed = "existed"
ATTR__password_hash = "password_hash"
ATTR__ip_address = "ip_address"
ATTR__created = "created"
ATTR__password_created = "password_created"
ATTR__alias = "alias"
ATTR__data_lookup_json = "data_lookup_json"
ATTR__activated = "activated"
ATTR__closed = "closed"
ATTR__code_attempts = "code_attempts"
KEY__totp_iv = "totp_iv"
KEY__user_id = "user_id"
KEY__occurred = "occurred"
KEY__duration_ms = "duration_ms"
KEY__input = "input"
KEY__ip = "ip"
KEY__status = "status"
KEY__endpoint = "endpoint"
KEY__dat_name = "datname"
KEY__authorization = "authorization"

DELETION_PURPOSE__application = "application"
DELETION_PURPOSE__application_configuration = "application_configuration"
DELETION_PURPOSE__application_dataset = "application_dataset"
DELETION_PURPOSE__configuration_authorization = "configuration_authorization"
DELETION_PURPOSE__database = "database"
DELETION_PURPOSE__database_assignment = "database_assignment"
DELETION_PURPOSE__default_role = "default_role"
DELETION_PURPOSE__email_account = "email_account"
DELETION_PURPOSE__email_template = "email_template"
DELETION_PURPOSE__node = "node"
DELETION_PURPOSE__node_authorization = "node_authorization"
DELETION_PURPOSE__user = "user"
DELETION_PURPOSE__user_self = "user_self"

DESCRIPTION__jaaql_db = "The core jaaql database, used to store user information, logs and application/auth configs"
DATABASE__jaaql_internal_name = "jaaql db"

URI__otp_auth = "otpauth://totp/%s?secret=%s"
URI__otp_issuer_clause = "&issuer=%s"

JWT__username = "username"
JWT__fully_authenticated = "fully_authenticated"
JWT__super_user = "super_user"
JWT__password = "password"
JWT__created = "created"
JWT__ip = "ip"

PG__default_connection_string = "postgresql://postgres:%s@localhost:5432/jaaql"

DIR__scripts = "scripts"
DIR__manager = "manager"
DIR__playground = "playground"
DIR__console = "console"
DB__empty = ""

DB__wildcard = "*"

MFA__null_issuer = "None"

PRECEDENCE__super_user = 999

SIGNUP__not_started = 0
SIGNUP__started = 1
SIGNUP__already_registered = 2
SIGNUP__completed = 3

RESET__not_started = 0
RESET__started = 1
RESET__completed = 2

REGEX__email = r'^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$'
REGEX__attach_as = r'^[A-Za-z_-]+$'


class JAAQLModel(BaseJAAQLModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def fetch_user_from_username(self, username: str, jaaql_connection: DBInterface, ip_address: str = None):
        inputs = {KEY__username: username}
        the_query = QUERY__fetch_user_latest_password
        if ip_address is not None:
            inputs[ATTR__ip_address] = ip_address
            the_query = QUERY__fetch_user_latest_credentials

        users = execute_supplied_statement(jaaql_connection, the_query, inputs, as_objects=True,
                                           encrypt_parameters=[KEY__username],
                                           encryption_salts={KEY__username: self.get_repeatable_salt()},
                                           decrypt_columns=[ATTR__password_hash, KEY__totp_iv, KEY__email],
                                           encryption_key=self.get_db_crypt_key())

        if len(users) != 1:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        user = users[0]
        user[KEY__id] = str(user[KEY__id])

        if ATTR__ip_id in user:
            user[ATTR__ip_id] = str(user[ATTR__ip_id])

        return user

    def add_email_account(self, inputs: dict, jaaql_interface: DBInterface):
        execute_supplied_statement(jaaql_interface, QUERY__email_account_ins, inputs, encryption_key=self.get_db_crypt_key(),
                                   encrypt_parameters=[KEY__password])
        self.email_manager.reload_service()

    def register_email_template(self, inputs: dict, jaaql_interface: DBInterface):
        inputs[KEY__account] = execute_supplied_statement_singleton(jaaql_interface, QUERY__email_account_sel,
                                                                    {KEY__email_account_name: inputs[KEY__account]}, as_objects=True)[KEY__id]
        if inputs[KEY__allow_signup] is None:
            inputs[KEY__allow_signup] = False
        if inputs[KEY__allow_confirm_signup_attempt] is None:
            inputs[KEY__allow_confirm_signup_attempt] = False
        execute_supplied_statement(jaaql_interface, QUERY__email_template_ins, inputs)

    def delete_email_account(self, inputs: dict, jaaql_connection: DBInterface):
        res = execute_supplied_statement_singleton(jaaql_connection, QUERY__email_account_sel, inputs, as_objects=True)[KEY__id]
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__email_account, res)}

    def delete_email_account_confirm(self, inputs: dict, jaaql_interface: DBInterface):
        params = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__email_account)
        execute_supplied_statement_singleton(jaaql_interface, QUERY__email_account_del, params)
        self.email_manager.reload_service()

    def unregister_email_template(self, inputs: dict, jaaql_connection: DBInterface):
        res = execute_supplied_statement_singleton(jaaql_connection, QUERY__email_account_sel, inputs, as_objects=True)[KEY__id]
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__email_template, res)}

    def unregister_email_template_confirm(self, inputs: dict, jaaql_interface: DBInterface):
        params = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__email_template)
        execute_supplied_statement_singleton(jaaql_interface, QUERY__email_template_del, params)

    def render_document(self, inputs: dict, oauth_token: str):
        inputs[KEY__oauth_token] = self.refresh(oauth_token)
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__ins_rendered_document, inputs,
                                                    encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__parameters, KEY__oauth_token],
                                                    as_objects=True)

    def fetch_document(self, inputs: dict, response: JAAQLResponse):
        res = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_rendered_document,
                                                   {KEY__document_id: inputs[KEY__document_id]}, singleton_message=ERR__document_id_not_found,
                                                   as_objects=True)

        if not res[KEY__completed]:
            raise HttpStatusException(ERR__document_still_rendering, HTTP_STATUS__too_early)

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
            raise HttpStatusException(ERR__document_still_rendering, HTTP_STATUS__too_early)

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

            return send_file(buffer, as_attachment=as_attachment, attachment_filename=res[KEY__filename])

    def verify_user(self, username: str, ip_address: str, profiler: Profiler = None):
        if len(username) == 0:
            raise HttpStatusException(ERR__empty_username)

        username = username.lower()

        # Hash by username to save time but security issue as a deleted user will share usernames. Potential reverse hash lookup. Minor
        hash_username = username.encode(crypt_utils.ENCODING__ascii)
        if len(hash_username) < 8:
            hash_username = hash_username * 8
            hash_username = hash_username[0:8]
        if profiler:
            profiler.perform_profile("Pre verify user")

        encrypted_ip = jaaql__encrypt(ip_address, self.get_db_crypt_key(), hash_username)
        existed_ip = False
        ip_id = None

        try:
            user = self.fetch_user_from_username(username, self.jaaql_lookup_connection, encrypted_ip)
            existed_ip = True
            ip_id = user[ATTR__ip_id]
        except HttpStatusException:
            user = self.fetch_user_from_username(username, self.jaaql_lookup_connection)

        if profiler:
            profiler.perform_profile("Fetch user")

        if not existed_ip:
            inputs = {
                KEY__id: user[KEY__id],
                ATTR__ip_address: ip_address
            }

            resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__user_ip_ins, inputs, as_objects=True)
            existed_ip = resp[ATTR__existed]
            ip_id = resp[KEY__id]

        if profiler:
            profiler.perform_profile("Insert ip")

        return user, existed_ip, str(ip_id), user[KEY__last_totp]

    def refresh(self, oauth_token: str):
        if oauth_token is None:  # The local bypass headers are being used
            jwt_data = {JWT__super_user: "true"}

            expiry_time = self.token_expiry_ms
            purpose = JWT_PURPOSE__oauth

            return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, purpose, expiry_ms=expiry_time)

        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), oauth_token, JWT_PURPOSE__oauth, allow_expired=True)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        created = crypt_utils.decrypt(jwt_obj_key, decoded[JWT__created])

        if datetime.fromisoformat(created) + timedelta(milliseconds=self.refresh_expiry_ms) < datetime.now():
            raise HttpStatusException(ERR__refresh_expired, HTTPStatus.UNAUTHORIZED)

        jwt_data = {
            JWT__username: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__username])),
            JWT__password: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__password])),
            JWT__fully_authenticated: True,
            JWT__ip: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__ip])),
            JWT__created: crypt_utils.encrypt(jwt_obj_key, created)
        }

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

    def verify_mfa(self, mfa_key: str, totp_iv: str, last_totp: str, user_id: str):
        if totp_iv is None:
            return  # MFA is disabled, we have passed
        elif self.force_mfa:
            # We shouldn't really get here, defensive programming
            raise HttpStatusException(ERR__mfa_must_be_enabled, HTTPStatus.UNAUTHORIZED)

        totp = pyotp.TOTP(totp_iv)
        verified = totp.verify(mfa_key)
        if not verified:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        if last_totp == mfa_key:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__user_totp_upd, {
            KEY__user_id: user_id,
            KEY__last_totp: mfa_key
        })

    def redeploy(self):
        if self.is_container:
            f = open("/JAAQL-middleware-python/redeploy", "w")
        else:
            f = open(join(dirname(get_jaaql_root()), "redeploy"), "w")
        f.write("Will be detected and redeployment will now happen")
        f.close()

        print("Redeploying JAAQL")

        threading.Thread(target=self.exit_jaaql, daemon=True).start()

    def authenticate_with_mfa_key(self, pre_auth: str, mfa_key: str, ip_address: str, response: JAAQLResponse):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), pre_auth, JWT_PURPOSE__pre_auth)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        username = crypt_utils.decrypt(jwt_key, decoded[JWT__username])
        user, _, ip_id, last_totp = self.verify_user(username, ip_address)

        self.verify_mfa(mfa_key, user[KEY__totp_iv], last_totp, user[KEY__id])

        response.user_id = user[KEY__id]
        response.ip_id = ip_id

        decoded[JWT__fully_authenticated] = True
        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), decoded, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

    def authenticate(self, username: str, password: str, ip_address: str, response: JAAQLResponse):
        user, _, ip_id, last_totp = self.verify_user(username, ip_address)
        if not crypt_utils.verify_password_hash(user[ATTR__password_hash], password, salt=user[KEY__id].encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        needs_further_auth = user.get(KEY__totp_iv) is not None

        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        jwt_data = {
            JWT__username: crypt_utils.encrypt(jwt_obj_key, username),
            JWT__password: crypt_utils.encrypt(jwt_obj_key, str(user[ATTR__password_created])),
            JWT__fully_authenticated: not needs_further_auth,
            JWT__ip: crypt_utils.encrypt(jwt_obj_key, ip_id),
            JWT__created: crypt_utils.encrypt(jwt_obj_key, datetime.now().isoformat())
        }

        response.user_id = user[KEY__id]
        response.ip_id = ip_id

        expiry_time = self.token_expiry_ms
        purpose = JWT_PURPOSE__oauth
        if needs_further_auth:
            expiry_time /= TOKEN__pre_auth_reduction_factor
            response.response_code = HTTPStatus.ACCEPTED
            purpose = JWT_PURPOSE__pre_auth

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, purpose, expiry_ms=expiry_time)

    def is_installed(self, response: JAAQLResponse):
        if not self.has_installed:
            response.response_code = HTTPStatus.UNPROCESSABLE_ENTITY
            return ERR__not_yet_installed

    def uninstall(self, db_super_user_password: str, uninstall_key: str):
        if not self.vault.has_obj(VAULT_KEY__allow_jaaql_uninstall):
            raise HttpStatusException(ERR__uninstallation_not_allowed)

        if self.jaaql_lookup_connection is None:
            raise HttpStatusException(ERR__not_yet_installed)

        if self.uninstall_key != uninstall_key:
            raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)

        jaaql_uri = self.vault.get_obj(VAULT_KEY__jaaql_lookup_connection)
        address, port, db, _, _ = DBInterface.fracture_uri(jaaql_uri)
        super_user_connection = create_interface(self.config, address, port, DB__postgres, USERNAME__postgres, db_super_user_password)

        self.jaaql_lookup_connection.close()

        execute_supplied_statement(super_user_connection, QUERY__uninstall_jaaql_0)
        execute_supplied_statement(super_user_connection, QUERY__uninstall_jaaql_1)
        execute_supplied_statement(super_user_connection, QUERY__uninstall_jaaql_2)
        execute_supplied_statement(super_user_connection, QUERY__uninstall_jaaql_3)

        self.vault.purge_object(VAULT_KEY__allow_jaaql_uninstall)
        self.vault.purge_object(VAULT_KEY__jaaql_lookup_connection)

        print("Rebooting to allow JAAQL config to be shared among workers")
        print("Executing with platform: " + platform.python_implementation())
        threading.Thread(target=self.exit_jaaql).start()

    def install(self, db_connection_string: str, superjaaql_password: str, password: str, install_key: str,
                use_mfa: bool, allow_uninstall: bool, ip_address: str, response: JAAQLResponse):
        if not use_mfa and self.force_mfa:
            raise HttpStatusException(ERR__mfa_must_be_enabled)
        if self.jaaql_lookup_connection is None:
            if allow_uninstall:
                self.vault.insert_obj(VAULT_KEY__allow_jaaql_uninstall, True)

            if install_key != self.install_key:
                raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)

            if db_connection_string is None:
                db_connection_string = PG__default_connection_string % os.environ[PG_ENV__password]

            address, port, db, username, db_password = DBInterface.fracture_uri(db_connection_string)

            db_interface = create_interface(self.config, address, port, db, username, db_password)
            conn = db_interface.get_conn()
            db_interface.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "install_1.sql"))
            resp = db_interface.execute_query(conn, QUERY__setup_jaaql_role)
            jaaql_password = resp[1][0][0]
            db_interface.commit(conn)
            db_interface.put_conn(conn)
            db_interface.close()
            self.jaaql_lookup_connection = create_interface(self.config, address, port, db, USERNAME__jaaql, jaaql_password)

            conn = self.jaaql_lookup_connection.get_conn()
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "install_2.sql"))
            self.jaaql_lookup_connection.put_conn(conn)

            self.add_node({
                KEY__node_name: NODE__host_node,
                KEY__description: None,
                KEY__port: port,
                KEY__address: address,
            }, self.jaaql_lookup_connection)
            self.vault.insert_obj(VAULT_KEY__jaaql_lookup_connection, db_connection_string)
            self.add_database({KEY__node: NODE__host_node, KEY__database_name: DB__jaaql}, self.jaaql_lookup_connection)

            user_id = self.create_user(self.jaaql_lookup_connection, USERNAME__jaaql, jaaql_password)
            mfa = self.sign_up_user(self.jaaql_lookup_connection, USERNAME__jaaql, password, user_id, ip_address, use_mfa=use_mfa, response=response)

            self.add_configuration_authorization({
                KEY__application: APPLICATION__manager,
                KEY__configuration: CONFIGURATION__host,
                KEY__role: USERNAME__jaaql
            }, self.jaaql_lookup_connection)
            self.add_configuration_authorization({
                KEY__application: APPLICATION__console,
                KEY__configuration: CONFIGURATION__host,
                KEY__role: USERNAME__jaaql
            }, self.jaaql_lookup_connection)
            self.add_configuration_authorization({
                KEY__application: APPLICATION__playground,
                KEY__configuration: CONFIGURATION__host,
                KEY__role: USERNAME__jaaql
            }, self.jaaql_lookup_connection)

            superjaaql_db_password = db_password
            super_otp_uri = None
            super_otp_qr = None
            if superjaaql_password is not None:
                # Because we are setting this user up as postgres, it has a role of every user. Therefore we set this
                # precedence as higher to override them
                super_user_id = self.create_user(self.jaaql_lookup_connection, USERNAME__superjaaql,
                                                 superjaaql_db_password, attach_as=USERNAME__postgres,
                                                 precedence=PRECEDENCE__super_user)
                super_mfa = self.sign_up_user(self.jaaql_lookup_connection, USERNAME__superjaaql, superjaaql_password,
                                              super_user_id, ip_address, use_mfa=use_mfa)
                super_otp_uri = super_mfa[KEY__otp_uri]
                super_otp_qr = super_mfa[KEY__otp_qr]
                self.add_configuration_authorization({
                    KEY__application: APPLICATION__manager,
                    KEY__configuration: CONFIGURATION__host,
                    KEY__role: USERNAME__postgres
                }, self.jaaql_lookup_connection)
                self.add_configuration_authorization({
                    KEY__application: APPLICATION__console,
                    KEY__configuration: CONFIGURATION__host,
                    KEY__role: USERNAME__postgres
                }, self.jaaql_lookup_connection)
                self.add_configuration_authorization({
                    KEY__application: APPLICATION__playground,
                    KEY__configuration: CONFIGURATION__host,
                    KEY__role: USERNAME__postgres
                }, self.jaaql_lookup_connection)

            base_url = self.url + SEPARATOR__dir + DIR__apps + SEPARATOR__dir
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_set_url,
                                       {KEY__application_url: base_url + DIR__console,
                                        KEY__application_name: APPLICATION__console})
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_set_url,
                                       {KEY__application_url: base_url + DIR__manager,
                                        KEY__application_name: APPLICATION__manager})
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_setup_host,
                                       {KEY__application: APPLICATION__manager})
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_set_url,
                                       {KEY__application_url: base_url + DIR__playground,
                                        KEY__application_name: APPLICATION__playground})
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_setup_host,
                                       {KEY__application: APPLICATION__playground})

            print("Rebooting to allow JAAQL config to be shared among workers")
            print("Executing with platform: " + platform.python_implementation())
            threading.Thread(target=self.exit_jaaql).start()

            return {
                KEY__jaaql_otp_uri: mfa[KEY__otp_uri],
                KEY__jaaql_otp_qr: mfa[KEY__otp_qr],
                KEY__superjaaql_otp_uri: super_otp_uri,
                KEY__superjaaql_otp_qr: super_otp_qr
            }
        else:
            raise HttpStatusException(ERR__already_installed)

    def log(self, user_id: str, occurred: datetime, duration_ms: int, exception: str, contr_input: str, ip: str, status: int,
            endpoint: str, databases: list = None):
        threading.Thread(target=self.log_sync, args=[user_id, occurred, duration_ms, exception, contr_input, ip, status, endpoint, databases]).start()

    def log_sync(self, user_id: str, occurred: datetime, duration_ms: int, exception: str, contr_input: str, ip: str, status: int, endpoint: str,
                 databases: list = None):
        if not self.do_audit:
            return
        if databases is None:
            databases = []
        if not isinstance(status, int):
            status = status.value

        parameters = {
            KEY__user_id: user_id,
            KEY__occurred: occurred.isoformat(),
            KEY__duration_ms: duration_ms,
            KEY__exception: exception,
            KEY__input: contr_input,
            KEY__ip: ip,
            KEY__status: int(status),
            KEY__endpoint: endpoint
        }

        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__log_ins, parameters,
                                   encrypt_parameters=[KEY__exception, KEY__input],
                                   encryption_key=self.get_db_crypt_key())

        # TODO do databases. Link the used database auth with the log

    def verify_jwt(self, jwt_token: str, ip_address: str, was_refresh: bool, profiler: Profiler, bypass: str = None) -> [DBInterface, str, str]:
        username = None

        if bypass is not None and bypass == self.local_access_key:
            username = USERNAME__superjaaql
            user, _, ip_id, last_totp = self.verify_user(username, ip_address)
        else:
            decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_token, JWT_PURPOSE__oauth, was_refresh)
            profiler.perform_profile("JWT decode")

            if not decoded:
                raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

            if JWT__super_user in decoded and ('localhost' in ip_address or '127.0.0.1' in ip_address):
                username = USERNAME__superjaaql
                user, _, ip_id, last_totp = self.verify_user(USERNAME__superjaaql, ip_address)
            else:
                if not decoded[JWT__fully_authenticated]:
                    raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

                jwt_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
                username = crypt_utils.decrypt(jwt_key, decoded[JWT__username])
                decoded_created = crypt_utils.decrypt(self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key), decoded[JWT__password])
                profiler.perform_profile("Decode password")

                user, _, ip_id, last_totp = self.verify_user(username, ip_address, profiler=profiler.copy())
                profiler.perform_profile("Verify user")
                if decoded_created != str(user[ATTR__password_created]):
                    raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
                profiler.perform_profile("Verify password hash")

                jwt_ip_id = crypt_utils.decrypt(jwt_key, decoded[JWT__ip])
                if ip_id != jwt_ip_id and 'localhost' not in ip_address and '127.0.0.1' not in ip_address:
                    raise HttpStatusException(ERR__new_ip, HTTPStatus.UNAUTHORIZED)
                profiler.perform_profile("Verify ip")

        params = {
            KEY__user_id: user[KEY__id],
            KEY__node: NODE__host_node
        }
        auth = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__role_connection_sel, params,
                                                    as_objects=True, decrypt_columns=[KEY__username, KEY__password],
                                                    encryption_key=self.get_db_crypt_key())
        profiler.perform_profile("Select auth")

        iv = user[KEY__totp_iv]
        interface = create_interface(self.config, auth[KEY__address], auth[KEY__port], DB__jaaql, auth[KEY__username], auth[KEY__password]
                                     ), user[KEY__id], ip_id, iv, user[ATTR__password_hash], last_totp, username, user[KEY__is_public]
        profiler.perform_profile("Interface creation")
        return interface

    def add_application(self, inputs: dict, jaaql_connection: DBInterface, ip_address: str, user_id: str, response: JAAQLResponse):
        public_username = inputs.pop(KEY__public_username)
        default_database = inputs.pop(KEY__default_database)
        inputs[KEY__application_url] = self.replace_default_app_url(inputs[KEY__application_url])
        if inputs[KEY__default_email_signup_template] is not None:
            inputs[KEY__default_email_signup_template] = execute_supplied_statement_singleton(jaaql_connection, QUERY__fetch_email_template_by_name, {
                KEY__template: inputs[KEY__default_email_signup_template]
            }, as_objects=True)[KEY__id]
        if inputs[KEY__default_email_already_signed_up_template] is not None:
            inputs[KEY__default_email_already_signed_up_template] = execute_supplied_statement_singleton(
                jaaql_connection, QUERY__fetch_email_template_by_name, {
                    KEY__template: inputs[KEY__default_email_already_signed_up_template]
                }, as_objects=True)[KEY__id]
        if inputs[KEY__default_reset_password_template] is not None:
            template_inputs = {KEY__template: inputs[KEY__default_reset_password_template]}
            inputs[KEY__default_reset_password_template] = execute_supplied_statement_singleton(jaaql_connection, QUERY__fetch_email_template_by_name,
                                                                                                template_inputs, as_objects=True)[KEY__id]
        execute_supplied_statement(jaaql_connection, QUERY__application_ins, inputs)
        if public_username is not None:
            password = str(uuid.uuid4())
            public_username = public_username.lower()
            crypt_utils.validate_password(password)
            self.sign_up_user(jaaql_connection, public_username, password,
                              self.create_user(jaaql_connection, public_username, public_application=inputs[KEY__application_name]),
                              ip_address, response=response)
            mup_inputs = {
                KEY__username: public_username,
                KEY__password: password,
                KEY__application: inputs[KEY__application_name]
            }
            self.make_user_public(mup_inputs, jaaql_connection)

        if default_database is not None:
            default_node = default_database.split("/")[0] if "/" in default_database else NODE__host_node
            default_database = default_database.split("/")[1] if "/" in default_database else default_database

            try:
                self.add_database({KEY__create: True, KEY__node: default_node, KEY__database_name: default_database}, jaaql_connection, user_id)
            except:
                pass  # Sometimes the database may already exist

            self.add_application_configuration({KEY__configuration_name: CONFIG__default, KEY__description: CONFIG__default_desc,
                                                KEY__application: inputs[KEY__application_name]}, jaaql_connection)
            self.add_application_dataset({KEY__dataset_name: DATASET__default, KEY__description: DATASET__default_desc,
                                          KEY__application: inputs[KEY__application_name]}, jaaql_connection)
            self.add_database_assignment({KEY__application: inputs[KEY__application_name], KEY__configuration: CONFIG__default,
                                          KEY__database: default_database, KEY__node: default_node, KEY__dataset: DATASET__default}, jaaql_connection)

            if public_username is not None:
                execute_supplied_statement(jaaql_connection, QUERY__node_credentials_set_public_user, {KEY__username: public_username,
                                                                                                       KEY__node: default_node})
                self.add_user_default_role({KEY__role: public_username}, jaaql_connection)
                self.add_configuration_authorization({KEY__application: inputs[KEY__application_name], KEY__configuration: CONFIG__default,
                                                      KEY__role: public_username}, jaaql_connection)

    def delete_application(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application, inputs)}

    def delete_application_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application)
        execute_supplied_statement(jaaql_connection, QUERY__application_del, parameters)

    def delete_database(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__database, inputs)}

    def delete_database_confirm(self, inputs: dict, user_id: int, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__database)
        parameters_drop = parameters.copy()
        if KEY__drop in parameters:
            parameters.pop(KEY__drop)
        execute_supplied_statement(jaaql_connection, QUERY__database_del, parameters)

        if KEY__drop in parameters_drop and parameters_drop[KEY__drop]:
            drop_inputs = {KEY__node: parameters_drop[KEY__node], KEY__user_id: user_id}
            res = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY__node_single_credential_sel, drop_inputs,
                                                       as_objects=True, encryption_key=self.get_db_crypt_key(),
                                                       decrypt_columns=[KEY__username, KEY__password])
            interface = create_interface(self.config, res[KEY__address], res[KEY__port], DB__empty,
                                         res[KEY__username], res[KEY__password])
            execute_supplied_statement(interface, QUERY__drop_database % parameters_drop[KEY__database_name])

    def get_applications(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_count, parameters, where_query, where_parameters)

    def get_my_applications(self, jaaql_connection: DBInterface):
        return execute_supplied_statement(jaaql_connection, QUERY__fetch_my_applications, as_objects=True)

    def get_default_templates_for_application(self, application: str):
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                    QUERY__fetch_application_default_templates,
                                                    {KEY__application: application}, as_objects=True)

    def get_public_user_credentials_for_application(self, application: str):
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                    QUERY__fetch_application_public_user_credentials,
                                                    {KEY__application: application}, as_objects=True)

    def fetch_user_default_roles(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__default_roles_sel, parameters,
                                         where_query, where_parameters)

    def add_user_default_role(self, inputs: dict, jaaql_connection: DBInterface):
        execute_supplied_statement(jaaql_connection, QUERY__default_roles_ins, inputs)

    def delete_user_default_role(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__default_role, inputs)}

    def delete_user_default_role_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__default_role)
        execute_supplied_statement(jaaql_connection, QUERY__default_roles_del, parameters)

    def add_node(self, inputs: dict, jaaql_connection: DBInterface):
        execute_supplied_statement(jaaql_connection, QUERY__node_create, inputs)

    def get_nodes(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)

        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__node_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__node_count, parameters, where_query,
                                         where_parameters)

    def delete_node(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__node, inputs)}

    def delete_node_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__node)
        execute_supplied_statement(jaaql_connection, QUERY__node_del, parameters)

    def add_database(self, inputs: dict, jaaql_connection: DBInterface, user_id: str = None):
        inputs_create = inputs.copy()
        if KEY__create in inputs:
            inputs.pop(KEY__create)
        execute_supplied_statement(jaaql_connection, QUERY__database_ins, inputs)

        if KEY__create in inputs_create and inputs_create[KEY__create]:
            create_inputs = {KEY__node: inputs_create[KEY__node], KEY__user_id: user_id}
            res = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY__node_single_credential_sel, create_inputs,
                                                       as_objects=True, encryption_key=self.get_db_crypt_key(),
                                                       decrypt_columns=[KEY__username, KEY__password])
            interface = create_interface(self.config, res[KEY__address], res[KEY__port], DB__empty,
                                         res[KEY__username], res[KEY__password])
            execute_supplied_statement(interface, QUERY__create_database % inputs[KEY__database_name])

    def update_application(self, inputs: dict, jaaql_connection: DBInterface):
        inputs[KEY__application_new_url] = self.replace_default_app_url(inputs[KEY__application_new_url])
        execute_supplied_statement(jaaql_connection, QUERY__application_upd, inputs)

    def get_databases(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)

        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__database_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__database_count, parameters, where_query,
                                         where_parameters)

    def add_application_dataset(self, inputs: dict, jaaql_connection: DBInterface):
        execute_supplied_statement(jaaql_connection, QUERY__application_dataset_ins, inputs)

    def get_application_datasets(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_dataset_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_dataset_count, parameters,
                                         where_query, where_parameters)

    def delete_application_dataset(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_dataset, inputs)}

    def delete_application_dataset_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        dataset = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_dataset)
        execute_supplied_statement(jaaql_connection, QUERY__application_dataset_del, dataset, as_objects=True)

    def add_application_configuration(self, inputs: dict, jaaql_connection: DBInterface):
        execute_supplied_statement(jaaql_connection, QUERY__application_configuration_ins, inputs)

    def get_application_configurations(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_configuration_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_configuration_count,
                                         parameters, where_query, where_parameters)

    def delete_application_configuration(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_configuration, inputs)}

    def delete_application_configuration_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_configuration)
        execute_supplied_statement(jaaql_connection, QUERY__application_configuration_del, parameters, as_objects=True)

    def add_database_assignment(self, inputs: dict, jaaql_connection: DBInterface):
        execute_supplied_statement(jaaql_connection, QUERY__assigned_database_ins, inputs)

    def get_assigned_databases(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__assigned_database_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__assigned_database_count, parameters,
                                         where_query, where_parameters)

    def remove_database_assignment(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__database_assignment, inputs)}

    def remove_database_assignment_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__database_assignment)
        execute_supplied_statement(jaaql_connection, QUERY__assigned_database_del, parameters, as_objects=True)

    def add_node_authorization(self, inputs: dict, connection: DBInterface):
        execute_supplied_statement(connection, QUERY__node_credentials_ins, inputs,
                                   encrypt_parameters=[KEY__username, KEY__password],
                                   encryption_key=self.get_db_crypt_key())

    def get_node_authorizations(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)
        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__node_credentials_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__node_credentials_count, parameters,
                                         where_query, where_parameters, encryption_key=self.get_db_crypt_key())

    def delete_node_authorization(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__node_authorization, inputs)}

    def delete_node_authorization_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__node_authorization)
        execute_supplied_statement(jaaql_connection, QUERY__node_credentials_del, parameters,
                                   as_objects=True)

    def add_configuration_authorization(self, inputs: dict, connection: DBInterface):
        execute_supplied_statement(connection, QUERY__configuration_authorization_ins, inputs)

    def get_configuration_authorizations(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs, False)
        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__configuration_authorization_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__configuration_authorization_count,
                                         parameters, where_query, where_parameters,
                                         encryption_key=self.get_db_crypt_key())

    def delete_configuration_authorization(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__configuration_authorization, inputs)}

    def delete_configuration_authorization_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key],
                                                DELETION_PURPOSE__configuration_authorization)
        execute_supplied_statement(jaaql_connection, QUERY__configuration_authorization_del, parameters)

    def revoke_user(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__user, inputs)}

    def revoke_user_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__user)
        user = self.fetch_user_from_username(parameters[KEY__email], jaaql_connection)
        if user[KEY__email] in [USERNAME__jaaql, USERNAME__superjaaql]:
            raise HttpStatusException(ERR__cant_revoke_system_user)
        execute_supplied_statement(jaaql_connection, QUERY__revoke_user, {KEY__id: user[KEY__id]})

    def close_account(self, inputs: dict, totp_iv: str, password_hash: str, user_id: str,
                      last_totp: str):
        if not crypt_utils.verify_password_hash(password_hash, inputs[KEY__password],
                                                salt=user_id.encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        self.verify_mfa(inputs[KEY__mfa_key], totp_iv, last_totp, user_id)

        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__user_self, {})}

    def close_account_confirm(self, inputs: dict, user_id: str):
        self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__user_self)
        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__revoke_user, {ATTR__the_user: user_id})

    def user_invite_and_check(self, inputs: dict, jaaql_connection: DBInterface):
        user_existed = False
        try:
            self.fetch_user_from_username(inputs[KEY__email], jaaql_connection)
            user_existed = True
        except HttpStatusException as sub_hs:
            if sub_hs.response_code != HTTPStatus.UNAUTHORIZED:
                raise sub_hs  # Unrelated exception, raise it

        if user_existed:
            raise HttpStatusException(ERR__already_signed_up, response_code=HTTPStatus.CONFLICT)

        return self.user_invite(jaaql_connection, inputs[KEY__email])[KEY__invite_key]

    def user_invite(self, jaaql_connection: DBInterface, email: str, email_template: str = None, template_lookup: dict = None):
        if template_lookup is not None:
            template_lookup = json.dumps(template_lookup)

        the_user = execute_supplied_statement_singleton(jaaql_connection, QUERY__user_id_from_username, {KEY__username: email},
                                                        encryption_key=self.get_db_crypt_key(),
                                                        encryption_salts={KEY__username: self.get_repeatable_salt()},
                                                        encrypt_parameters=[KEY__username], as_objects=True)[KEY__id]
        params = {
            ATTR__data_lookup_json: template_lookup,
            ATTR__the_user: the_user,
            KEY__email_template: email_template,
            KEY__invite_code: "".join([CODE__letters[random.randint(0, len(CODE__letters) - 1)] for _ in range(CODE__invite_length)])
        }
        return execute_supplied_statement_singleton(jaaql_connection, QUERY__sign_up_insert, params, as_objects=True)

    def enable_user_mfa(self, user_id: str):
        totp_iv, totp_uri, totp_b64_qr = self.gen_mfa()

        parameters = {
            KEY__user_id: user_id,
            KEY__totp_iv: totp_iv
        }

        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__set_mfa, parameters,
                                   encrypt_parameters=[KEY__totp_iv], encryption_key=self.get_db_crypt_key())

        return totp_uri, totp_b64_qr

    def fetch_account_info(self, username: str, totp_iv: str):
        return {
            KEY__email: username,
            KEY__mfa_enabled: totp_iv is not None
        }

    def enable_disable_mfa(self, inputs: dict, user_id: str, totp_iv: str, last_totp: str, password_hash: str):
        if self.force_mfa:
            raise HttpStatusException(ERR__mfa_must_be_enabled)

        if not crypt_utils.verify_password_hash(password_hash, inputs[KEY__password], salt=user_id.encode(
                crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        totp_uri = None
        totp_b64_qr = None

        if totp_iv is None:
            totp_uri, totp_b64_qr = self.enable_user_mfa(user_id)
        else:
            self.verify_mfa(inputs[KEY__mfa_key], totp_iv, last_totp, user_id)
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__disable_mfa, {KEY__user_id: user_id})

        return {
            KEY__otp_uri: totp_uri,
            KEY__otp_qr: totp_b64_qr
        }

    def make_user_public(self, inputs: dict, jaaql_connection: DBInterface):
        lower_user = inputs[KEY__username].lower()
        if lower_user in (USERNAME__jaaql, USERNAME__superjaaql):
            raise HttpStatusException(ERR__cannot_make_user_public)

        user = self.fetch_user_from_username(inputs[KEY__username], jaaql_connection)
        totp_iv = user[KEY__totp_iv]
        password_hash = user[ATTR__password_hash]
        last_totp = user[KEY__last_totp]
        user_id = user[KEY__id]

        if not crypt_utils.verify_password_hash(password_hash, inputs[KEY__password], salt=user_id.encode(
                crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        if totp_iv is None and inputs.get(KEY__mfa_key) is not None:
            raise HttpStatusException(ERR__unexpected_mfa_token)
        elif totp_iv is not None:
            self.verify_mfa(inputs.get(KEY__mfa_key), totp_iv, last_totp, user_id)
            execute_supplied_statement(jaaql_connection, QUERY__disable_mfa, {KEY__user_id: user_id})

        new_password = inputs.get(KEY__new_password)
        new_password_confirm = inputs.get(KEY__new_password_confirm)

        if new_password != new_password_confirm:
            raise HttpStatusException(ERR__passwords_do_not_match)

        if new_password is not None:
            self.add_password(jaaql_connection, user_id, new_password)

        query_data = {
            KEY__user_id: user_id,
            KEY__application: inputs[KEY__application],
            KEY__username: inputs[KEY__username],
            KEY__new_password: inputs[KEY__password] if new_password is None else new_password
        }

        execute_supplied_statement(jaaql_connection, QUERY__make_user_public, query_data)

    def gen_mfa(self):
        _, totp_iv = crypt_utils.key_stretcher(str(uuid.uuid4()))
        totp_iv = b32e(totp_iv).decode(ENCODING__utf)

        mfa_issuer = self.config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__mfa_issuer]
        mfa_label = self.config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__mfa_label]
        totp_uri = URI__otp_auth % (mfa_label, totp_iv)
        if mfa_issuer != MFA__null_issuer and mfa_issuer is not None:
            totp_uri += URI__otp_issuer_clause % mfa_issuer

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        buffered = BytesIO()
        qr.make_image().save(buffered, format=FORMAT__png)
        img_str = b64e(buffered.getvalue())
        totp_b64_qr = HTML__base64_png + img_str.decode("ASCII")

        return totp_iv, totp_uri, totp_b64_qr

    def sign_up_user_with_token(self, token: str, password: str = None, ip_address: str = None, response: JAAQLResponse = None):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_fetch, parameters={KEY__invite_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)

        username = resp[KEY__email]
        inputs = {KEY__username: username}
        users = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_user_latest_password, inputs, as_objects=True,
                                           encrypt_parameters=[KEY__username], encryption_salts={KEY__username: self.get_repeatable_salt()},
                                           decrypt_columns=[ATTR__password_hash, KEY__totp_iv, KEY__email], encryption_key=self.get_db_crypt_key())
        if len(users) != 0:
            raise HttpStatusException(ERR__already_signed_up, response_code=HTTPStatus.CONFLICT)

        res = self.sign_up_user(self.jaaql_lookup_connection, username, password, None, ip_address, response=response)
        res[KEY__email] = username

        return res

    def fetch_signup(self, token: str):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_fetch, parameters={KEY__invite_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)

        res = {}
        if resp[KEY__email_template] and resp[ATTR__data_lookup_json]:
            template_table = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template,
                                                                  {KEY__id: resp[KEY__email_template]}, as_objects=True)[KEY__data_validation_table]
            res[KEY__parameters] = self.select_from_data_validation_table(template_table, json.loads(resp[ATTR__data_lookup_json]))

        return res

    def finish_signup(self, token: str):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_fetch, parameters={KEY__invite_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)

        if resp[KEY__email_template] and resp[ATTR__data_lookup_json]:
            template_table = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template,
                                                                  {KEY__id: resp[KEY__email_template]}, as_objects=True)[KEY__data_validation_table]
            self.delete_from_data_validation_table(template_table, json.loads(resp[ATTR__data_lookup_json]))

        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__sign_up_close, {KEY__invite_key: resp[KEY__invite_key]})

    def sign_up_user(self, jaaql_connection: DBInterface, username: str, password: str, user_id: str = None, ip_address: str = None,
                     use_mfa: bool = False, response: JAAQLResponse = None, allow_password_error: bool = False):
        if user_id is None:
            user_id = execute_supplied_statement_singleton(jaaql_connection, QUERY__user_id_from_username, {KEY__username: username},
                                                           encryption_key=self.get_db_crypt_key(),
                                                           encryption_salts={KEY__username: self.get_repeatable_salt()},
                                                           encrypt_parameters=[KEY__username], as_objects=True)[KEY__id]
            user_id = str(user_id)
        try:
            self.add_password(jaaql_connection, user_id, password)
        except HttpStatusException as ex:
            if not allow_password_error:
                raise ex

        totp_uri = None
        totp_b64_qr = None

        if self.force_mfa or use_mfa:
            totp_uri, totp_b64_qr = self.enable_user_mfa(user_id)

        if response is not None:
            _, _, ip_id, _ = self.verify_user(username, ip_address)

            response.user_id = user_id
            response.ip_id = ip_id

        resp = {
            KEY__otp_uri: totp_uri,
            KEY__otp_qr: totp_b64_qr
        }

        return resp

    def fetch_default_roles_as_list(self):
        return [row[0] for row in execute_supplied_statement(self.jaaql_lookup_connection, QUERY__default_roles_sel)[RET__rows]]

    def fetch_allowed_recipients_for_email_template(self, username: str, template: Union[str, dict], get_address: bool = False):
        if isinstance(template, str):
            template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_by_name, {
                KEY__email_template: template
            }, as_objects=True)

        vw_name = template[KEY__recipient_validation_view]
        if vw_name is None:
            if get_address:
                return {None: username}
            else:
                return []

        where_clause = "pg_has_role(:username, sender_role, 'MEMBER')"
        cols = ["key"]
        if get_address:
            cols.append("address")
        cols_str = ", ".join(cols)
        res = execute_supplied_statement(self.jaaql_lookup_connection,
                                         "SELECT " + cols_str + " FROM \"" + vw_name + "\" WHERE " + where_clause,
                                         {KEY__username: username}, as_objects=True)

        if get_address:
            return {cur_res[KEY__key]: cur_res[KEY__address] for cur_res in res}
        else:
            return [cur_res[KEY__key] for cur_res in res]

    def delete_from_data_validation_table(self, val_table: str, pkey_vals: dict):
        val_table_esc = '"%s"' % val_table
        pkeys_where = " AND ".join(['"' + col + '" = :' + col for col in pkey_vals.keys()])
        pkeys_returning = ",".join(['"' + col + '"' for col in pkey_vals.keys()])
        del_query = "DELETE FROM " + val_table_esc + " WHERE " + pkeys_where + " RETURNING " + pkeys_returning
        execute_supplied_statement_singleton(self.jaaql_lookup_connection, del_query, pkey_vals)

    def select_from_data_validation_table(self, val_table: str, pkey_vals: dict):
        val_table_esc = '"%s"' % val_table
        pkeys_where = " AND ".join(['"' + col + '" = :' + col for col in pkey_vals.keys()])
        sel_query = "SELECT * FROM " + val_table_esc + " WHERE " + pkeys_where
        sanitized_params = execute_supplied_statement_singleton(self.jaaql_lookup_connection, sel_query, pkey_vals, as_objects=True)

        return {key: value for key, value in sanitized_params.items() if key not in pkey_vals}

    def fetch_email_templates(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)

        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__email_templates_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__email_templates_count, parameters, where_query, where_parameters)

    def fetch_email_accounts(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)

        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__email_accounts_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__email_accounts_count, parameters, where_query,
                                         where_parameters)

    def fetch_user_email_history(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs, False)
        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__email_history_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__email_history_count,
                                         parameters, where_query, where_parameters,
                                         encryption_key=self.get_db_crypt_key())

    def fetch_user_singular_email_history(self, email_id: str, user_id: str):
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__email_history_singular_sel,
                                                    {KEY__id: email_id, KEY__user_id: user_id}, encryption_key=self.get_db_crypt_key(),
                                                    decrypt_columns=[KEY__subject, KEY__recipient, KEY__body, KEY__attachments], as_objects=True)

        if resp[KEY__attachments] is not None:
            resp[KEY__attachments] = [{
                KEY__filename: b64d(attachment.split(":")[0]).decode(ENCODING__ascii),
                KEY__content: attachment.split(":")[1]} for attachment in resp[KEY__attachments].split("::")]

        return resp

    def send_email(self, inputs: dict, username: str, oauth_token: str, user_id: str):
        if inputs[KEY__recipient] is not None and inputs[KEY__attachments] is not None:
            raise HttpStatusException(ERR__cant_send_attachments)

        app_url = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY__fetch_url_from_application_name,
                                                       {KEY__application: inputs[KEY__application]},
                                                       as_objects=True)[KEY__application_url]
        template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_by_name, {
            KEY__email_template: inputs[KEY__email_template]
        }, as_objects=True)

        params = inputs[KEY__parameters]
        if params is not None and template[KEY__data_validation_table] is None:
            raise HttpStatusException(ERR__unexpected_parameters)
        if template[KEY__data_validation_table] is not None and params is None:
            params = {}
        if template[KEY__data_validation_table] is not None:
            params, _ = self.fetch_sanitized_email_params(template, params)

        recipient_names = inputs[KEY__recipient]
        recipients = inputs[KEY__recipient]

        if username != USERNAME__superjaaql:
            allowed_recipients = self.fetch_allowed_recipients_for_email_template(username, template, True)
            if inputs[KEY__recipient] not in allowed_recipients:
                raise HttpStatusException(ERR__recipient_not_allowed)
            recipient_names = allowed_recipients[inputs[KEY__recipient]]

        self.email_manager.construct_and_send_email(self.url, app_url, template, user_id, recipient_names, recipients, {}, params,
                                                    attachments=EmailAttachment.deserialize_list(inputs[KEY__attachments], template[KEY__id]),
                                                    attachment_access_token=self.refresh(oauth_token))

    def fetch_sanitized_email_params(self, template: dict, params: dict):
        val_table = template[KEY__data_validation_table]
        val_cols = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_table_columns,
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
        pkey_vals = execute_supplied_statement_singleton(self.jaaql_lookup_connection, ins_query, params, as_objects=True)
        pkey_vals = {key: str(val) if isinstance(val, uuid.UUID) else val for key, val in pkey_vals.items()}
        select_table = template[KEY__data_validation_view] if template[KEY__data_validation_view] is not None else val_table
        return self.select_from_data_validation_table(select_table, pkey_vals), pkey_vals

    def signup_status(self, inputs: dict):
        select_param = {KEY__invite_or_poll_key: inputs[KEY__invite_or_poll_key]}
        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_poll, parameters=select_param, as_objects=True,
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    singleton_message=ERR__cant_find_sign_up)

        existed = False
        try:
            _ = self.fetch_user_from_username(resp[KEY__email], self.jaaql_lookup_connection)[KEY__id]
            existed = True
        except HttpStatusException as sub_hs:
            if sub_hs.response_code != HTTPStatus.UNAUTHORIZED:
                raise sub_hs  # Unrelated exception, raise it

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

    def request_signup(self, inputs: dict):
        if self.invite_only:
            raise HttpStatusException(ERR__cannot_self_sign_up, HTTPStatus.UNAUTHORIZED)

        app_url = None
        if inputs[KEY__application]:
            app_url = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                           QUERY__fetch_url_from_application_name,
                                                           {KEY__application: inputs[KEY__application]},
                                                           as_objects=True)[KEY__application_url]

        user_existed = False
        user_id = None
        try:
            user_id = self.create_user(self.jaaql_lookup_connection, inputs[KEY__email])
        except HttpStatusException as hs:
            if not hs.message.startswith(SQL__err_duplicate_user):
                raise hs  # Unrelated exception, raise it

            try:
                user_id = self.fetch_user_from_username(inputs[KEY__email], self.jaaql_lookup_connection)[KEY__id]
                user_existed = True
            except HttpStatusException as sub_hs:
                if sub_hs.response_code != HTTPStatus.UNAUTHORIZED:
                    raise sub_hs  # Unrelated exception, raise it

            if user_id is None:
                user_id = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__user_id_from_username,
                                                               {KEY__username: inputs[KEY__email]},
                                                               encryption_key=self.get_db_crypt_key(),
                                                               encryption_salts={KEY__username: self.get_repeatable_salt()},
                                                               encrypt_parameters=[KEY__username], as_objects=True)[KEY__id]

        attempts = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__sign_up_count, {ATTR__the_user: user_id},
                                                        as_objects=True)[ATTR__count]
        if user_existed and attempts >= RESEND__invite_max or attempts >= RESEND__invite_not_registered_max:
            raise HttpStatusException(ERR__too_many_signup_attempts, HTTPStatus.TOO_MANY_REQUESTS)

        template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_by_name, {
            KEY__email_template: inputs[KEY__email_template]
        }, as_objects=True)
        template_already_exists = execute_supplied_statement_singleton(
            self.jaaql_lookup_connection, QUERY__fetch_email_template_by_name, {
                KEY__email_template: inputs[KEY__already_signed_up_email_template]
            }, as_objects=True
        )

        if not template[KEY__allow_signup] or not template_already_exists[KEY__allow_confirm_signup_attempt]:
            raise HttpStatusException(ERR__template_not_signup)

        params = inputs[KEY__parameters]
        if params is not None and template[KEY__data_validation_table] is None:
            raise HttpStatusException(ERR__unexpected_parameters)
        if params is None and template[KEY__data_validation_table] is not None:
            params = {}

        sanitized_params = {}
        pkey_vals = None

        if template[KEY__data_validation_table] is not None:
            if EMAIL_PARAM__signup_key in params:
                raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__signup_key)
            if EMAIL_PARAM__invite_code in params:
                raise HttpStatusException(ERR__unexpected_validation_column % EMAIL_PARAM__invite_code)

            sanitized_params, pkey_vals = self.fetch_sanitized_email_params(template, params)

        template = template_already_exists if user_existed else template
        invite_keys = self.user_invite(self.jaaql_lookup_connection, inputs[KEY__email], template[KEY__id], pkey_vals)
        optional_params = {EMAIL_PARAM__signup_key: invite_keys[KEY__invite_key], EMAIL_PARAM__invite_code: invite_keys[KEY__invite_code]}
        optional_params = {**optional_params, **sanitized_params}

        self.email_manager.construct_and_send_email(self.url, app_url, template, user_id, inputs[KEY__email], None, {}, optional_params)

        return {KEY__invite_key: invite_keys[KEY__invite_poll_key]}

    def send_reset_password_email(self, inputs: dict):
        app_url = None
        if inputs[KEY__application]:
            app_url = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_url_from_application_name,
                                                           {KEY__application: inputs[KEY__application]}, as_objects=True)[KEY__application_url]
        user_exists = True
        user = None
        try:
            user = self.fetch_user_from_username(inputs[KEY__email], self.jaaql_lookup_connection)
        except HttpStatusException:
            user_exists = False

        if user_exists and user[KEY__is_public]:
            raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)

        attempts = None
        if user_exists:
            attempts = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_count, {ATTR__the_user: user[KEY__id]},
                                                            as_objects=True)[ATTR__count]
        else:
            attempts = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fake_reset_count, {KEY__email: inputs[KEY__email]},
                                                            encryption_key=self.get_db_crypt_key(),
                                                            encryption_salts={KEY__email: self.get_repeatable_salt()},
                                                            encrypt_parameters=[KEY__email], as_objects=True)[ATTR__count]
        if attempts >= RESEND__reset_max:
            raise HttpStatusException(ERR__too_many_reset_requests, HTTPStatus.TOO_MANY_REQUESTS)

        template = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template_by_name, {
            KEY__email_template: inputs[KEY__email_template]
        }, as_objects=True)

        if not template[KEY__allow_reset_password]:
            raise HttpStatusException(ERR__template_reset_password)

        reset_keys = {}
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

                sanitized_params, pkey_vals = self.fetch_sanitized_email_params(template, params)

            template_lookup = None
            if pkey_vals is not None:
                template_lookup = json.dumps(pkey_vals)
            params = {
                ATTR__data_lookup_json: template_lookup,
                ATTR__the_user: user[KEY__id],
                KEY__email_template: template[KEY__id],
                KEY__reset_code: "".join([CODE__alphanumeric[random.randint(0, len(CODE__alphanumeric) - 1)] for _ in range(CODE__reset_length)])
            }

            reset_keys = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_insert, params, as_objects=True)
            optional_params = {EMAIL_PARAM__reset_key: reset_keys[KEY__reset_key], EMAIL_PARAM__reset_code: reset_keys[KEY__reset_code]}
            optional_params = {**optional_params, **sanitized_params}

            self.email_manager.construct_and_send_email(self.url, app_url, template, user[KEY__id], inputs[KEY__email], None, {}, optional_params)
        else:
            params = {
                KEY__email: inputs[KEY__email]
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

    def reset_password_perform_reset(self, inputs: dict):
        token = inputs[KEY__reset_key]
        password = inputs[KEY__password]

        resp = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__reset_fetch, parameters={KEY__reset_or_poll_key: token},
                                                    decrypt_columns=[KEY__email], encryption_key=self.get_db_crypt_key(),
                                                    as_objects=True, singleton_message=ERR__cant_find_sign_up)
        self.add_password(self.jaaql_lookup_connection, str(resp[ATTR__the_user]), password)
        execute_supplied_statement(self.jaaql_lookup_connection, QUERY__reset_close, parameters={KEY__reset_key: token})

        res = {
            KEY__email: resp[KEY__email]
        }
        if resp[KEY__email_template] and resp[ATTR__data_lookup_json]:
            template_table = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__fetch_email_template,
                                                                  {KEY__id: resp[KEY__email_template]}, as_objects=True)[KEY__data_validation_table]
            res[KEY__parameters] = self.select_from_data_validation_table(template_table, json.loads(resp[ATTR__data_lookup_json]))

        return res

    def create_user(self, jaaql_connection: DBInterface, username: str, db_password: str = None, mobile: str = None,
                    attach_as: str = None, precedence: int = None, roles: str = "", public_application: str = None):
        if db_password is None:
            db_password = str(uuid.uuid4())

        if not public_application and username != USERNAME__jaaql and username != USERNAME__superjaaql and not re.match(REGEX__email, username):
            raise HttpStatusException(ERR__invalid_username)
        elif public_application and not re.match(REGEX__attach_as, username):
            raise HttpStatusException(ERR__invalid_username_internal)
        elif attach_as and not re.match(REGEX__attach_as, username):
            raise HttpStatusException(ERR__invalid_username_internal)

        parameters = {
            ATTR__email: username,
            ATTR__mobile: mobile,
            ATTR__alias: attach_as,
            KEY__is_public: public_application is not None,
            KEY__application: public_application,
            ATTR__public_credentials: str(username + ":") if public_application is not None else None
        }

        user_id = execute_supplied_statement_singleton(jaaql_connection, QUERY__user_ins, parameters,
                                                       encrypt_parameters=[ATTR__email],
                                                       encryption_salts={ATTR__email: self.get_repeatable_salt()},
                                                       encryption_key=self.get_db_crypt_key(),
                                                       as_objects=True)[KEY__id]

        attached = attach_as is not None
        if attach_as is None:
            attach_as = user_id

        if public_application is not None:
            attach_as = username

        self.add_node_authorization({
            KEY__node: NODE__host_node,
            KEY__role: attach_as,
            KEY__username: attach_as,
            KEY__password: db_password,
            KEY__precedence: precedence
        }, self.jaaql_lookup_connection)

        if not attached:
            inputs = {
                KEY__username: username if public_application is not None else user_id,
                KEY__password: db_password
            }
            execute_supplied_statement(self.jaaql_lookup_connection, QUERY__user_create_role, inputs)

        if len(roles) == 0:
            roles = []
        else:
            roles = roles.split(",")
        roles = roles + self.fetch_default_roles_as_list()
        roles = list(set(roles))
        for role in roles:
            if not re.match(REGEX__attach_as, role):
                raise HttpStatusException(ERR__invalid_default_role % role)
            # Parameters sanitised, we _cannot_ bind parameters into grant role
            execute_supplied_statement(jaaql_connection, QUERY__grant_role % (role, attach_as))

        return str(user_id)

    def my_logs(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__user_log_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__user_log_count, parameters, where_query,
                                         where_parameters,
                                         decrypt_columns=[KEY__address, KEY__exception],
                                         encryption_key=self.get_db_crypt_key())

    def my_ips(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__user_ip_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__user_ip_count, parameters, where_query,
                                         where_parameters, decrypt_columns=[KEY__address],
                                         encryption_key=self.get_db_crypt_key())

    def my_configs(self, jaaql_connection: DBInterface, inputs: dict):
        return execute_supplied_statement(jaaql_connection, QUERY__my_configs, inputs, as_objects=True)

    def is_alive(self):
        version = execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__postgres_version, as_objects=True)[ATTR__version]
        if "PostgreSQL " not in version:
            raise HttpStatusException(ERR__keep_alive_failed)

    def add_password(self, jaaql_connection: DBInterface, user_id: str, password: str):
        crypt_utils.validate_password(password)
        new_password = crypt_utils.hash_password(password, user_id.encode(crypt_utils.ENCODING__ascii))
        parameters = {
            ATTR__the_user: user_id,
            ATTR__password_hash: new_password
        }

        execute_supplied_statement(jaaql_connection, QUERY__user_password_ins, parameters,
                                   encrypt_parameters=[ATTR__password_hash],
                                   encryption_key=self.get_db_crypt_key(),
                                   encryption_salts={ATTR__password_hash: user_id})

    def change_password(self, inputs: dict, totp_iv: str, oauth_token: str, password_hash: str, user_id: str,
                        last_totp: str, jaaql_connection: DBInterface):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), oauth_token, JWT_PURPOSE__oauth)
        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)

        if not crypt_utils.verify_password_hash(password_hash, inputs[KEY__password], salt=user_id.encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        self.verify_mfa(inputs[KEY__mfa_key], totp_iv, last_totp, user_id)

        new_password = inputs[KEY__new_password]
        new_password_confirm = inputs[KEY__new_password_confirm]

        if new_password != new_password_confirm:
            raise HttpStatusException(ERR__passwords_do_not_match)

        self.add_password(jaaql_connection, user_id, new_password)

        decoded[JWT__password] = crypt_utils.encrypt(jwt_obj_key, crypt_utils.hash_password(new_password))

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), decoded, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

    @staticmethod
    def build_db_addr(row: dict):
        db_name = "" if row[KEY__database] is DB__wildcard else ("/" + row[KEY__database])
        return row[KEY__username] + ":" + row[KEY__password] + "@" + row[KEY__address] + ":" + str(row[KEY__port]) + db_name

    def config_assigned_databases(self, inputs: dict, jaaql_connection: DBInterface, user_id: str):
        inputs[KEY__user_id] = user_id

        inputs_config_check = {
            KEY__application: inputs[KEY__application],
            KEY__configuration: inputs[KEY__configuration]
        }
        execute_supplied_statement_singleton(jaaql_connection, QUERY__my_configs_where, inputs_config_check)

        # It is not a mistake to use the jaaql_lookup_connection rather than the user's connection here
        data = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__authorized_configuration,
                                          inputs, as_objects=True, encryption_key=self.get_db_crypt_key(),
                                          decrypt_columns=[
                                              KEY__username,
                                              KEY__password,
                                          ])

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_crypt_key)
        obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)

        check_dbs = [row[KEY__database] for row in data]
        if len(set(check_dbs)) != len(check_dbs):
            duplicates = Counter(check_dbs)
            duplicates = [itm for itm in duplicates.keys() if duplicates[itm] > 1]
            raise Exception(ERR__duplicated_database % (user_id, SEPARATOR__comma_space.join(duplicates)))

        # Combines the existing row, overriding KEY__database with a JWT containing the encrypted database UUID
        ret = [{
            KEY__dataset_description: row[KEY__dataset_description],
            KEY__dataset: row[KEY__dataset],
            KEY__connection: crypt_utils.jwt_encode(jwt_key, {
                KEY__is_node: row[KEY__database] == DB__wildcard,
                KEY__node: crypt_utils.encrypt(obj_key, row[KEY__node]),
                KEY__db_url: crypt_utils.encrypt(obj_key, JAAQLModel.build_db_addr(row))
            }, JWT_PURPOSE__connection)
        } for row in data]

        return ret

    def obtain_connection(self, inputs: dict, jaaql_connection: DBInterface):
        was_connection_none = inputs.get(KEY__connection, None) is None
        connection = inputs.get(KEY__connection, None)

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_crypt_key)
        obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)

        if connection is None:
            connection = jaaql_connection
        else:
            jwt_decoded = crypt_utils.jwt_decode(jwt_key, connection, JWT_PURPOSE__connection)
            if not jwt_decoded:
                raise HttpStatusException(ERR__connection_expired, HTTP_STATUS_CONNECTION_EXPIRED)
            is_node = jwt_decoded[KEY__is_node]
            db_url = jwt_decoded[KEY__db_url]
            db_url = crypt_utils.decrypt(obj_key, db_url)
            address, port, database, username, password = DBInterface.fracture_uri(db_url, allow_missing_database=is_node)
            non_null_db = KEY__database in inputs and inputs[KEY__database] is not None
            if is_node:
                database = inputs[KEY__database] if non_null_db else DB__empty
            elif non_null_db:
                raise HttpStatusException(ERR__cannot_override_db, HTTPStatus.UNPROCESSABLE_ENTITY)

            connection = create_interface(self.config, address, port, database, username, password)

        return connection, was_connection_none

    def config_assigned_database_roles(self, inputs: dict, jaaql_connection: DBInterface):
        inputs[KEY_query] = QUERY__my_roles
        return self.submit(inputs, jaaql_connection)[RET__rows]

    def submit(self, inputs: dict, jaaql_connection: DBInterface, force_transactional: bool = False):
        connection, was_connection_none = self.obtain_connection(inputs, jaaql_connection)

        if KEY__database in inputs:
            inputs.pop(KEY__database)

        caught_ex = None
        to_ret = None
        try:
            to_ret = InterpretJAAQL(connection).transform(inputs, force_transactional=force_transactional)
        except Exception as ex:
            caught_ex = ex

        if not was_connection_none:
            threading.Thread(target=connection.close).start()

        if caught_ex is not None:
            raise caught_ex

        return to_ret
