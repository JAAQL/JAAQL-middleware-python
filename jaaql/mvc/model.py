import base64
import hashlib
import string
import sys
import tempfile
import traceback
import urllib.parse
import uuid
import signal
import secrets
import shlex
from typing import Dict, Any

from cryptography.hazmat.primitives import hashes

import re

import jwt
from jwcrypto import jwe
from io import BytesIO
from flask import send_file

from jwt import PyJWKClient

from jaaql.documentation.documentation_internal import KEY__code, KEY__redirect_uri, KEY__state
from jaaql.exceptions.jaaql_interpretable_handled_errors import *
from jaaql.db.db_pg_interface import DBPGInterface, QUERY__dba_query_external
from jaaql.email.email_manager_service import EmailAttachment
from jaaql.mvc.base_model import BaseJAAQLModel, VAULT_KEY__jwt_crypt_key
from jaaql.exceptions.http_status_exception import HttpStatusException, ERR__already_installed, HttpSingletonStatusException
from os.path import join
from jaaql.interpreter.interpret_jaaql import KEY_query, KEY_parameters
from jaaql.constants import *
from jaaql.utilities.cron import check_if_should_fire_cron
from jaaql.utilities.utils import get_jaaql_root, get_base_url
from jaaql.db.db_utils import create_interface, jaaql__encrypt, create_interface_for_db, jaaql__decrypt
from jaaql.db.db_utils_no_circ import submit, get_required_db, objectify
from jaaql.utilities import crypt_utils
from jaaql.utilities.utils_no_project_imports import get_cookie_attrs, COOKIE_JAAQL_AUTH, COOKIE_OIDC, COOKIE_LOGIN_MARKER, \
    get_sloppy_cookie_attrs
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

KEY__is_the_anonymous_user = "is_the_anonymous_user"

QUERY__ins_rendered_document = "INSERT INTO document_request (encrypted_parameters, encrypted_access_token, template, create_file, application) VALUES (:parameters, :oauth_token, :name, :create_file, :application) RETURNING uuid as document_id"
QUERY__purge_rendered_document = "DELETE FROM document_request WHERE completed is not null and uuid = :document_id RETURNING content"
QUERY__fetch_rendered_document = "SELECT app.base_url, rd.uuid as document_id, 'pdf' as render_as, rd.file_name, rd.create_file, rd.completed, rd.encrypted_access_token as oauth_token FROM document_request rd INNER JOIN document_template able ON rd.template = able.name INNER JOIN application app ON app.name = rd.application WHERE rd.uuid = :document_id"
QUERY__fetch_cron_jobs = "SELECT * FROM remote_procedure WHERE access = 'S'";

