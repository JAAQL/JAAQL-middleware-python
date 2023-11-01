import uuid

import re
from wsgiref.handlers import format_date_time
from jaaql.db.db_pg_interface import DBPGInterface, QUERY__dba_query_external
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jwt_crypt_key
from jaaql.exceptions.http_status_exception import HttpStatusException, ERR__already_installed, HttpSingletonStatusException
from os.path import join
from jaaql.interpreter.interpret_jaaql import KEY_query, KEY_parameters
from jaaql.constants import *
from jaaql.utilities.utils import get_jaaql_root, get_base_url
from jaaql.db.db_utils import create_interface, jaaql__encrypt, create_interface_for_db
from jaaql.db.db_utils_no_circ import submit, get_required_db, objectify
from jaaql.utilities import crypt_utils
from jaaql.utilities.utils_no_project_imports import get_cookie_attrs, COOKIE_JAAQL_AUTH, COOKIE_ATTR_EXPIRES
from jaaql.mvc.response import *
import threading
from datetime import datetime, timedelta
from jaaql.mvc.handmade_queries import *
from jwt.utils import base64url_decode
import json
import os
from queue import Queue
from jaaql.services.shared_var_service import ARG__value, ARG__variable, SHARED_VAR__frozen
import subprocess
import time
import random
import requests

from jaaql.migrations.migrations import run_migrations

NGINX_MARKER__first = "limit_req_status 429;\n    "
NGINX_MARKER__second = "proxy_set_header X-Real-IP $remote_addr;\n    "
NGINX_INSERT__frozen = "    return 503;\n    "

ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__invalid_level = "Invalid level!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__email_template_not_installed = "Either email template does not exist"
ERR__lacking_permissions = "Only an administrator can perform this action!"
ERR__cant_send_attachments = "Cannot send attachments to other people"
ERR__keep_alive_failed = "Keep alive failed"
ERR__template_not_signup = "Sign up template does not have the correct type"
ERR__template_not_already = "Already signed up template does not have the correct type"
ERR__template_not_reset = "Reset template does not have the correct type"
ERR__template_not_unregistered = "Unregistered template does not have the correct type"
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

