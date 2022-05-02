from jaaql.db.db_interface import DBInterface, RET__rows
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jaaql_lookup_connection, CONFIG_KEY__security, \
    CONFIG_KEY_SECURITY__mfa_label, CONFIG_KEY_SECURITY__mfa_issuer, VAULT_KEY__jwt_obj_crypt_key, \
    VAULT_KEY__jwt_crypt_key
from jaaql.exceptions.http_status_exception import HttpStatusException, HTTPStatus, ERR__connection_expired, \
    HTTP_STATUS_CONNECTION_EXPIRED, ERR__already_installed, ERR__passwords_do_not_match, ERR__cannot_override_db, \
    ERR__already_signed_up

from typing import Optional
from distutils.dir_util import copy_tree
from jaaql.mvc.response import JAAQLResponse
from collections import Counter
from os.path import dirname
from jaaql.utilities import crypt_utils
import uuid
import os
import pyotp
import qrcode
import qrcode.image.svg
from base64 import b64encode as b64e, b32encode as b32e
from io import BytesIO
from datetime import datetime, timedelta
from jaaql.interpreter.interpret_jaaql import InterpretJAAQL, KEY_query
from jaaql.constants import *
from os.path import join
from jaaql.utilities.utils import get_jaaql_root
import threading
import shutil

TOKEN__pre_auth_reduction_factor = 15

ERR__incorrect_install_key = "Incorrect install key!"
ERR__incorrect_credentials = "Incorrect credentials!"
ERR__password_incorrect = "Your password is incorrect!"
ERR__invalid_token = "Invalid token!"
ERR__new_ip = "Token being used from an ip address not associated with these credentials. Please refresh it"
ERR__new_ua = "Token being used from a different browser. Please refresh it"
ERR__refresh_expired = "Token too old to be used for refresh. Please authenticate again"
ERR__duplicated_database = "User %s has a duplicate database precedence with databases '%s'"
ERR__not_sole_owner = "You are not the sole owner of this connection"
ERR__mfa_must_be_enabled = "MFA must be turned on!"

USERNAME__jaaql = "jaaql"
USERNAME__superjaaql = "superjaaql"
USERNAME__postgres = "postgres"

NODE__host_node = "host"
DB__jaaql = "jaaql"

APPLICATION__console = "console"
APPLICATION__playground = "playground"
APPLICATION__manager = "manager"
CONFIGURATION__host = "host"

QUERY__my_roles = "SELECT rolname FROM pg_roles WHERE pg_has_role(oid, 'member');"
QUERY__grant_role = "GRANT %s TO %s"
QUERY__default_roles_sel = "SELECT * FROM jaaql__default_role"
QUERY__default_roles_ins = "INSERT INTO jaaql__default_role (the_role) VALUES (:role)"
QUERY__default_roles_del = "DELETE FROM jaaql__default_role WHERE the_role = :role"
QUERY__fetch_my_applications = "SELECT * FROM jaaql__my_applications"
QUERY__application_set_url = "UPDATE jaaql__application SET url = :url WHERE name = :name"
QUERY__application_ins = "INSERT INTO jaaql__application (name, description, url) VALUES (:name, :description, :url)"
QUERY__application_setup_host = "INSERT INTO jaaql__assigned_database (application, configuration, database, node, dataset) VALUES (:application, 'host', '%s', '%s', 'node')" % (
    DB__jaaql, NODE__host_node)
