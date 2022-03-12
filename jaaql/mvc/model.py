from jaaql.db.db_interface import DBInterface
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jaaql_lookup_connection, CONFIG_KEY_security,\
    CONFIG_KEY_SECURITY__mfa_label, CONFIG_KEY_SECURITY__mfa_issuer, VAULT_KEY__jwt_obj_crypt_key,\
    VAULT_KEY__jwt_crypt_key, VAULT_KEY__jaaql_db_id, DIR__vault, FILE__was_installed
from jaaql.exceptions.http_status_exception import HttpStatusException, HTTPStatus
from typing import Optional
from jaaql.mvc.response import JAAQLResponse
from collections import Counter
from os.path import dirname
from jaaql.utilities import crypt_utils
import uuid
import pyotp
import qrcode
import qrcode.image.svg
from base64 import b64encode as b64e, b32encode as b32e
from io import BytesIO
from datetime import datetime, timedelta
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL
from jaaql.constants import *
from os.path import join
from jaaql.utilities.utils import get_jaaql_root
import time
import threading


ERR__already_installed = "JAAQL has already been installed!"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__password_incorrect = "Your password is incorrect!"
ERR__passwords_do_not_match = "The supplied passwords do not match!"
ERR__mfa_reused = "MFA has already been used. Please wait for a new one to generate"
ERR__invalid_token = "Invalid token!"
ERR__new_ip = "Token being used from an ip address not associated with these credentials. Please refresh it"
ERR__new_ua = "Token being used from a different browser. Please refresh it"
ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__duplicated_database = "User %s has a duplicate database precedence with databases '%s'"

JAAQL__username = "jaaql"

