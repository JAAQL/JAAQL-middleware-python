import sys

import json
import base64
import requests
import traceback

from jwcrypto import jwk
from cryptography import x509

from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.db.db_interface import DBInterface
import jaaql.utilities.crypt_utils as crypt_utils
from jaaql.db.db_utils import create_interface
from jaaql.constants import *
from jaaql.utilities.options import OPT_KEY__canned_queries
from jaaql.config_constants import *
from jaaql.email.email_manager import EmailManager
from os.path import dirname
from jaaql.services.cached_canned_query_service import CachedCannedQueryService
import threading

import uuid
import subprocess
import time
import os
from os.path import join


CONFIG_KEY_security = "SECURITY"
CONFIG_KEY_SECURITY__mfa_label = "mfa_label"
CONFIG_KEY_SECURITY__mfa_issuer = "mfa_issuer"
CONFIG_KEY_SECURITY__do_audit = "do_audit"
CONFIG_KEY_SECURITY__token_expiry_ms = "token_expiry_ms"
CONFIG_KEY_SECURITY__oidc_login_expiry_ms = "oidc_login_expiry_ms"
CONFIG_KEY_SECURITY__token_refresh_expiry_ms = "token_refresh_expiry_ms"

ERR__expected_matcher = "'like' or '='"
ERR__expected_attribute = "attribute name"
ERR__expected_operand = "operand"
ERR__expected_logic = "'AND' or 'OR'"

ERR__expected_parser = "Expected %s in search parameter not '%s'"
ERR__missing_page_size = "Cannot provide one or the other for page/size. Please provide both or neither"
ERR__unexpected_paren_close = "Cannot process ')' in search as no associated '('"
ERR__unexpected_parse_err = "Unexpected error whilst parsing search string. Please inspect"
ERR__unsupported_direction = "Sort direction should be ASC, DESC or left empty"
ERR__unsupported_column_names = "Please format sorts like 'colname ASC,othercol DESC'. Spaced columns not yet supported"
ERR__unexpected_quote = "Unexpected single quote. Only usable within the operand (after 'like' or '=')"

EXPECTING__attr = 0
EXPECTING__matcher = 1
EXPECTING__operand = 2
EXPECTING__logic = 3
EXPECTING__total = 4

WHERE__id = "where_query_"

KEY__db_crypt_key = "db_crypt_key"

VAULT_KEY__jwt_crypt_key = "jwt_crypt_key"
VAULT_KEY__jwt_obj_crypt_key = "jwt_obj_crypt_key"

FILE__was_installed = "was_installed"

JWT__data = "data"

WARNING__uninstall_allowed = "Due to installation parameters, the system can be uninstalled completely via the API. We do not recommend this being " \
                             "used in production systems (the super user db password is required to perform uninstallation so it is not 'open') "

DIR__apps = "apps"
SEPARATOR__dir = "/"


class JAAQLPivotData:
    def __init__(self, level_data: list, matching: list = None):
        self.matching = matching
        self.level_data = level_data
        self.matching = matching

        self.copy_from_idx = None
        self.copy_to_idx = None

        self.check_idxs = None


class JAAQLPivotInfo:
    def __init__(self, name, keys: [str], on: str):
        self.name = name
        self.keys = keys
        if isinstance(keys, str):
            self.keys = [keys]
        self.on = on
        if not self.on.startswith(self.name + "_"):
            self.on = self.name + "_" + self.on


