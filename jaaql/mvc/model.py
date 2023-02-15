import uuid

from jaaql.db.db_pg_interface import DBPGInterface
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jwt_crypt_key
from jaaql.exceptions.http_status_exception import HttpStatusException, HTTPStatus, ERR__already_installed
from os.path import join
from jaaql.constants import *
from jaaql.mvc.response import JAAQLResponse
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.utilities.utils import get_jaaql_root
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


ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__invalid_level = "Invalid level!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__email_template_not_installed = "Either email template does not exist"
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
                                               already_exists: bool = False, is_the_anonymous_user: bool = False, ):
        account_id = create_account(connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                    username, attach_as, already_exists,
                                    is_the_anonymous_user)

        if password:
            self.add_account_password(account_id, password)

        return account_id

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
            time.sleep(5)

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
                resp = super_interface.execute_query(conn, QUERY__setup_jaaql_role_with_password, {KEY__password: jaaql_db_password})
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
                incorrect_credentials = crypt_utils.verify_password_hash(account[KG__account_password__hash], password,
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

    def submit(self, inputs: dict, account_id: str, verification_hook: Queue):
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