QUERY__application_del = "DELETE FROM jaaql__application WHERE name = :name"
QUERY__application_sel = "SELECT * FROM jaaql__application"
QUERY__application_count = "SELECT COUNT(*) FROM jaaql__application"
QUERY__application_upd = "UPDATE jaaql__application SET name = coalesce(:new_name, name), description = coalesce(:new_description, description), url = coalesce(:new_url, url) WHERE name = :name"
QUERY__database_ins = "INSERT INTO jaaql__database (node, name) VALUES (:node, :name)"
QUERY__node_create = "SELECT jaaql__create_node(:name, :address, :port, :description);"
QUERY__database_sel = "SELECT * FROM jaaql__database"
QUERY__node_sel = "SELECT * FROM jaaql__node"
QUERY__database_del = "DELETE FROM jaaql__database WHERE name = :name AND node = :node"
QUERY__node_del = "SELECT jaaql__delete_node(:name);"
QUERY__database_count = "SELECT COUNT(*) FROM jaaql__database"
QUERY__node_count = "SELECT COUNT(*) FROM jaaql__node"
QUERY__application_dataset_ins = "INSERT INTO jaaql__application_dataset (application, name, description) VALUES (:application, :name, :description)"
QUERY__application_dataset_del = "DELETE FROM jaaql__application_dataset WHERE name = :name AND application = :application"
QUERY__application_dataset_sel = "SELECT * FROM jaaql__application_dataset"
QUERY__application_dataset_count = "SELECT COUNT(*) FROM jaaql__application_dataset"
QUERY__application_configuration_ins = "INSERT INTO jaaql__application_configuration (application, name, description) VALUES (:application, :name, :description)"
QUERY__application_configuration_del = "DELETE FROM jaaql__application_configuration WHERE name = :name AND application = :application"
QUERY__application_configuration_sel = "SELECT * FROM jaaql__application_configuration"
QUERY__application_configuration_count = "SELECT COUNT(*) FROM jaaql__application_configuration"
QUERY__assigned_database_ins = "INSERT INTO jaaql__assigned_database (application, configuration, database, node, dataset) VALUES (:application, :configuration, :database, :node, :dataset)"
QUERY__assigned_database_del = "DELETE FROM jaaql__assigned_database WHERE application = :application AND configuration = :configuration AND dataset = :dataset"
QUERY__assigned_database_sel = "SELECT * FROM jaaql__assigned_database"
QUERY__assigned_database_count = "SELECT COUNT(*) FROM jaaql__assigned_database"
QUERY__configuration_authorization_ins = "INSERT INTO jaaql__authorization_configuration (application, configuration, role) VALUES (:application, :configuration, :role)"
QUERY__configuration_authorization_del = "DELETE FROM jaaql__authorization_configuration WHERE application = :application AND role = :role AND configuration = :configuration"
QUERY__configuration_authorization_sel = "SELECT * FROM jaaql__authorization_configuration"
QUERY__configuration_authorization_count = "SELECT COUNT(*) FROM jaaql__authorization_configuration"
QUERY__node_credentials_ins = "INSERT INTO jaaql__credentials_node (node, role, db_encrypted_username, db_encrypted_password, precedence) VALUES (:node, :role, :username, :password, coalesce(:precedence, 0))"
QUERY__node_credentials_del = "UPDATE jaaql__credentials_node SET deleted = current_timestamp WHERE role = :role AND node = :node AND deleted is null"
QUERY__node_credentials_sel = "SELECT id, node, role, deleted FROM jaaql__credentials_node"
QUERY__role_connection_sel = "SELECT ad.id as id, ad.db_encrypted_username as username, ad.db_encrypted_password as password, nod.address, nod.port FROM jaaql__credentials_node ad INNER JOIN jaaql__node nod ON nod.name = ad.node WHERE role = (SELECT coalesce(alias, email) FROM jaaql__user WHERE email = :role) AND node = :node AND ad.deleted is null AND nod.deleted is null;"
QUERY__node_credentials_count = "SELECT COUNT(*) FROM jaaql__credentials_node"
QUERY__user_ins = "INSERT INTO jaaql__user (email, mobile, alias) VALUES (lower(:email), :mobile, :alias) RETURNING id"
QUERY__revoke_user = "UPDATE jaaql__user SET deleted = current_timestamp WHERE email = lower(:username) AND email not in ('jaaql', 'superjaaql') AND deleted is NULL"
QUERY__disable_mfa = "UPDATE jaaql__user SET enc_totp_iv = null WHERE id = :user_id"
QUERY__set_mfa = "UPDATE jaaql__user SET enc_totp_iv = :totp_iv WHERE id = :user_id"
QUERY__user_id_from_username = "SELECT id FROM jaaql__user WHERE email = lower(:username) AND deleted is null"
QUERY__user_totp_upd = "UPDATE jaaql__user SET last_totp = :last_totp WHERE id = :user_id"
QUERY__user_ip_sel = "SELECT encrypted_address as address, first_use, most_recent_use FROM jaaql__my_ips"
QUERY__user_ip_count = "SELECT COUNT(*) FROM jaaql__my_ips"
QUERY__user_ip_ins = "INSERT INTO jaaql__user_ip (the_user, address_hash, encrypted_address) VALUES (:id, :address_hash, :ip_address) ON CONFLICT ON CONSTRAINT jaaql__user_ip_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_ua_ins = "INSERT INTO jaaql__user_ua (the_user, ua_hash, encrypted_ua) VALUES (:id, :ua_hash, :ua) ON CONFLICT ON CONSTRAINT jaaql__user_ua_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_password_ins = "INSERT INTO jaaql__user_password (the_user, password_hash) VALUES (:the_user, :password_hash)"
QUERY__fetch_user_latest_password = "SELECT id, email, password_hash, enc_totp_iv as totp_iv, last_totp FROM jaaql__user_latest_password WHERE email = lower(:username)"
QUERY__user_create_role = "SELECT jaaql__create_role(lower(:username), :password)"
QUERY__log_ins = "INSERT INTO jaaql__log (the_user, occurred, duration_ms, encrypted_exception, encrypted_input, ip, ua, status, endpoint) VALUES (:user_id, :occurred, :duration_ms, :exception, :input, :ip, :ua, :status, :endpoint)"
QUERY__user_log_sel = "SELECT occurred, encrypted_address as address, encrypted_ua as user_agent, status, endpoint, duration_ms, encrypted_exception as exception FROM jaaql__my_logs"
QUERY__user_log_count = "SELECT COUNT(*) FROM jaaql__my_logs"
QUERY__my_configs = "SELECT * FROM jaaql__my_configurations WHERE application = :application or :application is null"
QUERY__my_configs_where = "SELECT * FROM jaaql__my_configurations WHERE application = :application AND configuration = :configuration"
QUERY__create_database = "create database \"%s\""
QUERY__drop_database = "drop database \"%s\""
QUERY__node_single_credential_sel = """
SELECT
    *
FROM
    jaaql__their_single_authorized_wildcard_node wn
WHERE (wn.node, wn.precedence) in 
    (SELECT
        wnsub.node,
        max(wnsub.precedence) as max_precedence
    FROM jaaql__their_single_authorized_wildcard_node wnsub
    WHERE (wnsub.role = '' or pg_has_role(jaaql__fetch_alias_from_id(:user_id), wnsub.role, 'MEMBER'))
    GROUP BY wnsub.node) AND
    (wn.role = '' or pg_has_role(jaaql__fetch_alias_from_id(:user_id), wn.role, 'MEMBER')) AND wn.node = :node;
"""
QUERY__authorized_configuration = """
SELECT
    jtac.*
FROM jaaql__their_authorized_configurations jtac
INNER JOIN (
    SELECT DISTINCT application, configuration FROM jaaql__their_authorized_app_only_configurations WHERE pg_has_role(jaaql__fetch_alias_from_id(:user_id), conf_role, 'MEMBER') AND application = :application AND configuration = :configuration
) sub ON sub.application = jtac.application AND sub.configuration = jtac.configuration
WHERE pg_has_role(jaaql__fetch_alias_from_id(:user_id), node_role, 'MEMBER') AND jtac.application = :application AND jtac.configuration = :configuration AND jtac.precedence IN (
    SELECT
        MAX(precedence)
    FROM jaaql__their_authorized_configurations
    WHERE pg_has_role(jaaql__fetch_alias_from_id(:user_id), node_role, 'MEMBER') AND application = :application AND configuration = :configuration
);
"""
FUNC__jaaql_create_node = "jaaql__create_node"

