import re
import uuid

from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.documentation.documentation_public import KEY__oauth_token
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jwt_crypt_key
from jaaql.exceptions.http_status_exception import HttpStatusException, HTTPStatus, ERR__already_installed
from os.path import join
from jaaql.constants import *
from jaaql.mvc.response import JAAQLResponse
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL, ASSERT_one, KEY_assert, KEY_query, KEY_parameters
from jaaql.utilities.utils import get_jaaql_root, get_base_url
from jaaql.db.db_utils import create_interface, jaaql__encrypt
from jaaql.utilities import crypt_utils
import threading
from datetime import datetime, timedelta
from jaaql.mvc.handmade_queries import *
from jwt.utils import base64url_decode
import json
import os
from queue import Queue
import subprocess
import time
import random

from jaaql.migrations.migrations import run_migrations

REGEX__object_name = r'^[0-9a-zA-Z_]{1,63}$'

ERR__invalid_object_name = "Object name '%s' is invalid. Must match regex: " + REGEX__object_name
ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__invalid_level = "Invalid level!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__email_template_not_installed = "Either email template does not exist"
ERR__lacking_permissions = "Only an administrator can perform this action!"
ERR__schema_invalid = "Schema invalid!"
ERR__cant_send_attachments = "Cannot send attachments to other people"
ERR__keep_alive_failed = "Keep alive failed"
ERR__template_not_signup = "Sign up template does not have the correct type"
ERR__template_not_already = "Already signed up template does not have the correct type"
ERR__template_not_reset = "Reset template does not have the correct type"
ERR__template_not_unregistered = "Unregistered template does not have the correct type"
ERR__unexpected_parameters = "Email parameters were not expected"
ERR__expected_parameters = "Email parameters were expected"
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

SQL__err_duplicate = "duplicate key value violates unique constraint"

RESEND__invite_max = 3
RESEND__reset_max = 2
RESET__not_started = 0
RESET__started = 1
RESET__completed = 2

CODE__letters = "ABCDEFGHIJKLMNPQRSTUVWXYZ"
CODE__invite_length = 6
CODE__max_attempts = 3
CODE__alphanumeric = "ABCDEFGHIJKLMNPQRSTUVWXYZ123456789"
CODE__reset_length = 8

SIGNUP__not_started = 0
SIGNUP__started = 1
SIGNUP__already_registered = 2
SIGNUP__completed = 3