SPECIAL_COLUMN_DBMS_USER = "dbms_user"


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

    def prepare_queries(self, inputs: dict, account_id: str):
        db_connection = create_interface_for_db(self.vault, self.config, account_id, inputs[KEY__database], None)

        self.is_dba(db_connection)

        res = []

        for query in inputs["queries"]:
            my_uuid = str(uuid.uuid4()).replace("-", "_")
            exc = None
            cost = None
            try:
                results = execute_supplied_statement(db_connection, query["query"].strip(), do_prepare_only=my_uuid)
                cost = float(results["rows"][0][0].split("..")[1].split(" ")[0])
            except Exception as ex:
                exc = str(ex).replace("PREPARE _jaaql_query_check_" + my_uuid + " as ", "").replace(
                    " ... _jaaql_query_check_" + my_uuid + " as ", "")

            res.append({
                "location": query["file"] + ":" + str(query["line_number"]),
                "name": query["name"],
                "cost": cost,
                "exception": exc,
            })

        return sorted(res, key=lambda x: (x["exception"] if x["exception"] is not None else '', float('-inf') if x["cost"] is None else -x["cost"]))

    def prepare_queries__old(self, connection: DBInterface, account_id: str, inputs: dict):
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

    def is_dba(self, connection: DBInterface):
        res = execute_supplied_statement_singleton(connection, QUERY__dba_query_external, as_objects=True)["pg_has_role"]
        if not res:
            raise HttpStatusException("You do not have dba privileges")

    def freeze(self, connection: DBInterface):
        self.is_super_admin(connection)

        if self.is_container:
            if self.is_frozen():
                raise HttpStatusException("JAAQL is already frozen")

            nginx_content = None
            with open("/etc/nginx/sites-available/jaaql", "r") as site_file:
                nginx_content = site_file.read()
            if nginx_content is None:
                raise HttpStatusException("Failed to open file for freezing")
            insert_index = nginx_content.index(NGINX_MARKER__first) + len(NGINX_MARKER__first)
            nginx_content = nginx_content[:insert_index] + NGINX_INSERT__frozen + nginx_content[insert_index:]
            insert_index = nginx_content.index(NGINX_MARKER__second) + len(NGINX_MARKER__second)
            nginx_content = nginx_content[:insert_index] + NGINX_INSERT__frozen + nginx_content[insert_index:]
            with open("/etc/nginx/sites-available/jaaql", "w") as site_file:
                site_file.write(nginx_content)
            subprocess.call("service nginx restart", shell=True)

            requests.post("http://127.0.0.1:" + str(PORT__shared_var_service) + ENDPOINT__set_shared_var,
                          json={ARG__variable: SHARED_VAR__frozen, ARG__value: True})
        else:
            raise HttpStatusException("Cannot freeze JAAQL running outside a container")

    def defrost(self, connection: DBInterface):
        self.is_super_admin(connection)

        if self.is_container:
            if not self.is_frozen():
                raise HttpStatusException("JAAQL is already defrosted")

            nginx_content = None
            with open("/etc/nginx/sites-available/jaaql", "r") as site_file:
                nginx_content = site_file.read()
            if nginx_content is None:
                raise HttpStatusException("Failed to open file for defrosting")
            nginx_content = nginx_content.replace("\n        return 503;", "")
            with open("/etc/nginx/sites-available/jaaql", "w") as site_file:
                site_file.write(nginx_content)
            subprocess.call("service nginx restart", shell=True)

            requests.post("http://127.0.0.1:" + str(PORT__shared_var_service) + ENDPOINT__set_shared_var,
                          json={ARG__variable: SHARED_VAR__frozen, ARG__value: False})
        else:
            raise HttpStatusException("Cannot defrost JAAQL running outside a container")

    def is_frozen(self):
        return requests.post("http://127.0.0.1:" + str(PORT__shared_var_service) + ENDPOINT__get_shared_var,
                             json={ARG__variable: SHARED_VAR__frozen}).json()[ARG__value]

    def clean(self, connection: DBInterface):
        self.is_super_admin(connection)

        if self.is_container:
            if not self.vault.get_obj(VAULT_KEY__allow_jaaql_uninstall):
                raise HttpStatusException("JAAQL not permitted to uninstall itself")

            subprocess.call("./pg_reboot.sh", cwd="/")
        else:
            subprocess.call("docker kill jaaql_pg")
            subprocess.call("docker rm jaaql_pg")
            subprocess.Popen("docker run --name jaaql_pg -p 5434:5432 jaaql/jaaql_pg", start_new_session=True, creationflags=0x00000008)
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

    def add_my_account_password(self, account_id: str, username: str, ip_address: str, is_the_anonymous_user: bool, old_password: str, password: str):
        if is_the_anonymous_user:
            raise HttpStatusException("Cannot change this user's password")
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
                jaaql_db_password = resp[2][0][0]
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
            return payload[KEY__account_id], payload[KEY__username], payload[KEY__ip_address], payload[KEY__is_the_anonymous_user], \
                payload[KEY__remember_me]
        except Exception:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

    def verify_auth_token(self, auth_token: str, ip_address: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth)
        if not decoded or decoded[KEY__ip_address] != ip_address:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        validate_is_most_recent_password(self.jaaql_lookup_connection, decoded[KEY__account_id], decoded[KEY__password],
                                         singleton_message=ERR__invalid_token, singleton_code=HTTPStatus.UNAUTHORIZED)

        return decoded[KEY__account_id], decoded[KEY__username], decoded[KEY__ip_address], decoded[KEY__is_the_anonymous_user], \
            decoded[KEY__remember_me]

    def refresh_auth_token(self, auth_token: str, ip_address: str, cookie: bool = False, response: JAAQLResponse = None):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth, allow_expired=True)
        remember_me = False
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
        if decoded.get(KEY__remember_me):
            remember_me = decoded[KEY__remember_me]

        if datetime.fromisoformat(decoded[KEY__created]) + timedelta(milliseconds=self.refresh_expiry_ms) < datetime.now():
            raise HttpStatusException(ERR__refresh_expired, HTTPStatus.UNAUTHORIZED)

        return self.get_auth_token(decoded[KEY__username], ip_address, cookie=cookie, remember_me=remember_me, response=response)

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

    def logout_cookie(self, response: JAAQLResponse):
        response.set_cookie(COOKIE_JAAQL_AUTH, "", attributes={COOKIE_ATTR_EXPIRES: format_date_time(0)}, is_https=self.is_https)

    def get_auth_token(self, username: str, ip_address: str, password: str = None, response: JAAQLResponse = None, cookie: bool = False,
                       remember_me: bool = False):
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
            KEY__is_the_anonymous_user: username == USERNAME__anonymous,
            KEY__remember_me: remember_me
        }

        if response is not None:
            response.account_id = str(account[KG__account__id]),
            response.ip_id = str(address)

        jwt_token = crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

        if cookie:
            response.set_cookie(COOKIE_JAAQL_AUTH, value=jwt_token,
                                attributes=get_cookie_attrs(self.vigilant_sessions, remember_me, self.is_container),
                                is_https=self.is_https)
        else:
            return jwt_token

    def attach_dispatcher_credentials(self, connection: DBInterface, inputs: dict):
        email_dispatcher__update(connection, self.get_db_crypt_key(), **inputs)

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

    def finish_security_event(self, inputs: dict):
        sec_evt = self.check_security_event_key_and_security_event_is_unlocked({
            KG__security_event__event_lock: inputs[KG__security_event__event_lock],
            KG__security_event__unlock_code: inputs[KG__security_event__unlock_code],
            KG__security_event__unlock_key: inputs[KG__security_event__unlock_key]
        }, returning=True)

        template = email_template__select(self.jaaql_lookup_connection, sec_evt[KG__security_event__application],
                                          sec_evt[KG__security_event__email_template])
        account = account__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), sec_evt[KG__security_event__account])

        parameters = None

        if template[KG__email_template__data_validation_table]:
            # app = application__select(self.jaaql_lookup_connection, sec_evt[KG__security_event__application])  # TODO try select parameters
            parameters = {}
            # TODO possibly load parameters

        if template[KG__email_template__type] in [EMAIL_TYPE__signup, EMAIL_TYPE__reset_password, EMAIL_TYPE__unregistered_password_reset]:
            self.add_account_password(sec_evt[KG__security_event__account], inputs[KEY__password])

        self.mark_security_event_unlocked(sec_evt)

        if template[KG__email_template__type] == EMAIL_TYPE__signup:
            data_relation = template[KG__email_template__data_validation_view]
            submit_data = {
                KEY__schema: template[KG__email_template__validation_schema],
                KEY__application: template[KEY__application],
                KEY_parameters: {
                    "signed_up_at": datetime.now(),
                    "dbms_user": sec_evt[KG__security_event__account]
                },
                KEY_query: f'UPDATE {data_relation} SET signed_up_at = :signed_up_at WHERE dbms_user = :dbms_user AND signed_up_at is null'  # Ignore pycharm PEP issue
            }
            # We now get the data that can be shown in the email
            submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, submit_data,
                   self.jaaql_lookup_connection.role, None, self.cached_canned_query_service)

        return {
            KEY__parameters: parameters,
            KEY__username: account[KG__account__username]
        }

    def send_email(self, is_the_anonymous_user: bool, account_id: str, inputs: dict, username: str):
        app = application__select(self.jaaql_lookup_connection, inputs[KEY__application])

        fetched_template = email_template__select(self.jaaql_lookup_connection, inputs[KEY__application], inputs[KEY__template])
        if is_the_anonymous_user and not fetched_template[KG__email_template__can_be_sent_anonymously]:
            raise HttpStatusException("Cannot send this template anonymously")

        # [25/10/23] The below code is disabled as send email allows only for sending to the current email
        # Anonymous email templates must be sent to the domain recipient
        # if fetched_template[KG__email_template__can_be_sent_anonymously]:
        #     if not fetched_template[KG__email_template__dispatcher_domain_recipient]:
        #         raise HttpStatusException("Must specify dispatcher domain recipient if sending anonymous emails!")

        # recipient = fetched_template[KG__email_template__dispatcher_domain_recipient].split("@")[0]
        # domain = email_dispatcher__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), inputs[KEY__application],
        #                                   fetched_template[KG__email_template__dispatcher])[KG__email_dispatcher__username].split("@")[1]
        # recipient = recipient + "@" + domain

        submit_data = {
            KEY__application: inputs[KG__security_event__application],
            KEY__parameters: inputs[KEY__parameters],
            KEY__schema: fetched_template[KG__email_template__validation_schema]
        }

        data_relation = fetched_template[KG__email_template__data_validation_view]
        if re.match(REGEX__dmbs_object_name, data_relation) is None:
            raise HttpStatusException("Unsafe data relation specified for email template")
        safe_parameters = []
        for key, val in inputs[KEY__parameters].items():
            if re.match(REGEX__dmbs_object_name, key) is None:
                raise HttpStatusException("Unsafe parameter specified for email template")
            safe_parameters.append(f'{key} = :{key}')  # Ignore pycharm PEP issue
        where_clause = " AND ".join(safe_parameters)
        submit_data[KEY_query] = f'SELECT * FROM {data_relation} WHERE {where_clause}'  # Ignore pycharm PEP issue
        # We now get the data that can be shown in the email
        email_replacement_data = submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection,
                                        submit_data, account_id, None, self.cached_canned_query_service,
                                        as_objects=True, singleton=True)

        # TODO write exception query. Select document_request where application = ... and template = ...
        # TODO change how file is named and waited for

        self.email_manager.construct_and_send_email(app[KG__application__artifacts_source],
                                                    fetched_template[KG__email_template__dispatcher], fetched_template,
                                                    username, email_replacement_data,
                                                    attachments=None, attachment_access_token=None)  # TODO load attachments

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

        unlock_code = self.gen_security_event_unlock_code(CODE__letters, CODE__reset_length)
        reg_env_ins = security_event__insert(self.jaaql_lookup_connection, inputs[KG__security_event__application], template, account_id,
                                             unlock_code)

        self.email_manager.send_email(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection,
                                      inputs[KG__security_event__application], template,
                                      app[KG__application__artifacts_source],
                                      app[KG__application__base_url], account_id, inputs[KEY__parameters],
                                      parameter_id=reg_env_ins[KG__security_event__event_lock], none_sanitized_parameters={
                EMAIL_PARAM__unlock_key: reg_env_ins[KG__security_event__unlock_key],
                EMAIL_PARAM__unlock_code: unlock_code
            })

        return {
            KG__security_event__event_lock: reg_env_ins[KG__security_event__event_lock]
        }

    def sign_up(self, inputs: dict, account_id: str):
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

        conn = None
        account_db_interface = None

        try:
            submit_data = {
                KEY__application: inputs[KG__security_event__application],
                KEY__parameters: inputs[KEY__parameters],
                KEY_query: inputs[KEY_query],
                KEY__schema: sign_up_template[KG__email_template__validation_schema]
            }

            account_db_interface = get_required_db(self.vault, self.config, self.jaaql_lookup_connection, submit_data, account_id)
            conn = account_db_interface.get_conn()

            ret = submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, submit_data, account_id, None,
                         self.cached_canned_query_service, as_objects=False, singleton=True, keep_alive_conn=True, conn=conn, interface=account_db_interface)
            ret = objectify(ret[list(ret.keys())[-1]], singleton=True)

            # This is the permissions check. It is an update that returns something that is ignored
            # An exception will be triggered here if the user does not have permissions
            where_clause = " AND ".join(['"' + key + '" = :' + key for key in ret.keys() if re.match(REGEX__dmbs_object_name, key) is not None])
            if len(where_clause) != 0:
                where_clause = " AND " + where_clause
            sign_up_table = sign_up_template[KG__email_template__data_validation_table]
            upt_query = f'UPDATE "{sign_up_table}" SET dbms_user = :dbms_user WHERE dbms_user is null{where_clause}'  # Ignore pycharm pep issue
            submit_data[KEY_query] = upt_query
            submit_data[KEY_parameters] = ret
            submit_data[KEY_parameters][SPECIAL_COLUMN_DBMS_USER] = None
            submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, submit_data, account_id,
                   None, self.cached_canned_query_service, keep_alive_conn=True, conn=conn, interface=account_db_interface)

            data_relation = sign_up_template[KG__email_template__data_validation_view]
            if data_relation is None:
                data_relation = sign_up_template[KG__email_template__data_validation_table]

            if inputs.get(KEY__username) is None:
                get_user_data = {
                    KEY__application: inputs[KG__security_event__application],
                    KEY__schema: sign_up_template[KG__email_template__validation_schema],
                    KEY_parameters: inputs[KEY__parameters],
                    KEY_query: f'SELECT dbms_user FROM {data_relation} WHERE {where_clause[5:]}'  # Ignore pycharm PEP issue
                }

                try:
                    dbms_user = submit(self.vault, self.config, self.get_db_crypt_key(),
                                       self.jaaql_lookup_connection, get_user_data,
                                       self.jaaql_lookup_connection.role, None,
                                       self.cached_canned_query_service, as_objects=True,
                                       singleton=True)["dbms_user"]

                    account = account__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), dbms_user)
                    inputs[KEY__username] = account[KG__account__username]
                except HttpSingletonStatusException:
                    raise HttpSingletonStatusException("User with specified parameters could not be found!")

            # We now create the user if the user doesn't exist
            account_existed = False
            try:
                new_account_id = self.create_account_with_potential_password(self.jaaql_lookup_connection, inputs[KEY__username])
            except HttpStatusException as hs:
                if not hs.message.startswith(SQL__err_duplicate):
                    raise hs  # Unrelated exception, raise it

                account = fetch_account_from_username(self.jaaql_lookup_connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                                      inputs[KEY__username])
                new_account_id = account[KG__account__id]
                if account[KG__account__most_recent_password] is not None:
                    account_existed = True

            # We set the dbms user in the application. This can potentially cause an index clash due to a unique index on the dbms_user column
            # This is desirable in many situations but will allow username enumeration
            submit_data[KEY__parameters][SPECIAL_COLUMN_DBMS_USER] = new_account_id
            submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, submit_data, account_id,
                   None, self.cached_canned_query_service, keep_alive_conn=True, conn=conn, interface=account_db_interface)

            # We abort if there have been too many requests. Everything is rolled back
            count = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                         QUERY__count_security_events_of_type_in_24hr_window,
                                                         {
                                                             KEY__type_one: EMAIL_TYPE__signup,
                                                             KEY__type_two: EMAIL_TYPE__already_signed_up,
                                                             KG__security_event__account: new_account_id
                                                         }, as_objects=True)[ATTR__count]
            if count >= RESEND__invite_max:
                raise HttpStatusException(ERR__too_many_signup_attempts, HTTPStatus.TOO_MANY_REQUESTS)

            # Now for the only leap of faith in this algorithm. We have to commit as otherwise the jaaql user cannot access the data
            # If this fails we are unfortunately up shit creek without a paddle but this can't fail if the application is designed correctly
            account_db_interface.put_conn_handle_error(conn, None)  # No errors. This will commit

            # Choose the relation. We are deliberately going from the sign-up template ONLY to reduce the scope of what can go wrong security wise
            # This is because a user can mix and match sign up and already signed up, potentially leaking data
            # We will change the model in the future when time allows that we have a single sign up and reset template with alternatives attached
            if re.match(REGEX__dmbs_object_name, data_relation) is None:
                raise HttpStatusException("Unsafe data relation specified for sign up")
            submit_data[KEY_query] = f'SELECT * FROM {data_relation} WHERE dbms_user = :dbms_user{where_clause}'  # Ignore pycharm PEP issue
            # We now get the data that can be shown in the email
            email_replacement_data = submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, submit_data,
                                            self.jaaql_lookup_connection.role, None, self.cached_canned_query_service, as_objects=True,
                                            singleton=True)

            template = already_signed_up_template if account_existed else sign_up_template
            unlock_code = self.gen_security_event_unlock_code(CODE__letters, CODE__invite_length)
            reg_event = security_event__insert(self.jaaql_lookup_connection, inputs[KG__security_event__application], template[KG__email_template__name],
                                               new_account_id, unlock_code)

            email_replacement_data[EMAIL_PARAM__app_url] = app[KG__application__base_url]
            email_replacement_data[EMAIL_PARAM__email_address] = inputs[KEY__username]
            email_replacement_data[EMAIL_PARAM__unlock_key] = reg_event[KG__security_event__unlock_key]
            email_replacement_data[EMAIL_PARAM__unlock_code] = unlock_code

            self.email_manager.construct_and_send_email(app[KG__application__artifacts_source], template[KG__email_template__dispatcher], template,
                                                        inputs[KEY__username], email_replacement_data)

            return {
                KG__security_event__event_lock: reg_event[KG__security_event__event_lock]
            }
        except Exception as err:
            if conn is not None:
                account_db_interface.put_conn_handle_error(conn, err)

            raise err

    def submit(self, inputs: dict, account_id: str, verification_hook: Queue = None, as_objects: bool = False, singleton: bool = False):
        return submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, inputs, account_id, verification_hook,
                      self.cached_canned_query_service, as_objects=as_objects, singleton=singleton)