class BaseJAAQLModel:

    def splice_into(self, x: [dict], y: [dict]):
        for i in range(len(x)):
            missing_dict_fields = [key for key in y[i].keys() if key not in x[i]]
            matching_dict_fields = [key for key in y[i].keys() if key in x[i]]
            for missing in missing_dict_fields:
                x[i][missing] = y[i][missing]
            for matching in matching_dict_fields:
                if isinstance(x[i][matching], list):
                    self.splice_into(x[i][matching], y[i][matching])

    def exit_jaaql(self):
        """
        Will terminate the worker forcefully which fires a hook in gunicorn_config.py
        This hook reloads all workers if the file exists in vault
        :return:
        """
        if self.is_container:
            open(join(DIR__vault, FILE__was_installed), 'a').close()
        if os.environ.get(ENVIRON__install_path, "").strip() == "/component-test-project":
            pid = open("app.pid", "r").read()
            subprocess.call("kill -HUP " + pid, shell=True)  # Kill gunicorn so coverage report is generated
        else:
            print("I am exiting and this will be picked up!")
            time.sleep(1.5)  # Allow other connections to have OK returned
            os._exit(0)

    def group(self, data: [dict], key_field_name: str):
        outer_dict = {}

        for itm in data:
            list_itm = [vals for _, vals in itm.items() if isinstance(vals, list)]
            val_itm = [key for key, val in itm.items() if key != key_field_name]
            if len(list_itm) == 0:
                if len(val_itm) == 1:
                    outer_dict[itm[key_field_name]] = itm[val_itm[0]]
                else:
                    outer_dict[itm[key_field_name]] = {key: itm[key] for key in val_itm}
            else:
                outer_dict[itm[key_field_name]] = self.group(list_itm[0], key_field_name)

        return outer_dict

    def pivot(self, data: [dict], pivot_info: [JAAQLPivotInfo]):
        if len(data) == 0:
            return data
        if not isinstance(pivot_info, list):
            pivot_info = [pivot_info]

        ret = []
        stack = [JAAQLPivotData(ret)]
        cols = list(data[0].keys())

        for row in data:
            copy_from_idx = 0
            last_pivot_length = -1
            for pivot, pivot_idx in zip(pivot_info, range(len(pivot_info))):
                copy_to_idx = cols.index(pivot.on)

                level_data = {key[last_pivot_length + 1:]: val for key, val in row.items() if copy_from_idx <=
                              cols.index(key) < copy_to_idx}
                matching = [level_data[key[last_pivot_length + 1:]] for key in pivot.keys]
                is_empty = len([match for match in matching if match is not None]) == 0

                cur = stack[pivot_idx]
                sub_list = cur.level_data
                if cur.matching != matching:
                    if not is_empty:
                        sub_list.append(level_data)
                    cur.matching = matching
                    stack = stack[0:pivot_idx + 1]

                    new_data = []
                    level_data[pivot.name] = new_data
                    stack.append(JAAQLPivotData(new_data))

                copy_from_idx = copy_to_idx
                last_pivot_length = len(pivot.name)

            cur = stack[-1]
            final_data = {key[last_pivot_length + 1:]: val for key, val in row.items() if copy_from_idx <=
                          cols.index(key)}
            is_empty = len([key for key in final_data if final_data[key] is not None]) == 0
            if not is_empty:
                cur.level_data.append(final_data)

        return ret

    def reload_cache(self):
        print("Received cache flush instruction")
        if os.path.exists("/queries/queries.json"):
            try:
                self.query_caches = json.loads(open("/queries/queries.json", "r").read())
                for key, encoded_list in self.query_caches["queries"].items():
                    # Replace each encoded string in the list with its decoded version.
                    self.query_caches["queries"][key] = [
                        base64.b64decode(encoded).decode('utf-8') for encoded in encoded_list
                    ]
                self.db_cache = 1
                print("Loaded query cache")
            except:
                traceback.print_exc()

    def set_jaaql_lookup_connection(self):
        if self.vault.has_obj(VAULT_KEY__jaaql_lookup_connection):
            jaaql_uri = self.vault.get_obj(VAULT_KEY__jaaql_lookup_connection)
            address, port, db, username, password = DBInterface.fracture_uri(jaaql_uri)
            self.jaaql_lookup_connection = create_interface(self.config, address, port, db, username, password=password)
            if self.options.get(OPT_KEY__canned_queries) or os.environ.get(ENVIRON__canned_queries) == "TRUE":
                self.cached_canned_query_service = CachedCannedQueryService(self.is_container, self.jaaql_lookup_connection)

    def __init__(self, config, vault_key: str, options: dict, migration_project_name: str = None,
                 migration_folder: str = None, is_container: bool = False, url: str = None):
        self.config = config
        self.migration_project_name = migration_project_name
        self.migration_folder = migration_folder
        self.is_container = is_container

        self.query_caches = {}
        self.db_cache = None

        self.prevent_arbitrary_queries = os.environ.get("PREVENT_ARBITRARY_QUERIES", "false") == "true"
        self.is_https = os.environ.get("IS_HTTPS", "false").lower().strip() == "true"
        self.vigilant_sessions = os.environ.get("VIGILANT_SESSIONS", "false").lower().strip() == "true"

        self.cached_canned_query_service = None

        self.url = url
        self.has_installed = False

        self.force_mfa = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__force_mfa]
        self.do_audit = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__do_audit]

        self.jwks = None
        if self.is_container:
            with open('/tmp/jwks.json', 'r') as f:
                self.jwks = json.load(f)

        self.application_url = os.environ.get("SERVER_ADDRESS", "")
        self.use_fapi_advanced = os.environ.get("USE_FAPI_ADVANCED", "").lower() == "true"

        self.fapi_pem = None
        self.fapi_cert = None
        self.fapi_enc = None
        self.fapi_enc_key = None
        if self.is_container:
            with open('/tmp/client_key.pem', "rb") as f:
                self.fapi_pem = f.read()

            with open('/tmp/client_encryption_key.pem', "rb") as f:
                self.fapi_enc = f.read()

            self.fapi_enc_key = jwk.JWK.from_pem(self.fapi_enc)

            if self.use_fapi_advanced:
                with open(f"/etc/letsencrypt/live/{self.application_url}/fullchain.pem", "rb") as f:
                    self.fapi_cert = f.read()
                    self.fapi_cert = x509.load_pem_x509_certificate(self.fapi_cert)

        self.vault = Vault(vault_key, DIR__vault)
        self.jaaql_lookup_connection = None
        self.email_manager = EmailManager(self.is_container)

        self.options = options

        self.token_expiry_ms = int(config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__token_expiry_ms])
        self.oidc_login_expiry_ms = int(config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__oidc_login_expiry_ms])
        self.refresh_expiry_ms = int(config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__token_refresh_expiry_ms])

        if not self.vault.has_obj(VAULT_KEY__db_repeatable_salt):
            self.vault.insert_obj(VAULT_KEY__db_repeatable_salt, crypt_utils.fetch_random_readable_salt().decode(crypt_utils.ENCODING__ascii))

        if not self.vault.has_obj(VAULT_KEY__db_crypt_key):
            _, db_crypt_key = crypt_utils.key_stretcher(str(uuid.uuid4()), length=crypt_utils.AES__key_length)
            self.vault.insert_obj(VAULT_KEY__db_crypt_key, db_crypt_key.decode(crypt_utils.ENCODING__ascii))

        if not self.vault.has_obj(VAULT_KEY__jwt_crypt_key):
            _, jwt_crypt_key = crypt_utils.key_stretcher(str(uuid.uuid4()))
            self.vault.insert_obj(VAULT_KEY__jwt_crypt_key, jwt_crypt_key.decode(crypt_utils.ENCODING__ascii))

        if not self.vault.has_obj(VAULT_KEY__jwt_obj_crypt_key):
            _, jwt_obj_crypt_key = crypt_utils.key_stretcher(str(uuid.uuid4()))
            self.vault.insert_obj(VAULT_KEY__jwt_obj_crypt_key, jwt_obj_crypt_key.decode(crypt_utils.ENCODING__ascii))

        if self.vault.has_obj(VAULT_KEY__jaaql_lookup_connection):
            if self.vault.has_obj(VAULT_KEY__allow_jaaql_uninstall):
                self.uninstall_key = str(uuid.uuid4())
                print(WARNING__uninstall_allowed, file=sys.stderr)
                print("UNINSTALL KEY: " + self.uninstall_key, file=sys.stderr)  # Print to stderr as unbuffered
            else:
                self.install_key = None
            self.has_installed = True

        self.set_jaaql_lookup_connection()

        self.reload_lock = threading.Lock()

        if not self.vault.has_obj(VAULT_KEY__jaaql_local_access_key):
            self.vault.insert_obj(VAULT_KEY__jaaql_local_access_key, str(uuid.uuid4()))

        if not self.vault.has_obj(VAULT_KEY__super_local_access_key):
            self.vault.insert_obj(VAULT_KEY__super_local_access_key, str(uuid.uuid4()))

        self.local_jaaql_access_key = os.environ.get(ENVIRON__JAAQL__JAAQL_BYPASS_KEY,
                                                     self.vault.get_obj(VAULT_KEY__super_local_access_key) if self.is_container else "00000-00000")
        self.local_super_access_key = os.environ.get(ENVIRON__JAAQL__SUPER_BYPASS_KEY,
                                                     self.vault.get_obj(VAULT_KEY__super_local_access_key) if self.is_container else "00000-00000")

        if self.vault.has_obj(VAULT_KEY__jaaql_lookup_connection):
            if self.is_container:
                self.jaaql_lookup_connection.close()  # Each individual class will have one
        else:
            self.install_key = str(uuid.uuid4())
            with open(os.path.join(dirname(dirname(dirname(__file__))), "install_key"), "w") as install_key_file:
                install_key_file.write(self.install_key)
            print("INSTALL KEY: " + self.install_key, file=sys.stderr)  # Print to stderr as unbuffered

        self.idp_session = requests.Session()

    def get_db_crypt_key(self):
        return self.vault.get_obj(VAULT_KEY__db_crypt_key).encode(crypt_utils.ENCODING__ascii)

    def reload_fapi_cert(self):
        with open(f"/etc/letsencrypt/live/{self.application_url}/fullchain.pem", "rb") as f:
            self.fapi_cert = f.read()
            self.fapi_cert = x509.load_pem_x509_certificate(self.fapi_cert)

    def get_vault_repeatable_salt(self):
        return self.vault.get_obj(VAULT_KEY__db_repeatable_salt)

    def get_repeatable_salt(self, addition: str = None):
        repeatable = self.vault.get_obj(VAULT_KEY__db_repeatable_salt)
        return crypt_utils.get_repeatable_salt(repeatable, addition)

    def get_default_app_url(self):
        return self.url + SEPARATOR__dir + DIR__apps

    def replace_default_app_url(self, url_with_default: str):
        if url_with_default is None:
            return None
        return url_with_default.replace("{{DEFAULT}}", self.get_default_app_url())
