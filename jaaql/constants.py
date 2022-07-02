KEY__id = "id"
KEY__last_totp = "last_totp"
KEY__attachment_name = "name"
KEY__application = "application"
KEY__application_description = "application_description"
KEY__configuration = "configuration"
KEY__configuration_name = "name"
KEY__configuration_description = "configuration_description"
KEY__exception = "exception"
KEY__data_validation_view = "data_validation_view"
KEY__allow_uninstall = "allow_uninstall"
KEY__uninstall_key = "uninstall_key"
KEY__install_key = "install_key"
KEY__deletion_key = "deletion_key"
KEY__render_as = "render_as"
KEY__url = "url"
KEY__superjaaql_password = "superjaaql_password"
KEY__public_username = "public_username"
KEY__records_total = "records_total"
KEY__records_filtered = "records_filtered"
KEY__data = "data"
KEY__db_url = "db_url"
KEY__precedence = "precedence"
KEY__roles = "roles"
KEY__pre_auth_key = "pre_auth_key"
KEY__email = "email"
KEY__sort = "sort"
KEY__invite_key = "invite_key"
KEY__invite_or_poll_key = "invite_or_poll_key"
KEY__invite_poll_key = "invite_poll_key"
KEY__invite_code = "invite_code"
KEY__invite_key_status = "invite_key_status"
KEY__reset_key = "reset_key"
KEY__reset_or_poll_key = "reset_or_poll_key"
KEY__reset_poll_key = "reset_poll_key"
KEY__reset_code = "reset_code"
KEY__reset_key_status = "reset_key_status"
KEY__parameters = "parameters"
KEY__oauth_token = "oauth_token"
KEY__template = "template"
KEY__create_file = "create_file"
KEY__subject = "subject"
KEY__recipient = "recipient"
KEY__completed = "completed"
KEY__filename = "filename"
KEY__content = "content"
KEY__attachments = "attachments"
KEY__app_relative_path = "app_relative_path"
KEY__sender = "sender"
KEY__search = "search"
KEY__application_name = "name"
KEY__db_super_user_password = "db_super_user_password"
KEY__dataset = "dataset"
KEY__dataset_name = "name"
KEY__dataset_description = "dataset_description"
KEY__size = "size"
KEY__database = "database"
KEY__node_name = "name"
KEY__authorization = "authorization"
KEY__argument = "argument"
KEY__is_node = "is_node"
KEY__application_new_url = "new_url"
KEY__connection = "connection"
KEY__node = "node"
KEY__application_url = "url"
KEY__key = "key"
KEY__role = "role"
KEY__mfa_key = "mfa_key"
KEY__mfa_enabled = "mfa_enabled"
KEY__username = "username"
KEY__password = "password"
KEY__default_database = "default_database"
KEY__new_password = "new_password"
KEY__new_password_confirm = "new_password_confirm"
KEY__page = "page"
KEY__use_mfa = "use_mfa"
KEY__show_deleted = "show_deleted"
KEY__description = "description"
KEY__database_name = "name"
KEY__create = "create"
KEY__drop = "drop"
KEY__force_transactional = "force_transactional"
KEY__port = "port"
KEY__address = "address"
KEY__jaaql_name = "jaaql_name"
KEY__otp_uri = "otp_uri"
KEY__otp_qr = "otp_qr"
KEY__jaaql_otp_uri = "jaaql_otp_uri"
KEY__jaaql_otp_qr = "jaaql_otp_qr"
KEY__superjaaql_otp_uri = "superjaaql_otp_uri"
KEY__superjaaql_otp_qr = "superjaaql_otp_qr"
KEY__is_public = "is_public"
KEY__account = "account"
KEY__encrypted_password = "encrypted_password"
KEY__email_template_name = "name"
KEY__column_name = "column_name"
KEY__table_name = "table_name"
KEY__is_primary = "is_primary"
KEY__data_validation_table = "data_validation_table"
KEY__recipient_validation_view = "recipient_validation_view"
KEY__email_template = "template"
KEY__do_send_signup_email = "do_send_signup_email"
KEY__allow_confirm_signup_attempt = "allow_confirm_signup_attempt"
KEY__allow_reset_password = "allow_reset_password"
KEY__already_signed_up_email_template = "existing_user_template"
KEY__allow_signup = "allow_signup"
KEY__email_account_name = "name"
KEY__email_sent = "sent"
KEY__body = "body"
KEY__default_email_signup_template = "default_email_signup_template"
KEY__default_email_already_signed_up_template = "default_email_already_signed_up_template"
KEY__default_reset_password_template = "default_reset_password_template"
KEY__document_id = "document_id"
KEY__as_attachment = "as_attachment"
KEY__email_account_protocol = "protocol"
KEY__email_account_host = "host"
KEY__email_account_port = "port"
KEY__email_account_username = "username"
KEY__email_account_send_name = "send_name"

