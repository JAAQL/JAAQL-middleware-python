import os
import re
import socket

# Do not delete this as it's being used elsewhere
from jaaql.generated_constants import *

KEY__username = "username"
KEY__password = "password"
KEY__remember_me = "remember_me"
KEY__attach_as = "attach_as"
KEY__ip_address = "ip_address"
KEY__created = "created"
KEY__ip_id = "ip_id"
KEY__application = "application"
KEY__debugging_account_id = "debugging_account_id"
KEY__schema = "schema"
KEY__database = "database"
KEY__role = "role"
KEY__read_only = "read_only"
KEY__prevent_unused_parameters = "prevent_unused_parameters"
KEY__timelines = "timelines"
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
KEY__sign_up_template = "sign_up"
KEY__template = "template"
KEY__already_signed_up_template = "already_signed_up"
KEY__reset_password_template = "reset_password"
KEY__unregistered_user_reset_password_template = "unregistered_user_reset_password"
KEY__parameters = "parameters"
KEY__query = "query"
KEY__security_key = "security_key"
KEY__id = "id"
KEY__oauth_token = "oauth_token"
KEY__accounts = "accounts"
KEY__registered = "registered"
KEY__restrictions = "restrictions"
KEY__command = "command"
KEY__args = "args"
KEY__document_id = "document_id"
KEY__as_attachment = "as_attachment"
KEY__create_file = "create_file"
KEY__attachment_name = "name"
KEY__filename = "filename"
KEY__completed = "completed"
KEY__content = "content"
KEY__render_as = "render_as"

CRON_minute = "minute"
CRON_hour = "hour"
CRON_dayOfMonth = "dayOfMonth"
CRON_month = "month"
CRON_dayOfWeek = "dayOfWeek"

REGEX__dmbs_object_name = r'^[0-9a-zA-Z_]{1,63}$'
REGEX__dmbs_procedure_name = r'^[0-9a-zA-Z_$-.\+]{1,63}$'
# An explicit type is spliced into the SQL after '::', so it must be a type name as FIESTA writes one and nothing more (use
# fullmatch): a realm name, or a Postgres datatype with an optional modifier, such as integer, numeric(4,2) or character varying(64)
REGEX__dmbs_type_name = r'(?:[A-Za-z_][A-Za-z0-9_]{0,62}|character varying)(?:\(\d{1,8}(?:,\d{1,8})?\))?'

# The optional request key KEY__timelines ({"<timeline>": "<ISO-8601 moment>" | null}) sets, for the request's transaction
# only, the moment each timeline is viewed at. A moment becomes the transaction-local setting GUC__timeline_prefix + name,
# which the generated timeline views read as nullif(current_setting('timeline.<name>', true), ''); the prefix must match the
# DBMS package. Names are lower-cased before they are checked (setting names are case-insensitive). The patterns are for
# re.fullmatch
GUC__timeline_prefix = "timeline."
TIMELINES__max_count = 16
TIMELINE__max_moment_length = 64
REGEX__timeline_name = r'^[a-z_][a-z0-9_]{0,62}$'
REGEX__timeline_moment = r'^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])([T ]([01][0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9](\.[0-9]{1,6})?)?(Z|[+-](0[0-9]|1[0-5]):[0-5][0-9])?)?$'

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

ENVIRON__JAAQL__SUPER_BYPASS_KEY = "JAAQL__SUPER_BYPASS_KEY"
ENVIRON__JAAQL__JAAQL_BYPASS_KEY = "JAAQL__JAAQL_BYPASS_KEY"

VAULT_KEY__db_crypt_key = "db_crypt_key"
VAULT_KEY__db_repeatable_salt = "repeatable_salt"
VAULT_KEY__super_local_access_key = "super_access_key"
VAULT_KEY__jaaql_local_access_key = "jaaql_access_key"
VAULT_KEY__super_db_credentials = "super_db_credentials"
VAULT_KEY__jaaql_lookup_connection = "jaaql_lookup_connection"
VAULT_KEY__allow_jaaql_uninstall = "Allow jaaql uninstall"
VAULT_KEY__jaaql_db_password = "Jaaql DB Password"
VAULT_KEY__postgres_bootstrap_password = "postgres_bootstrap_password"
VAULT_KEY__keycloak_realm_admin_secret = "keycloak_realm_admin_secret"

# Used for re-installation
VAULT_KEY__db_connection_string = "db_connection_string"
VAULT_KEY__jaaql_password = "jaaql_password"
VAULT_KEY__super_db_password = "super_db_password"

