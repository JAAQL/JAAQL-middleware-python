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

        @self.cors_route(ENDPOINT__refresh, DOCUMENTATION__oauth_refresh)
        def refresh_oauth_token(auth_token_for_refresh: str, ip_address: str):
            return self.model.refresh_auth_token(auth_token_for_refresh, ip_address)

        @self.cors_route(ENDPOINT__install, DOCUMENTATION__install)
        def install(http_inputs: dict):
            return self.model.install(**http_inputs)

        @self.cors_route(ENDPOINT__execute_migrations, DOCUMENTATION__migrations)
        def execute_migrations(connection: DBInterface):
            return self.model.execute_migrations(connection)

        @self.cors_route('/internal/is_installed', DOCUMENTATION__is_installed)
        def is_installed(response: JAAQLResponse):
            return self.model.is_installed(response)

        @self.cors_route(ENDPOINT__is_alive, DOCUMENTATION__is_alive)
        def is_alive():
            self.model.is_alive()

        @self.cors_route('/accounts', DOCUMENTATION__create_account)
        def accounts(connection: DBInterface, http_inputs: dict):
            self.model.create_account_with_potential_password(connection, **http_inputs)

        @self.cors_route('/prepare', DOCUMENTATION__prepare)
        def prepare(connection: DBInterface, account_id: str, http_inputs: dict):
            raise HttpStatusException("Not yet implemented", HTTPStatus.NOT_IMPLEMENTED)
            # self.model.prepare_queries(connection, account_id, http_inputs)

        @self.cors_route('/account/password', DOCUMENTATION__password)
        def password(account_id: str, username: str, ip_address: str, http_inputs: dict):
            return self.model.add_my_account_password(account_id, username, ip_address, **http_inputs)

        @self.cors_route('/submit', DOCUMENTATION__submit)
        def submit(http_inputs: dict, account_id: str, verification_hook: queue.Queue):
            return self.model.submit(http_inputs, account_id, verification_hook=verification_hook)

        @self.cors_route('/internal/clean', DOCUMENTATION__clean)
        def clean(connection: DBInterface):
            self.model.clean(connection)

        @self.cors_route('/internal/dispatchers', DOCUMENTATION__dispatchers)
        def dispatchers(connection: DBInterface, http_inputs: dict):
            self.model.attach_dispatcher_credentials(connection, http_inputs)

        @self.cors_route('/sign-up', DOCUMENTATION__sign_up)
        def sign_up(http_inputs: dict):
            return self.model.sign_up(http_inputs)

        @self.cors_route('/account/reset-password', DOCUMENTATION__reset_password)
        def reset_password(http_inputs: dict):
            return self.model.reset_password(http_inputs)

        @self.cors_route('/security-event', DOCUMENTATION__security_event)
        def security_event(http_inputs: dict, ip_address: str):
            if self.is_post():
                return self.model.check_security_event_key_and_security_event_is_unlocked(http_inputs)
            else:
                return self.model.finish_security_event(http_inputs, ip_address)