class JAAQLModel(BaseJAAQLModel):
    VERIFICATION_QUEUE = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.DISCOVERY_CACHE = {}
        self.JWKS_CACHE = {}

    def redeploy(self, connection: DBInterface):
        raise HttpStatusException("Not yet implemented", response_code=HTTPStatus.NOT_IMPLEMENTED)

    def create_account_with_potential_api_key(self, connection: DBInterface,
                                              sub: str | None, provider: str = None, tenant: str = None,
                                              username: str = None,
                                              email: str = None, attach_as: str = None,
                                              api_key: str = None, already_exists: bool = False, allow_already_exists: bool = False,
                                              registered: bool = False):
        if sub is None:
            sub = username

        account_id = create_account(connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                    username, sub, email, provider,
                                    tenant, api_key,
                                    attach_as, already_exists, allow_already_exists)

        if account_id == "account_already_existed":
            account_id = attach_as

        if registered:
            mark_account_registered(connection, account_id)

        return account_id

    def shallow_federate_batch_potential_with_api_key(self, connection: DBInterface, accounts: list):
        for cur_input in accounts:
            # TODO SHORTCUT TAKEN
            # The email is not set and registered is assumed to be true
            # Should come from the OIDC scopes
            self.create_account_with_potential_api_key(
                connection,
                cur_input[KG__account__sub], cur_input[KG__account__provider], cur_input[KG__account__tenant],
                cur_input[KG__account__username], attach_as=cur_input[KEY__attach_as],
                api_key=cur_input[KEY__password], allow_already_exists=True, registered=True
            )

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

    def parse_gdesc_output(self, output):
        """
        Parse the output of gdesc to extract column names and types.
        """
        lines = output.strip().split('\n')
        columns = {}
        parsing = False
        for line in lines:
            if line.strip().replace(" ", "") == "Column|Type":
                # Found the header line
                parsing = True
                continue
            if parsing:
                if line.strip() == '':
                    # End of table
                    break
                # Parse the line
                parts = [part.strip() for part in line.strip().split('|')]
                if len(parts) >= 2:
                    column_name = parts[0]
                    column_type = parts[1]
                    columns[column_name] = {
                        "type": column_type,
                        "nullable": True  # We can't figure this out with gdesc
                    }
        return columns

    def fetch_domains(self, inputs: dict, account_id: str):
        db_connection = create_interface_for_db(self.vault, self.config, account_id, inputs[KEY__database], None)
        self.is_dba(db_connection)

        domains_query = """
SELECT
    t.typname AS type_name,
    CASE
        WHEN t.typtype = 'd' THEN bt.typname
        ELSE t.typname
    END AS base_type,
    t.typtype
FROM
    pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    LEFT JOIN pg_type bt ON bt.oid = t.typbasetype
WHERE
    t.typtype IN ('b', 'd')
    AND n.nspname NOT IN ('information_schema')
    AND left(t.typname, 1) <> '_'
    AND left(t.typname, 3) <> 'pg_'
ORDER BY
    n.nspname,
    t.typname;
"""

        return execute_supplied_statement(db_connection, domains_query, as_objects=True)

    def prepare_queries(self, inputs: dict, account_id: str):
        cost_only = inputs.get("cost_only", False)
        db_connection = create_interface_for_db(self.vault, self.config, account_id, inputs[KEY__database], None)

        self.is_dba(db_connection)

        res = []

        for query in inputs["queries"]:
            my_uuid = str(uuid.uuid4()).replace("-", "_")
            exc = None
            cost = None
            type_resolution_method = None
            columns = None
            try:
                results = execute_supplied_statement(db_connection, query["query"].strip(),
                                                     do_prepare_only=my_uuid)  # Fetch cursor descriptors here too and then merge
                cost = float(results["rows"][0][0].split("..")[1].split(" ")[0])
            except Exception as ex:
                exc = str(ex).replace("PREPARE _jaaql_query_check_" + my_uuid + " as ", "").replace(
                    " ... _jaaql_query_check_" + my_uuid + " as ", "")

            if exc is None and not cost_only:
                try:
                    domain_types = execute_supplied_statement(db_connection, query["query"].strip(), do_prepare_only=my_uuid, attempt_fetch_domain_types=True)
                    type_resolution_method = "temp_view"
                    temp_columns = [row[0] for row in domain_types['rows']]
                    nullable = [row[4] for row in domain_types['rows']]
                    temp_types = [row[3] if row[3] is not None else row[2] for row in domain_types['rows']]
                    columns = {
                        col: {
                            "type": temp_types[idx],
                            "nullable": nullable[idx]
                        }
                        for col, idx in zip(temp_columns, range(len(temp_columns)))
                    }
                except Exception as ex:
                    pass  # This is fine

                if columns is None:
                    try:
                        type_resolution_method = "gdesc"
                        psql = [
                            "psql",
                            "-U", "postgres",
                            "-d", inputs[KEY__database],
                            "-q", "-X", "--pset", "pager=off", "-f", "-"
                        ]
                        results = execute_supplied_statement(db_connection, query["query"].strip(), do_prepare_only=my_uuid, psql=psql,
                                                             pre_psql="SET SESSION AUTHORIZATION \"" + account_id + "\";")
                        columns = self.parse_gdesc_output(results['rows'][0])
                    except:
                        type_resolution_method = "failed"

            res.append({
                "location": query["file"] + ":" + str(query["line_number"]),
                "name": query["name"],
                "cost": cost,
                "columns": columns,
                "exception": exc,
                "type_resolution_method": type_resolution_method
            })

        if inputs.get("sort_cost", True):
            return sorted(res, key=lambda x: (x["exception"] if x["exception"] is not None else '', float('-inf') if x["cost"] is None else -x["cost"]))
        else:
            return res

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
            with open("/etc/nginx/conf.d/jaaql.conf", "r") as site_file:
                nginx_content = site_file.read()
            if nginx_content is None:
                raise HttpStatusException("Failed to open file for freezing")
            insert_index = nginx_content.index(NGINX_MARKER__first) + len(NGINX_MARKER__first)
            nginx_content = nginx_content[:insert_index] + NGINX_INSERT__frozen + nginx_content[insert_index:]
            insert_index = nginx_content.index(NGINX_MARKER__second) + len(NGINX_MARKER__second)
            nginx_content = nginx_content[:insert_index] + NGINX_INSERT__frozen + nginx_content[insert_index:]
            with open("/etc/nginx/conf.d/jaaql.conf", "w") as site_file:
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
            with open("/etc/nginx/conf.d/jaaql.conf", "r") as site_file:
                nginx_content = site_file.read()
            if nginx_content is None:
                raise HttpStatusException("Failed to open file for defrosting")
            nginx_content = nginx_content.replace("\n        return 503;", "")
            with open("/etc/nginx/conf.d/jaaql.conf", "w") as site_file:
                site_file.write(nginx_content)
            subprocess.call("service nginx restart", shell=True)

            requests.post("http://127.0.0.1:" + str(PORT__shared_var_service) + ENDPOINT__set_shared_var,
                          json={ARG__variable: SHARED_VAR__frozen, ARG__value: False})
        else:
            raise HttpStatusException("Cannot defrost JAAQL running outside a container")

    def is_frozen(self):
        return requests.post("http://127.0.0.1:" + str(PORT__shared_var_service) + ENDPOINT__get_shared_var,
                             json={ARG__variable: SHARED_VAR__frozen}).json()[ARG__value]

    def fetch_user_registries_for_tenant(self, inputs: dict):
        schema = inputs.get(KEY__schema, None)
        if not schema:
            schema = application__select(self.jaaql_lookup_connection, inputs[KEY__application])[KG__application__default_schema]

        database = application_schema__select(self.jaaql_lookup_connection, inputs[KEY__application], schema)
        providers = fetch_providers_from_tenant_and_database(self.jaaql_lookup_connection, inputs[KG__user_registry__tenant],
                                                             database[KG__application_schema__database])

        return {
            "providers": [
                {
                    KG__user_registry__provider: provider[KG__identity_provider_service__name],
                    KG__identity_provider_service__logo_url: provider[KG__identity_provider_service__logo_url]
                }
                for provider in providers
            ]
        }

    def fetch_discovery_content(self, database: str, provider: str, tenant: str, discovery_url: str = None):
        lookup = database + ":" + provider + ":" + tenant
        discovery = self.DISCOVERY_CACHE.get(lookup)
        if not discovery:
            res = requests.get(discovery_url)
            if res.status_code != 200:
                raise Exception(f"Failed to fetch discovery document for {provider}, {tenant} with url {discovery_url}")
            self.DISCOVERY_CACHE[lookup] = res.json()
            discovery = self.DISCOVERY_CACHE[lookup]
        return discovery

    def fetch_jwks_client(self, database: str, provider: str, tenant: str, discovery):
        jwks_url = discovery.get("jwks_uri").replace("localhost", "host.docker.internal")
        if not jwks_url:
            raise Exception(f"Discovery document for {provider}, {tenant} did not have JWKS url")
        lookup = database + ":" + provider + ":" + tenant
        jwks = self.JWKS_CACHE.get(lookup)
        if not jwks:
            self.JWKS_CACHE[lookup] = PyJWKClient(jwks_url)
            jwks = self.JWKS_CACHE[lookup]
        return jwks

    def generate_code_challenge(self, code_verifier):
        """
        Generate a code challenge from the code verifier.
        Uses SHA256 and then base64-url encodes the result.
        """
        # Compute SHA256 hash of the verifier (as ASCII bytes)
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        # Base64-url encode and strip off any trailing '=' characters
        challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        return challenge

    def fetch_jwks(self):
        return self.jwks

    def get_cert_thumbprint(self) -> str:
        fingerprint = self.fapi_cert.fingerprint(hashes.SHA256())
        return base64.urlsafe_b64encode(fingerprint).rstrip(b'=').decode('utf-8')

    def exchange_auth_code(self, inputs: dict, oidc_cookie: str, ip_address: str, response: JAAQLResponse):
        response.delete_cookie(COOKIE_OIDC, self.is_https)
        oidc_state = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), oidc_cookie, JWT_PURPOSE__oidc)

        application = oidc_state[KEY__application]
        application_tuple = application__select(self.jaaql_lookup_connection, application)
        provider = oidc_state[KG__user_registry__provider]
        tenant = oidc_state[KG__user_registry__tenant]
        database = jaaql__decrypt(oidc_state["database"], self.get_db_crypt_key())
        code_verifier = jaaql__decrypt(oidc_state["code_verifier"], self.get_db_crypt_key())

        user_registry = user_registry__select(self.jaaql_lookup_connection, provider, tenant)
        database_user_registry = database_user_registry__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), provider, tenant, database)

        discovery = self.fetch_discovery_content(database, provider, tenant, user_registry[KG__user_registry__discovery_url])
        jwk_client = self.fetch_jwks_client(database, provider, tenant, discovery)

        expected_issuer = discovery.get("issuer")
        if not expected_issuer:
            raise Exception(f"Failed to fetch issuer in discovery document for {provider}, {tenant}")

        token_endpoint = discovery.get("token_endpoint")
        if not token_endpoint:
            raise Exception(f"No token endpoint for {provider}, {tenant}")
        allowed_algs = discovery.get("id_token_signing_alg_values_supported")
        if not allowed_algs:
            raise Exception(f"No allowed algs for {provider}, {tenant}")

        jarms_response = inputs["response"]
        if self.use_fapi_advanced:
            jwe_token = jwe.JWE()
            jwe_token.deserialize(jarms_response)
            jwe_token.decrypt(self.fapi_enc_key)
            jarms_response = jwe_token.payload
        else:
            jarms_response = jarms_response.encode('utf-8')

        signing_key = jwk_client.get_signing_key_from_jwt(jarms_response)
        jarms_payload = jwt.decode(
            jarms_response,
            signing_key.key,
            algorithms=allowed_algs,
            audience=database_user_registry[KG__database_user_registry__client_id],
            issuer=expected_issuer
        )

        if jarms_payload[KEY__state] != oidc_state.get('state'):
            raise UserUnauthorized()

        token_request_payload = {
            'grant_type': 'authorization_code',
            'code': jarms_payload[KEY__code],
            'redirect_uri': application_tuple[KG__application__base_url] + "/api" + ENDPOINT__oidc_get_token,
            'client_id': database_user_registry[KG__database_user_registry__client_id],
            'code_verifier': code_verifier
        }

        kwargs = {}
        if self.use_fapi_advanced:
            kwargs["verify"] = True
            kwargs["cert"] = (f"/etc/letsencrypt/live/{self.application_url}/fullchain.pem", f"/etc/letsencrypt/live/{self.application_url}/privkey.pem")
        else:
            payload = {
                "iss": database_user_registry[KG__database_user_registry__client_id],
                "sub": database_user_registry[KG__database_user_registry__client_id],
                "aud": token_endpoint,
                "jti": str(uuid.uuid4()),
                "iat": int(time.time()),
                "exp": int(time.time()) + 300  # Token valid for 5 minutes
            }
            token_request_payload["client_assertion_type"] = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            token_request_payload["client_assertion"] = jwt.encode(payload, self.fapi_pem, algorithm="PS256", headers={
                "kid": self.jwks["keys"][0]["kid"]
            })

        token_response = self.idp_session.post(
            token_endpoint.replace("localhost", "host.docker.internal"),
            data=token_request_payload,
            **kwargs
        )

        token_data = token_response.json()
        id_token = token_data.get('id_token')
        access_token = token_data.get('access_token')

        signing_key = jwk_client.get_signing_key_from_jwt(id_token)
        id_payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=allowed_algs,
            audience=database_user_registry[KG__database_user_registry__client_id],
            issuer=expected_issuer
        )

        if id_payload.get("nonce") != oidc_state["nonce"]:
            print("Nonce mismatch")
            print(id_payload.get("nonce"))
            print(oidc_state["nonce"])
            raise UserUnauthorized()

        if self.use_fapi_advanced:
            access_signing_key = jwk_client.get_signing_key_from_jwt(access_token)
            access_payload = jwt.decode(
                access_token,
                access_signing_key.key,
                algorithms=allowed_algs,
                issuer=expected_issuer
            )

            # 2. Extract and check the cnf claim.
            cnf_claim = access_payload.get("cnf")
            if not cnf_claim:
                print("No cnf claim!")
                raise UserUnauthorized()  # Access token is missing the 'cnf' claim.

            expected_thumbprint = cnf_claim.get("x5t#S256")
            if not expected_thumbprint:
                print("No thumbprint!")
                raise UserUnauthorized()  # The 'cnf' claim does not contain the 'x5t#S256' field.

            # 3. Compute the thumbprint of the certificate used for mTLS.
            client_cert_thumbprint = self.get_cert_thumbprint()

            # 4. Compare the thumbprints.
            if client_cert_thumbprint != expected_thumbprint:
                self.reload_fapi_cert()
                client_cert_thumbprint = self.get_cert_thumbprint()
                if client_cert_thumbprint != expected_thumbprint:
                    print("Thumbprint mismatch")
                    print(client_cert_thumbprint)
                    print(expected_thumbprint)
                    raise UserUnauthorized()  # Access token 'cnf' claim does not match the client's certificate thumbprint.

        sub = id_payload.get("sub")

        account = None
        try:
            account = fetch_account_from_sub(self.jaaql_lookup_connection, self.get_db_crypt_key(), self.get_vault_repeatable_salt(),
                                             sub, provider, tenant)
            if not account[KG__account__email_verified]:
                email_verified = id_payload.get('email_verified')
                if email_verified:
                    mark_account_registered(self.jaaql_lookup_connection, account[KG__account__id])

        except HttpSingletonStatusException:
            # User does not exist, federate it
            print("federating user")
            email = id_payload.get('email')
            email_verified = id_payload.get('email_verified')
            account_id = self.create_account_with_potential_api_key(self.jaaql_lookup_connection,
                                                                    sub, provider, tenant,
                                                                    None, email, registered=email_verified)
            print("new federated user with account id " + account_id)
            account = account__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), account_id)
            db_params = {"tenant": tenant, "application": application, "account_id": account_id, "provider": provider,
                         "email": email, "sub": sub}
            parameters = fetch_parameters_for_federation_procedure(self.jaaql_lookup_connection,
                                                                   database_user_registry[KG__database_user_registry__federation_procedure])
            for claim in parameters:
                claim_name = claim[KG__federation_procedure_parameter__name]
                db_params[claim_name] = id_payload.get(claim_name)

            procedure_name = database_user_registry[KG__database_user_registry__federation_procedure]
            if re.match(REGEX__dmbs_procedure_name, procedure_name) is None:
                raise HttpStatusException("Unsafe data federation procedure")

            procedure_params = []
            for key, _ in db_params.items():
                if re.match(REGEX__dmbs_object_name, key) is None:
                    raise HttpStatusException("Unsafe data federation parameter " + key)
                procedure_params.append(f"{key} => :{key}")

            submit_data = {
                KEY__application: application,
                KEY_query: f"SELECT * FROM \"{procedure_name}\"({", ".join(procedure_params)});",
                KEY__schema: oidc_state["schema"],
                KEY__parameters: db_params
            }

            print("Preparing federating procedure")

            submit(self.vault, self.config, self.get_db_crypt_key(),
                   self.jaaql_lookup_connection, submit_data, ROLE__jaaql,
                   None, self.cached_canned_query_service, as_objects=True, singleton=True)

            print("Federated user")
            print(submit_data)

        salt_user = self.get_repeatable_salt(account[KG__account__id])
        encrypted_salted_ip_address = jaaql__encrypt(ip_address, self.get_db_crypt_key(), salt_user)  # An optimisation, it is used later twice
        address = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY___add_or_update_validated_ip_address,
                                                       {KG__validated_ip_address__account: account[KG__account__id],
                                                        KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address},
                                                       as_objects=True)[KG__validated_ip_address__uuid]

        jwt_data = {
            KEY__account_id: str(account[KG__account__id]),
            KEY__username: sub,
            KEY__password: None,
            KEY__ip_address: ip_address,
            KEY__ip_id: str(address),
            KEY__created: datetime.now().isoformat(),
            KEY__is_the_anonymous_user: False,
            KEY__remember_me: True
        }

        if response is not None:
            response.account_id = str(account[KG__account__id]),
            response.ip_id = str(address)

        jwt_token = crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), jwt_data, JWT_PURPOSE__oauth, expiry_ms=self.token_expiry_ms)

        response.set_cookie(COOKIE_JAAQL_AUTH, value=jwt_token,
                            attributes=get_cookie_attrs(self.vigilant_sessions, False, self.is_container),
                            is_https=self.is_https)

        response.set_cookie(COOKIE_LOGIN_MARKER, value="true", is_https=True, attributes=get_sloppy_cookie_attrs())

        response.response_code = HTTPStatus.FOUND
        response.raw_headers["Location"] = oidc_state[KEY__redirect_uri]

    def fetch_redirect_uri(self, inputs: dict, response: JAAQLResponse):
        schema = inputs.get(KEY__schema, None)
        application = application__select(self.jaaql_lookup_connection, inputs[KEY__application])
        if not schema:
            schema = application[KG__application__default_schema]

        database = application_schema__select(self.jaaql_lookup_connection, inputs[KEY__application], schema)
        user_registry = user_registry__select(self.jaaql_lookup_connection, inputs[KG__user_registry__provider], inputs[KG__user_registry__tenant])
        database_user_registry = database_user_registry__select(self.jaaql_lookup_connection, self.get_db_crypt_key(), inputs[KG__user_registry__provider],
                                                                inputs[KG__user_registry__tenant], database[KG__application_schema__database])

        discovery = self.fetch_discovery_content(database[KG__application_schema__database], inputs[
            KG__user_registry__provider], inputs[KG__user_registry__tenant], user_registry[KG__user_registry__discovery_url])

        auth_endpoint = discovery.get("authorization_endpoint")
        if not auth_endpoint:
            raise Exception("Authorization endpoint not found in discovery document")

        parameters = fetch_parameters_for_federation_procedure(self.jaaql_lookup_connection,
                                                               database_user_registry[KG__database_user_registry__federation_procedure])
        scope_list = [parameter[KG__federation_procedure_parameter__name] for parameter in parameters]
        client_id = urllib.parse.quote(database_user_registry[KG__database_user_registry__client_id])

        nonce = secrets.token_urlsafe(32)
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = self.generate_code_challenge(code_verifier)
        real_redirect_uri = application[KG__application__base_url] + "/" + inputs[KEY__redirect_uri]
        oidc_redirect_uri = application[KG__application__base_url] + "/api" + ENDPOINT__oidc_get_token

        oidc_session = crypt_utils.jwt_encode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), {
            "redirect_uri": real_redirect_uri,
            "code_verifier": jaaql__encrypt(code_verifier, self.get_db_crypt_key()),
            "nonce": nonce,
            "state": state,
            "tenant": inputs[KG__user_registry__tenant],
            "provider": inputs[KG__user_registry__provider],
            "application": inputs[KEY__application],
            "schema": schema,
            "database": jaaql__encrypt(database[KG__application_schema__database], self.get_db_crypt_key())
        }, JWT_PURPOSE__oidc, expiry_ms=self.oidc_login_expiry_ms)

        response.set_cookie(COOKIE_OIDC, value=oidc_session,
                            attributes=get_cookie_attrs(True, False, self.is_container),
                            is_https=self.is_https)

        default_scopes = ["openid", "profile", "email"]
        for scope in scope_list:
            if scope not in default_scopes:
                default_scopes.append(scope)

        par_endpoint = discovery.get("pushed_authorization_request_endpoint")
        if not par_endpoint:
            raise Exception("Pushed Authorization Request endpoint not found in discovery document.")
        par_endpoint = par_endpoint.replace("localhost", "host.docker.internal")

        par_payload = {
            "client_id": database_user_registry[KG__database_user_registry__client_id],
            "response_type": "code",
            "code_challenge_method": "S256",
            "scope": " ".join(["openid"]),  # should later be default scopes, may cause issues now
            "nonce": nonce,
            "state": state,
            "code_challenge": code_challenge,
            "redirect_uri": oidc_redirect_uri,
        }

        kwargs = {}
        if self.use_fapi_advanced:
            current_time = int(time.time())
            payload = {
                **par_payload,
                "response_mode": "jwt",
                "iss": database_user_registry[KG__database_user_registry__client_id],
                "aud": discovery.get("issuer"),
                "jti": str(uuid.uuid4()),
                "iat": current_time,
                "nbf": current_time - 1,
                "exp": current_time + 300  # Token valid for 5 minutes
            }
            par_payload = {
                "client_id": database_user_registry[KG__database_user_registry__client_id],
                "request": jwt.encode(payload, self.fapi_pem, algorithm="PS256", headers={
                    "kid": self.jwks["keys"][0]["kid"],
                    "typ": "oauth-authz-req+jwt"
                })
            }
            kwargs["verify"] = True
            kwargs["cert"] = (f"/etc/letsencrypt/live/{self.application_url}/fullchain.pem", f"/etc/letsencrypt/live/{self.application_url}/privkey.pem")
        else:
            payload = {
                "iss": database_user_registry[KG__database_user_registry__client_id],
                "sub": database_user_registry[KG__database_user_registry__client_id],
                "aud": discovery.get("pushed_authorization_request_endpoint"),
                "jti": str(uuid.uuid4()),
                "iat": int(time.time()),
                "exp": int(time.time()) + 300  # Token valid for 5 minutes
            }
            par_payload["client_assertion_type"] = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            par_payload["client_assertion"] = jwt.encode(payload, self.fapi_pem, algorithm="PS256", headers={
                "kid": self.jwks["keys"][0]["kid"]
            })

        par_response = self.idp_session.post(
            par_endpoint,
            data=par_payload,
            **kwargs
        )

        if par_response.status_code not in (200, 201):
            print(par_response.status_code)
            print(par_response.text)
            raise Exception(f"PAR request failed with status {par_response.status_code}: {par_response.text}")

        par_data = par_response.json()
        request_uri = par_data.get("request_uri")
        if not request_uri:
            raise Exception("No request_uri returned from the PAR endpoint.")

        redirect_url = auth_endpoint + "?request_uri=" + urllib.parse.quote(request_uri) + f"{"" if self.use_fapi_advanced else "&response_mode=query.jwt"
            }&client_id=" + client_id

        response.response_code = HTTPStatus.FOUND
        response.raw_headers["Location"] = redirect_url

    def set_web_config(self, connection: DBInterface):
        self.is_super_admin(connection)

        if self.is_container:
            # Define the path to your file
            file_path = '/etc/nginx/conf.d/jaaql.conf'
            override = os.environ.get("SET_WEB_CONFIG_OVERRIDE", "")
            if len(override) != 0:
                override += "."
            config_path = f"nginx.{override}config"
            if os.path.exists("/nginx-mount/" + config_path):
                config_path = "/nginx-mount/" + config_path
            else:
                if not os.path.exists(config_path):
                    config_path = "www/" + config_path
                    if not os.path.exists(config_path):
                        print("Could not find config file '" + config_path + "'")
                        return

            new_data = open(config_path, "r").read()
            new_data = new_data.replace("{{JAAQL_INSTALL_LOCATION}}", os.environ.get("INSTALL_PATH"))

            # Read the file content
            with open(file_path, 'r') as file:
                lines = file.readlines()

            # Initialize variables to track the current state and to store updated lines
            in_section = False
            updated_lines = []

            do_write = True

            for line in lines:
                if "listen 443 quic" in line:
                    do_write = False
                if line.strip().startswith('charset'):
                    in_section = True
                    continue  # Skip to the next iteration
                elif (line.startswith('}') or line.strip().startswith("listen 443 ssl") or line.strip().startswith("# listen 443 ssl")) and in_section:
                    # Append new data before the end marker when in a section
                    updated_lines.append(new_data + "\n")
                    in_section = False

                if not in_section or line.startswith('}') or line.strip().startswith("listen 443 ssl") or line.strip().startswith("# listen 443 ssl"):
                    updated_lines.append(line)

            second_iteration_updated_lines = []
            in_localhost = False
            for line in updated_lines:
                if line.strip().startswith("server_name localhost;"):
                    in_localhost = True

                if line.startswith("}"):
                    in_localhost = False

                if line.strip().startswith("listen 443 ssl"):
                    second_iteration_updated_lines.append("    http3 on;")
                    second_iteration_updated_lines.append("    listen 443 quic reuseport;")
                    second_iteration_updated_lines.append("    listen [::]:443 quic reuseport ipv6only=on;")
                    second_iteration_updated_lines.append("    add_header Alt-Svc 'h3=\":443\"; ma=86400';")

                if not in_localhost or not line.strip().startswith("limit_req"):  # Ignore limit req for local requests
                    second_iteration_updated_lines.append(line)

            # Write the updated content back to the file
            if do_write:
                with open(file_path, 'w') as file:
                    file.writelines(second_iteration_updated_lines)

            subprocess.call(['nginx', '-s', 'reload'])
        else:
            print("No headers set for local debugging server")

    def clean(self, connection: DBInterface):
        self.is_super_admin(connection)

        if self.is_container:
            if not self.vault.get_obj(VAULT_KEY__allow_jaaql_uninstall):
                raise HttpStatusException("JAAQL not permitted to uninstall itself")
            DBPGInterface.close_all_pools()
            subprocess.call("./pg_reboot.sh", cwd="/")
        else:
            subprocess.call("docker kill jaaql_pg")
            subprocess.call("docker rm jaaql_pg")
            subprocess.Popen("docker run --name jaaql_pg -p 5434:5432 --mount type=bind,source=" + tempfile.gettempdir().replace("\\", "/") + "/jaaql-debug-slurp-in,target=/slurp-in jaaql/jaaql_pg", start_new_session=True, creationflags=0x00000008)
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

    def execute_migrations(self, connection: DBInterface):
        self.is_super_admin(connection)

        base_url = get_base_url(self.config, self.is_container)
        run_migrations(base_url, self.local_super_access_key, self.local_jaaql_access_key, self.jaaql_lookup_connection)

    def is_installed(self):
        if not self.has_installed:
            raise NotYetInstalled()

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
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts,
                                                                        "ZZZZ.reset_references.sql"))
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts,
                                                                        "ZZZZ.generated_functions_views_and_permissions.sql"))
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "05.install_static_data.generated.sql"))
            self.jaaql_lookup_connection.execute_script_file(conn, join(get_jaaql_root(), DIR__scripts, "06.install_jaaql.exceptions.sql"))
            self.jaaql_lookup_connection.commit(conn)
            self.jaaql_lookup_connection.put_conn(conn)

            self.create_account_with_potential_api_key(self.jaaql_lookup_connection,
                                                       None, None, None,
                                                       USERNAME__jaaql, None, ROLE__jaaql,
                                                       jaaql_password, already_exists=True)
            self.create_account_with_potential_api_key(self.jaaql_lookup_connection,
                                                       None, None, None,
                                                       USERNAME__super_db, None, ROLE__postgres,
                                                       super_db_password, already_exists=True)
            self.create_account_with_potential_api_key(self.jaaql_lookup_connection,
                                                       None, None, None,
                                                       USERNAME__anonymous, None, None,
                                                       PASSWORD__anonymous)

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
            except UserUnauthorized as ex:
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
            return payload[KEY__account_id], payload[KEY__username], payload[KEY__ip_address], payload[KEY__username] == USERNAME__anonymous, \
                payload[KEY__remember_me]
        except Exception:
            raise UserUnauthorized()

    def verify_auth_token(self, auth_token: str, ip_address: str):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth)
        if not decoded or (decoded[KEY__ip_address] != ip_address and ip_address not in IPS__local):
            if os.environ.get("JAAQL_DEBUGGING") == "TRUE":
                print("IP not in ips_local: " + ip_address)
            raise UserUnauthorized()

        if decoded[KEY__username] != USERNAME__anonymous:
            try:
                account = fetch_account_from_id(self.jaaql_lookup_connection, decoded[KEY__account_id], singleton_code=HTTPStatus.UNAUTHORIZED,
                                                singleton_message=ERR__invalid_token)
                if (decoded[KEY__password] is not None and decoded[KEY__password] != "None") and account[KG__account__api_key] != decoded[KEY__password]:
                    raise HttpSingletonStatusException(ERR__invalid_token, HTTPStatus.UNAUTHORIZED)
            except HttpSingletonStatusException:
                raise UserUnauthorized()

        return decoded[KEY__account_id], decoded[KEY__username], decoded[KEY__ip_address], decoded[KEY__username] == USERNAME__anonymous, \
            decoded[KEY__remember_me]

    def refresh_auth_token(self, auth_token: str, ip_address: str, cookie: bool = False, response: JAAQLResponse = None):
        decoded = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), auth_token, JWT_PURPOSE__oauth, allow_expired=True)
        remember_me = False
        if not decoded:
            raise UserUnauthorized()
        if decoded.get(KEY__remember_me):
            remember_me = decoded[KEY__remember_me]

        if datetime.fromisoformat(decoded[KEY__created]) + timedelta(milliseconds=self.refresh_expiry_ms) < datetime.now():
            raise UserUnauthorized()

        return self.get_auth_token(decoded[KEY__username], ip_address, cookie=cookie, remember_me=remember_me, response=response, is_refresh=True, account_id=
                                   decoded[KEY__account_id])

    def get_bypass_user(self, username: str, ip_address: str, provider: str = None, tenant: str = None):
        account = fetch_account_from_username(self.jaaql_lookup_connection, username, singleton_code=HTTPStatus.UNAUTHORIZED)
        salt_user = self.get_repeatable_salt(account[KG__account__id])
        encrypted_salted_ip_address = jaaql__encrypt(ip_address, self.get_db_crypt_key(), salt_user)
        address = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY___add_or_update_validated_ip_address,
                                                       {KG__validated_ip_address__account: account[KG__account__id],
                                                        KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address},
                                                       as_objects=True)[KG__validated_ip_address__uuid]

        return account[KG__account__id], address

    def logout_cookie(self, response: JAAQLResponse):
        response.delete_cookie(COOKIE_JAAQL_AUTH, self.is_https)

    def get_auth_token(
        self,
        username: str, ip_address: str, password: str = None,
        response: JAAQLResponse = None, remember_me: bool = False, cookie: bool = False,
        is_refresh=False, account_id: str = None
    ):
        incorrect_credentials = False
        account = None
        encrypted_salted_ip_address = None

        try:
            if account_id is None:
                account = fetch_account_from_username(
                    self.jaaql_lookup_connection,
                    username,
                    singleton_code=HTTPStatus.UNAUTHORIZED)
            else:
                account = fetch_account_from_id(
                    self.jaaql_lookup_connection,
                    account_id,
                    singleton_code=HTTPStatus.UNAUTHORIZED)
        except HttpStatusException as exc:
            if exc.response_code == HTTPStatus.UNAUTHORIZED:
                incorrect_credentials = True
            else:
                raise exc

        if not incorrect_credentials:
            salt_user = self.get_repeatable_salt(account[KG__account__id])

            encrypted_salted_ip_address = jaaql__encrypt(ip_address, self.get_db_crypt_key(), salt_user)  # An optimisation, it is used later twice

            if is_refresh:
                incorrect_credentials = not exists_matching_validated_ip_address(self.jaaql_lookup_connection, encrypted_salted_ip_address)
            elif os.environ.get("JAAQL_ACCEPTANCE_PASSWORD") is not None:
                incorrect_credentials = password != os.environ["JAAQL_ACCEPTANCE_PASSWORD"]
            elif password is not None:
                incorrect_credentials = jaaql__decrypt(account[KG__account__api_key], self.get_db_crypt_key()) != password
            else:
                incorrect_credentials = True

        if incorrect_credentials:
            raise UserUnauthorized()

        address = execute_supplied_statement_singleton(self.jaaql_lookup_connection,
                                                       QUERY___add_or_update_validated_ip_address,
                                                       {KG__validated_ip_address__account: account[KG__account__id],
                                                        KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address},
                                                       as_objects=True)[KG__validated_ip_address__uuid]

        jwt_data = {
            KEY__account_id: str(account[KG__account__id]),
            KEY__username: username,
            KEY__password: None if account[KG__account__api_key] is None else str(account[KG__account__api_key]),  # This comes out encrypted, it's okay!
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
            return res[KG__application__base_url] + "/" + DIR__render_template + "/" + str(res[KEY__document_id]) + "." + res[KEY__render_as]
        else:
            return res[KG__application__base_url] + "/api/rendered_documents/" + res[KEY__document_id]

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
        if inputs[KEY__parameters] is not None:
            inputs[KEY__parameters] = json.dumps(inputs[KEY__parameters])
        return execute_supplied_statement_singleton(self.jaaql_lookup_connection, QUERY__ins_rendered_document, inputs,
                                                    encryption_key=self.get_db_crypt_key(), encrypt_parameters=[KEY__parameters, KEY__oauth_token],
                                                    as_objects=True)

    def send_email(self, is_the_anonymous_user: bool, account_id: str, inputs: dict, username: str, auth_token: str):
        app = application__select(self.jaaql_lookup_connection, inputs[KEY__application])

        fetched_template = email_template__select(self.jaaql_lookup_connection, inputs[KEY__application], inputs[KEY__template])
        if is_the_anonymous_user and not fetched_template[KG__email_template__can_be_sent_anonymously]:
            raise HttpStatusException("Cannot send this template anonymously")

        if fetched_template[KG__email_template__fixed_address]:
            username = fetched_template[KG__email_template__fixed_address]

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

        data_relation = fetched_template[KG__email_template__data_view]
        if re.match(REGEX__dmbs_object_name, data_relation) is None:
            raise HttpStatusException("Unsafe " + KG__email_template__data_view + " specified for email template")
        safe_parameters = []
        for key, val in inputs[KEY__parameters].items():
            if re.match(REGEX__dmbs_object_name, key) is None:
                raise HttpStatusException("Unsafe parameter specified for email template")
            safe_parameters.append(f'{key} = :{key}')  # Ignore pycharm PEP issue
        where_clause = " AND ".join(safe_parameters)
        if len(where_clause) != 0:
            where_clause = " WHERE " + where_clause
        submit_data[KEY_query] = f'SELECT * FROM {data_relation}{where_clause}'  # Ignore pycharm PEP issue
        # We now get the data that can be shown in the email
        email_replacement_data = submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection,
                                        submit_data, account_id, None, self.cached_canned_query_service,
                                        as_objects=True, singleton=True)

        document_templates = fetch_document_templates_for_email_template(self.jaaql_lookup_connection, inputs[KEY__application],
                                                                         inputs[KEY__template])
        attachments = [
            EmailAttachment(
                template[KG__document_template__name], template[KG__document_template__application], inputs[KEY__parameters],
                template[KG__document_template__email_template]
            )
            for template in document_templates
        ]

        attachment_base_url = ""
        if self.is_container:
            attachment_base_url = app[KG__application__base_url]

        self.email_manager.construct_and_send_email(app[KG__application__templates_source],
                                                    fetched_template[KG__email_template__dispatcher], fetched_template,
                                                    username, email_replacement_data,
                                                    attachments=attachments, attachment_access_token=auth_token,
                                                    attachment_base_url=attachment_base_url)

    from typing import Any, Dict

    def _kc_get_token(self) -> str:
        kc_base = os.environ.get("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
        kc_client_id = os.environ.get("KEYCLOAK_REALM_ADMIN_ID", "admin")
        kc_client_secret = os.environ.get("KEYCLOAK_REALM_ADMIN_SECRET", "admin")
        resp = requests.post(
            f"{kc_base}/realms/master/protocol/openid-connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": kc_client_id,
                "client_secret": kc_client_secret,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _kc_find_user_id_by_username(self, access_token: str, username: str) -> str | None:
        kc_base = os.environ.get("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
        kc_realm = os.environ["KEYCLOAK_REALM"]
        r = requests.get(
            f"{kc_base}/admin/realms/{kc_realm}/users",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"username": username, "exact": "true"},
            timeout=20,
        )
        r.raise_for_status()
        for u in r.json() or []:
            if u.get("username") == username:
                return u.get("id")
        return None

    def _kc_delete_pw_and_passkeys(self, access_token: str, user_id: str) -> None:
        kc_base = os.environ.get("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
        kc_realm = os.environ["KEYCLOAK_REALM"]
        creds = requests.get(
            f"{kc_base}/admin/realms/{kc_realm}/users/{user_id}/credentials",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        creds.raise_for_status()
        for c in creds.json():
            ctype = (c.get("type") or "").lower()
            cid = c.get("id")
            if not cid:
                continue
            if ctype == "password" or ctype.startswith("webauthn"):
                d = requests.delete(
                    f"{kc_base}/admin/realms/{kc_realm}/users/{user_id}/credentials/{cid}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=20,
                )
                if d.status_code != HTTPStatus.NO_CONTENT:
                    d.raise_for_status()

    def _kc_set_temp_password(self, access_token: str, user_id: str, temp_pw: str) -> None:
        kc_base = os.environ.get("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
        kc_realm = os.environ["KEYCLOAK_REALM"]
        r = requests.put(
            f"{kc_base}/admin/realms/{kc_realm}/users/{user_id}/reset-password",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"type": "password", "value": temp_pw, "temporary": True},
            timeout=20,
        )
        r.raise_for_status()

    def _kc_create_user_if_missing(self, access_token: str, username: str) -> str:
        kc_base = os.environ.get("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
        kc_realm = os.environ["KEYCLOAK_REALM"]
        uid = self._kc_find_user_id_by_username(access_token, username)
        if uid:
            return uid
        r = requests.post(
            f"{kc_base}/admin/realms/{kc_realm}/users",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"username": username, "email": username, "enabled": True, "emailVerified": True},
            timeout=20,
        )
        if r.status_code == HTTPStatus.CONFLICT.value:
            # Race with another creator: fetch id again
            uid = self._kc_find_user_id_by_username(access_token, username)
            if not uid:
                r.raise_for_status()
            return uid
        r.raise_for_status()
        loc = r.headers.get("Location", "").rstrip("/")
        return loc.split("/")[-1] if loc else self._kc_find_user_id_by_username(access_token, username)

    def _gen_alnum_16(self) -> str:
        alnum = string.ascii_letters + string.digits
        return "".join(secrets.choice(alnum) for _ in range(16))

    def _gate_run_singleton(self, inputs: dict, account_id: str, security_event: dict) -> Any:
        # Fetch configured procedure
        proc_name = security_event[KG__security_event__database_procedure]
        if re.match(REGEX__dmbs_procedure_name, proc_name) is None:
            raise HttpStatusException(
                "Unsafe " + KG__security_event__database_procedure + " specified for security event"
            )

        # Validate parameter keys
        params = inputs[KEY__parameters]
        explicit_types = inputs.get("explicit_types", {})
        for k in params.keys():
            if re.match(REGEX__dmbs_object_name, k) is None:
                raise HttpStatusException("Unsafe parameter specified for database procedure")

        # Build SELECT * FROM proc(arg => :arg::<type>, ...)
        introduced = False
        query = f"SELECT * FROM \"{proc_name}\"("
        for k in params.keys():
            explicit_type = explicit_types.get(k)
            v = params[k]

            if introduced:
                query += ","

            if explicit_type and v is not None and explicit_type[0] != "_":
                query += f"\n\t{k} => :{k}::{explicit_type}"
            else:
                query += f"\n\t{k} => :{k}"

            introduced = True

        query += "\n)" if introduced else "()"

        submit_data = {
            KEY__application: inputs[KG__security_event__application],
            KEY__parameters: params,
            KEY_query: query,
        }

        # Must return exactly one row (singleton=True enforces this)
        return submit(
            self.vault,
            self.config,
            self.get_db_crypt_key(),
            self.jaaql_lookup_connection,
            submit_data,
            account_id,
            None,
            self.cached_canned_query_service,
            as_objects=True,
            singleton=True,
        )

    def security_event__reset_user_password(
            self,
            inputs: dict,
            account_id: str,
            security_event: dict
    ) -> Dict[str, Any]:
        """
        Gate via DB procedure (must return exactly one row), then:
        - remove all password and passkey credentials,
        - set a new 16-char alphanumeric TEMPORARY password,
        - return { temporary_password, response }.
        """
        # 1) Gate (throws if fails)
        response_obj = self._gate_run_singleton(inputs, account_id, security_event)

        # 2) Keycloak ops
        username = inputs["email"]  # username == email
        access_token = self._kc_get_token()
        user_id = self._kc_find_user_id_by_username(access_token, username)
        if not user_id:
            # If you want to enforce existence only, raise; otherwise create:
            user_id = self._kc_create_user_if_missing(access_token, username)

        self._kc_delete_pw_and_passkeys(access_token, user_id)

        temp_pw = self._gen_alnum_16()
        self._kc_set_temp_password(access_token, user_id, temp_pw)

        return {
            "temporary_password": temp_pw,
            "response": response_obj,
            "subject": user_id
        }

    def security_event__delete_user(
            self,
            inputs: dict,
            account_id: str,
            security_event: dict
    ) -> Dict[str, Any]:
        """
        Gate via DB procedure (must return exactly one row), then delete the Keycloak user.
        Returns { response } (the singleton row from the gate).
        """
        # 1) Gate (throws if fails)
        response_obj = self._gate_run_singleton(inputs, account_id, security_event)

        # 2) Keycloak delete
        username = inputs["email"]  # username == email
        access_token = self._kc_get_token()
        user_id = self._kc_find_user_id_by_username(access_token, username)
        if not user_id:
            raise HttpStatusException("Keycloak user not found for delete")

        kc_base = os.environ["KEYCLOAK_URL"].rstrip("/")
        kc_realm = os.environ["KEYCLOAK_REALM"]
        d = requests.delete(
            f"{kc_base}/admin/realms/{kc_realm}/users/{user_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        if d.status_code not in (HTTPStatus.NO_CONTENT,):
            d.raise_for_status()

        return response_obj

    def security_event__create_user(
            self,
            inputs: dict,
            account_id: str,
            security_event: dict,
    ) -> Dict[str, Any]:
        """
        Executes the configured database function for the security event (must return exactly 1 row),
        then ensures a Keycloak user exists for inputs["email"] with a newly-set TEMPORARY password.

        Returns:
            {
                "temporary_password": "<16-char alphanumeric>",
                "response": <single row/object from the DB function>
            }
        Raises:
            - Any exception from the submit() call (bubbles up).
            - HTTP errors from Keycloak (bubbles up).
        """

        # 1) Gate: run the configured DB procedure and require exactly one row
        response_obj = self._gate_run_singleton(inputs, account_id, security_event)

        # 2) Keycloak ops
        username = inputs["email"]  # username == email
        access_token = self._kc_get_token()

        # Policy: if exactly one local account row -> reset password; if 0 or >1 -> create user
        should_create_user = False
        try:
            _ = fetch_account_from_username(self.jaaql_lookup_connection, username)
            should_create_user = False
        except HttpSingletonStatusException:
            should_create_user = True

        if should_create_user:
            user_id = self._kc_create_user_if_missing(access_token, username)
        else:
            user_id = self._kc_find_user_id_by_username(access_token, username)
            if not user_id:
                # Local account exists but KC user missing -> create it
                user_id = self._kc_create_user_if_missing(access_token, username)

        # Set a new 16-char alphanumeric temporary password
        temp_pw = self._gen_alnum_16()
        self._kc_set_temp_password(access_token, user_id, temp_pw)

        return {
            "temporary_password": temp_pw,
            "response": response_obj,
            "subject": user_id
        }

    def handle_procedure(self, http_inputs: dict, is_the_anonymous_user: bool, auth_token: str, username: str, ip_address: str, account_id: str):
        rpc = remote_procedure__select(self.jaaql_lookup_connection, http_inputs[KG__remote_procedure__application], http_inputs[KG__remote_procedure__name])

        args = http_inputs[KEY__args]
        if args is None:
            args = {}

        if rpc[KG__remote_procedure__access] not in [RPC_ACCESS__private, RPC_ACCESS__public]:
            raise HttpStatusException(f"Cannot call procedure with type '{rpc[KG__remote_procedure__access]}'")

        if rpc[KG__remote_procedure__access] == RPC_ACCESS__private and is_the_anonymous_user:
            raise HttpStatusException("Cannot call a private remote procedure as the public user")

        encoded_args = base64.b64encode(json.dumps(args).encode(ENCODING__utf)).decode(ENCODING__utf)
        encoded_access_token = base64.b64encode(auth_token.encode(ENCODING__utf)).decode(ENCODING__utf)
        encoded_username = base64.b64encode(username.encode(ENCODING__utf)).decode(ENCODING__utf)
        encoded_ip_address = base64.b64encode(ip_address.encode(ENCODING__utf)).decode(ENCODING__utf)
        encoded_account_id = base64.b64encode(account_id.encode(ENCODING__utf)).decode(ENCODING__utf)

        command = [rpc[KG__remote_procedure__command], encoded_args, encoded_access_token, encoded_username, encoded_ip_address, encoded_account_id]
        command = " ".join(command)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)

        try:
            res = json.loads(result.stdout)
            if os.environ.get("JAAQL_PROCEDURE_DEBUGGING", "false").lower() == "true":
                print(result.stderr)
            if result.returncode == 0:
                return res
            elif "error_code" in res:
                raise JaaqlInterpretableHandledError.deserialize_from_json(res)
            else:
                raise Exception("Unrecognised error object")
        except JaaqlInterpretableHandledError as e:
            raise e
        except Exception:
            print(result.stdout)
            print(result.stderr)
            if result.returncode != 0:
                raise UnhandledRemoteProcedureError()

            traceback.print_exc()
            raise HttpStatusException("Could not intepret remote procedure result", HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_webhook(self, application: str, name: str, body: bytes, headers: dict, args: dict,
                       response: JAAQLResponse, account_id: str | None):
        rpc = remote_procedure__select(self.jaaql_lookup_connection, application, name)
        if rpc[KG__remote_procedure__access] != RPC_ACCESS__webhook:
            raise HttpStatusException("Procedure type is not type webhook")

        encoded_body = base64.b64encode(body).decode(ENCODING__utf)
        encoded_headers = base64.b64encode(json.dumps(headers).encode(ENCODING__utf)).decode(ENCODING__utf)
        encoded_args = base64.b64encode(json.dumps(args).encode(ENCODING__utf)).decode(ENCODING__utf)

        # --- Build argv & cwd without using a shell ---
        base_cmd = rpc[KG__remote_procedure__command]  # e.g.
        # "cd /procs && node --import ./__imports__.js RemoteProcedures/webhook/document.proc.entrypoint.js"

        cwd = None
        m = re.match(r'^\s*cd\s+([^\s;]+)\s*&&\s*(.*)$', base_cmd)
        if m:
            cwd = m.group(1)
            base_cmd = m.group(2)

        argv = shlex.split(base_cmd)  # ["node","--import","./__imports__.js","RemoteProcedures/...entrypoint.js"]
        argv += [encoded_headers, encoded_args, encoded_body]
        if account_id is not None:
            argv += [account_id]

        # No shell; pass argv list. Capture output as text.
        result = subprocess.run(
            argv,
            cwd=cwd,  # None if no "cd … &&" in the command
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

        try:
            res = json.loads(result.stdout)
            if result.returncode == 0:
                response.response_code = res.get('statusCode', 200)
                response.raw_headers = res.get('headers', {}) or {}

                body_str = res.get('body', '')
                if res.get('isBase64Encoded'):
                    # be tolerant to padding/whitespace
                    import re as _re
                    s = _re.sub(r"\s+", "", body_str)
                    s += "=" * (-len(s) % 4)
                    response.raw_response = base64.b64decode(s)
                    response.is_binary = True
                else:
                    response.raw_response = body_str
                    response.is_binary = False
            elif isinstance(res, dict) and "error_code" in res:
                raise JaaqlInterpretableHandledError.deserialize_from_json(res)
            else:
                raise Exception("Unrecognised error object")
        except JaaqlInterpretableHandledError:
            raise
        except Exception:
            # Helpful debug
            print("----- STDOUT -----\n", result.stdout, file=sys.stderr)
            print("----- STDERR -----\n", result.stderr, file=sys.stderr)
            if result.returncode != 0:
                raise UnhandledRemoteProcedureError()
            traceback.print_exc()
            raise HttpStatusException("Could not interpret webhook procedure result", HTTPStatus.INTERNAL_SERVER_ERROR)

    def set_procedures(self, inputs: dict, connection: DBInterface):
        execute_supplied_statement(
            connection,
            "DELETE FROM remote_procedure WHERE application = :application",
            { KEY__application: inputs[KEY__application] })

        for proc in inputs["procs"]:
            execute_supplied_statement(
                connection,
                "INSERT INTO remote_procedure (application, name, command, access, cron) VALUES(:application, :name, :command, :access, :cron)",
                { **proc, KG__remote_procedure__application: inputs[KEY__application] })


    def execute_cron_jobs(self, ip_address: str):
        if ip_address not in IPS__local:
            raise UserUnauthorized()

        print("Checking cron job execution status...")

        crons = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_cron_jobs,
                                           as_objects=True)

        for cron in crons:
            if check_if_should_fire_cron(cron["cron"]):
                print("Executing cron job " + cron["name"] + " for application " + cron[KEY__application])
                subprocess.Popen(
                    cron[KEY__command],
                    shell=True,
                    start_new_session=True,  # detach from gunicorn worker
                    text=True
                )

    def get_last_successful_build_time(self):
        if os.environ.get("JAAQL_DEBUGGING") == "TRUE":
            return jaaql__select(self.jaaql_lookup_connection)[KG__jaaql__last_successful_build_time]
        else:
            return 0

    def set_last_successful_build_time(self, http_inputs: dict, ip_address: str):
        if ip_address not in IPS__local:
            raise UserUnauthorized()

        if os.environ.get("JAAQL_DEBUGGING") == "TRUE":
            jaaql__update(self.jaaql_lookup_connection, last_successful_build_time=http_inputs[KG__jaaql__last_successful_build_time])

    def flush_cache(self, ip_address: str):
        if ip_address not in IPS__local:
            raise UserUnauthorized()

        os.kill(int(open("app.pid", "r").read()), signal.SIGUSR1)

    def execute(self, inputs: dict, account_id: str, verification_hook: Queue = None, as_objects: bool = False, singleton: bool = False):
        if self.query_caches is None:
            self.reload_cache()

        if self.db_cache == 1:
            schemas = execute_supplied_statement(self.jaaql_lookup_connection, QUERY__fetch_application_schemas, {
                KG__application_schema__application: self.query_caches["application"]
            }, as_objects=True)
            if len(schemas) == 0:
                print("Couldn't find application " + self.query_caches["application"])
                raise Exception()
            self.db_cache = {itm[KG__application_schema__name]: itm for itm in schemas}
            print("Loaded DB Cache")

        for key, val in inputs["query"].items():
            if isinstance(val, dict):
                trimmed = val["query"].strip()
                val["query"] = self.query_caches["queries"][trimmed.split(":")[0]][int(trimmed.split(":")[1])]
            else:
                trimmed = val.strip()
                inputs["query"][key] = self.query_caches["queries"][trimmed.split(":")[0]][int(trimmed.split(":")[1])]

        return submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, inputs, account_id, verification_hook,
                      self.cached_canned_query_service, as_objects=as_objects, singleton=singleton, db_cache=self.db_cache)

    def call_proc(self, inputs: dict, account_id: str, verification_hook: Queue = None, as_objects: bool = False, singleton: bool = False):
        parameters = inputs["parameters"]
        query_name = inputs["query"]
        if re.match(REGEX__dmbs_procedure_name, query_name) is None:
            raise HttpStatusException("Unsafe procedure name " + query_name)
        query = "SELECT * FROM \"" + query_name + "\"("

        parameter_keys = list(parameters.keys())
        introduced = False
        explicit_types = inputs.get("explicit_types", {})

        absent = ""

        for parameter_key in parameter_keys:
            if re.match(REGEX__dmbs_object_name, parameter_key) is None:
                raise HttpStatusException("Unsafe parameter key " + parameter_key)
            explicit_type = explicit_types.get(parameter_key)
            parameter_value = parameters[parameter_key]

            if introduced:
                query += ","

            if explicit_type and parameter_value is not None and explicit_type[0] != "_":
                query += f"\n\t{parameter_key} => :{parameter_key}::{explicit_type}"
            else:
                query += f"\n\t{parameter_key} => :{parameter_key}{absent}"

            introduced = True

        query += " )"

        inputs["query"] = {
            "_jaaql_procedure": query
        }

        return submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, inputs, account_id, verification_hook,
                      self.cached_canned_query_service, as_objects=as_objects, singleton=singleton, db_cache=None)

    def submit(self, inputs: dict, account_id: str, verification_hook: Queue = None, as_objects: bool = False, singleton: bool = False, ip_address: str = None):
        if ip_address not in IPS__local and self.prevent_arbitrary_queries:
            raise UnhandledJaaqlServerError("Not allowed to send queries to server!")

        return submit(self.vault, self.config, self.get_db_crypt_key(), self.jaaql_lookup_connection, inputs, account_id, verification_hook,
                      self.cached_canned_query_service, as_objects=as_objects, singleton=singleton)


    def begin_oidc_logout(self, inputs: dict, response: JAAQLResponse):
        """
		Start RP-initiated logout: clear app cookies, set logout state cookie, and 302 to OP end-session.
		inputs requires:
			- KEY__application
			- KG__user_registry__provider
			- KG__user_registry__tenant
			- KEY__redirect_uri (final place in your app after logout, e.g. "logged-out" or "")
			- optional: "id_token_hint" (if you persisted the ID token)
		"""
        # Resolve schema & app
        schema = inputs.get(KEY__schema)
        application = application__select(self.jaaql_lookup_connection, inputs[KEY__application])
        if not schema:
            schema = application[KG__application__default_schema]

        # Resolve registry and discovery
        database = application_schema__select(self.jaaql_lookup_connection, inputs[KEY__application], schema)
        user_registry = user_registry__select(self.jaaql_lookup_connection, inputs[KG__user_registry__provider], inputs[KG__user_registry__tenant])
        db_user_registry = database_user_registry__select(
        	self.jaaql_lookup_connection, self.get_db_crypt_key(),
        	inputs[KG__user_registry__provider], inputs[KG__user_registry__tenant],
        	database[KG__application_schema__database]
        )

        discovery = self.fetch_discovery_content(
        	database[KG__application_schema__database],
        	inputs[KG__user_registry__provider],
        	inputs[KG__user_registry__tenant],
        	user_registry[KG__user_registry__discovery_url]
        )

        end_session = discovery.get("end_session_endpoint")
        if not end_session:
            # Fallback for older KC if discovery is missing the field
            issuer = discovery.get("issuer", "").rstrip("/")
            end_session = issuer + "/protocol/openid-connect/logout"

        # Final hop inside YOUR app after KC returns
        final_app_redirect = application[KG__application__base_url] + "/" + (inputs.get(KEY__redirect_uri) or "")
        # The URL that KC will call after it logs the user out (your handler)
        post_logout = application[KG__application__base_url] + "/api/oidc/post-logout"

        # Store the logout round-trip state (re-using your OIDC cookie machinery)
        state = secrets.token_urlsafe(32)
        logout_session = crypt_utils.jwt_encode(
        	self.vault.get_obj(VAULT_KEY__jwt_crypt_key),
        	{
        		"redirect_uri": final_app_redirect,
        		"state": state,
        		"tenant": inputs[KG__user_registry__tenant],
        		"provider": inputs[KG__user_registry__provider],
        		"application": inputs[KEY__application],
        		"schema": schema
        	},
        	JWT_PURPOSE__oidc,
        	expiry_ms=self.oidc_login_expiry_ms
        )

        response.set_cookie(
        	COOKIE_OIDC,
        	value=logout_session,
        	attributes=get_cookie_attrs(True, False, self.is_container),
        	is_https=self.is_https
        )

        # Kill your own app session immediately
        response.delete_cookie(COOKIE_JAAQL_AUTH, self.is_https)
        # Optional: clear the UI helper marker
        response.set_cookie(COOKIE_LOGIN_MARKER, value="", is_https=True, attributes=get_sloppy_cookie_attrs())

        # Build front-channel logout URL (Keycloak requires either id_token_hint OR client_id with post_logout_redirect_uri)
        url = urllib.parse.urlsplit(end_session)
        q = dict(urllib.parse.parse_qsl(url.query, keep_blank_values=True))

        q["post_logout_redirect_uri"] = post_logout
        q["state"] = state

        id_token_hint = inputs.get("id_token_hint")
        if id_token_hint:
            q["id_token_hint"] = id_token_hint
        else:
            q["client_id"] = db_user_registry[KG__database_user_registry__client_id]  # KC >= 18 accepts this fallback

        logout_url = urllib.parse.urlunsplit((
            url.scheme, url.netloc, url.path,
            urllib.parse.urlencode(q, doseq=False, safe="/:"), url.fragment
        ))

        response.response_code = HTTPStatus.FOUND
        response.raw_headers["Location"] = logout_url

    def finish_oidc_logout(self, inputs: dict, response: JAAQLResponse):
        """
        Handle the OP redirect after logout. Validates state, clears OIDC cookie, and 302 to your final URL.
        Expect 'state' in inputs (query param).
        """
        # Read & clear the stored logout session
        oidc_cookie = inputs.get("oidc_cookie")  # if your routing passes cookies in inputs; otherwise fetch from request in your framework
        if not oidc_cookie:
            # fall back to reading directly if your framework wires cookies differently
            raise HttpStatusException("Missing logout state", HTTPStatus.BAD_REQUEST)

        logout_state = crypt_utils.jwt_decode(self.vault.get_obj(VAULT_KEY__jwt_crypt_key), oidc_cookie, JWT_PURPOSE__oidc)
        if not logout_state:
            raise HttpStatusException("Invalid logout state", HTTPStatus.BAD_REQUEST)

        if inputs.get("state") != logout_state.get("state"):
            raise HttpStatusException("Logout state mismatch", HTTPStatus.BAD_REQUEST)

        # Remove the OIDC cookie now that we're done
        response.delete_cookie(COOKIE_OIDC, self.is_https)

        # Redirect to the place the app wanted to land after logout
        response.response_code = HTTPStatus.FOUND
        response.raw_headers["Location"] = logout_state["redirect_uri"]
