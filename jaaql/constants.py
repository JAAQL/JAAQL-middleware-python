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

KEY__username = "username"
KEY__password = "password"
KEY__attach_as = "attach_as"
KEY__ip_address = "ip_address"
KEY__created = "created"
KEY__ip_id = "ip_id"
KEY__application = "application"
KEY__schema = "schema"
KEY__database = "database"
KEY__role = "role"
KEY__read_only = "read_only"
KEY__install_key = "install_key"
KEY__jaaql_password = "jaaql_password"
KEY__super_db_password = "super_db_password"
KEY__old_password = "old_password"
KEY__position = "position"
KEY__file = "file"
KEY__error = "error"
KEY__error_row_number = "row_number"
KEY__error_index = "index"
KEY__error_query = "query"
KEY__error_set = "set"
KEY__allow_uninstall = "allow_uninstall"

SEPARATOR__comma_space = ", "
SEPARATOR__comma = ","
SEPARATOR__space = " "

JAAQL__arg_marker = ":"

DIR__config = "config"
DIR__www = "www"
DIR__render_template = "rendered_documents"

FILE__config = "config.ini"
FILE__canned_queries = "canned_queries.jsql"

ENCODING__utf = "UTF-8"
ENCODING__ascii = "ascii"
EXAMPLE__jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.e30.yXvILkvUUCBqAFlAv6wQ1Q-QRAjfe3eSosO949U73Vo"

VAULT_KEY__db_crypt_key = "db_crypt_key"
VAULT_KEY__db_repeatable_salt = "repeatable_salt"
VAULT_KEY__jaaql_local_access_key = "jaaql_access_key"
VAULT_KEY__super_db_credentials = "super_db_credentials"
VAULT_KEY__jaaql_lookup_connection = "jaaql_lookup_connection"
VAULT_KEY__allow_jaaql_uninstall = "Allow jaaql uninstall"
VAULT_KEY__jaaql_db_password = "Jaaql DB Password"

# Used for re-installation
VAULT_KEY__db_connection_string = "db_connection_string"
VAULT_KEY__jaaql_password = "jaaql_password"
VAULT_KEY__super_db_password = "super_db_password"

ENVIRON__vault_key = "JAAQL_VAULT_PASSWORD"
ENVIRON__local_install = "JAAQL_LOCAL_INSTALL"
ENVIRON__jaaql_profiling = "JAAQL_PROFILING"
ENVIRON__email_accounts = "JAAQL_EMAIL_ACCOUNTS"
ENVIRON__install_path = "INSTALL_PATH"
ENVIRON__sentinel_url = "SENTINEL_URL"
ENVIRON__canned_queries = "CANNED_QUERIES"

EMAIL_PARAM__signup_key = "JAAQL_INVITE_KEY"
EMAIL_PARAM__invite_code = "JAAQL_INVITE_SHORT_CODE"
EMAIL_PARAM__app_url = "APP_URL"

EMAIL_PARAM__reset_key = "JAAQL_RESET_KEY"
EMAIL_PARAM__reset_code = "JAAQL_RESET_SHORT_CODE"

CONFIG_KEY__server = "SERVER"
CONFIG_KEY_SERVER__port = "port"

JWT_PURPOSE__oauth = "oauth"
JWT_PURPOSE__pre_auth = "pre_auth"
JWT_PURPOSE__connection = "connection"

ERR__invalid_token = "Invalid token!"
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
ENDPOINT__install = "/internal/install"

CONFIG__default = "Default config"
CONFIG__default_desc = "Default config description"
DATASET__default = "Default dataset"
DATASET__default_desc = "Default dataset description"

USERNAME__jaaql = "jaaql"
USERNAME__super_db = "super_db"
USERNAME__anonymous = "anonymous"
PASSWORD__anonymous = "jaaql_public_password"
ROLE__jaaql = "jaaql"
ROLE__postgres = "postgres"

PROTOCOL__postgres = "postgresql://"

VERSION = "4.5.1"

