from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.base_controller import BaseJAAQLController
from jaaql.documentation.documentation_internal import *
from jaaql.documentation.documentation_public import *
from jaaql.documentation.documentation_shared import *
from jaaql.mvc.response import JAAQLResponse
from jaaql.db.db_interface import DBInterface
import queue


class JAAQLController(BaseJAAQLController):

    def __init__(self, model: JAAQLModel, is_prod: bool, base_url: str, do_profiling: bool = False):
        super().__init__(model, is_prod, base_url, do_profiling)

    def create_app(self):

        @self.cors_route('/oauth/token', DOCUMENTATION__oauth_token)
        def fetch_oauth_token(http_inputs: dict, ip_address: str, response: JAAQLResponse):
            return self.model.get_auth_token(**http_inputs, ip_address=ip_address, response=response)

        @self.cors_route('/internal/redeploy', DOCUMENTATION__deploy)
        def redeploy(connection: DBInterface):
            return self.model.redeploy(connection)

        @self.cors_route(ENDPOINT__refresh, DOCUMENTATION__oauth_refresh)
        def refresh_oauth_token(auth_token: str, ip_address: str):
            return self.model.refresh_auth_token(auth_token, ip_address)

        @self.cors_route('/internal/canned-queries', DOCUMENTATION__canned_queries)
        def refresh_app_config(connection: DBInterface, inputs: dict):
            self.model.refresh_cached_canned_query_service(connection, **inputs)

        @self.cors_route(ENDPOINT__install, DOCUMENTATION__install)
        def install(http_inputs: dict):
            return self.model.install(**http_inputs)

        @self.cors_route('/internal/uninstall', DOCUMENTATION__uninstall)
        def uninstall():
            raise HttpStatusException(HTTPStatus.NOT_IMPLEMENTED.description, HTTPStatus.NOT_IMPLEMENTED.value)

        @self.cors_route('/internal/is_installed', DOCUMENTATION__is_installed)
        def is_installed(response: JAAQLResponse):
            return self.model.is_installed(response)

        @self.cors_route(ENDPOINT__is_alive, DOCUMENTATION__is_alive)
        def is_alive():
            self.model.is_alive()

        @self.cors_route('/email/account', DOCUMENTATION__drop_email_account)
        def drop_email_account(http_inputs: dict, connection: DBInterface):
            self.model.drop_email_account(connection, **http_inputs)

        @self.cors_route('/accounts', DOCUMENTATION__create_account)
        def accounts(connection: DBInterface, http_inputs: dict):
            self.model.create_account(connection, http_inputs)

        @self.cors_route('/account/password', DOCUMENTATION__password)
        def password(user_id: str, username: str, ip_address: str, http_inputs: dict):
            return self.model.add_my_account_password(user_id, username, ip_address, **http_inputs)

        @self.cors_route('/submit', DOCUMENTATION__submit)
        def submit(http_inputs: dict, user_id: str, verification_hook: queue.Queue):
            return self.model.submit(http_inputs, user_id, verification_hook=verification_hook)

        @self.cors_route('/account/signup/request', DOCUMENTATION__sign_up_request_invite)
        def signup_request(http_inputs: dict):
            return self.model.request_signup(http_inputs)

        @self.cors_route('/account/signup/status', DOCUMENTATION__sign_up_status)
        def signup_request(http_inputs: dict):
            return self.model.signup_status(http_inputs)

        @self.cors_route('/account/signup/activate', DOCUMENTATION__sign_up_with_invite)
        def signup_activate(http_inputs: dict):
            return self.model.sign_up_user_with_token(http_inputs[KEY__invite_key], http_inputs[KEY__password])

        @self.cors_route('/account/signup/fetch', DOCUMENTATION__sign_up_fetch)
        def signup_fetch(http_inputs: dict):
            return self.model.fetch_signup(http_inputs[KEY__invite_key])

        @self.cors_route('/account/signup/finish', DOCUMENTATION__sign_up_finish)
        def signup_finish(http_inputs: dict):
            self.model.finish_signup(http_inputs[KEY__invite_key])

        @self.cors_route('/account/reset-password', DOCUMENTATION__reset_password)
        def reset_password(http_inputs: dict):
            return self.model.send_reset_password_email(http_inputs)

        @self.cors_route('/account/reset-password/status', DOCUMENTATION__reset_password_status)
        def reset_password_status(http_inputs: dict):
            return self.model.reset_password_status(http_inputs)

        @self.cors_route('/account/reset-password/reset', DOCUMENTATION__reset_password_with_invite)
        def reset_password_reset(http_inputs: dict):
            return self.model.reset_password_perform_reset(http_inputs)

        @self.cors_route(ENDPOINT__jaaql_emails, DOCUMENTATION__email)
        def emails(http_inputs: dict, auth_token: str, user_id: str, ip_address: str, is_public: bool, username: str):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)

            return self.model.send_email(http_inputs, auth_token, user_id, ip_address, username)

        @self.cors_route('/documents', DOCUMENTATION__document)
        def documents(http_inputs: dict, auth_token: str, ip_address: str, response: JAAQLResponse):
            if self.is_get():
                return self.model.fetch_document(http_inputs, response)
            else:
                return self.model.render_document(http_inputs, auth_token, ip_address)

        @self.cors_route('/rendered_documents', DOCUMENTATION__rendered_document)
        def documents(http_inputs: dict):
            return self.model.fetch_document_stream(http_inputs)
