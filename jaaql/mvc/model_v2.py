from jaaql.mvc.base_model import BaseJAAQLModel
from jaaql.mvc.queries import *
from jaaql.constants import *
from jaaql.utilities import crypt_utils
from typing import Optional
from jaaql.config_constants import *
=from jaaql.db.db_utils import execute_supplied_statement_singleton, execute_supplied_statement, jaaql__encrypt
from jaaql.db.db_interface import DBInterface
from jaaql.db.db_interface_factory import DBInterfaceFactory
from jaaql.mvc.response import JAAQLResponse
from base64 import b64encode as b64e, b32encode as b32e
from jaaql.exceptions.http_status_exception import HttpStatusException, ERR__already_installed, HTTPStatus
from jaaql.utilities.utils import get_jaaql_root, Profiler
import os
import uuid
import qrcode
from io import BytesIO
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import re
from os.path import join

ATTR__secure_password = "secure_pass"
ATTR__superuser_password = "superuser_password"
ATTR__email = "email"
ATTR__public_credentials = "public_credentials"
ATTR__mobile = "mobile"
ATTR__alias = "alias"
ATTR__ip_address = "ip_address"
ATTR__existed = "existed"

ERR__user_exists = "User already exists!"
ERR__tenant_no_access = "No access to this tenant!"
ERR__incorrect_install_key = "Incorrect install key!"
ERR__invalid_username = "Invalid signup username. Expected an email address"
ERR__invalid_username_internal = "Invalid username. Expected something simple (letters, numbers, underscore and dash)"
ERR__empty_username = "Username cannot be empty"

PG__default_connection_string = "postgresql://postgres:%s@localhost:5432/postgres"

SU__max_conns = 2

SCRIPT__install = "01.install.sql"
SCRIPT__create_system = "02.create_system.sql"

REGEX__email = r'^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$'
REGEX__attach_as = r'^[A-Za-z_-]+$'

RSA__key_size = 2048
RSA__public_exponent = 65537

TENANT__default = "default"