ATTR__email = "email"
ATTR__mobile = "mobile"
ATTR__the_user = "the_user"
ATTR__existed = "existed"
ATTR__password_hash = "password_hash"
ATTR__address_hash = "address_hash"
ATTR__ip_address = "ip_address"
ATTR__ua_hash = "ua_hash"
ATTR__ua = "ua"
ATTR__alias = "alias"
KEY__totp_iv = "totp_iv"
KEY__user_id = "user_id"
KEY__occurred = "occurred"
KEY__duration_ms = "duration_ms"
KEY__input = "input"
KEY__ip = "ip"
KEY__ua = "ua"
KEY__status = "status"
KEY__endpoint = "endpoint"
KEY__dat_name = "datname"
KEY__authorization = "authorization"

DELETION_PURPOSE__application = "application"
DELETION_PURPOSE__application_dataset = "application_dataset"
DELETION_PURPOSE__application_configuration = "application_configuration"
DELETION_PURPOSE__database_assignment = "database_assignment"
DELETION_PURPOSE__configuration_authorization = "configuration_authorization"
DELETION_PURPOSE__node_authorization = "node_authorization"
DELETION_PURPOSE__database = "database"
DELETION_PURPOSE__node = "node"
DELETION_PURPOSE__default_role = "default_role"
DELETION_PURPOSE__user = "user"
DELETION_PURPOSE__user_self = "user_self"

DESCRIPTION__jaaql_db = "The core jaaql database, used to store user information, logs and application/auth configs"
DATABASE__jaaql_internal_name = "jaaql db"

URI__otp_auth = "otpauth://totp/%s?secret=%s"
URI__otp_issuer_clause = "&issuer=%s"
HTML__base64_png = "data:image/png;base64,"
FORMAT__png = "png"