QUERY__application_ins = "INSERT INTO jaaql__application (name, description, url) VALUES (:name, :description, :url)"
QUERY__application_del = "DELETE FROM jaaql__application WHERE name = :name"
QUERY__application_sel = "SELECT * FROM jaaql__application"
QUERY__application_count = "SELECT COUNT(*) FROM jaaql__application"
QUERY__application_upd = "UPDATE jaaql__application SET name = coalesce(:new_name, name), description = coalesce(:new_description, description), url = coalesce(:new_url, url) WHERE name = :name"
QUERY__database_ins = "INSERT INTO jaaql__database (name, description, port, address, jaaql_name, interface_class, is_console_level) VALUES (:name, :description, :port, :address, :jaaql_name, 'DBPGInterface', :is_console_level) RETURNING id"
QUERY__database_sel = "SELECT * FROM jaaql__database"
QUERY__database_del = "UPDATE jaaql__database SET deleted = current_timestamp WHERE id = :id AND deleted is null"
QUERY__database_count = "SELECT COUNT(*) FROM jaaql__database"
QUERY__application_parameter_ins = "INSERT INTO jaaql__application_database_parameter (application, name, description) VALUES (:application, :name, :description)"
QUERY__application_parameter_del = "DELETE FROM jaaql__application_database_parameter WHERE name = :name AND application = :application"
QUERY__application_parameter_sel = "SELECT * FROM jaaql__application_database_parameter"
QUERY__application_parameter_count = "SELECT COUNT(*) FROM jaaql__application_database_parameter"
QUERY__application_configuration_ins = "INSERT INTO jaaql__application_database_configuration (application, name, description) VALUES (:application, :name, :description)"
QUERY__application_configuration_del = "DELETE FROM jaaql__application_database_configuration WHERE name = :name AND application = :application"
QUERY__application_configuration_sel = "SELECT * FROM jaaql__application_database_configuration"
QUERY__application_configuration_count = "SELECT COUNT(*) FROM jaaql__application_database_configuration"
QUERY__application_argument_ins = "INSERT INTO jaaql__application_database_argument (application, configuration, database, parameter) VALUES (:application, :configuration, :database, :parameter)"
QUERY__application_argument_del = "DELETE FROM jaaql__application_database_argument WHERE application = :application AND configuration = :configuration AND parameter = :parameter"
QUERY__application_argument_sel = "SELECT * FROM jaaql__application_database_argument"
QUERY__application_argument_count = "SELECT COUNT(*) FROM jaaql__application_database_argument"
QUERY__application_authorization_ins = "INSERT INTO jaaql__authorization_application (application, role) VALUES (:application, :role)"
QUERY__application_authorization_del = "DELETE FROM jaaql__authorization_application WHERE application = :application AND role = :role"
QUERY__application_authorization_sel = "SELECT * FROM jaaql__authorization_application"
QUERY__application_authorization_count = "SELECT COUNT(*) FROM jaaql__authorization_application"
QUERY__database_authorization_ins = "INSERT INTO jaaql__authorization_database (database, role, db_encrypted_username, db_encrypted_password, precedence) VALUES (:database, :role, :username, :password, coalesce(:precedence, 0))"
QUERY__database_authorization_del = "UPDATE jaaql__authorization_database SET deleted = current_timestamp WHERE id = :id AND deleted is null"
QUERY__database_authorization_sel = "SELECT id, database, role, db_encrypted_username as username, db_encrypted_password as password, deleted FROM jaaql__authorization_database"
QUERY__database_authorization_sel_one = "SELECT d.port, d.name, d.address, ad.database, ad.db_encrypted_username as username, ad.db_encrypted_password as password FROM jaaql__authorization_database ad INNER JOIN jaaql__database d ON d.id = ad.database WHERE role = :role AND ad.database = :database AND d.deleted is null and ad.deleted is null"
QUERY__database_authorization_count = "SELECT COUNT(*) FROM jaaql__authorization_database"
QUERY__user_ins = "INSERT INTO jaaql__user (email, mobile, enc_totp_iv) VALUES (lower(:email), :mobile, :totp_iv) RETURNING id"
QUERY__user_del = "UPDATE jaaql__user SET deleted = current_timestamp WHERE id = :the_user"
QUERY__user_totp_upd = "UPDATE jaaql__user SET last_totp = :last_totp WHERE id = :user_id"
QUERY__user_ip_sel = "SELECT encrypted_address as address, first_use, most_recent_use FROM jaaql__my_ips"
QUERY__user_ip_count = "SELECT COUNT(*) FROM jaaql__my_ips"
QUERY__user_ip_ins = "INSERT INTO jaaql__user_ip (the_user, address_hash, encrypted_address) VALUES (:id, :address_hash, :ip_address) ON CONFLICT ON CONSTRAINT jaaql__user_ip_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_ua_ins = "INSERT INTO jaaql__user_ua (the_user, ua_hash, encrypted_ua) VALUES (:id, :ua_hash, :ua) ON CONFLICT ON CONSTRAINT jaaql__user_ua_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_password_ins = "INSERT INTO jaaql__user_password (the_user, password_hash) VALUES (:the_user, :password_hash)"
QUERY__fetch_user_latest_password = "SELECT id, email, password_hash, enc_totp_iv as totp_iv, last_totp FROM jaaql__user_latest_password WHERE email = :username"
QUERY__user_create_role = "SELECT jaaql__create_role(:username, :password)"
QUERY__log_ins = "INSERT INTO jaaql__log (the_user, occurred, duration_ms, encrypted_exception, encrypted_input, ip, ua, status, endpoint) VALUES (:user_id, :occurred, :duration_ms, :exception, :input, :ip, :ua, :status, :endpoint)"
QUERY__user_log_sel = "SELECT occurred, encrypted_address as address, encrypted_ua as user_agent, status, endpoint, duration_ms, encrypted_exception as exception FROM jaaql__my_logs"
QUERY__user_log_count = "SELECT COUNT(*) FROM jaaql__my_logs"
QUERY__my_configs = "SELECT * FROM jaaql__my_configurations"
QUERY__authorized_configuration = """SELECT parameter_name, parameter_description, username, password, name, port, address, database, is_console_level FROM jaaql__their_authorized_configurations WHERE application = :application AND configuration = :configuration AND pg_has_role(:username, application_role, 'MEMBER') AND pg_has_role(:username, database_role, 'MEMBER')
        AND precedence IN (
            SELECT
                MAX(jad.precedence)
            FROM jaaql__authorized_configuration ac
            INNER JOIN
                 jaaql__authorization_database jad on ac.database = jad.database
            INNER JOIN
                 jaaql__database jd on jad.database = jd.id
            WHERE pg_has_role(:username, ac.application_role, 'MEMBER')
                AND pg_has_role(:username, ac.database_role, 'MEMBER')
            GROUP BY ac.parameter_name
        )
"""