ENVIRON__vault_key = "JAAQL_VAULT_PASSWORD"
ENVIRON__local_install = "JAAQL_LOCAL_INSTALL"
ENVIRON__jaaql_profiling = "JAAQL_PROFILING"
ENVIRON__install_path = "INSTALL_PATH"
ENVIRON__sentinel_url = "SENTINEL_URL"
# The time in seconds over which a JAAQL query request (its statements and its COMMIT) is reported to Sentinel as a slow query; 0 or
# less turns slow-query reports off. Read once per process, see jaaql/utilities/slow_queries.py
ENVIRON__sentinel_slow_query_seconds = "SENTINEL_SLOW_QUERY_SECONDS"
ENVIRON__canned_queries = "CANNED_QUERIES"

SLOW_QUERY__default_seconds = 3
# A slow query is reported at most once an hour per process; its slow runs in between are counted into its next report. A query that has
# not been slow for this long is forgotten
SLOW_QUERY__repeat_seconds = 3600
# At most this many slow-query reports per process in any hour, so a database in trouble cannot push real errors out of Sentinel's list
SLOW_QUERY__max_reports_per_hour = 10
# Of those, at most this many for the queries of one account, so one login cannot spend them all
SLOW_QUERY__max_reports_per_account_per_hour = 3
# The queries a process keeps track of for the above; beyond it the one longest not slow is forgotten
SLOW_QUERY__max_tracked_queries = 1000
# A parameter whose name matches, at any depth of its value, is shown in a slow-query report as <redacted>. api_key holds a reversibly
# encrypted password; a document_id fetches its rendered document without a login
SLOW_QUERY__redacted_key = re.compile(r"pass(word|wd)|pwd|secret|token|api_?key|private_?key|credential|authori[sz]ation|document_id",
                                      re.IGNORECASE)

# Reports waiting for the per-process sender; a report that finds the queue full is dropped, never waited for
SENTINEL__queue_size = 50
SENTINEL__connect_timeout = 3.05
SENTINEL__read_timeout = 10

EMAIL_PARAM__unlock_key = "JAAQL__UNLOCK_KEY"
EMAIL_PARAM__unlock_code = "JAAQL__UNLOCK_CODE"
EMAIL_PARAM__app_url = "JAAQL__APP_URL"
EMAIL_PARAM__app_name = "JAAQL__APP_NAME"
EMAIL_PARAM__email_address = "JAAQL__EMAIL_ADDRESS"

CONFIG_KEY__server = "SERVER"
CONFIG_KEY_SERVER__port = "port"

JWT_PURPOSE__oauth = "oauth"
JWT_PURPOSE__oidc = "oidc"
JWT_PURPOSE__pre_auth = "pre_auth"
JWT_PURPOSE__connection = "connection"

SQLStateJaaql = 'JQ000'

ERR__invalid_token = "Invalid token!"
ERR__user_public = "Cannot perform this action on a public user!"
ERR__too_many_signup_attempts = "Too many signup attempts"
ERR__too_many_reset_requests = "Too many reset requests"
ERR__too_many_code_attempts = "Code disabled due to too many incorrect attempts. Please use the link in the email"
ERR__document_still_rendering = "Document still rendering"
ERR__document_id_not_found = "Document id not found"
ERR__unlock_code_expired = "The short unlock code has expired. Please use the long link found in your email"
ERR__invalid_lock = "Either security event does not exist, has already been used, has expired"
ERR__incorrect_lock_code = "Incorrect lock code"
ERR__timelines_malformed = "'timelines' must be an object mapping timeline names to moments"
ERR__timelines_too_many = "'timelines' names %d timelines, at most %d are allowed"
ERR__timeline_name_invalid = "Timeline name %s is invalid: expected a letter or underscore followed by at most 62 letters, digits or underscores"
ERR__timeline_name_repeated = "Timeline '%s' is named more than once in 'timelines' (timeline names are case-insensitive)"
ERR__timeline_moment_invalid = "Moment %s for timeline '%s' is invalid: expected null or an ISO-8601 date or date-time of at most %d characters, such as '2024-03-01', '2024-03-01T12:30:00' or '2024-03-01T12:30:00+01:00'"
ERR__timelines_with_autocommit = "'timelines' cannot be combined with 'autocommit': a moment holds for the request's transaction, which autocommit ends after every statement"

PG_ENV__password = "POSTGRES_PASSWORD"

HTML__base64_png = "data:image/png;base64,"
FORMAT__png = "png"

NODE__host_node = "host"
DB__jaaql = "jaaql"
DB__postgres = "postgres"

PORT__ems = 6061
PORT__mms = 6062
PORT__shared_var_service = 6063