JWT__username = "username"
JWT__fully_authenticated = "fully_authenticated"
JWT__password = "password"
JWT__created = "created"
JWT__ua = "ua"
JWT__ip = "ip"

PG__default_connection_string = "postgresql://postgres:%s@localhost:5432/jaaql"
PG_ENV__password = "POSTGRES_PASSWORD"

DIR__scripts = "scripts"
DIR__apps = "apps"
SEPARATOR__dir = "/"
DIR__www = "www"
DIR__manager = "manager"
DIR__playground = "playground"
DIR__console = "console"
DB__empty = ""

DB__wildcard = "*"

MFA__null_issuer = "None"

PRECEDENCE__super_user = 999


class JAAQLModel(BaseJAAQLModel):

    def __init__(self, config, vault_key: str, migration_db_interface=None, migration_project_name: str = None,
                 migration_folder: str = None, is_container: bool = False, url: str = None):
        super().__init__(config, vault_key, migration_db_interface, migration_project_name, migration_folder,
                         is_container, url)

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
            JWT__fully_authenticated: True,
            JWT__ua: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__ua])),
            JWT__ip: crypt_utils.encrypt(jwt_obj_key, crypt_utils.decrypt(jwt_obj_key, decoded[JWT__ip])),
            JWT__created: crypt_utils.encrypt(jwt_obj_key, created)
        }

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data,
                                      expiry_ms=self.token_expiry_ms)

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

    def authenticate_with_mfa_key(self, pre_auth: str, mfa_key: str, ip_address: str, user_agent: str,
                                  response: JAAQLResponse):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), pre_auth)
        if not decoded:
            raise HttpStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)

        jwt_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        username = crypt_utils.decrypt(jwt_key, decoded[JWT__username])
        user, _, _, ip_id, ua_id, last_totp = self.verify_user(username, ip_address, user_agent)

        self.verify_mfa(mfa_key, user[KEY__totp_iv], last_totp, user[KEY__id])

        response.user_id = user[KEY__id]
        response.ip_id = ip_id
        response.ua_id = ua_id

        decoded[JWT__fully_authenticated] = True
        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), decoded,
                                      expiry_ms=self.token_expiry_ms)

    def authenticate(self, username: str, password: str, ip_address: str, user_agent: str, response: JAAQLResponse):
        user, _, _, ip_id, ua_id, last_totp = self.verify_user(username, ip_address, user_agent)
        if not crypt_utils.verify_password_hash(user[ATTR__password_hash], password,
                                                salt=user[KEY__id].encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__incorrect_credentials, HTTPStatus.UNAUTHORIZED)

        needs_further_auth = user.get(KEY__totp_iv) is not None

        jwt_obj_key = self.vault.get_obj(VAULT_KEY__jwt_obj_crypt_key)
        jwt_data = {
            JWT__username: crypt_utils.encrypt(jwt_obj_key, username),
            JWT__password: crypt_utils.encrypt(jwt_obj_key, crypt_utils.hash_password(user[ATTR__password_hash])),
            JWT__fully_authenticated: not needs_further_auth,
            JWT__ua: crypt_utils.encrypt(jwt_obj_key, ua_id),
            JWT__ip: crypt_utils.encrypt(jwt_obj_key, ip_id),
            JWT__created: crypt_utils.encrypt(jwt_obj_key, datetime.now().isoformat())
        }

        response.user_id = user[KEY__id]
        response.ip_id = ip_id
        response.ua_id = ua_id

        expiry_time = self.token_expiry_ms
        if needs_further_auth:
            expiry_time /= TOKEN__pre_auth_reduction_factor
            response.response_code = HTTPStatus.ACCEPTED
        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data,
                                      expiry_ms=expiry_time)

    def copy_apps(self):
        if self.is_container:
            apps_dir = join(DIR__www, DIR__apps)
            if not os.path.exists(DIR__apps):
                os.makedirs(DIR__apps)
            for app_dir in os.scandir(join(get_jaaql_root(), DIR__apps)):
                if app_dir.is_dir():
                    if os.path.exists(join(apps_dir, app_dir.name)):
                        shutil.rmtree(join(apps_dir, app_dir.name))
            copy_tree(join(get_jaaql_root(), DIR__apps), apps_dir)

    def install(self, db_connection_string: str, superjaaql_password: str, password: str, install_key: str,
                use_mfa: bool, ip_address: str, user_agent: str, response: JAAQLResponse):
        if not use_mfa and self.force_mfa:
            raise HttpStatusException(ERR__mfa_must_be_enabled)
        if self.jaaql_lookup_connection is None:
            if install_key != self.install_key:
                raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)

            if db_connection_string is None:
                db_connection_string = PG__default_connection_string % os.environ[PG_ENV__password]

            address, port, db, username, db_password = DBInterface.fracture_uri(db_connection_string)

            db_interface = DBInterface.create_interface(self.config, address, port, db, username, db_password)
            conn = db_interface.get_conn()
            resp = db_interface.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "install_1.sql"))
            db_interface.put_conn(conn)
            db_interface.close()

            jaaql_password = resp['rows'][0][0]
            self.jaaql_lookup_connection = DBInterface.create_interface(self.config, address, port, db, USERNAME__jaaql,
                                                                        jaaql_password)

            conn = self.jaaql_lookup_connection.get_conn()
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts,
                                                                        "install_2.sql"))
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
            mfa = self.sign_up_user(self.jaaql_lookup_connection, USERNAME__jaaql, password, user_id, ip_address,
                                    user_agent, use_mfa=use_mfa, response=response)

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
                self.create_user(self.jaaql_lookup_connection, USERNAME__superjaaql, superjaaql_db_password,
                                 attach_as=USERNAME__postgres, precedence=PRECEDENCE__super_user)
                super_mfa = self.sign_up_user(self.jaaql_lookup_connection, USERNAME__superjaaql, password, user_id,
                                              ip_address, user_agent, use_mfa=use_mfa)
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

            self.copy_apps()

            base_url = self.url + SEPARATOR__dir + DIR__apps + SEPARATOR__dir
            self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_set_url,
                                            {KEY__application_url: base_url + DIR__console,
                                             KEY__application_name: APPLICATION__console})
            self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_set_url,
                                            {KEY__application_url: base_url + DIR__manager,
                                             KEY__application_name: APPLICATION__manager})
            self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_setup_host,
                                            {KEY__application: APPLICATION__manager})
            self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_set_url,
                                            {KEY__application_url: base_url + DIR__playground,
                                             KEY__application_name: APPLICATION__playground})
            self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__application_setup_host,
                                            {KEY__application: APPLICATION__playground})

            print("Rebooting to allow JAAQL config to be shared among workers")
            threading.Thread(target=self.exit_jaaql).start()

            return {
                KEY__jaaql_otp_uri: mfa[KEY__otp_uri],
                KEY__jaaql_otp_qr: mfa[KEY__otp_qr],
                KEY__superjaaql_otp_uri: super_otp_uri,
                KEY__superjaaql_otp_qr: super_otp_qr
            }
        else:
            raise HttpStatusException(ERR__already_installed)

    def log(self, user_id: str, occurred: datetime, duration_ms: int, exception: str, contr_input: str, ip: str,
            ua: Optional[str], status: int, endpoint: str, databases: list = None):
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

        if not decoded[JWT__fully_authenticated]:
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
            KEY__node: NODE__host_node
        }
        auth = self.execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                         QUERY__role_connection_sel, params,
                                                         as_objects=True,
                                                         decrypt_columns=[KEY__username, KEY__password],
                                                         encryption_key=self.get_db_crypt_key())

        iv = user[KEY__totp_iv]
        return DBInterface.create_interface(self.config, auth[KEY__address], auth[KEY__port], DB__jaaql,
                                            auth[KEY__username], auth[KEY__password]
                                            ), user[KEY__id], ip_id, ua_id, iv, user[ATTR__password_hash], last_totp, \
               username

    def add_application(self, inputs: dict, jaaql_connection: DBInterface):
        default_url = self.url + SEPARATOR__dir + DIR__apps
        inputs[KEY__application_url] = inputs[KEY__application_url].replace("{{DEFAULT}}", default_url)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_ins, inputs)

    def delete_application(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application, inputs)}

    def delete_application_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_del, parameters,
                                        as_objects=True)

    def delete_database(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__database, inputs)}

    def delete_database_confirm(self, inputs: dict, user_id: int, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__database)
        parameters_drop = parameters.copy()
        if KEY__drop in parameters:
            parameters.pop(KEY__drop)
        self.execute_supplied_statement(jaaql_connection, QUERY__database_del, parameters)

        if KEY__drop in parameters_drop and parameters_drop[KEY__drop]:
            drop_inputs = {KEY__node: parameters_drop[KEY__node], KEY__user_id: user_id}
            res = self.execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                            QUERY__node_single_credential_sel, drop_inputs,
                                                            as_objects=True, encryption_key=self.get_db_crypt_key(),
                                                            decrypt_columns=[KEY__username, KEY__password])
            interface = DBInterface.create_interface(self.config, res[KEY__address], res[KEY__port], DB__empty,
                                                     res[KEY__username], res[KEY__password])
            self.execute_supplied_statement(interface, QUERY__drop_database % parameters_drop[KEY__database_name])

    def get_applications(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_count, parameters,
                                         where_query, where_parameters)

    def get_my_applications(self, jaaql_connection: DBInterface):
        return self.execute_supplied_statement(jaaql_connection, QUERY__fetch_my_applications, as_objects=True)

    def fetch_user_default_roles(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__default_roles_sel, parameters,
                                         where_query, where_parameters)

    def add_user_default_role(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__default_roles_ins, inputs)

    def delete_user_default_role(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__default_role, inputs)}

    def delete_user_default_role_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__default_role)
        self.execute_supplied_statement(jaaql_connection, QUERY__default_roles_del, parameters)

    def add_node(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__node_create, inputs)

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
        self.execute_supplied_statement(jaaql_connection, QUERY__node_del, parameters)

    def add_database(self, inputs: dict, jaaql_connection: DBInterface, user_id: int = None):
        inputs_create = inputs.copy()
        if KEY__create in inputs:
            inputs.pop(KEY__create)
        self.execute_supplied_statement(jaaql_connection, QUERY__database_ins, inputs)

        if KEY__create in inputs_create and inputs_create[KEY__create]:
            create_inputs = {KEY__node: inputs_create[KEY__node], KEY__user_id: user_id}
            res = self.execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                            QUERY__node_single_credential_sel, create_inputs,
                                                            as_objects=True, encryption_key=self.get_db_crypt_key(),
                                                            decrypt_columns=[KEY__username, KEY__password])
            interface = DBInterface.create_interface(self.config, res[KEY__address], res[KEY__port], DB__empty,
                                                     res[KEY__username], res[KEY__password])
            self.execute_supplied_statement(interface, QUERY__create_database % inputs[KEY__database_name])

    def update_application(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_upd, inputs)

    def get_databases(self, inputs: dict, jaaql_connection: DBInterface):
        paging_dict, parameters = self.setup_paging_parameters(inputs)

        paging_query, where_query, where_parameters = self.construct_formatted_paging_queries(paging_dict, parameters)
        full_query = QUERY__database_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__database_count, parameters, where_query,
                                         where_parameters)

    def add_application_dataset(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__application_dataset_ins, inputs)

    def get_application_datasets(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__application_dataset_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__application_dataset_count, parameters,
                                         where_query, where_parameters)

    def delete_application_dataset(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__application_dataset, inputs)}

    def delete_application_dataset_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        dataset = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__application_dataset)
        self.execute_supplied_statement(jaaql_connection, QUERY__application_dataset_del, dataset, as_objects=True)

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

    def add_database_assignment(self, inputs: dict, jaaql_connection: DBInterface):
        self.execute_supplied_statement(jaaql_connection, QUERY__assigned_database_ins, inputs)

    def get_assigned_databases(self, inputs: dict, jaaql_connection: DBInterface):
        paging_query, where_query, where_parameters, parameters = self.construct_paging_queries(inputs)
        full_query = QUERY__assigned_database_sel + paging_query

        return self.execute_paging_query(jaaql_connection, full_query, QUERY__assigned_database_count, parameters,
                                         where_query, where_parameters)

    def remove_database_assignment(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__database_assignment, inputs)}

    def remove_database_assignment_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__database_assignment)
        self.execute_supplied_statement(jaaql_connection, QUERY__assigned_database_del, parameters,
                                        as_objects=True)

    def add_node_authorization(self, inputs: dict, connection: DBInterface):
        self.execute_supplied_statement(connection, QUERY__node_credentials_ins, inputs,
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
        self.execute_supplied_statement(jaaql_connection, QUERY__node_credentials_del, parameters,
                                        as_objects=True)

    def add_configuration_authorization(self, inputs: dict, connection: DBInterface):
        self.execute_supplied_statement(connection, QUERY__configuration_authorization_ins, inputs)

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
        self.execute_supplied_statement(jaaql_connection, QUERY__configuration_authorization_del, parameters)

    def revoke_user(self, inputs: dict):
        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__user, inputs)}

    def revoke_user_confirm(self, inputs: dict, jaaql_connection: DBInterface):
        parameters = self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__user)
        self.execute_supplied_statement(jaaql_connection, QUERY__revoke_user, parameters)

    def close_account(self, http_inputs: dict, totp_iv: str, password_hash: str, user_id: str,
                      last_totp: str):
        if not crypt_utils.verify_password_hash(password_hash, http_inputs[KEY__password],
                                                salt=user_id.encode(crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        self.verify_mfa(http_inputs[KEY__mfa_key], totp_iv, last_totp, user_id)

        return {KEY__deletion_key: self.request_deletion_key(DELETION_PURPOSE__user_self, {})}

    def close_account_confirm(self, inputs: dict, user_id: str):
        self.validate_deletion_key(inputs[KEY__deletion_key], DELETION_PURPOSE__user_self)
        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__revoke_user, {ATTR__the_user: user_id})

    def user_invite(self, inputs: dict):
        ms_two_weeks = 1000 * 60 * 60 * 24 * 14
        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), inputs, ms_two_weeks)

    def enable_user_mfa(self, user_id: str):
        totp_iv, totp_uri, totp_b64_qr = self.gen_mfa()

        parameters = {
            KEY__user_id: user_id,
            KEY__totp_iv: totp_iv
        }

        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__set_mfa, parameters,
                                        encrypt_parameters=[KEY__totp_iv], encryption_key=self.get_db_crypt_key())

        return totp_uri, totp_b64_qr

    def fetch_account_info(self, username: str, totp_iv: str):
        return {
            KEY__email: username,
            KEY__mfa_enabled: totp_iv is not None
        }

    def enable_disable_mfa(self, http_inputs: dict, user_id: str, totp_iv: str, last_totp: str, password_hash: str):
        if self.force_mfa:
            raise HttpStatusException(ERR__mfa_must_be_enabled)

        if not crypt_utils.verify_password_hash(password_hash, http_inputs[KEY__password], salt=user_id.encode(
                crypt_utils.ENCODING__ascii)):
            raise HttpStatusException(ERR__password_incorrect, HTTPStatus.UNAUTHORIZED)

        totp_uri = None
        totp_b64_qr = None

        if totp_iv is None:
            totp_uri, totp_b64_qr = self.enable_user_mfa(user_id)
        else:
            self.verify_mfa(http_inputs[KEY__mfa_key], totp_iv, last_totp, user_id)
            self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__disable_mfa, {KEY__user_id: user_id})

        return {
            KEY__otp_uri: totp_uri,
            KEY__otp_qr: totp_b64_qr
        }

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

    def sign_up_user_with_token(self, token: str, password: str, ip_address: str, user_agent: str,
                                response: JAAQLResponse):
        token = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), token)

        inputs = {KEY__username: token[KEY__email]}
        users = self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_user_latest_password,
                                                inputs, as_objects=True,
                                                decrypt_columns=[ATTR__password_hash, KEY__totp_iv],
                                                encryption_key=self.get_db_crypt_key())
        if len(users) != 0:
            raise HttpStatusException(ERR__already_signed_up, response_code=HTTPStatus.CONFLICT)

        return self.sign_up_user(self.jaaql_lookup_connection, token[KEY__email], password, None, ip_address,
                                 user_agent, response=response)

    def sign_up_user(self, jaaql_connection: DBInterface, username: str, password: str, user_id: str = None,
                     ip_address: str = None, user_agent: str = None, use_mfa: bool = False,
                     response: JAAQLResponse = None):
        if user_id is None:
            user_id = self.execute_supplied_statement_singleton(jaaql_connection, QUERY__user_id_from_username,
                                                                {KEY__username: username}, as_objects=True
                                                                )[KEY__username]

        self.add_password(jaaql_connection, user_id, password)

        totp_uri = None
        totp_b64_qr = None

        if self.force_mfa or use_mfa:
            totp_uri, totp_b64_qr = self.enable_user_mfa(user_id)

        if response is not None:
            _, _, _, ip_id, ua_id, _ = self.verify_user(username, ip_address, user_agent)

            response.user_id = user_id
            response.ua_id = ua_id
            response.ip_id = ip_id

        return {
            KEY__otp_uri: totp_uri,
            KEY__otp_qr: totp_b64_qr
        }

    def fetch_default_roles_as_list(self):
        return [row[0] for row in self.execute_supplied_statement(self.jaaql_lookup_connection,
                                                                  QUERY__default_roles_sel)[RET__rows]]

    def create_user(self, jaaql_connection: DBInterface, username: str, db_password: str = None, mobile: str = None,
                    attach_as: str = None, precedence: int = None, roles: str = None):
        if db_password is None:
            db_password = str(uuid.uuid4())

        if attach_as is None:
            attach_as = username

        parameters = {
            ATTR__email: username,
            ATTR__mobile: mobile,
            ATTR__alias: attach_as if attach_as != username else None
        }
        user_id = self.execute_supplied_statement_singleton(jaaql_connection, QUERY__user_ins, parameters,
                                                            as_objects=True)[KEY__id]

        self.add_node_authorization({
            KEY__node: NODE__host_node,
            KEY__role: attach_as,
            KEY__username: attach_as,
            KEY__password: db_password,
            KEY__precedence: precedence
        }, self.jaaql_lookup_connection)

        inputs = {
            KEY__username: username,
            KEY__password: db_password
        }
        self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__user_create_role, inputs)

        if roles is not None:
            roles = roles.split(",") + self.fetch_default_roles_as_list()
            roles = list(set(roles))
            for role in roles:
                # This is not SQL injection. We are protected by the postgres level access control of the connection
                self.execute_supplied_statement(jaaql_connection, QUERY__grant_role % (role, attach_as))

        return user_id

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

    def my_configs(self, jaaql_connection: DBInterface, inputs: dict):
        return self.execute_supplied_statement(jaaql_connection, QUERY__my_configs, inputs, as_objects=True)

    def add_password(self, jaaql_connection: DBInterface, user_id: str, password: str):
        crypt_utils.validate_password(password)
        new_password = crypt_utils.hash_password(password, user_id.encode(crypt_utils.ENCODING__ascii))
        parameters = {
            ATTR__the_user: user_id,
            ATTR__password_hash: new_password
        }
        self.execute_supplied_statement(jaaql_connection, QUERY__user_password_ins, parameters,
                                        encrypt_parameters=[ATTR__password_hash],
                                        encryption_key=self.get_db_crypt_key(),
                                        encryption_salts={ATTR__password_hash: user_id})

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

        self.add_password(jaaql_connection, user_id, new_password)

        decoded[JWT__password] = crypt_utils.encrypt(jwt_obj_key, crypt_utils.hash_password(new_password))

        return crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), decoded,
                                      expiry_ms=self.token_expiry_ms)

    @staticmethod
    def build_db_addr(row: dict):
        db_name = "" if row[KEY__database] is DB__wildcard else ("/" + row[KEY__database])
        return row[KEY__username] + ":" + row[KEY__password] + "@" + row[KEY__address] + ":" + str(row[
                                                                                                       KEY__port]) + db_name

    def config_assigned_databases(self, inputs: dict, jaaql_connection: DBInterface, user_id: str):
        inputs[KEY__user_id] = user_id

        inputs_config_check = {
            KEY__application: inputs[KEY__application],
            KEY__configuration: inputs[KEY__configuration]
        }
        self.execute_supplied_statement_singleton(jaaql_connection, QUERY__my_configs_where, inputs_config_check)

        # It is not a mistake to use the jaaql_lookup_connection rather than the user's connection here
        data = self.execute_supplied_statement(self.jaaql_lookup_connection, QUERY__authorized_configuration,
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
            })
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
            jwt_decoded = crypt_utils.jwt_decode(jwt_key, connection)
            if not jwt_decoded:
                raise HttpStatusException(ERR__connection_expired, HTTP_STATUS_CONNECTION_EXPIRED)
            is_node = jwt_decoded[KEY__is_node]
            db_url = jwt_decoded[KEY__db_url]
            db_url = crypt_utils.decrypt(obj_key, db_url)
            address, port, database, username, password = DBInterface.fracture_uri(db_url,
                                                                                   allow_missing_database=is_node)
            non_null_db = KEY__database in inputs and inputs[KEY__database] is not None
            if is_node:
                database = inputs[KEY__database] if non_null_db else DB__empty
            elif non_null_db:
                raise HttpStatusException(ERR__cannot_override_db, HTTPStatus.UNPROCESSABLE_ENTITY)

            connection = DBInterface.create_interface(self.config, address, port, database, username, password)

        return connection, was_connection_none

    def config_assigned_database_roles(self, inputs: dict, jaaql_connection: DBInterface, user_id: str):
        inputs[KEY_query] = QUERY__my_roles
        return self.submit(inputs, jaaql_connection)[RET__rows]

    def submit(self, http_inputs: dict, jaaql_connection: DBInterface, force_transactional: bool = False):
        connection, was_connection_none = self.obtain_connection(http_inputs, jaaql_connection)

        if KEY__database in http_inputs:
            http_inputs.pop(KEY__database)

        caught_ex = None
        to_ret = None
        try:
            to_ret = InterpretJAAQL(connection).transform(http_inputs, force_transactional=force_transactional)
        except Exception as ex:
            caught_ex = ex

        if not was_connection_none:
            connection.pg_pool.closeall()

        if caught_ex is not None:
            raise caught_ex

        return to_ret