ATTR__email = "email"
ATTR__mobile = "mobile"
ATTR__the_user = "the_user"
ATTR__existed = "existed"
ATTR__password_hash = "password_hash"
ATTR__address_hash = "address_hash"
ATTR__ip_address = "ip_address"
ATTR__ua_hash = "ua_hash"
ATTR__ua = "ua"
KEY__totp_iv = "totp_iv"
KEY__user_id = "user_id"
KEY__occurred = "occurred"
KEY__duration_ms = "duration_ms"
KEY__input = "input"
KEY__ip = "ip"
KEY__ua = "ua"
KEY__status = "status"
KEY__endpoint = "endpoint"
KEY__is_console_level = "is_console_level"

DELETION_PURPOSE__account = "account"
DELETION_PURPOSE__application = "application"
DELETION_PURPOSE__application_parameter = "application_parameter"
DELETION_PURPOSE__application_configuration = "application_configuration"
DELETION_PURPOSE__application_argument = "application_argument"
DELETION_PURPOSE__application_authorization = "application_authorization"
DELETION_PURPOSE__database_authorization = "database_authorization"
DELETION_PURPOSE__database = "database"

DESCRIPTION__jaaql_db = "The core jaaql database, used to store user information, logs and application/auth configs"
DATABASE__jaaql_internal_name = "jaaql db"

URI__otp_auth = "otpauth://totp/%s?secret=%s"
URI__otp_issuer_clause = "&issuer=%s"
HTML__base64_png = "data:image/png;base64,"
FORMAT__png = "png"

JWT__username = "username"
JWT__password = "password"
JWT__created = "created"
JWT__ua = "ua"
JWT__ip = "ip"

KEY__db_name = "db_name"