def get_ipv6_address():
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('2001:db8::', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def get_ipv4_address() -> str:
    """Return the primary IPv4 address the kernel would use for an outbound
    connection.  Falls back to 127.0.0.1 if no IPv4 stack is present."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # The target doesn’t have to be reachable; we just want the
        # kernel to pick an interface and tell us which source IP
        # it would use.
        s.connect(('8.8.8.8', 1))          # 1 = arbitrary port
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


IPS__local = [
    "127.0.0.1", "localhost", "172.17.0.1", os.environ.get("SERVER_ADDRESS", "thisipcantexist"), get_ipv6_address(), "::1", get_ipv4_address()
]

ENDPOINT__send_email = "/send-email"
ENDPOINT__execute_migrations = "/internal/migrations"
ENDPOINT__internal_applications = "/internal/applications"
ENDPOINT__internal_templates = "/internal/emails/templates"
ENDPOINT__internal_accounts = "/internal/emails/accounts"
ENDPOINT__is_alive = "/internal/is-alive"
ENDPOINT__deep_health = "/internal/deep-health"

# Synthetic query the BATON microcompiler injects into every queries.json so
# deep_health() can resolve a query through the cache. Must match the microcompiler
# constant HEALTH_QUERY_CACHE_KEY (index is always 0).
QUERY_CACHE_KEY__health = "__health__"
QUERY_CACHE_REF__health = QUERY_CACHE_KEY__health + ":0"
ENDPOINT__report_sentinel_error = "/sentinel/reporting/error"
ENDPOINT__install = "/internal/install"
ENDPOINT__set_shared_var = "/set-shared-var"
ENDPOINT__get_shared_var = "/get-shared-var"
ENDPOINT__oidc_get_token = "/exchange-auth-code"

# Routes whose queries are never reported as slow. Sentinel's own ingest route first: a report of it would be a report of a report.
# The rest is deploy-time and development tooling, where slow statements are expected (/prepare type-checks every query of a build)
SLOW_QUERY__unreported_routes = frozenset({
    ENDPOINT__report_sentinel_error, ENDPOINT__install, "/internal/clean", ENDPOINT__execute_migrations, "/internal/freeze", "/internal/defrost",
    "/internal/set-web-config", "/internal/dispatchers", "/prepare", "/domains", "/procedures", "/accounts", "/accounts/batch", "/build-time"
})
# Routes whose queries are not reported as slow when the request names no application, however it logged in: jaaql-monitor posts every
# statement of a deploy script, a migration (migrate.sh), freeze, defrost and a procedure test run to /submit without one, logging in with
# a bypass key in development and with a password on a box, while BATON names its application in every request it sends
SLOW_QUERY__unreported_without_application = frozenset({"/submit"})

# Routes whose failures are never reported as server errors (jaaql/utilities/server_errors.py): Sentinel's own ingest route, so a report
# never reports itself, and the deploy-time ones
SERVER_ERROR__unreported_routes = frozenset({
    ENDPOINT__report_sentinel_error, ENDPOINT__install, "/internal/clean", ENDPOINT__execute_migrations
})
# The routes whose inputs a server-error report shows with their values: the query routes, whose SQL and parameters a slow-query report
# shows too (values included, secrets redacted). Every other route's report names its inputs only: a login's email address, an
# authorization code, a webhook's payload are never sent
SERVER_ERROR__routes_with_inputs = frozenset({"/submit", "/execute", "/call-proc"})
# The same limits as slow queries, in a budget of their own: one report per error per hour per process, its repeats counted into its next
# report; at most this many reports an hour, this many of them for one account; this many errors kept track of
SERVER_ERROR__max_reports_per_hour = 10
SERVER_ERROR__max_reports_per_account_per_hour = 3
SERVER_ERROR__max_tracked_errors = 1000
# The server faults one request notes for its report at most
SERVER_ERROR__max_faults = 5

CONFIG__default = "Default config"
CONFIG__default_desc = "Default config description"
DATASET__default = "Default dataset"
DATASET__default_desc = "Default dataset description"

TEMPLATES_DEFAULT_DIRECTORY = "Templates"

USERNAME__jaaql = "jaaql"
USERNAME__super_db = "super_db"
USERNAME__superuser = "superuser"
USERNAME__anonymous = "anonymous"
PASSWORD__anonymous = "jaaql_public_password"
ROLE__jaaql = "jaaql"
ROLE__postgres = "postgres"
ROLE__dba = "dba"

PROTOCOL__postgres = "postgresql://"

VERSION = "5.3.24"

