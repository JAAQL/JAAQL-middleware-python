from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.base_controller import BaseJAAQLController, ERR__unexpected_argument, ERR__expected_argument
from jaaql.documentation.documentation_internal import *
from jaaql.documentation.documentation_public import *
from jaaql.documentation.documentation_shared import *
from jaaql.mvc.response import JAAQLResponse
from jaaql.db.db_interface import DBInterface


class JAAQLController(BaseJAAQLController):

    def __init__(self, model: JAAQLModel, is_prod: bool, base_url: str, do_profiling: bool = False):
        super().__init__(model, is_prod, base_url, do_profiling)

    def create_app(self):

        @self.cors_route('/oauth/token', DOCUMENTATION__oauth_token)
        def fetch_oauth_token(sql_inputs: dict, ip_address: str, response: JAAQLResponse):
            if KEY__pre_auth_key in sql_inputs:
                if KEY__username in sql_inputs or KEY__password in sql_inputs:
                    rep_var = KEY__username if KEY__username in sql_inputs else KEY__password
                    raise HttpStatusException(ERR__unexpected_argument % rep_var, HTTPStatus.BAD_REQUEST)
                if KEY__mfa_key not in sql_inputs:
                    raise HttpStatusException(ERR__expected_argument % KEY__mfa_key, HTTPStatus.BAD_REQUEST)
                return self.model.authenticate_with_mfa_key(sql_inputs[KEY__pre_auth_key], sql_inputs[KEY__mfa_key],
                                                            ip_address, response)
            else:
                if KEY__username not in sql_inputs or KEY__password not in sql_inputs:
                    rep_var = KEY__username if KEY__username in sql_inputs else KEY__password
                    raise HttpStatusException(ERR__expected_argument % rep_var, HTTPStatus.BAD_REQUEST)
                if KEY__mfa_key in sql_inputs:
                    raise HttpStatusException(ERR__unexpected_argument % KEY__mfa_key, HTTPStatus.BAD_REQUEST)
                return self.model.authenticate(username=sql_inputs[KEY__username], password=sql_inputs[KEY__password],
                                               ip_address=ip_address, response=response)

        @self.cors_route('/internal/redeploy', DOCUMENTATION__deploy)
        def redeploy():
            return self.model.redeploy()

        @self.cors_route(ENDPOINT__refresh, DOCUMENTATION__oauth_refresh)
        def refresh_oauth_token(oauth_token: str):
            return self.model.refresh(oauth_token)

        @self.cors_route(ENDPOINT__install, DOCUMENTATION__install)
        def install(http_inputs: dict, ip_address: str, response: JAAQLResponse):
            return self.model.install(**http_inputs, ip_address=ip_address, response=response)

        @self.cors_route('/internal/uninstall', DOCUMENTATION__uninstall)
        def uninstall(http_inputs: dict):
            self.model.uninstall(**http_inputs)

        @self.cors_route('/internal/is_installed', DOCUMENTATION__is_installed)
        def is_installed(response: JAAQLResponse):
            return self.model.is_installed(response)

        @self.cors_route(ENDPOINT__internal_applications, DOCUMENTATION__applications)
        def applications(http_inputs: dict, jaaql_connection: DBInterface, ip_address: str, user_id: str, response: JAAQLResponse):
            if self.is_get():
                return self.model.get_applications(http_inputs, jaaql_connection)
            elif self.is_post():
                self.model.add_application(http_inputs, jaaql_connection, ip_address, user_id, response)
            elif self.is_put():
                self.model.update_application(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application(http_inputs)

        @self.cors_route('/applications', DOCUMENTATION__my_applications)
        def public_applications(jaaql_connection: DBInterface):
            return self.model.get_my_applications(jaaql_connection)

        @self.cors_route('/applications/public-user', DOCUMENTATION__applications_public_user_credentials)
        def application_public_user_credentials(http_inputs: dict):
            return self.model.get_public_user_credentials_for_application(http_inputs[KEY__application])

        @self.cors_route('/applications/default-templates', DOCUMENTATION__applications_default_email_templates)
        def application_public_user_credentials(http_inputs: dict):
            return self.model.get_default_templates_for_application(http_inputs[KEY__application])

        @self.cors_route('/internal/applications/confirm-deletion', DOCUMENTATION__applications_confirm_deletion)
        def confirm_application_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/databases', DOCUMENTATION__databases)
        def databases(http_inputs: dict, jaaql_connection: DBInterface, user_id: str):
            if self.is_post():
                self.model.add_database(http_inputs, jaaql_connection, user_id)
            elif self.is_get():
                return self.model.get_databases(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_database(http_inputs)

        @self.cors_route('/internal/databases/confirm-deletion', DOCUMENTATION__databases_confirm_deletion)
        def confirm_database_deletion(http_inputs: dict, user_id: int, jaaql_connection: DBInterface):
            self.model.delete_database_confirm(http_inputs, user_id, jaaql_connection)

        @self.cors_route('/internal/nodes', DOCUMENTATION__nodes)
        def nodes(sql_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_node(sql_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_nodes(sql_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_node(sql_inputs)

        @self.cors_route('/internal/nodes/confirm-deletion', DOCUMENTATION__nodes_confirm_deletion)
        def confirm_node_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_node_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/applications/datasets', DOCUMENTATION__application_datasets)
        def application_datasets(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application_dataset(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_application_datasets(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application_dataset(http_inputs)

        @self.cors_route('/internal/applications/datasets/confirm-deletion', DOCUMENTATION__application_datasets_confirm_deletion)
        def confirm_application_dataset_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_dataset_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/applications/configurations', DOCUMENTATION__application_configurations)
        def application_configurations(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_application_configuration(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_application_configurations(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_application_configuration(http_inputs)

        @self.cors_route('/internal/applications/configurations/confirm-deletion', DOCUMENTATION__application_configurations_confirm_deletion)
        def confirm_application_configuration_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_application_configuration_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/applications/configurations/assigned-databases', DOCUMENTATION__assigned_databases)
        def assigned_databases(sql_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_database_assignment(sql_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_assigned_databases(sql_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.remove_database_assignment(sql_inputs)

        @self.cors_route('/internal/applications/configurations/assigned-databases/confirm-deletion',
                         DOCUMENTATION__database_assignment_confirm_deletion)
        def confirm_remove_database_assignment(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.remove_database_assignment_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/nodes/credentials', DOCUMENTATION__authorization_node)
        def node_authorization(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_node_authorization(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_node_authorizations(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_node_authorization(http_inputs)

        @self.cors_route('/internal/nodes/credentials/confirm-deletion', DOCUMENTATION__authorization_node_confirm_deletion)
        def confirm_node_authorization_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_node_authorization_confirm(http_inputs, jaaql_connection)

        @self.cors_route(ENDPOINT__configuration_authorizations, DOCUMENTATION__authorization_configuration)
        def node_authorization(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_configuration_authorization(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.get_configuration_authorizations(http_inputs, jaaql_connection)
            else:  # self.is_delete()
                return self.model.delete_configuration_authorization(http_inputs)

        @self.cors_route('/internal/authorizations/configurations/confirm-deletion', DOCUMENTATION__authorization_configuration_confirm_deletion)
        def confirm_node_authorization_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_configuration_authorization_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/users', DOCUMENTATION__users)
        def users(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.create_user(jaaql_connection, http_inputs[KEY__email])
            elif self.is_put():
                return self.model.user_invite_and_check(http_inputs, jaaql_connection)
            elif self.is_get():
                raise NotImplementedError()  # TODO
            else:
                return self.model.revoke_user(http_inputs)

        @self.cors_route('/internal/users/make-public', DOCUMENTATION__user_make_public)
        def user_make_public(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.make_user_public(http_inputs, jaaql_connection)

        @self.cors_route('/internal/users/confirm-deletion', DOCUMENTATION__users_confirm_revoke)
        def revoke_user_confirm(http_inputs: dict, jaaql_connection: DBInterface, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.revoke_user_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/internal/users/default-roles', DOCUMENTATION__user_default_roles)
        def default_roles(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_get():
                return self.model.fetch_user_default_roles(http_inputs, jaaql_connection)
            elif self.is_post():
                return self.model.add_user_default_role(http_inputs, jaaql_connection)
            elif self.is_delete():
                return self.model.delete_user_default_role(http_inputs)

        @self.cors_route('/internal/users/default-roles/confirm-deletion', DOCUMENTATION__user_default_roles_confirm_deletion)
        def confirm_default_role_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_user_default_role_confirm(http_inputs, jaaql_connection)

        @self.cors_route(ENDPOINT__internal_accounts, DOCUMENTATION__email_accounts)
        def email_accounts(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.add_email_account(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.fetch_email_accounts(http_inputs, jaaql_connection)
            else:
                return self.model.delete_email_account(http_inputs, jaaql_connection)

        @self.cors_route('/internal/emails/accounts/confirm-deletion', DOCUMENTATION__email_accounts_confirm_deletion)
        def email_accounts_confirm_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.delete_email_account_confirm(http_inputs, jaaql_connection)

        @self.cors_route(ENDPOINT__internal_templates, DOCUMENTATION__email_templates)
        def email_templates(http_inputs: dict, jaaql_connection: DBInterface):
            if self.is_post():
                self.model.register_email_template(http_inputs, jaaql_connection)
            elif self.is_get():
                return self.model.fetch_email_templates(http_inputs, jaaql_connection)
            else:
                return self.model.unregister_email_template(http_inputs, jaaql_connection)

        @self.cors_route('/internal/emails/templates/confirm-deletion', DOCUMENTATION__email_template_confirm_deletion)
        def email_templates_confirm_deletion(http_inputs: dict, jaaql_connection: DBInterface):
            self.model.unregister_email_template_confirm(http_inputs, jaaql_connection)

        @self.cors_route('/account/info', DOCUMENTATION__my_account_info)
        def account_info(username: str, totp_iv: str):
            return self.model.fetch_account_info(username, totp_iv)

        @self.cors_route('/account/mfa', DOCUMENTATION__account_mfa)
        def mfa(http_inputs: dict, user_id: str, totp_iv: str, last_totp: str, password_hash: str, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.enable_disable_mfa(http_inputs, user_id, totp_iv, last_totp, password_hash)

        @self.cors_route('/account/signup/request', DOCUMENTATION__sign_up_request_invite)
        def signup_request(http_inputs: dict):
            return self.model.request_signup(http_inputs)

        @self.cors_route('/account/signup/status', DOCUMENTATION__sign_up_status)
        def signup_request(http_inputs: dict):
            return self.model.signup_status(http_inputs)

        @self.cors_route('/account/signup/activate', DOCUMENTATION__sign_up_with_invite)
        def signup_activate(http_inputs: dict, ip_address: str, response: JAAQLResponse):
            return self.model.sign_up_user_with_token(http_inputs[KEY__invite_key], http_inputs[KEY__password], ip_address, response)

        @self.cors_route('/account/signup/fetch', DOCUMENTATION__sign_up_fetch)
        def signup_fetch(http_inputs: dict):
            return self.model.fetch_signup(http_inputs[KEY__invite_key])

        @self.cors_route('/account/signup/finish', DOCUMENTATION__sign_up_finish)
        def signup_finish(http_inputs: dict):
            self.model.finish_signup(http_inputs[KEY__invite_key])

        @self.cors_route('/account/logs', DOCUMENTATION__my_logs)
        def fetch_logs(http_inputs: dict, jaaql_connection: DBInterface, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.my_logs(http_inputs, jaaql_connection)

        @self.cors_route('/account/addresses', DOCUMENTATION__my_ips)
        def fetch_addresses(http_inputs: dict, jaaql_connection: DBInterface, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.my_ips(http_inputs, jaaql_connection)

        @self.cors_route('/account/password', DOCUMENTATION__password)
        def change_password(http_inputs: dict, totp_iv: str, oauth_token: str, password_hash: str, user_id: str, last_totp: str,
                            jaaql_connection: DBInterface, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.change_password(http_inputs, totp_iv, oauth_token, password_hash, user_id, last_totp, jaaql_connection)

        @self.cors_route('/account/reset-password', DOCUMENTATION__reset_password)
        def reset_password(http_inputs: dict):
            return self.model.send_reset_password_email(http_inputs)

        @self.cors_route('/account/reset-password/status', DOCUMENTATION__reset_password_status)
        def reset_password_status(http_inputs: dict):
            return self.model.reset_password_status(http_inputs)

        @self.cors_route('/account/reset-password/reset', DOCUMENTATION__reset_password_with_invite)
        def reset_password_reset(http_inputs: dict):
            return self.model.reset_password_perform_reset(http_inputs)

        @self.cors_route('/account/close', DOCUMENTATION__account_close)
        def close_account(http_inputs: dict, totp_iv: str, password_hash: str, user_id: str, last_totp: str, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.close_account(http_inputs, totp_iv, password_hash, user_id, last_totp)

        @self.cors_route('/account/confirm-close', DOCUMENTATION__account_close_confirm)
        def close_account_confirm(http_inputs: dict, user_id: str):
            return self.model.close_account_confirm(http_inputs, user_id)

        @self.cors_route('/configurations', DOCUMENTATION__my_configs)
        def my_configs(jaaql_connection: DBInterface, http_inputs: dict):
            return self.model.my_configs(jaaql_connection, http_inputs)

        @self.cors_route('/configurations/assigned-databases', DOCUMENTATION__config_assigned_databases)
        def config_assigned_databases(http_inputs: dict, jaaql_connection: DBInterface, user_id: str):
            return self.model.config_assigned_databases(http_inputs, jaaql_connection, user_id)

        @self.cors_route('/configurations/assigned-databases/roles', DOCUMENTATION__assigned_database_roles)
        def connection_roles(http_inputs: dict, jaaql_connection: DBInterface):
            return self.model.config_assigned_database_roles(http_inputs, jaaql_connection)

        @self.cors_route('/submit', DOCUMENTATION__submit)
        def submit(http_inputs: dict, jaaql_connection: DBInterface):
            return self.model.submit(http_inputs, jaaql_connection)

        @self.cors_route('/submit-file', DOCUMENTATION__submit_file)
        def submit_file(http_inputs: dict, jaaql_connection: DBInterface):
            return self.model.submit(http_inputs, jaaql_connection, True)

        @self.cors_route('/emails/allowed_recipients', DOCUMENTATION__email_allowed_recipients)
        def emails_allowed_recipients(inputs: dict, username: str):
            return self.model.fetch_allowed_recipients_for_email_template(inputs[KEY__email_template], username)

        @self.cors_route(ENDPOINT__jaaql_emails, DOCUMENTATION__email)
        def emails(http_inputs: dict, jaaql_connection: DBInterface, username: str, is_public: bool, oauth_token: str, user_id: str):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            if self.is_get():
                return self.model.fetch_user_email_history(http_inputs, jaaql_connection)
            else:
                return self.model.send_email(http_inputs, username, oauth_token, user_id)

        @self.cors_route('/emails/history', DOCUMENTATION__email_history)
        def emails_history(http_inputs: dict, user_id: str, is_public: bool):
            if is_public:
                raise HttpStatusException(ERR__user_public, HTTPStatus.UNAUTHORIZED)
            return self.model.fetch_user_singular_email_history(http_inputs[KEY__id], user_id)

        @self.cors_route('/documents', DOCUMENTATION__document)
        def documents(http_inputs: dict, oauth_token: str, response: JAAQLResponse):
            if self.is_get():
                return self.model.fetch_document(http_inputs, response)
            else:
                return self.model.render_document(http_inputs, oauth_token)

        @self.cors_route('/rendered_documents', DOCUMENTATION__rendered_document)
        def documents(http_inputs: dict):
            return self.model.fetch_document_stream(http_inputs)

        @self.cors_route(ENDPOINT__is_alive, DOCUMENTATION__is_alive)
        def is_alive():
            self.model.is_alive()