class JAAQLModel(BaseJAAQLModel):

    def __init__(self, config, vault_key: str, migration_db_interface=None, migration_project_name: str = None,
                 migration_folder: str = None, reboot_on_install: bool = False):
        super().__init__(config, vault_key, migration_db_interface, migration_project_name, migration_folder,
                         reboot_on_install)

    def verify_user(self, username: str, ip_address: str, user_agent: str):
        username = username.lower()

        inputs = {KEY__username: username}
        users = self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_user_latest_password,
                                                 inputs, as_objects=True,
                                                 decrypt_columns=[ATTR__password_hash, KEY__totp_iv],
                                                 encryption_key=self.get_db_crypt_key())

        if len(users) == 0:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        user = users[0]

        hashed_ip = crypt_utils.hash_password(ip_address, user[KEY__id].encode(crypt_utils.ENCODING__ascii))
        inputs = {
            KEY__id: user[KEY__id],
            ATTR__address_hash: hashed_ip,
            ATTR__ip_address: ip_address
        }

        resp = self.execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__user_ip_ins, inputs,
                                                          as_objects=True,
                                                          encrypt_parameters=[ATTR__address_hash, ATTR__ip_address],
                                                          encryption_key=self.get_db_crypt_key(),
                                                          encryption_salts={ATTR__address_hash: user[KEY__id]})
        existed_ip = resp[ATTR__existed]
        ip_id = resp[KEY__id]

        existed_ua = None
        ua_id = None

        if user_agent is not None:
            hashed_ua = crypt_utils.hash_password(user_agent, user[KEY__id].encode(crypt_utils.ENCODING__ascii))
            inputs = {
                KEY__id: user[KEY__id],
                ATTR__ua_hash: hashed_ua,
                ATTR__ua: user_agent
            }

            resp = self.execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__user_ua_ins, inputs,
                                                              as_objects=True,
                                                              encrypt_parameters=[ATTR__ua_hash, ATTR__ua],
                                                              encryption_key=self.get_db_crypt_key(),
                                                              encryption_salts={ATTR__ua_hash: user[KEY__id]})
            existed_ua = resp[ATTR__existed]
            ua_id = resp[KEY__id]

        return user, existed_ip, existed_ua, ip_id, ua_id, user[KEY__last_totp]

    def refresh(self, oauth_token: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), oauth_token, allow_expired=True)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        created = crypt_utils.decrypt(jwt_obj_key, decoded[JWT__created])

        if datetime.fromisoformat(created) + timedelta(
                milliseconds=self.refresh_expiry_ms) < datetime.now():
            raise HttpStatusException(ERR__refresh_expired, HTTPStatus.UNAUTHORIZED)

        jwt_data = {
            JWT__username: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__username])),
            JWT__password: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__password])),
            JWT__ua: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__ua])),
            JWT__ip: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__ip])),
            JWT__created: crypt_utils.encrypt(jwt_obj_key, created)
        }

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data,
                                      expiry_ms=self.token_expiry_ms)

    def verify_mfa(self, mfa_key: str, totp_iv: str, last_totp: str, user_id: str):
        totp = pyotp.TOTP(totp_iv)
        verified = totp.verify(mfa_key)
        if not verified and self.use_mfa:
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        if last_totp == mfa_key and self.use_mfa:
            raise HttpStatusException(ERR__mfa_reused, HTTPStatus.UNAUTHORIZED)

        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__user_totp_upd, {
            KEY__user_id: user_id,
            KEY__last_totp: mfa_key
        })

    def redeploy(self):
        f = open(join(dirname(get_jaaql_root()), "redeploy"), "w")
        f.write("Will be detected and redeployment will now happen")
        f.close()

        print("Redeploying JAAQL")

        threading.Thread(target=self.exit_jaaql, daemon=True).start()

    def authenticate(self, username: str, password: str, mfa_key: str, ip_address: str, user_agent: str,
                     response: JAAQLResponse):
        user, _, _, ip_id, ua_id, last_totp = self.verify_user(username, ip_address, user_agent)
        if not crypt_utils.verify_password_hash(user[ATTR__password_hash], password,
                                                salt=user[KEY__id].encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        totp_iv = user[KEY__totp_iv]
        self.verify_mfa(mfa_key, totp_iv, last_totp, user[KEY__id])

        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        jwt_data = {
            JWT__username: crypt_utils.encrypt(jwt_obj_key, username),
            JWT__password: crypt_utils.encrypt(jwt_obj_key, crypt_utils.hash_password(user[ATTR__password_hash])),
            JWT__ua: crypt_utils.encrypt(jwt_obj_key, ua_id),
            JWT__ip: crypt_utils.encrypt(jwt_obj_key, ip_id),
            JWT__created: crypt_utils.encrypt(jwt_obj_key, datetime.now().isoformat())
        }

        response.user_id = user[KEY__id]
        response.ip_id = ip_id
        response.ua_id = ua_id

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data,
                                      expiry_ms=self.token_expiry_ms)

    def install(self, db_connection_string: str, password: str, install_key: str, ip_address: str, user_agent: str,
                response: JAAQLResponse):
        if self.jaaql_lookup_connection is None:
            if install_key != self.install_key:
                raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)
            address, port, db, username, db_password = DBInterface.fracture_uri(db_connection_string)

            db_interface = DBInterface.create_interface(self.config, address, port, db, username, db_password)
            conn = db_interface.get_conn()
            resp = db_interface.execute_script_file(conn, join(get_jaaql_root(), "scripts", "install_1.sql"))
            db_interface.put_conn(conn)
            db_interface.close()

            jaaql_password = resp['rows'][0][0]
            self.jaaql_lookup_connection = DBInterface.create_interface(self.config, address, port, db, JAAQL__username,
                                                                        jaaql_password)

            conn = self.jaaql_lookup_connection.get_conn()
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), "scripts", "install_2.sql"))
            self.jaaql_lookup_connection.put_conn(conn)

            database_id = self.add_database({
                KEY__database_name: db,
                KEY__description: DESCRIPTION__jaaql_db,
                KEY__port: port,
                KEY__address: address,
                KEY__jaaql_name: DATABASE__jaaql_internal_name,
                KEY__is_console_level: False
            }, self.jaaql_lookup_connection)
            self.vault.insert_obj(VAULT_KEY__jaaql_db_id, database_id)
            self.vault.insert_obj(VAULT_KEY__jaaql_lookup_connection, db_connection_string)

            qr, user_id, ip_id, ua_id = self.add_and_setup_user(JAAQL__username, password, None,
                                                                self.jaaql_lookup_connection, database_id,
                                                                jaaql_password, ip_address, user_agent)

            response.user_id = user_id
            response.ip_id = ip_id
            response.ua_id = ua_id

            if self.reboot_on_install:
                print("Rebooting to allow JAAQL config to be shared among workers")
                threading.Thread(target=self.exit_jaaql).start()
            return qr
        else:
            raise HttpStatusException(ERR__already_installed)

    def log(self, user_id: str, occurred: datetime, duration_ms: int, exception: str, contr_input: str, ip: str,
            ua: Optional[str], status: int, endpoint: str, databases: list = None):
        if databases is None:
            databases = []

        parameters = {
            KEY__user_id: user_id,
            KEY__occurred: occurred.isoformat(),
            KEY__duration_ms: duration_ms,
            KEY__exception: exception,
            KEY__input: contr_input,
            KEY__ip: ip,
            KEY__ua: ua,
            KEY__status: int(status),
            KEY__endpoint: endpoint
        }

        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__log_ins, parameters,
                                         encrypt_parameters=[KEY__exception, KEY__input],
                                         encryption_key=self.get_db_crypt_key())

        # TODO do databases. Link the used database auth with the log

    def verify_jwt(self, jwt_token: str, ip_address: str, user_agent: str,
                   was_refresh: bool) -> [DBInterface, str, str]:
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_token, was_refresh)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        username = crypt_utils.decrypt(jwt_key, decoded[JWT__username])
        double_hashed_password = crypt_utils.decrypt(self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key),
                                                     decoded[JWT__password])

        user, _, _, ip_id, ua_id, last_totp = self.verify_user(username, ip_address, user_agent)
        if not crypt_utils.verify_password_hash(double_hashed_password, user[ATTR__password_hash]):
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        jwt_ip_id = crypt_utils.decrypt(jwt_key, decoded[JWT__ip])
        if ip_id != jwt_ip_id:
            raise HttpStatusException(ERR__new_ip, HTTPStatus.UNAUTHORIZED)

        if jwt_ip_id is None and ua_id is not None:
            raise HttpStatusException(ERR__new_ua, HTTPStatus.UNAUTHORIZED)
        jwt_ua_id = crypt_utils.decrypt(jwt_key, decoded[JWT__ua])
        if ua_id != jwt_ua_id:
            raise HttpStatusException(ERR__new_ua, HTTPStatus.UNAUTHORIZED)

        params = {
            KEY__role: username,
            KEY__database: self.vault.get_obj(VAULT_KEY__jaaql_db_id)
        }
        auth = self.execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                          QUERY__database_authorization_sel_one, params,
                                                          as_objects=True,
                                                          decrypt_columns=[KEY__username, KEY__password, KEY__port,
                                                                           KEY__database_name, KEY__address],
                                                          encryption_key=self.get_db_crypt_key())

        iv = user[KEY__totp_iv]
        return DBInterface.create_interface(self.config, auth[KEY__address], auth[KEY__port], auth[KEY__database_name],
                                            auth[KEY__username], auth[KEY__password]
                                            ), user[KEY__id], ip_id, ua_id, iv, user[ATTR__password_hash], last_totp

    def add_application(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_ins, inputs)

    def delete_application(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application, inputs)}

    def delete_application_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_del, parameters,
                                         as_objects=True)

    def delete_database(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__database, inputs)}

    def delete_database_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__database)
        self.execute_supplied_statement(jaaql_connection, QUERY__database_del, parameters,
                                         as_objects=True)

    def get_applications(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_count, parameters,
                                         where_query, where_parameters)

    def add_database(self, inputs: dict, jaaql_connection: DBInterface):
        return self.execute_supplied_statement(jaaql_connection,
                                                QUERY__database_ins, inputs, as_objects=True,
                                                encryption_key=self.get_db_crypt_key(),
                                                encrypt_parameters=[
                                                    KEY__database_name,
                                                    KEY__address,
                                                    KEY__port
                                                ])[0][KEY__id]

    def update_application(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_upd, inputs)

    def get_databases(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)

        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__database_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__database_count, parameters, where_query,
                                         where_parameters, encryption_key=self.get_db_crypt_key(),
                                         decrypt_columns=[KEY__port, KEY__address, KEY__database_name])

    def add_application_parameter(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_parameter_ins, inputs)

    def get_application_parameters(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_parameter_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_parameter_count, parameters,
                                         where_query, where_parameters)

    def delete_application_parameter(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_parameter, inputs)}

    def delete_application_parameter_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_parameter)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_parameter_del, parameters,
                                         as_objects=True)

    def add_application_configuration(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_configuration_ins, inputs)

    def get_application_configurations(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_configuration_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_configuration_count,
                                         parameters, where_query, where_parameters)

    def delete_application_configuration(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_configuration, inputs)}

    def delete_application_configuration_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_configuration)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_configuration_del, parameters,
                                         as_objects=True)

    def add_application_argument(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_argument_ins, inputs)

    def get_application_arguments(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_argument_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_argument_count, parameters,
                                         where_query, where_parameters)

    def delete_application_argument(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_argument, inputs)}

    def delete_application_argument_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_argument)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_argument_del, parameters,
                                         as_objects=True)

    def add_application_authorization(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_authorization_ins, inputs)

    def get_application_authorizations(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_authorization_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_authorization_count,
                                         parameters, where_query, where_parameters)

    def delete_application_authorization(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_authorization, inputs)}

    def delete_application_authorization_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_authorization)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_authorization_del, parameters,
                                        as_objects=True)

    def add_database_authorization(self, inputs: dict, connection: DBInterface):
        self.execute_supplied_statement(connection, QUERY__database_authorization_ins, inputs,
                                        encrypt_parameters=[KEY__username, KEY__password],
                                        encryption_key=self.get_db_crypt_key())

    def get_database_authorizations(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)
        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__database_authorization_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__database_authorization_count, parameters,
                                         where_query, where_parameters, decrypt_columns=[KEY__username, KEY__password],
                                         encryption_key=self.get_db_crypt_key())

    def delete_database_authorization(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__database_authorization, inputs)}

    def delete_database_authorization_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__database_authorization)
        self.execute_supplied_statement(jaaql_connection, QUERY__database_authorization_del, parameters,
                                         as_objects=True)

    def user_invite(self, inputs: dict):
        # TODO Make sure that we can't invite a user that already exists
        ms_two_weeks = 1000 * 60 * 60 * 24 * 14
        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), inputs, ms_two_weeks)

    def signup(self, http_inputs: dict, response: JAAQLResponse, user_agent: str, ip_address: str):
        token = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), http_inputs[KEY__invite_key])
        if not token:
            raise HttpStatusException(ERR__invalid_token)

        email = token[KEY__email]
        password = http_inputs[KEY__password]

        qr, user_id, ip_id, ua_id = self.add_and_setup_user(email, password, None, self.jaaql_lookup_connection,
                                                            self.vault.get_obj(VAULT_KEY__jaaql_db_id),
                                                            str(uuid.uuid4()), ip_address, user_agent)

        response.user_id = user_id
        response.ip_id = ip_id
        response.ua_id = ua_id

        return qr

    def add_and_setup_user(self, username: str, password: str, mobile: Optional[str], jaaql_connection: DBInterface,
                           database_id: str, jaaql_password: str, ip_address: str, user_agent: str):
        crypt_utils.validate_password(password)

        _, totp_iv = crypt_utils.key_stretcher(str(uuid.uuid4()))
        totp_iv = b32e(totp_iv).decode(ENCODING__utf)

        parameters = {
            ATTR__email: username,
            ATTR__mobile: mobile,
            KEY__totp_iv: totp_iv
        }
        user_id = self.execute_supplied_statement(jaaql_connection, QUERY__user_ins, parameters, as_objects=True,
                                                   encrypt_parameters=[KEY__totp_iv],
                                                   encryption_key=self.get_db_crypt_key())
        user_id = user_id[0][KEY__id]

        password = crypt_utils.hash_password(password, user_id.encode(crypt_utils.ENCODING__ascii))
        parameters = {
            ATTR__the_user: user_id,
            ATTR__password_hash: password
        }
        self.execute_supplied_statement(jaaql_connection, QUERY__user_password_ins, parameters,
                                         encrypt_parameters=[ATTR__password_hash],
                                         encryption_key=self.get_db_crypt_key(),
                                         encryption_salts={ATTR__password_hash: user_id})

        mfa_issuer = self.config[CONFIG_KEY_security][CONFIG_KEY_SECURITY__mfa_issuer]
        mfa_label = self.config[CONFIG_KEY_security][CONFIG_KEY_SECURITY__mfa_label]
        totp_uri = URI__otp_auth % (mfa_label, totp_iv)
        if mfa_issuer != "None" and mfa_issuer is not None:
            totp_uri += URI__otp_issuer_clause % mfa_issuer

        self.add_database_authorization({
            KEY__database: database_id,
            KEY__role: username,
            KEY__username: username,
            KEY__password: jaaql_password,
            KEY__precedence: None
        }, self.jaaql_lookup_connection)

        inputs = {
            KEY__username: username,
            KEY__password: jaaql_password
        }
        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__user_create_role, inputs)

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        buffered = BytesIO()
        qr.make_image().save(buffered, format=FORMAT__png)
        img_str = b64e(buffered.getvalue())
        totp_b64_qr = HTML__base64_png + img_str.decode("ASCII")

        user, _, _, ip_id, ua_id, _ = self.verify_user(username, ip_address, user_agent)

        return {
            KEY__otp_uri: totp_uri,
            KEY__otp_qr: totp_b64_qr
        }, user[KEY__id], ip_id, ua_id

    def my_logs(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__user_log_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__user_log_count, parameters, where_query,
                                         where_parameters,
                                         decrypt_columns=[KEY__address, KEY__user_agent, KEY__exception],
                                         encryption_key=self.get_db_crypt_key())

    def my_ips(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__user_ip_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__user_ip_count, parameters, where_query,
                                         where_parameters, decrypt_columns=[KEY__address],
                                         encryption_key=self.get_db_crypt_key())

    def my_configs(self, jaaql_connection: DBInterface):
        return self.execute_supplied_statement(jaaql_connection, QUERY__my_configs, as_objects=True)

    def change_password(self, http_inputs: dict, totp_iv: str, oauth_token: str, password_hash: str, user_id: str,
                        last_totp: str, jaaql_connection: DBInterface):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), oauth_token)
        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)

        if not crypt_utils.verify_password_hash(password_hash, http_inputs[KEY__password],
                                                salt=user_id.encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        self.verify_mfa(http_inputs[KEY__mfa_key], totp_iv, last_totp, user_id)

        new_password = http_inputs[KEY__new_password]
        new_password_confirm = http_inputs[KEY__new_password_confirm]

        if new_password != new_password_confirm:
            raise HttpStatusException(ERR__passwords_do_not_match)

        new_password = crypt_utils.hash_password(new_password, user_id.encode(crypt_utils.ENCODING__ascii))
        parameters = {
            ATTR__the_user: user_id,
            ATTR__password_hash: new_password
        }
        self.execute_supplied_statement(jaaql_connection, QUERY__user_password_ins, parameters,
                                         encrypt_parameters=[KEY__totp_iv],
                                         encryption_key=self.get_db_crypt_key(),
                                         encryption_salts={ATTR__password_hash: user_id})

        decoded[JWT__password] = crypt_utils.encrypt(jwt_obj_key, crypt_utils.hash_password(new_password))

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), decoded,
                                      expiry_ms=self.token_expiry_ms)

    def close_account(self, http_inputs: dict, totp_iv: str, password_hash: str, user_id: str,
                      last_totp: str):
        if not crypt_utils.verify_password_hash(password_hash, http_inputs[KEY__password],
                                                salt=user_id.encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        self.verify_mfa(http_inputs[KEY__mfa_key], totp_iv, last_totp, user_id)

        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__account, {})}

    def close_account_confirm(self, inputs: dict, user_id: str):
        self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__account)
        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__user_del, {ATTR__the_user: user_id})

    @staticmethod
    def build_db_addr(row: dict):
        return row[KEY__username] + ":" + row[KEY__password] + "@" + row[KEY__address] + ":" + row[
            KEY__port] + "/" + row[KEY__database_name]

    def config_databases(self, http_inputs: dict, jaaql_connection: DBInterface, user_id: str):
        http_inputs[KEY__username] = jaaql_connection.username

        # It is not a mistake to use the jaaql_lookup_connection rather than the user's connection here
        data = self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__authorized_configuration,
                                                http_inputs, as_objects=True, encryption_key=self.get_db_crypt_key(),
                                                decrypt_columns=[
                                                    KEY__username,
                                                    KEY__password,
                                                    KEY__address,
                                                    KEY__database_name,
                                                    KEY__port
                                                ])

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_crypt_key)
        obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)

        check_dbs = [row[KEY__database] for row in data]
        if len(set(check_dbs)) != len(check_dbs):
            duplicates = Counter(check_dbs)
            duplicates = [itm for itm in duplicates.keys() if duplicates[itm] > 1]
            raise Exception(ERR__duplicated_database % (user_id, SEPARATOR__comma_space.join(duplicates)))

        # Combines the existing row, overriding KEY__database with a JWT containing the encrypted database UUID
        ret = [{KEY__parameter_description: row[KEY__parameter_description], KEY__parameter_name: row[
            KEY__parameter_name], KEY__database: crypt_utils.jwt_encode(
            jwt_key, {KEY__db_url: crypt_utils.encrypt(obj_key, JAAQLModel.build_db_addr(
                row) + "##" + str(row[KEY__is_console_level]))})} for row in data]

        return ret

    def submit(self, http_inputs: dict, jaaql_connection: DBInterface):
        database = http_inputs.get(KEY__database, None)

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_crypt_key)
        obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        was_database_none = database is None

        if database is None:
            database = jaaql_connection
        else:
            db_url = crypt_utils.jwt_decode(jwt_key, database)[KEY__db_url]
            db_url = crypt_utils.decrypt(obj_key, db_url)
            db_parts = db_url.split("##")
            db_url = db_parts[0]
            is_console_level = db_parts[1] == "True"
            address, port, database, username, password = DBInterface.fracture_uri(db_url)

            if KEY__db_name in http_inputs and is_console_level:
                database = http_inputs[KEY__db_name]
            elif KEY__db_name in http_inputs:
                raise HttpStatusException("Cannot override DB", HTTPStatus.UNAUTHORIZED)

            database = DBInterface.create_interface(self.config, address, port, database, username, password)

        if KEY__database in http_inputs:
            http_inputs.pop(KEY__database)

        caught_ex = None
        to_ret = None
        try:
            to_ret = InterpretJAAQL(database).transform(http_inputs)
        except Exception as ex:
            caught_ex = ex

        if not was_database_none:
            database.pg_pool.closeall()

        if caught_ex is not None:
            raise caught_ex

        return to_ret