ATTR__deleted = "deleted"

HEADER__security = "Authentication-Token"
HEADER__security_bypass = "Authentication-Token-Bypass"

SQL__where = "WHERE"
SQL__order_by = "ORDER BY"
SQL__limit = "LIMIT"
SQL__offset = "OFFSET"
SQL__asc = "ASC"
SQL__desc = "DESC"
SQL__and = "AND"
SQL__or = "OR"
SQL__like = "LIKE"
SQL__eq = "="
SQL__paren_open = "("
SQL__paren_close = ")"
SQL__single_quote = "'"
SQL__double_quote = '"'
SQL__lower = "lower"
SQL__varchar_cast = "::varchar"
SQL__is_null = "is null"

SEPARATOR__comma_space = ", "
SEPARATOR__comma = ","
SEPARATOR__space = " "

JAAQL__arg_marker = ":"

DIR__config = "config"
DIR__www = "www"
DIR__render_template = "rendered_documents"

FILE__config = "config.ini"

ENCODING__utf = "UTF-8"
ENCODING__ascii = "ascii"
EXAMPLE__jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.e30.yXvILkvUUCBqAFlAv6wQ1Q-QRAjfe3eSosO949U73Vo"

VAULT_KEY__db_crypt_key = "db_crypt_key"
VAULT_KEY__db_repeatable_salt = "repeatable_salt"
VAULT_KEY__jaaql_local_access_key = "jaaql_access_key"
VAULT_KEY__jaaql_lookup_connection = "jaaql_lookup_connection"
VAULT_KEY__allow_jaaql_uninstall = "Allow jaaql uninstall"

ENVIRON__vault_key = "JAAQL_VAULT_PASSWORD"
ENVIRON__email_credentials = "JAAQL_EMAIL_CREDENTIALS"
ENVIRON__install_path = "INSTALL_PATH"
ENVIRON__sentinel_url = "SENTINEL_URL"

EMAIL_PARAM__signup_key = "JAAQL_INVITE_KEY"
EMAIL_PARAM__invite_code = "JAAQL_INVITE_SHORT_CODE"

EMAIL_PARAM__reset_key = "JAAQL_RESET_KEY"
EMAIL_PARAM__reset_code = "JAAQL_RESET_SHORT_CODE"

CONFIG_KEY__server = "SERVER"
CONFIG_KEY_SERVER__port = "port"

JWT_PURPOSE__oauth = "oauth"
JWT_PURPOSE__pre_auth = "pre_auth"
JWT_PURPOSE__connection = "connection"

ERR__not_yet_installed = "JAAQL has not yet been installed!"
ERR__user_public = "Cannot perform this action on a public user!"
ERR__too_many_signup_attempts = "Too many signup attempts"
ERR__too_many_reset_requests = "Too many reset requests"
ERR__too_many_code_attempts = "Code disabled due to too many incorrect attempts. Please use the link in the email"
ERR__document_still_rendering = "Document still rendering"
ERR__document_id_not_found = "Document id not found"

PG_ENV__password = "POSTGRES_PASSWORD"

HTML__base64_png = "data:image/png;base64,"
FORMAT__png = "png"

NODE__host_node = "host"
DB__jaaql = "jaaql"
DB__postgres = "postgres"

PORT__ems = 6061

ENDPOINT__reload_accounts = "/reload-accounts"
ENDPOINT__send_email = "/send-email"
ENDPOINT__internal_applications = "/internal/applications"
ENDPOINT__internal_templates = "/internal/emails/templates"
ENDPOINT__internal_accounts = "/internal/emails/accounts"
ENDPOINT__is_alive = "/internal/is-alive"
ENDPOINT__jaaql_emails = "/emails"
ENDPOINT__report_sentinel_error = "/sentinel/reporting/error"

VERSION = "3.0.11"

HTTP_STATUS__too_early = 425  # Shiv for python 3.8

USERNAME__jaaql = "jaaql"
