from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.base_controller import BaseJAAQLController, ERR__expected_argument, ERR__unexpected_argument
from jaaql.documentation.documentation_internal import *
from jaaql.documentation.documentation_public import *
from jaaql.documentation.documentation_shared import *
from jaaql.mvc.response import JAAQLResponse
from jaaql.db.db_interface import DBInterface


class JAAQLController(BaseJAAQLController):

    def __init__(self, model: JAAQLModel):
        super().__init__(model)

    def create_app(self):

        @self.cors_route('/oauth/token', DOCUMENTATION__oauth_token)
        def fetch_oauth_token(http_inputs: dict, ip_address: str, user_agent: str, response: JAAQLResponse):
            if self.model.use_mfa and KEY__mfa_key not in http_inputs:
                raise HttpStatusException(ERR__expected_argument % KEY__mfa_key, HTTPStatus.BAD_REQUEST)
            elif not self.model.use_mfa and http_inputs.get(KEY__mfa_key, None) is not None:
                raise HttpStatusException(ERR__unexpected_argument % KEY__mfa_key, HTTPStatus.BAD_REQUEST)
            elif not self.model.use_mfa:
                http_inputs[KEY__mfa_key] = None
            return self.model.authenticate(**http_inputs, ip_address=ip_address, user_agent=user_agent,
                                           response=response)

        @self.cors_route('/redeploy', DOCUMENTATION__deploy)
        def redeploy():
            return self.model.redeploy()

        @self.cors_route(ENDPOINT__refresh, DOCUMENTATION__oauth_refresh)
        def refresh_oauth_token(oauth_token: str):
            return self.model.refresh(oauth_token)

        @self.cors_route('/internal/install', DOCUMENTATION__install)
        def install(http_inputs: dict, ip_address: str, user_agent: str, response: JAAQLResponse):
            return self.model.install(**http_inputs, ip_address=ip_address, user_agent=user_agent, response=response)

        @self.cors_route('/internal/applications', DOCUMENTATION__applications)
        def applications(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_applications(http_inputs, jaaql_connection)
            elif self.is_put():
                self.model.update_application(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application(http_inputs, jaaql_connection)

        @self.cors_route('/internal/applications/confirm-deletion', DOCUMENTATION__applications_confirm_deletion)
        def confirm_application_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/databases', DOCUMENTATION__databases)
        def databases(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                return self.model.add_database(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_databases(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_database(http_inputs, jaaql_connection)

        @self.cors_route('/internal/databases/confirm-deletion', DOCUMENTATION__databases_confirm_deletion)
        def confirm_database_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_database_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/application-parameters', DOCUMENTATION__application_parameters)
        def application_parameters(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application_parameter(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_application_parameters(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application_parameter(http_inputs, jaaql_connection)

        @self.cors_route('/internal/application-parameters/confirm-deletion',
                         DOCUMENTATION__application_parameters_confirm_deletion)
        def confirm_application_parameter_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_parameter_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/application-configurations', DOCUMENTATION__application_configurations)
        def application_configurations(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application_configuration(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_application_configurations(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application_configuration(http_inputs, jaaql_connection)

        @self.cors_route('/internal/application-configurations/confirm-deletion',
                         DOCUMENTATION__application_configurations_confirm_deletion)
        def confirm_application_configuration_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_configuration_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/application-arguments', DOCUMENTATION__application_arguments)
        def application_arguments(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application_argument(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_application_arguments(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application_argument(http_inputs, jaaql_connection)

        @self.cors_route('/internal/application-arguments/confirm-deletion',
                         DOCUMENTATION__application_arguments_confirm_deletion)
        def confirm_application_argument_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_argument_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/authorization/application', DOCUMENTATION__authorization_application)
        def application_authorization(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application_authorization(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_application_authorizations(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application_authorization(http_inputs, jaaql_connection)

        @self.cors_route('/internal/authorization/application/confirm-deletion',
                         DOCUMENTATION__authorization_application_confirm_deletion)
        def confirm_application_authorization_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_authorization_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/authorization/database', DOCUMENTATION__authorization_database)
        def database_authorization(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_database_authorization(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_database_authorizations(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_database_authorization(http_inputs, jaaql_connection)

        @self.cors_route('/internal/authorization/database/confirm-deletion',
                         DOCUMENTATION__authorization_database_confirm_deletion)
        def confirm_database_authorization_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_database_authorization_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/users/invite', DOCUMENTATION__user_invite)
        def user_invite(http_inputs: dict):
            return self.model.user_invite(http_inputs)

        @self.cors_route('/account/signup', DOCUMENTATION__sign_up)
        def signup(http_inputs: dict, response: JAAQLResponse, user_agent: str, ip_address: str):
            return self.model.signup(http_inputs, response, user_agent, ip_address)

        @self.cors_route('/account/logs', DOCUMENTATION__my_logs)
        def fetch_logs(http_inputs: dict, jaaql_connection: DBInterface):
            return self.model.my_logs(http_inputs, jaaql_connection)

        @self.cors_route('/account/addresses', DOCUMENTATION__my_ips)
        def fetch_addresses(http_inputs: dict, jaaql_connection: DBInterface):
            return self.model.my_ips(http_inputs, jaaql_connection)

        @self.cors_route('/account/password', DOCUMENTATION__password)
        def change_password(http_inputs: dict, totp_iv: str, oauth_token: str, password_hash: str, user_id: str,
                            last_totp: str, jaaql_connection: DBInterface):
            return self.model.change_password(http_inputs, totp_iv, oauth_token, password_hash, user_id,
                                              last_totp, jaaql_connection)

        @self.cors_route('/account/close', DOCUMENTATION__account_close)
        def close_account(http_inputs: dict, totp_iv: str, password_hash: str, user_id: str,
                          last_totp: str):
            return self.model.close_account(http_inputs, totp_iv, password_hash, user_id, last_totp)

        @self.cors_route('/account/confirm-close', DOCUMENTATION__account_close_confirm)
        def close_account_confirm(http_inputs: dict, user_id: str):
            return self.model.close_account_confirm(http_inputs, user_id)

        @self.cors_route('/configurations', DOCUMENTATION__my_configs)
        def my_configs(jaaql_connection: DBInterface):
            return self.model.my_configs(jaaql_connection)

        @self.cors_route('/configurations/databases', DOCUMENTATION__config_databases)
        def config_databases(http_inputs: dict, jaaql_connection: DBInterface, user_id: str):
            return self.model.config_databases(http_inputs, jaaql_connection, user_id)

        @self.cors_route('/submit', DOCUMENTATION__submit)
        def submit(http_inputs: dict, jaaql_connection: DBInterface):
            return self.model.submit(http_inputs, jaaql_connection)