class JAAQLModel(BaseJAAQLModel):
    VERIFICATION_QUEUE = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def redeploy(self, connection: DBInterface):
        raise HttpStatusException("Not yet implemented", response_code=HTTPStatus.NOT_IMPLEMENTED)

    def create_account_with_potential_password(self, connection: DBInterface, username: str, attach_as: str = None, password: str = None,
                                               already_exists: bool = False, is_the_anonymous_user: bool = False):
        account_id = create_account(connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                    username, attach_as, already_exists,
                                    is_the_anonymous_user)

        if password:
            self.add_account_password(account_id, password)

        return account_id

    def validate_query(self, queries: list, query, allow_list=True):
        if isinstance(query, list) and allow_list:
            for sub_query in query:
                self.validate_query(queries, sub_query, allow_list=False)
            return

        if not isinstance(query, dict):
            raise HttpStatusException("Expected query to be dict")

        if "line_number" not in query:
            raise HttpStatusException("Expected line number in query")
        if not isinstance(query["line_number"], int):
            raise HttpStatusException("Expected integer as line number for query")

        if "position" not in query:
            raise HttpStatusException("Expected position in query")
        if not isinstance(query["position"], int):
            raise HttpStatusException("Expected integer as position for query")

        if "name" not in query:
            raise HttpStatusException("Expected name in query")
        if not isinstance(query["name"], str):
            raise HttpStatusException("Expected string as name for query")

        not_allowed = [key for key in query.keys() if key not in ["name", "position", "line_number"]]
        if len(not_allowed):
            raise HttpStatusException("Unexpected keys in query: " + ", ".join(not_allowed))

        queries.append(query)

    def prepare_queries(self, connection: DBInterface, account_id: str, inputs: dict):
        # Important! Permission check by checking that the user can in insert into the application table. This is equivalent of checking if the user
        # owns the application. We currently have no concept of application ownership
        res = execute_supplied_statement_singleton(connection, """SELECT
    *
FROM information_schema.role_table_grants
WHERE
    table_schema = quote_ident('public')
    AND table_catalog = 'jaaql'
    AND table_name = quote_ident('application')
    AND grantee = :grantee
    AND privilege_type = 'INSERT'
        """, parameters={"grantee": account_id}, as_objects=True, singleton_message="You do not have permissions to prepare queries!")

        if KEY__application not in inputs:
            raise HttpStatusException("Missing application from request")

        if not isinstance(inputs[KEY__application], str):
            raise HttpStatusException("Application must be a string")

        application = application__select(connection, inputs[KEY__application])

        for frame, requests in inputs.items():
            if frame == KEY__application:
                continue  # This is not a frame but the application name

            if not isinstance(requests, list):
                raise HttpStatusException("Requests must be a list type")

            found_singletons = []
            found_queries = []

            for found_request in requests:
                if not isinstance(found_request, dict):
                    raise HttpStatusException("Request must be a dictionary type")

                if "singletons" not in found_request and "queries" not in found_request:
                    raise HttpStatusException("Request must have either singletons or queries")

                if "parameters" in found_request:
                    parameters = found_request["parameters"]
                    if not isinstance(parameters, list):
                        raise HttpStatusException("Expected parameters to be list type")
                    for parameter in parameters:
                        if not isinstance(parameter, dict):
                            raise HttpStatusException("Parameter must be of dict type")

                        if "line_number" not in parameter:
                            raise HttpStatusException("Parameter must have line number")
                        if "position" not in parameter:
                            raise HttpStatusException("Parameter must have position")
                        if "name" not in parameter:
                            raise HttpStatusException("Parameter must have name")
                        line_number = parameter["line_number"]
                        position = parameter["position"]
                        name = parameter["name"]
                        if not isinstance(line_number, int):
                            raise HttpStatusException("Parameter line number must be an integer")
                        if not isinstance(position, int):
                            raise HttpStatusException("Parameter position must be an integer")
                        if not isinstance(name, str):
                            raise HttpStatusException("Parameter name must be a string")

                        disallowed_keys = [key for key in parameter.keys() if key not in ["line_number", "position", "name"]]
                        if len(disallowed_keys) != 0:
                            raise HttpStatusException("Unrecognised keys found in parameter: " + ", ".join(disallowed_keys))

                if "singletons" in found_request:
                    singletons = found_request["singletons"]
                    if not isinstance(singletons, dict):
                        raise HttpStatusException("Expected singletons to be dictionary type")
                    for query in singletons:
                        self.validate_query(found_singletons, query)

                if "queries" in found_request:
                    queries = found_request["queries"]
                    if not isinstance(queries, dict):
                        raise HttpStatusException("Expected queries to be dictionary type")
                    for query in queries:
                        if isinstance(query, dict):
                            if "line_number" in query:
                                self.validate_query(found_singletons, query)
                            else:
                                pass  # We are dealing with a store type query
                        if isinstance(query, list):
                            self.validate_query(found_singletons, query)

    def is_super_admin(self, connection: DBInterface):
        res = execute_supplied_statement_singleton(connection, "select usesuper from pg_user where usename = CURRENT_USER",
                                                   as_objects=True)["usesuper"]
        if not res:
            raise HttpStatusException("You do not have super user privileges")

    def clean(self, connection: DBInterface):
        self.is_super_admin(connection)

        if self.is_container:
            if not self.vault.get_obj(VAULT_KEY__allow_jaaql_uninstall):
                raise HttpStatusException("JAAQL not permitted to uninstall itself")

            subprocess.call("./pg_reboot.sh", cwd="/")
        else:
            subprocess.call("docker kill jaaql_pg")
            subprocess.call("docker rm jaaql_pg")
            subprocess.Popen("docker run --name jaaql_pg -p 5434:5432 jaaql/jaaql_pg", start_new_session=True)
            time.sleep(7.5)

        DBPGInterface.close_all_pools()
        self.jaaql_lookup_connection = None
        self.install_key = str(uuid.uuid4())
        self.install(
            self.vault.get_obj(VAULT_KEY__db_connection_string),
            self.vault.get_obj(VAULT_KEY__jaaql_password),
            self.vault.get_obj(VAULT_KEY__super_db_password),
            self.install_key,
            True,
            False,
            self.vault.get_obj(VAULT_KEY__jaaql_db_password)
        )

    def add_account_password(self, account_id: str, password: str):
        crypt_utils.validate_password(password)
        salt = self.get_repeatable_salt(account_id)
        add_account_password(
            self.jaaql_lookup_connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
            account_id, crypt_utils.hash_password(password, salt)
        )

    def verify_current_password(self, account_id: str, password: str):
        most_recent_password = fetch_most_recent_password(self.jaaql_lookup_connection, self.get_db_crypt_key(), account_id)
        if not crypt_utils.verify_password_hash(most_recent_password, password, salt=self.get_repeatable_salt(account_id)):
            raise HttpStatusException(ERR__incorrect_credentials)

    def add_my_account_password(self, account_id: str, username: str, ip_address: str, old_password: str, password: str):
        self.verify_current_password(account_id, old_password)
        self.add_account_password(account_id, password)
        return self.get_auth_token(password=password, ip_address=ip_address, username=username)

    def execute_migrations(self, connection: DBInterface):
        self.is_super_admin(connection)

        base_url = get_base_url(self.config, self.is_container)
        run_migrations(base_url, self.local_super_access_key, self.local_jaaql_access_key, self.jaaql_lookup_connection, self.is_container,
                       self.migration_project_name, migration_folder=self.migration_folder, config=self.config, options=self.options,
                       key=self.get_db_crypt_key())

    def is_installed(self, response: JAAQLResponse):
        if not self.has_installed:
            response.response_code = HTTPStatus.UNPROCESSABLE_ENTITY
            return ERR__not_yet_installed

    def is_alive(self):
        version = execute_supplied_statement_singleton(self.jaaql_lookup_connection, "SELECT version() as version;", as_objects=True)[ATTR__version]
        if "PostgreSQL " not in version:
            raise HttpStatusException(ERR__keep_alive_failed)

    def install(self, db_connection_string: str, jaaql_password: str, super_db_password: str, install_key: str, allow_uninstall: bool,
                do_reboot: bool = True, jaaql_db_password: str = None):
        if self.jaaql_lookup_connection is None:
            if allow_uninstall or not self.is_container:
                self.vault.insert_obj(VAULT_KEY__allow_jaaql_uninstall, True)
                self.vault.insert_obj(VAULT_KEY__db_connection_string, db_connection_string)
                self.vault.insert_obj(VAULT_KEY__jaaql_password, jaaql_password)
                self.vault.insert_obj(VAULT_KEY__super_db_password, super_db_password)

            if install_key != self.install_key:
                raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)

            if db_connection_string is None:
                db_connection_string = PG__default_connection_string % os.environ[PG_ENV__password]

            address, port, _, username, db_password = DBInterface.fracture_uri(db_connection_string)

            super_interface = create_interface(self.config, address, port, DB__jaaql, username, db_password)
            conn = super_interface.get_conn()
            super_interface.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "01.install_domains.generated.sql"))
            super_interface.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "02.install_super_user.exceptions.sql"))
            super_interface.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "03.install_super_user.handwritten.sql"))
            if jaaql_db_password is not None:
                super_interface.execute_query(conn, QUERY__setup_jaaql_role_with_password, {KEY__password: jaaql_db_password})
            else:
                resp = super_interface.execute_query(conn, QUERY__setup_jaaql_role)
                jaaql_db_password = resp[1][0][0]
            if allow_uninstall or not self.is_container:
                self.vault.insert_obj(VAULT_KEY__jaaql_db_password, jaaql_db_password)
            super_interface.commit(conn)
            super_interface.put_conn(conn)
            super_interface.close()

            self.jaaql_lookup_connection = create_interface(self.config, address, port, DB__jaaql, ROLE__jaaql, jaaql_db_password)
            conn = self.jaaql_lookup_connection.get_conn()
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts,
                                                                        "04.install_jaaql_data_structures.generated.sql"))
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "05.install_jaaql.exceptions.sql"))
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "06.install_jaaql.handwritten.sql"))
            self.jaaql_lookup_connection.commit(conn)
            self.jaaql_lookup_connection.put_conn(conn)

            self.create_account_with_potential_password(self.jaaql_lookup_connection, USERNAME__jaaql, ROLE__jaaql, jaaql_password,
                                                        already_exists=True)
            self.create_account_with_potential_password(self.jaaql_lookup_connection, USERNAME__super_db, ROLE__postgres, super_db_password,
                                                        already_exists=True)
            self.create_account_with_potential_password(self.jaaql_lookup_connection, USERNAME__anonymous, password=PASSWORD__anonymous,
                                                        is_the_anonymous_user=True)

            super_conn_str = PROTOCOL__postgres + username + ":" + db_password + "@" + address + ":" + str(port) + "/"
            self.vault.insert_obj(VAULT_KEY__super_db_credentials, super_conn_str)
            jaaql_lookup_str = PROTOCOL__postgres + ROLE__jaaql + ":" + jaaql_db_password + "@" + address + ":" + str(port) + "/" + DB__jaaql
            self.vault.insert_obj(VAULT_KEY__jaaql_lookup_connection, jaaql_lookup_str)

            if self.is_container and do_reboot:
                self.jaaql_lookup_connection.close()
                print("Rebooting to allow JAAQL config to be shared among workers")
                threading.Thread(target=self.exit_jaaql).start()
            else:
                self.has_installed = True
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
            return payload[KEY__account_id], payload[KEY__username], payload[KEY__ip_address], payload[KEY__is_the_anonymous_user]
        except Exception:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

    def verify_auth_token(self, auth_token: str, ip_address: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth)
        if not decoded or decoded[KEY__ip_address] != ip_address:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        validate_is_most_recent_password(self.jaaql_lookup_connection, decoded[KEY__account_id], decoded[KEY__password],
                                         singleton_message=ERR__invalid_token, singleton_code=HTTPStatus.UNAUTHORIZED)

        return decoded[KEY__account_id], decoded[KEY__username], decoded[KEY__ip_address], decoded[KEY__is_the_anonymous_user]

    def refresh_auth_token(self, auth_token: str, ip_address: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth, allow_expired=True)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        if datetime.fromisoformat(decoded[KEY__created]) + timedelta(milliseconds=self.refresh_expiry_ms) < datetime.now():
            raise HttpStatusException(ERR__refresh_expired, HTTPStatus.UNAUTHORIZED)

        return self.get_auth_token(decoded[KEY__username], ip_address)

    def get_bypass_user(self, username: str, ip_address: str):
        account = fetch_most_recent_password_from_username(self.jaaql_lookup_connection, self.get_db_crypt_key(),
                                                           self.get_vault_repeatable_salt(), username, singleton_code=HTTPStatus.UNAUTHORIZED)
        salt_user = self.get_repeatable_salt(account[KG__account__id])
        encrypted_salted_ip_address = jaaql__encrypt(ip_address, self.get_db_crypt_key(), salt_user)
        address = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY___add_or_update_validated_ip_address,
                                                       {KG__validated_ip_address__account: account[KG__account__id],
                                                        KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address},
                                                       as_objects=True)[KG__validated_ip_address__uuid]

        return account[KG__account__id], address

    def get_auth_token(self, username: str, ip_address: str, password: str = None, response: JAAQLResponse = None):
        incorrect_credentials = False
        account = None
        encrypted_salted_ip_address = None

        try:
            account = fetch_most_recent_password_from_username(self.jaaql_lookup_connection, self.get_db_crypt_key(),
                                                               self.get_vault_repeatable_salt(), username, singleton_code=HTTPStatus.UNAUTHORIZED)
        except HttpStatusException as exc:
            if exc.response_code == HTTPStatus.UNAUTHORIZED:
                incorrect_credentials = True
            else:
                raise exc

        if not incorrect_credentials:
            salt_user = self.get_repeatable_salt(account[KG__account__id])

            encrypted_salted_ip_address = jaaql__encrypt(ip_address, self.get_db_crypt_key(), salt_user)  # An optimisation, it is used later twice

            if password is not None:
                incorrect_credentials = not crypt_utils.verify_password_hash(account[KG__account_password__hash], password,
                                                                             salt=self.get_repeatable_salt(account[KG__account__id]))
            else:
                incorrect_credentials = not exists_matching_validated_ip_address(self.jaaql_lookup_connection, encrypted_salted_ip_address)

        if incorrect_credentials:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        address = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY___add_or_update_validated_ip_address,
                                                       {KG__validated_ip_address__account: account[KG__account__id],
                                                        KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address},
                                                       as_objects=True)[KG__validated_ip_address__uuid]

        jwt_data = {
            KEY__account_id: str(account[KG__account__id]),
            KEY__password: str(account[KG__account_password__uuid]),
            KEY__username: username,
            KEY__ip_address: ip_address,
            KEY__ip_id: str(address),
            KEY__created: datetime.now().isoformat(),
            KEY__is_the_anonymous_user: username == USERNAME__anonymous
        }

        if response is not None:
            response.account_id = str(account[KG__account__id]),
            response.ip_id = str(address)

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

    def create_interface_for_db(self, user_id: str, database: str, sub_role: str = None):
        jaaql_uri = self.vault.get_obj(VAULT_KEY__super_db_credentials)
        address, port, _, username, password = DBInterface.fracture_uri(jaaql_uri)
        return create_interface(self.config, address, port, database, username, password=password, role=user_id, sub_role=sub_role)

    def attach_dispatcher_credentials(self, connection: DBInterface, inputs: dict):
        email_dispatcher__update(connection, self.get_db_crypt_key(), **inputs)

    def send_email(self, application: str, template: str, application_artifacts_source: str, application_base_url: str, account_id: str,
                   parameters: dict = None, parameter_id: str = None, none_sanitized_parameters: dict = None):
        if none_sanitized_parameters is None:
            none_sanitized_parameters = {}

        account = account__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), account_id)
        template = email_template__select(self.jaaql_lookup_connection, application, template)

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
            self.submit({
                KEY__application: application,
                KEY__schema: template[KG__email_template__validation_schema],
                KEY_query: ins_query,
                KEY_parameters: parameters,
                KEY_assert: ASSERT_one
            }, account_id)
            parameter_id = execute_supplied_statement_singleton(self.jaaql_lookup_connection, ins_query, parameters, as_objects=True)[KEY__id]

            sel_table = \
                template[KG__email_template__data_validation_table] if template[KG__email_template__data_validation_view] is None \
                else template[KG__email_template__data_validation_view]

            sel_query = "SELECT * FROM %s WHERE id = :id" % sel_table
            self.submit({
                KEY__application: application,
                KEY__schema: template[KG__email_template__validation_schema],
                KEY_query: sel_query,
                KEY_parameters: parameters,
                KEY_assert: ASSERT_one
            }, account_id)
            parameters = execute_supplied_statement_singleton(self.jaaql_lookup_connection, sel_query, {KEY__id: parameter_id}, as_objects=True)
        else:
            parameters = {}

        none_sanitized_parameters[EMAIL_PARAM__app_url] = application_base_url
        none_sanitized_parameters[EMAIL_PARAM__email_address] = account[KG__account__username]
        parameters = {**parameters, **none_sanitized_parameters}

        self.email_manager.construct_and_send_email(application_artifacts_source, template[KG__email_template__dispatcher], template,
                                                    account[KG__account__username], parameters)

    def gen_security_event_unlock_code(self, codeset: str, length: int):
        return "".join([codeset[random.randint(0, len(codeset) - 1)] for _ in range(length)])

    def check_security_event_key_and_security_event_is_unlocked(self, inputs: dict, returning: bool = False):
        evt = check_security_event_unlock(
            self.jaaql_lookup_connection, inputs[KG__security_event__event_lock], inputs[KG__security_event__unlock_code],
            inputs[KG__security_event__unlock_key], singleton_message=ERR__invalid_lock
        )

        if evt[KG__security_event__wrong_key_attempt_count] >= CODE__max_attempts:
            raise HttpStatusException("Too many invalid attempts to unlock the code")

        timezone = evt[KG__security_event__creation_timestamp].tzinfo
        add_seconds = timedelta(seconds=evt[KG__application__unlock_code_validity_period])
        print(timezone)
        print(evt[KG__security_event__creation_timestamp])
        print(add_seconds)
        print(evt[KG__security_event__creation_timestamp] + add_seconds)
        print(datetime.now(timezone))
        if evt[KG__security_event__creation_timestamp] + add_seconds < datetime.now(timezone):
            raise HttpStatusException(ERR__unlock_code_expired)

        if not evt[KEY__key_fits]:
            raise HttpStatusException(ERR__incorrect_lock_code)

        if returning:
            return evt
        else:
            template = email_template__select(self.jaaql_lookup_connection, evt[KG__security_event__application],
                                              evt[KG__security_event__email_template])
            return template[KG__email_template__type]

    def mark_security_event_unlocked(self, sec_evt: dict):
        security_event__update(self.jaaql_lookup_connection, sec_evt[KG__security_event__application], sec_evt[KG__security_event__event_lock],
                               unlock_timestamp=datetime.now())

    def finish_security_event(self, inputs: dict, ip_address: str):
        sec_evt = self.check_security_event_key_and_security_event_is_unlocked({
            KG__security_event__event_lock: inputs[KG__security_event__event_lock],
            KG__security_event__unlock_code: inputs[KG__security_event__unlock_code],
            KG__security_event__unlock_key: inputs[KG__security_event__unlock_key]
        }, returning=True)

        template = email_template__select(self.jaaql_lookup_connection, sec_evt[KG__security_event__application],
                                          sec_evt[KG__security_event__email_template])

        parameters = None

        if template[KG__email_template__data_validation_table]:
            app = application__select(self.jaaql_lookup_connection, sec_evt[KG__security_event__application])  # TODO try select parameters
            parameters = {}
            # TODO possibly load parameters

        if template[KG__email_template__type] in [EMAIL_TYPE__signup, EMAIL_TYPE__reset_password, EMAIL_TYPE__unregistered_password_reset]:
            self.add_account_password(sec_evt[KG__security_event__account], inputs[KEY__password])

        account = account__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), sec_evt[KG__security_event__account])
        auth_token = self.get_auth_token(account[KG__account__username], ip_address, inputs[KEY__password])

        self.mark_security_event_unlocked(sec_evt)

        return {
            KEY__oauth_token: auth_token,
            KEY__parameters: parameters
        }

    def reset_password(self, inputs: dict):
        app = application__select(self.jaaql_lookup_connection, inputs[KG__security_event__application])
        if inputs[KEY__reset_password_template] is None:
            inputs[KEY__reset_password_template] = app[KG__application__default_r_et]
        if inputs[KEY__unregistered_user_reset_password_template] is None:
            inputs[KEY__unregistered_user_reset_password_template] = app[KG__application__default_u_et]

        if inputs[KEY__reset_password_template] is None:
            raise HttpStatusException("Missing reset password template for application. Either supply one in the reset call or set a default")

        if inputs[KEY__unregistered_user_reset_password_template] is None:
            raise HttpStatusException("Missing unregistered user template for application. Either supply one in the reset call or set a default")

        reset_template = email_template__select(self.jaaql_lookup_connection, inputs[KG__security_event__application],
                                                inputs[KEY__reset_password_template])
        if reset_template[KG__email_template__type] != EMAIL_TYPE__reset_password:
            raise HttpStatusException(ERR__template_not_reset)

        unregistered_template = email_template__select(self.jaaql_lookup_connection, inputs[KG__security_event__application],
                                                       inputs[KEY__unregistered_user_reset_password_template])
        if unregistered_template[KG__email_template__type] != EMAIL_TYPE__unregistered_password_reset:
            raise HttpStatusException(ERR__template_not_unregistered)

        account_existed = False
        try:
            account_id = self.create_account_with_potential_password(self.jaaql_lookup_connection, inputs[KEY__username])
        except HttpStatusException as hs:
            if not hs.message.startswith(SQL__err_duplicate):
                raise hs  # Unrelated exception, raise it

            account = fetch_account_from_username(self.jaaql_lookup_connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                                  inputs[KEY__username])
            account_id = account[KG__account__id]
            if account[KG__account__most_recent_password] is not None:
                account_existed = True

        count = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                     QUERY__count_security_events_of_type_in_24hr_window,
                                                     {
                                                         KEY__type_one: EMAIL_TYPE__reset_password,
                                                         KEY__type_two: EMAIL_TYPE__unregistered_password_reset,
                                                         KG__security_event__account: account_id
                                                     }, as_objects=True)[ATTR__count]

        if count >= RESEND__reset_max:
            raise HttpStatusException(ERR__too_many_reset_requests, HTTPStatus.TOO_MANY_REQUESTS)

        template = None
        if account_existed and inputs[KEY__reset_password_template] is not None:
            template = inputs[KEY__reset_password_template]
        elif not account_existed and inputs[KEY__unregistered_user_reset_password_template] is not None:
            template = inputs[KEY__unregistered_user_reset_password_template]

        unlock_code = self.gen_security_event_unlock_code(CODE__letters, CODE__invite_length)
        reg_env_ins = security_event__insert(self.jaaql_lookup_connection, inputs[KG__security_event__application], template, account_id,
                                             unlock_code)

        self.send_email(inputs[KG__security_event__application], template, app[KG__application__artifacts_source],
                        app[KG__application__base_url], account_id, inputs[KEY__parameters],
                        parameter_id=reg_env_ins[KG__security_event__event_lock], none_sanitized_parameters={
                EMAIL_PARAM__unlock_key: reg_env_ins[KG__security_event__unlock_key],
                EMAIL_PARAM__unlock_code: unlock_code
            })

        return {
            KG__security_event__event_lock: reg_env_ins[KG__security_event__event_lock]
        }

    def sign_up(self, inputs: dict):
        app = application__select(self.jaaql_lookup_connection, inputs[KG__security_event__application])
        if inputs[KEY__sign_up_template] is None:
            inputs[KEY__sign_up_template] = app[KG__application__default_s_et]
        if inputs[KEY__already_signed_up_template] is None:
            inputs[KEY__already_signed_up_template] = app[KG__application__default_a_et]

        if inputs[KEY__sign_up_template] is None:
            raise HttpStatusException("Missing sign up template for application. Either supply one in the sign up call or set a default")

        if inputs[KEY__already_signed_up_template] is None:
            raise HttpStatusException("Missing already signed up template for application. Either supply one in the sign up call or set a default")

        sign_up_template = email_template__select(self.jaaql_lookup_connection, inputs[KG__security_event__application],
                                                  inputs[KEY__sign_up_template])
        if sign_up_template[KG__email_template__type] != EMAIL_TYPE__signup:
            raise HttpStatusException(ERR__template_not_signup)

        already_signed_up_template = email_template__select(self.jaaql_lookup_connection, inputs[KG__security_event__application],
                                                            inputs[KEY__already_signed_up_template])
        if already_signed_up_template[KG__email_template__type] != EMAIL_TYPE__already_signed_up:
            raise HttpStatusException(ERR__template_not_already)

        account_existed = False
        try:
            account_id = self.create_account_with_potential_password(self.jaaql_lookup_connection, inputs[KEY__username])
        except HttpStatusException as hs:
            if not hs.message.startswith(SQL__err_duplicate):
                raise hs  # Unrelated exception, raise it

            account = fetch_account_from_username(self.jaaql_lookup_connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                                  inputs[KEY__username])
            account_id = account[KG__account__id]
            if account[KG__account__most_recent_password] is not None:
                account_existed = True

        count = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                     QUERY__count_security_events_of_type_in_24hr_window,
                                                     {
                                                         KEY__type_one: EMAIL_TYPE__signup,
                                                         KEY__type_two: EMAIL_TYPE__already_signed_up,
                                                         KG__security_event__account: account_id
                                                     }, as_objects=True)[ATTR__count]

        if count >= RESEND__invite_max:
            raise HttpStatusException(ERR__too_many_signup_attempts, HTTPStatus.TOO_MANY_REQUESTS)

        template = None
        if account_existed and inputs[KEY__already_signed_up_template] is not None:
            template = inputs[KEY__already_signed_up_template]
        elif not account_existed and inputs[KEY__sign_up_template] is not None:
            template = inputs[KEY__sign_up_template]

        unlock_code = self.gen_security_event_unlock_code(CODE__letters, CODE__invite_length)
        reg_env_ins = security_event__insert(self.jaaql_lookup_connection, inputs[KG__security_event__application], template, account_id,
                                             unlock_code)

        self.send_email(inputs[KG__security_event__application], template, app[KG__application__artifacts_source],
                        app[KG__application__base_url], account_id, inputs[KEY__parameters],
                        parameter_id=reg_env_ins[KG__security_event__event_lock], none_sanitized_parameters={
                EMAIL_PARAM__unlock_key: reg_env_ins[KG__security_event__unlock_key],
                EMAIL_PARAM__unlock_code: unlock_code
            })

        return {
            KG__security_event__event_lock: reg_env_ins[KG__security_event__event_lock]
        }

    def submit(self, inputs: dict, account_id: str, verification_hook: Queue = None):
        if not isinstance(inputs, dict):
            raise HttpStatusException("Expected object or string input")

        if KEY__application in inputs:
            schemas = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_application_schemas, {
                KG__application_schema__application: inputs[KEY__application]
            }, as_objects=True)
            if len(schemas) == 0:
                raise HttpStatusException("Application has no schemas!")
            if not schemas[0][KG__application__is_live]:
                raise HttpStatusException("Application is currently being deployed. Please wait a few minutes until deployment is complete")
            schemas = {itm[KG__application_schema__name]: itm for itm in schemas}

            found_db = None
            if KEY__schema in inputs:
                found_db = schemas[inputs[KEY__schema]][KEY__database]
                inputs.pop(KEY__schema)
            else:
                if len(schemas) == 1:
                    found_db = schemas[list(schemas.keys())[0]][KEY__database]
                else:
                    found_dbs = [val[KEY__database] for _, val in schemas.items() if val[KEY__is_default]]
                    if len(found_dbs) == 1:
                        found_db = found_dbs[0]

            if not found_db:
                raise HttpStatusException(ERR__schema_invalid)

            inputs[KEY__database] = found_db

        if KEY__database not in inputs:
            inputs[KEY__database] = DB__jaaql

        sub_role = inputs.pop(KEY__role) if KEY__role in inputs else None
        required_db = self.create_interface_for_db(account_id, inputs[KEY__database], sub_role)

        return InterpretJAAQL(required_db).transform(inputs, skip_commit=inputs.get(KEY__read_only), wait_hook=verification_hook,
                                                     encryption_key=self.get_db_crypt_key(),
                                                     canned_query_service=self.cached_canned_query_service)