class JAAQLModel(BaseJAAQLModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute_script_file(self, dbi: DBInterface, script: str):
        conn = dbi.get_conn()
        dbi.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, script))
        dbi.execute_query(conn, QUERY__setup_jaaql_role)
        dbi.commit(conn)
        dbi.put_conn(conn)
        dbi.close()

    # For oauth request, user sends plaintext username

    def fetch_salt(self, sys_dbi: DBInterface, user_tenant: str):
        ret = execute_supplied_statement_singleton(sys_dbi, QUERY__fetch_tenant_salt, {KEY__tenant: user_tenant})
        return ret[RET__row][0].encode(crypt_utils.ENCODING__ascii)

    def fetch_system_singletons(self, sys_dbi: DBInterface):
        return execute_supplied_statement_singleton(sys_dbi, QUERY__initialise_singleton, as_objects=True)

    def add_user_public_key(self, sys_dbi: DBInterface, user_id: str, public_key: str, system_symmetric_key: bytes):
        parameters = {
            ATTR__the_user: user_id,
            KEY__public_key: public_key
        }

        execute_supplied_statement(sys_dbi, QUERY__user_password_ins, parameters, encrypt_parameters=[KEY__public_key],
                                   encryption_key=system_symmetric_key, encryption_salts={KEY__public_key: user_id})

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

    def enable_user_mfa(self, dbi: DBInterface, system_symmetric_key: bytes, user_id: str):
        totp_iv, totp_uri, totp_b64_qr = self.gen_mfa()

        parameters = {
            KEY__user_id: user_id,
            KEY__totp_iv: totp_iv
        }

        execute_supplied_statement(dbi, QUERY__set_mfa, parameters, encrypt_parameters=[KEY__totp_iv], encryption_key=system_symmetric_key)

        return totp_uri, totp_b64_qr

    def add_user_ip_address_and_check_existing(self, sys_dbi: DBInterface, system_symmetric_key: bytes, user_id: str, ip_address: str):
        user_id = str(user_id)  # Could be uuid type
        ip_address = jaaql__encrypt(ip_address, system_symmetric_key, user_id)

        res = execute_supplied_statement_singleton(sys_dbi, QUERY__user_ip_ins, { KEY__user_id: user_id, ATTR__ip_address: ip_address },
                                                   as_objects=True)

        return res[ATTR__existed], res[KEY__id]


    def sign_up_user(self, sys_dbi: DBInterface, system_symmetric_key: bytes, tenant: str, username: str, public_key: str, force_mfa: bool = False,
                     system_tenant_salt: bytes = None, ip_address: str = None, response: JAAQLResponse = None, use_mfa: bool = False):
        if system_tenant_salt is None:
            system_tenant_salt = self.fetch_salt(sys_dbi, tenant)

        if force_mfa is None:
            force_mfa = self.fetch_system_singletons(sys_dbi)[KEY__force_mfa]

        user_id = execute_supplied_statement_singleton(sys_dbi, QUERY__user_id_from_username, {KEY__username: username},
                                                       encryption_key=system_symmetric_key, encryption_salts={KEY__username: system_tenant_salt},
                                                       encrypt_parameters=[KEY__username], as_objects=True)[KEY__id]
        user_id = str(user_id)
        self.add_user_public_key(sys_dbi, user_id, public_key, system_symmetric_key)

        totp_uri = None
        totp_b64_qr = None

        if force_mfa or use_mfa:
            totp_uri, totp_b64_qr = self.enable_user_mfa(sys_dbi, system_symmetric_key, user_id)

        if response is not None:
            _, ip_id = self.add_user_ip_address_and_check_existing(sys_dbi, system_symmetric_key, user_id, ip_address)

            response.user_id = user_id
            response.ip_id = ip_id

        return {
            KEY__otp_uri: totp_uri,
            KEY__otp_qr: totp_b64_qr
        }

    # requires tenant, nullable
    # user_tenant is a tenant of the user fetched and passed in by controller
    # system_symmetric_key is also passed through
    def create_user(self, dbi: Optional[DBInterface], sys_dbi: DBInterface, system_symmetric_key: bytes, tenant: str, username: str,
                    application: str = None, user_tenant: str = None, mobile: str = None, attach_as: str = None, roles: str = "",
                    system_tenant_salt: bytes = None, is_public: bool = False):
        if user_tenant is not None and user_tenant != tenant:
            raise HttpStatusException(ERR__tenant_no_access)

        if dbi is None:
            dbi = sys_dbi

        if system_tenant_salt is None:
            system_tenant_salt = self.fetch_salt(sys_dbi, tenant)

        if not is_public and username != sys_dbi.system and username != USERNAME__superjaaql and not re.match(REGEX__email, username):
            raise HttpStatusException(ERR__invalid_username)
        elif is_public and not re.match(REGEX__attach_as, username):
            raise HttpStatusException(ERR__invalid_username_internal)
        elif attach_as and not re.match(REGEX__attach_as, username):
            raise HttpStatusException(ERR__invalid_username_internal)

        parameters = {
            ATTR__email: username,
            ATTR__mobile: mobile,
            ATTR__alias: attach_as,
            KEY__is_public: is_public,
            KEY__tenant: tenant,
            KEY__application: application if is_public else None,
            ATTR__public_credentials: str(username + ":") if is_public else None
        }

        params = [ATTR__email, ATTR__mobile, ATTR__alias]
        salts = {ATTR__email: system_tenant_salt}
        ret_user = execute_supplied_statement_singleton(dbi, QUERY__user_ins, parameters, encrypt_parameters=params, encryption_salts=salts,
                                                        encryption_key=system_symmetric_key, as_objects=True)
        user_id = ret_user[KEY__id]
        user_existed = ret_user[KEY__email] is None

        if user_existed:
            raise HttpStatusException(ERR__user_exists, HTTPStatus.CONFLICT)

        db_username = attach_as

        if attach_as is None:
            db_username = username if is_public else user_id
            execute_supplied_statement(sys_dbi, QUERY__user_create_role, {KEY__username: db_username})

        if application is not None:
            execute_supplied_statement(sys_dbi, QUERY__grant_default_roles, {KEY__the_application: application, KEY__user_id: user_id,
                                                                             KEY__username: db_username})

        roles = roles.split(",")
        roles = list(set(roles))
        for role in roles:
            execute_supplied_statement(dbi, QUERY__grant_role, {KEY__role: role, KEY__username: db_username})

        return user_id

    def create_system(self, dbi: DBInterface, sys_name: str, public_key: str, use_mfa: bool, force_mfa: bool,
                      allow_system_reset_password: bool, application: str = None, application_description: str = None):
        sys_input = {KEY__system_name: sys_name}
        db_password = execute_supplied_statement_singleton(dbi, QUERY__system_create_role, sys_input)[RET__rows][0]
        sys_input[ATTR__superuser_password] = db_password
        execute_supplied_statement(dbi, QUERY__system_create, sys_input, encrypt_parameters=[ATTR__superuser_password],
                                   encryption_key=self.get_db_crypt_key())

        sys_dbi = self.dbif.fetch_interface(sys_name, sys_name, db_password)
        self.execute_script_file(sys_dbi, SCRIPT__create_system)

        system_public_key = None
        system_private_key = None
        system_symmetric_key = str(uuid.uuid4())
        if allow_system_reset_password:
            private_key = rsa.generate_private_key(
                public_exponent=RSA__public_exponent,
                key_size=RSA__key_size,
                backend=default_backend()
            )
            system_public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode(ENCODING__ascii)
            system_private_key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode(ENCODING__ascii)

        execute_supplied_statement(sys_dbi, QUERY__initialise_singleton, {
            KEY__allow_system_password_reset: allow_system_reset_password,
            KEY__system_public_key: system_public_key,
            KEY__system_private_key: system_private_key,
            KEY__system_symmetric_key: system_symmetric_key
        }, encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__system_private_key, KEY__system_symmetric_key])
        if force_mfa:
            execute_supplied_statement(sys_dbi, QUERY__force_mfa)

        execute_supplied_statement(sys_dbi, QUERY__setup_application,
                                   {KEY__application_name: application, KEY__application_description: application_description})

        tenant_salt = self.fetch_salt(sys_dbi, TENANT__default)
        self.create_user(None, sys_dbi, system_symmetric_key.encode(ENCODING__ascii), TENANT__default, sys_dbi.system, application,
                         attach_as=sys_dbi.system, system_tenant_salt=tenant_salt)
        self.sign_up_user(sys_dbi, tenant_salt, TENANT__default, sys_dbi.system, public_key, system_tenant_salt=tenant_salt, use_mfa=use_mfa,
                          force_mfa=force_mfa)

    # RSA(b_pr_key, random_uuid()) = jaaql_private_data_key, -- Incorrect. It's symmetrically encrypted + not required
    # jaaql_public_key,
    # RSA(b_pr_key_2, random_uuid()) = superjaaql_private_data_key,  -- Incorrect symmetrically encrypted + not required
    # superjaaql_public_key,
    # install_key
    # use_mfa,
    # force_mfa,
    # allow_uninstall
    # allow_system_reset_password

    def install(self, inputs: dict, ip_address: str, response: JAAQLResponse):
        if self.root_connection is not None:
            raise HttpStatusException(ERR__already_installed)

        if inputs[KEY__install_key] != self.install_key:
            raise HttpStatusException(ERR__incorrect_install_key, HTTPStatus.UNAUTHORIZED)

        db_connection_string = inputs[KEY__db_connection_string]
        if db_connection_string is None:
            db_connection_string = PG__default_connection_string % os.environ[PG_ENV__password]

        address, port, db, username, db_password = DBInterface.fracture_uri(db_connection_string)
        self.vault.insert_obj(VAULT_KEY__superuser_connection, db_connection_string)
        self.dbif = DBInterfaceFactory(self.config, self.get_db_crypt_key(), address, port)
        self.root_connection = self.dbif.fetch_interface(username, username, db_password, SU__max_conns)
        self.execute_script_file(self.root_connection, SCRIPT__install)

        self.create_system(self.root_connection, SYSTEM__jaaql, inputs[KEY__public_key], inputs[KEY__use_mfa], inputs[KEY__force_mfa],
                           inputs[KEY__allow_system_reset_password])
