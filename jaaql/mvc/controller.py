from jaaql.mvc.exception_queries import SECURITY_EVENT_TYPE__create, SECURITY_EVENT_TYPE__delete, \
    SECURITY_EVENT_TYPE__reset
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.base_controller import BaseJAAQLController
from jaaql.documentation.documentation_internal import *
from jaaql.documentation.documentation_public import *
from jaaql.documentation.documentation_shared import *
from jaaql.mvc.response import JAAQLResponse
from jaaql.db.db_interface import DBInterface
from flask import request
import queue

from jaaql.utilities.utils_no_project_imports import COOKIE_OIDC


class JAAQLController(BaseJAAQLController):

    def __init__(self, model: JAAQLModel, is_prod: bool, base_url: str, do_profiling: bool = False):
        super().__init__(model, is_prod, base_url, do_profiling)

    def create_app(self):

        @self.publish_route('/oauth/token', DOCUMENTATION__oauth_token)
        def fetch_oauth_token(http_inputs: dict, ip_address: str, response: JAAQLResponse):
            return self.model.get_auth_token(**http_inputs, ip_address=ip_address, response=response, is_refresh=False)

        @self.publish_route('/oauth/cookie', DOCUMENTATION__oauth_cookie)
        def fetch_oauth_cookie(http_inputs: dict, ip_address: str, response: JAAQLResponse):
            self.model.get_auth_token(**http_inputs, ip_address=ip_address, response=response, cookie=True, is_refresh=False)

        @self.publish_route('/logout-cookie', DOCUMENTATION__logout_cookie)
        def fetch_oauth_cookie(response: JAAQLResponse):
            self.model.logout_cookie(response)

        @self.publish_route('/oauth/refresh-cookie', DOCUMENTATION__oauth_refresh)
        def refresh_oauth_cookie(auth_token_for_refresh: str, ip_address: str, response: JAAQLResponse):
            self.model.refresh_auth_token(auth_token_for_refresh, ip_address, cookie=True, response=response)

        @self.publish_route("/internal/freeze", DOCUMENTATION__freeze)
        def refresh_oauth_token(connection: DBInterface):
            self.model.freeze(connection)

        @self.publish_route("/internal/defrost", DOCUMENTATION__defrost)
        def refresh_oauth_token(connection: DBInterface):
            self.model.defrost(connection)

        @self.publish_route("/internal/frozen", DOCUMENTATION__check_frozen)
        def refresh_oauth_token():
            return self.model.is_frozen()

        @self.publish_route(ENDPOINT__refresh, DOCUMENTATION__oauth_refresh)
        def refresh_oauth_token(auth_token_for_refresh: str, ip_address: str):
            return self.model.refresh_auth_token(auth_token_for_refresh, ip_address)

        @self.publish_route(ENDPOINT__install, DOCUMENTATION__install)
        def install(http_inputs: dict):
            return self.model.install(**http_inputs)

        @self.publish_route(ENDPOINT__execute_migrations, DOCUMENTATION__migrations)
        def execute_migrations(connection: DBInterface):
            return self.model.execute_migrations(connection)

        @self.publish_route('/internal/is_installed', DOCUMENTATION__is_installed)
        def is_installed():
            return self.model.is_installed()

        @self.publish_route(ENDPOINT__is_alive, DOCUMENTATION__is_alive)
        def is_alive():
            self.model.is_alive()

        @self.publish_route('/accounts', DOCUMENTATION__create_account)
        def accounts(connection: DBInterface, http_inputs: dict):
            registered = http_inputs.get(KEY__registered, True)
            if KEY__registered in http_inputs:
                http_inputs.pop(KEY__registered)
            if registered is None:
                registered = True
            self.model.create_account_with_potential_api_key(connection, username=http_inputs[KEY__username],
                                                             api_key=http_inputs[KEY__password], attach_as=http_inputs[KEY__attach_as],
                                                             registered=registered, sub=None)

        @self.publish_route('/accounts/batch', DOCUMENTATION__create_account_batch)
        def accounts(connection: DBInterface, http_inputs: dict):
            self.model.shallow_federate_batch_potential_with_api_key(connection, **http_inputs)

        @self.publish_route('/prepare', DOCUMENTATION__prepare)
        def prepare(http_inputs: dict, account_id: str):
            return self.model.prepare_queries(http_inputs, account_id)

        @self.publish_route('/procedures', DOCUMENTATION__procedures)
        def procedures(connection: DBInterface, http_inputs: dict):
            self.model.set_procedures(http_inputs, connection)

        @self.publish_route('/domains', DOCUMENTATION__domains)
        def prepare(http_inputs: dict, account_id: str):
            return self.model.fetch_domains(http_inputs, account_id)

        @self.publish_route('/submit', DOCUMENTATION__submit)
        def submit(http_inputs: dict, account_id: str, verification_hook: queue.Queue, ip_address: str):
            return self.model.submit(http_inputs, account_id, verification_hook=verification_hook, ip_address=ip_address)

        @self.publish_route('/execute', DOCUMENTATION__execute)
        def execute(http_inputs: dict, account_id: str, verification_hook: queue.Queue):
            return self.model.execute(http_inputs, account_id, verification_hook=verification_hook)

        @self.publish_route('/call-proc', DOCUMENTATION__execute)
        def call_proc(http_inputs: dict, account_id: str, verification_hook: queue.Queue):
            return self.model.call_proc(http_inputs, account_id, verification_hook=verification_hook)

        @self.publish_route('/internal/clean', DOCUMENTATION__clean)
        def clean(connection: DBInterface):
            self.model.clean(connection)

        @self.publish_route('/security-event', DOCUMENTATION__security_event)
        def security_event(http_inputs: dict, account_id: str):
            security_event = security_event__select(self.model.jaaql_lookup_connection, http_inputs[KEY__application],
                                                    name=http_inputs[KG__security_event__name],
                                                    type=http_inputs[KG__security_event__type])
            http_inputs["email"] = http_inputs[KEY__parameters]["email"]
            if security_event[KG__security_event__type] == SECURITY_EVENT_TYPE__create:
                return self.model.security_event__create_user(http_inputs, account_id, security_event)
            elif security_event[KG__security_event__type] == SECURITY_EVENT_TYPE__delete:
                return self.model.security_event__delete_user(http_inputs, account_id, security_event)
            elif security_event[KG__security_event__type] == SECURITY_EVENT_TYPE__reset:
                return self.model.security_event__reset_user_password(http_inputs, account_id, security_event)
            else:
                raise HttpStatusException("Invalid security event type")

        @self.publish_route('/internal/dispatchers', DOCUMENTATION__dispatchers)
        def dispatchers(connection: DBInterface, http_inputs: dict):
            self.model.attach_dispatcher_credentials(connection, http_inputs)

        @self.publish_route('/email', DOCUMENTATION__emails)
        def send_email(is_the_anonymous_user: bool, account_id: str, http_inputs: dict, username: str, auth_token: str):
            return self.model.send_email(is_the_anonymous_user, account_id, http_inputs, username, auth_token)

        @self.publish_route('/cron', DOCUMENTATION__cron)
        def cron(ip_address: str):
            self.model.execute_cron_jobs(ip_address)

        @self.publish_route('/build-time', DOCUMENTATION__last_successful_build_timestamp)
        def build_time(http_inputs: dict, ip_address: str):
            if self.is_post():
                self.model.set_last_successful_build_time(http_inputs, ip_address)
            else:
                return self.model.get_last_successful_build_time()

        @self.publish_route('/flush-cache', DOCUMENTATION__flush_cache)
        def flush_cache(ip_address: str):
            self.model.flush_cache(ip_address)

        @self.publish_route('/webhook/<application>/<name>', DOCUMENTATION__webhook)
        def handle_webhook(application: str, name: str, body: bytes, headers: dict, args: dict, response: JAAQLResponse):
            self.model.handle_webhook(application, name, body, headers, args, response, None)

        @self.publish_route('/secure/<application>/<name>', DOCUMENTATION__secure_webhook)
        def handle_secure_webhook(application: str, name: str, body: bytes, headers: dict, args: dict,
                                  response: JAAQLResponse, account_id: str):
            self.model.handle_webhook(application, name, body, headers, args, response, account_id)

        @self.publish_route('/remote_procedure', DOCUMENTATION__remote_procedures)
        def handle_remote_procedure(http_inputs: dict, is_the_anonymous_user: bool, auth_token: str, username: str, ip_address: str, account_id: str):
            return self.model.handle_procedure(http_inputs, is_the_anonymous_user, auth_token, username, ip_address, account_id)

        @self.publish_route('/internal/set-web-config', DOCUMENTATION__set_web_config)
        def set_web_config(connection: DBInterface):
            self.model.set_web_config(connection)

        @self.publish_route('/fetch-user-registries-for-tenant', DOCUMENTATION__oidc_user_registries)
        def fetch_user_providers_for_tenant(http_inputs: dict):
            return self.model.fetch_user_registries_for_tenant(http_inputs)

        @self.publish_route('/oidc-redirect-url', DOCUMENTATION__oidc_redirect_url)
        def fetch_redirect_url(http_inputs: dict, response: JAAQLResponse):
            self.model.fetch_redirect_uri(http_inputs, response)

        @self.publish_route(ENDPOINT__oidc_get_token, DOCUMENTATION__oidc_exchange_code)
        def exchange_auth_code(http_inputs: dict, ip_address: str, response: JAAQLResponse):
            try:
                self.model.exchange_auth_code(http_inputs, request.cookies.get(COOKIE_OIDC), ip_address, response)
            except:  # Sometimes this can fail when the user didn't exist before
                response.response_code = HTTPStatus.FOUND
                response.raw_headers["Location"] = self.model.url.replace("_", "localhost")

        @self.publish_route('/.well-known/jwks', DOCUMENTATION__jwks)
        def fetch_jwks():
            return self.model.fetch_jwks()

        @self.publish_route('/documents', DOCUMENTATION__document)
        def documents(http_inputs: dict, auth_token: str, ip_address: str, response: JAAQLResponse):
            if self.is_get():
                return self.model.fetch_document(http_inputs, response)
            else:
                return self.model.render_document(http_inputs, auth_token, ip_address)

        @self.publish_route('/rendered_documents', DOCUMENTATION__rendered_document)
        def documents(http_inputs: dict):
            return self.model.fetch_document_stream(http_inputs)

        @self.publish_route('/oidc/logout', DOCUMENTATION__oidc_begin_logout)
        def begin_oidc_logout(http_inputs: dict, response: JAAQLResponse):
            # inputs: application, tenant, provider, optional schema, redirect_uri, optional id_token_hint
            self.model.begin_oidc_logout(http_inputs, response)

        @self.publish_route('/oidc/post-logout', DOCUMENTATION__oidc_post_logout)
        def finish_oidc_logout(http_inputs: dict, response: JAAQLResponse):
            # KC returns ?state=... here; validate against cookie and bounce to final app URL
            self.model.finish_oidc_logout(
                {"state": http_inputs["state"], "oidc_cookie": request.cookies.get(COOKIE_OIDC)},
                response
            )
