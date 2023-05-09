"""
This script was generated from jaaql.fxli at 09/05/2023, 23:01:02
"""

from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement, execute_supplied_statement_singleton


# Generated keys for table 'application'
KG__application__name = "name"
KG__application__base_url = "base_url"
KG__application__artifacts_source = "artifacts_source"
KG__application__default_schema = "default_schema"
KG__application__default_s_et = "default_s_et"
KG__application__default_a_et = "default_a_et"
KG__application__default_r_et = "default_r_et"
KG__application__default_u_et = "default_u_et"
KG__application__unlock_key_validity_period = "unlock_key_validity_period"
KG__application__unlock_code_validity_period = "unlock_code_validity_period"
KG__application__is_live = "is_live"

# Generated queries for table 'application'
QG__application_delete = "DELETE FROM application WHERE name = :name"
QG__application_insert = """
    INSERT INTO application (name, base_url, artifacts_source,
        default_schema, default_s_et, default_a_et,
        default_r_et, default_u_et)
    VALUES (:name, :base_url, :artifacts_source,
        :default_schema, :default_s_et, :default_a_et,
        :default_r_et, :default_u_et)
    RETURNING unlock_key_validity_period, unlock_code_validity_period, is_live
"""
QG__application_select_all = "SELECT * FROM application"
QG__application_select = "SELECT * FROM application WHERE name = :name"
QG__application_update = """
    UPDATE
        application
    SET
        base_url = COALESCE(:base_url, base_url),
        artifacts_source = COALESCE(:artifacts_source, artifacts_source),
        default_schema = COALESCE(:default_schema, default_schema),
        default_s_et = COALESCE(:default_s_et, default_s_et),
        default_a_et = COALESCE(:default_a_et, default_a_et),
        default_r_et = COALESCE(:default_r_et, default_r_et),
        default_u_et = COALESCE(:default_u_et, default_u_et),
        unlock_key_validity_period = COALESCE(:unlock_key_validity_period, unlock_key_validity_period),
        unlock_code_validity_period = COALESCE(:unlock_code_validity_period, unlock_code_validity_period),
        is_live = COALESCE(:is_live, is_live)
    WHERE
        name = :name
"""


# Generated methods for table 'application'
def application__delete(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__application_delete,
        {
            # Key Fields
            KG__application__name: name
        }
    )


def application__update(
    connection: DBInterface,
    name,
    base_url=None, artifacts_source=None, default_schema=None,
    default_s_et=None, default_a_et=None, default_r_et=None,
    default_u_et=None, unlock_key_validity_period=None, unlock_code_validity_period=None,
    is_live=None
):
    execute_supplied_statement(
        connection, QG__application_update,
        {
            # Key Fields
            KG__application__name: name,

            # None Key Fields
            KG__application__base_url: base_url,
            KG__application__artifacts_source: artifacts_source,
            KG__application__default_schema: default_schema,
            KG__application__default_s_et: default_s_et,
            KG__application__default_a_et: default_a_et,
            KG__application__default_r_et: default_r_et,
            KG__application__default_u_et: default_u_et,
            KG__application__unlock_key_validity_period: unlock_key_validity_period,
            KG__application__unlock_code_validity_period: unlock_code_validity_period,
            KG__application__is_live: is_live
        }
    )


def application__select(
    connection: DBInterface,
    name,
    singleton_code: int = None, singleton_message: str = "application does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__application_select, 
        {
            # Key Fields
            KG__application__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def application__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__application_select_all,
        as_objects=True
    )


def application__insert(
    connection: DBInterface,
    name, base_url,
    artifacts_source=None, default_schema=None, default_s_et=None,
    default_a_et=None, default_r_et=None, default_u_et=None
):
    return execute_supplied_statement_singleton(
        connection, QG__application_insert,
        {
            KG__application__name: name,
            KG__application__base_url: base_url,
            KG__application__artifacts_source: artifacts_source,
            KG__application__default_schema: default_schema,
            KG__application__default_s_et: default_s_et,
            KG__application__default_a_et: default_a_et,
            KG__application__default_r_et: default_r_et,
            KG__application__default_u_et: default_u_et
        }, as_objects=True
    )


# Generated keys for table 'application_schema'
KG__application_schema__application = "application"
KG__application_schema__name = "name"
KG__application_schema__database = "database"

# Generated queries for table 'application_schema'
QG__application_schema_delete = "DELETE FROM application_schema WHERE application = :application AND name = :name"
QG__application_schema_insert = """
    INSERT INTO application_schema (application, name, database)
    VALUES (:application, :name, :database)
"""
QG__application_schema_select_all = "SELECT * FROM application_schema"
QG__application_schema_select = "SELECT * FROM application_schema WHERE application = :application AND name = :name"
QG__application_schema_update = """
    UPDATE
        application_schema
    SET
        database = COALESCE(:database, database)
    WHERE
        application = :application AND name = :name
"""


# Generated methods for table 'application_schema'
def application_schema__delete(
    connection: DBInterface,
    application, name
):
    execute_supplied_statement(
        connection, QG__application_schema_delete,
        {
            # Key Fields
            KG__application_schema__application: application,
            KG__application_schema__name: name
        }
    )


def application_schema__update(
    connection: DBInterface,
    application, name,
    database=None
):
    execute_supplied_statement(
        connection, QG__application_schema_update,
        {
            # Key Fields
            KG__application_schema__application: application,
            KG__application_schema__name: name,

            # None Key Fields
            KG__application_schema__database: database
        }
    )


def application_schema__select(
    connection: DBInterface,
    application, name,
    singleton_code: int = None, singleton_message: str = "application_schema does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__application_schema_select, 
        {
            # Key Fields
            KG__application_schema__application: application,
            KG__application_schema__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def application_schema__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__application_schema_select_all,
        as_objects=True
    )


def application_schema__insert(
    connection: DBInterface,
    application, name, database
):
    execute_supplied_statement(
        connection, QG__application_schema_insert,
        {
            KG__application_schema__application: application,
            KG__application_schema__name: name,
            KG__application_schema__database: database
        }
    )


# Generated keys for table 'email_dispatcher'
KG__email_dispatcher__application = "application"
KG__email_dispatcher__name = "name"
KG__email_dispatcher__display_name = "display_name"
KG__email_dispatcher__protocol = "protocol"
KG__email_dispatcher__url = "url"
KG__email_dispatcher__port = "port"
KG__email_dispatcher__username = "username"
KG__email_dispatcher__password = "password"
KG__email_dispatcher__whitelist = "whitelist"

# Generated queries for table 'email_dispatcher'
QG__email_dispatcher_delete = "DELETE FROM email_dispatcher WHERE application = :application AND name = :name"
QG__email_dispatcher_insert = """
    INSERT INTO email_dispatcher (application, name, display_name,
        protocol, url, port,
        username, password, whitelist)
    VALUES (:application, :name, :display_name,
        :protocol, :url, :port,
        :username, :password, :whitelist)
"""
QG__email_dispatcher_select_all = "SELECT * FROM email_dispatcher"
QG__email_dispatcher_select = "SELECT * FROM email_dispatcher WHERE application = :application AND name = :name"
QG__email_dispatcher_update = """
    UPDATE
        email_dispatcher
    SET
        display_name = COALESCE(:display_name, display_name),
        protocol = COALESCE(:protocol, protocol),
        url = COALESCE(:url, url),
        port = COALESCE(:port, port),
        username = COALESCE(:username, username),
        password = COALESCE(:password, password),
        whitelist = COALESCE(:whitelist, whitelist)
    WHERE
        application = :application AND name = :name
"""


# Generated methods for table 'email_dispatcher'
def email_dispatcher__delete(
    connection: DBInterface,
    application, name
):
    execute_supplied_statement(
        connection, QG__email_dispatcher_delete,
        {
            # Key Fields
            KG__email_dispatcher__application: application,
            KG__email_dispatcher__name: name
        }
    )


def email_dispatcher__update(
    connection: DBInterface, encryption_key: bytes,
    application, name,
    display_name=None, protocol=None, url=None,
    port=None, username=None, password=None,
    whitelist=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__email_dispatcher_update,
        {
            # Key Fields
            KG__email_dispatcher__application: application,
            KG__email_dispatcher__name: name,

            # None Key Fields
            KG__email_dispatcher__display_name: display_name,
            KG__email_dispatcher__protocol: protocol,
            KG__email_dispatcher__url: url,
            KG__email_dispatcher__port: port,
            KG__email_dispatcher__username: username,
            KG__email_dispatcher__password: password,
            KG__email_dispatcher__whitelist: whitelist
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__email_dispatcher__password
        ]
    )


def email_dispatcher__select(
    connection: DBInterface, encryption_key: bytes,
    application, name,
    singleton_code: int = None, singleton_message: str = "email_dispatcher does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__email_dispatcher_select, 
        {
            # Key Fields
            KG__email_dispatcher__application: application,
            KG__email_dispatcher__name: name
        }, encryption_key=encryption_key, decrypt_columns=[
            KG__email_dispatcher__password
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def email_dispatcher__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__email_dispatcher_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__email_dispatcher__password
        ],
        as_objects=True
    )


def email_dispatcher__insert(
    connection: DBInterface, encryption_key: bytes,
    application, name, display_name,
    protocol=None, url=None, port=None,
    username=None, password=None, whitelist=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__email_dispatcher_insert,
        {
            KG__email_dispatcher__application: application,
            KG__email_dispatcher__name: name,
            KG__email_dispatcher__display_name: display_name,
            KG__email_dispatcher__protocol: protocol,
            KG__email_dispatcher__url: url,
            KG__email_dispatcher__port: port,
            KG__email_dispatcher__username: username,
            KG__email_dispatcher__password: password,
            KG__email_dispatcher__whitelist: whitelist
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__email_dispatcher__password
        ]
    )


# Generated keys for table 'jaaql'
KG__jaaql__the_anonymous_user = "the_anonymous_user"
KG__jaaql__security_event_attempt_limit = "security_event_attempt_limit"

# Generated queries for table 'jaaql'
QG__jaaql_delete = "DELETE FROM jaaql"
QG__jaaql_insert = """
    INSERT INTO jaaql (the_anonymous_user, security_event_attempt_limit)
    VALUES (:the_anonymous_user, :security_event_attempt_limit)
"""
QG__jaaql_select_all = "SELECT * FROM jaaql"
QG__jaaql_select = "SELECT * FROM jaaql"
QG__jaaql_update = """
    UPDATE
        jaaql
    SET
        the_anonymous_user = COALESCE(:the_anonymous_user, the_anonymous_user),
        security_event_attempt_limit = COALESCE(:security_event_attempt_limit, security_event_attempt_limit)
"""


# Generated methods for table 'jaaql'
def jaaql__delete(
    connection: DBInterface
):
    execute_supplied_statement(
        connection, QG__jaaql_delete)


def jaaql__update(
    connection: DBInterface,
    the_anonymous_user=None, security_event_attempt_limit=None
):
    execute_supplied_statement(
        connection, QG__jaaql_update,
        {
            # None Key Fields
            KG__jaaql__the_anonymous_user: the_anonymous_user,
            KG__jaaql__security_event_attempt_limit: security_event_attempt_limit
        }
    )


def jaaql__select(
    connection: DBInterface,
    singleton_code: int = None, singleton_message: str = "jaaql does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__jaaql_select,
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def jaaql__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__jaaql_select_all,
        as_objects=True
    )


def jaaql__insert(
    connection: DBInterface,
    the_anonymous_user, security_event_attempt_limit
):
    execute_supplied_statement(
        connection, QG__jaaql_insert,
        {
            KG__jaaql__the_anonymous_user: the_anonymous_user,
            KG__jaaql__security_event_attempt_limit: security_event_attempt_limit
        }
    )


# Generated keys for table 'email_template'
KG__email_template__application = "application"
KG__email_template__dispatcher = "dispatcher"
KG__email_template__name = "name"
KG__email_template__type = "type"
KG__email_template__content_url = "content_url"
KG__email_template__validation_schema = "validation_schema"
KG__email_template__data_validation_table = "data_validation_table"
KG__email_template__data_validation_view = "data_validation_view"
KG__email_template__dispatcher_domain_recipient = "dispatcher_domain_recipient"
KG__email_template__can_be_sent_anonymously = "can_be_sent_anonymously"

# Generated queries for table 'email_template'
QG__email_template_delete = "DELETE FROM email_template WHERE application = :application AND name = :name"
QG__email_template_insert = """
    INSERT INTO email_template (application, dispatcher, name,
        type, content_url, validation_schema,
        data_validation_table, data_validation_view, dispatcher_domain_recipient,
        can_be_sent_anonymously)
    VALUES (:application, :dispatcher, :name,
        :type, :content_url, :validation_schema,
        :data_validation_table, :data_validation_view, :dispatcher_domain_recipient,
        :can_be_sent_anonymously)
"""
QG__email_template_select_all = "SELECT * FROM email_template"
QG__email_template_select = "SELECT * FROM email_template WHERE application = :application AND name = :name"
QG__email_template_update = """
    UPDATE
        email_template
    SET
        dispatcher = COALESCE(:dispatcher, dispatcher),
        type = COALESCE(:type, type),
        content_url = COALESCE(:content_url, content_url),
        validation_schema = COALESCE(:validation_schema, validation_schema),
        data_validation_table = COALESCE(:data_validation_table, data_validation_table),
        data_validation_view = COALESCE(:data_validation_view, data_validation_view),
        dispatcher_domain_recipient = COALESCE(:dispatcher_domain_recipient, dispatcher_domain_recipient),
        can_be_sent_anonymously = COALESCE(:can_be_sent_anonymously, can_be_sent_anonymously)
    WHERE
        application = :application AND name = :name
"""


# Generated methods for table 'email_template'
def email_template__delete(
    connection: DBInterface,
    application, name
):
    execute_supplied_statement(
        connection, QG__email_template_delete,
        {
            # Key Fields
            KG__email_template__application: application,
            KG__email_template__name: name
        }
    )


def email_template__update(
    connection: DBInterface,
    application, name,
    dispatcher=None, type=None, content_url=None,
    validation_schema=None, data_validation_table=None, data_validation_view=None,
    dispatcher_domain_recipient=None, can_be_sent_anonymously=None
):
    execute_supplied_statement(
        connection, QG__email_template_update,
        {
            # Key Fields
            KG__email_template__application: application,
            KG__email_template__name: name,

            # None Key Fields
            KG__email_template__dispatcher: dispatcher,
            KG__email_template__type: type,
            KG__email_template__content_url: content_url,
            KG__email_template__validation_schema: validation_schema,
            KG__email_template__data_validation_table: data_validation_table,
            KG__email_template__data_validation_view: data_validation_view,
            KG__email_template__dispatcher_domain_recipient: dispatcher_domain_recipient,
            KG__email_template__can_be_sent_anonymously: can_be_sent_anonymously
        }
    )


def email_template__select(
    connection: DBInterface,
    application, name,
    singleton_code: int = None, singleton_message: str = "email_template does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__email_template_select, 
        {
            # Key Fields
            KG__email_template__application: application,
            KG__email_template__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def email_template__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__email_template_select_all,
        as_objects=True
    )


def email_template__insert(
    connection: DBInterface,
    application, dispatcher, name,
    type, content_url,
    validation_schema=None, data_validation_table=None, data_validation_view=None,
    dispatcher_domain_recipient=None, can_be_sent_anonymously=None
):
    execute_supplied_statement(
        connection, QG__email_template_insert,
        {
            KG__email_template__application: application,
            KG__email_template__dispatcher: dispatcher,
            KG__email_template__name: name,
            KG__email_template__type: type,
            KG__email_template__content_url: content_url,
            KG__email_template__validation_schema: validation_schema,
            KG__email_template__data_validation_table: data_validation_table,
            KG__email_template__data_validation_view: data_validation_view,
            KG__email_template__dispatcher_domain_recipient: dispatcher_domain_recipient,
            KG__email_template__can_be_sent_anonymously: can_be_sent_anonymously
        }
    )


# Generated keys for table 'document_template'
KG__document_template__application = "application"
KG__document_template__name = "name"
KG__document_template__content_path = "content_path"
KG__document_template__email_template = "email_template"

# Generated queries for table 'document_template'
QG__document_template_delete = "DELETE FROM document_template WHERE application = :application AND name = :name"
QG__document_template_insert = """
    INSERT INTO document_template (application, name, content_path,
        email_template)
    VALUES (:application, :name, :content_path,
        :email_template)
"""
QG__document_template_select_all = "SELECT * FROM document_template"
QG__document_template_select = "SELECT * FROM document_template WHERE application = :application AND name = :name"
QG__document_template_update = """
    UPDATE
        document_template
    SET
        content_path = COALESCE(:content_path, content_path),
        email_template = COALESCE(:email_template, email_template)
    WHERE
        application = :application AND name = :name
"""


# Generated methods for table 'document_template'
def document_template__delete(
    connection: DBInterface,
    application, name
):
    execute_supplied_statement(
        connection, QG__document_template_delete,
        {
            # Key Fields
            KG__document_template__application: application,
            KG__document_template__name: name
        }
    )


def document_template__update(
    connection: DBInterface,
    application, name,
    content_path=None, email_template=None
):
    execute_supplied_statement(
        connection, QG__document_template_update,
        {
            # Key Fields
            KG__document_template__application: application,
            KG__document_template__name: name,

            # None Key Fields
            KG__document_template__content_path: content_path,
            KG__document_template__email_template: email_template
        }
    )


def document_template__select(
    connection: DBInterface,
    application, name,
    singleton_code: int = None, singleton_message: str = "document_template does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__document_template_select, 
        {
            # Key Fields
            KG__document_template__application: application,
            KG__document_template__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def document_template__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__document_template_select_all,
        as_objects=True
    )


def document_template__insert(
    connection: DBInterface,
    application, name, content_path,
    email_template=None
):
    execute_supplied_statement(
        connection, QG__document_template_insert,
        {
            KG__document_template__application: application,
            KG__document_template__name: name,
            KG__document_template__content_path: content_path,
            KG__document_template__email_template: email_template
        }
    )


# Generated keys for table 'document_request'
KG__document_request__application = "application"
KG__document_request__template = "template"
KG__document_request__uuid = "uuid"
KG__document_request__request_timestamp = "request_timestamp"
KG__document_request__encrypted_access_token = "encrypted_access_token"
KG__document_request__encrypted_parameters = "encrypted_parameters"
KG__document_request__render_timestamp = "render_timestamp"

# Generated queries for table 'document_request'
QG__document_request_delete = "DELETE FROM document_request WHERE uuid = :uuid"
QG__document_request_insert = """
    INSERT INTO document_request (application, template, uuid,
        encrypted_access_token, encrypted_parameters, render_timestamp)
    VALUES (:application, :template, :uuid,
        :encrypted_access_token, :encrypted_parameters, :render_timestamp)
    RETURNING request_timestamp
"""
QG__document_request_select_all = "SELECT * FROM document_request"
QG__document_request_select = "SELECT * FROM document_request WHERE uuid = :uuid"
QG__document_request_update = """
    UPDATE
        document_request
    SET
        application = COALESCE(:application, application),
        template = COALESCE(:template, template),
        request_timestamp = COALESCE(:request_timestamp, request_timestamp),
        encrypted_access_token = COALESCE(:encrypted_access_token, encrypted_access_token),
        encrypted_parameters = COALESCE(:encrypted_parameters, encrypted_parameters),
        render_timestamp = COALESCE(:render_timestamp, render_timestamp)
    WHERE
        uuid = :uuid
"""


# Generated methods for table 'document_request'
def document_request__delete(
    connection: DBInterface,
    uuid
):
    execute_supplied_statement(
        connection, QG__document_request_delete,
        {
            # Key Fields
            KG__document_request__uuid: uuid
        }
    )


def document_request__update(
    connection: DBInterface, encryption_key: bytes,
    uuid,
    application=None, template=None, request_timestamp=None,
    encrypted_access_token=None, encrypted_parameters=None, render_timestamp=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__document_request_update,
        {
            # Key Fields
            KG__document_request__uuid: uuid,

            # None Key Fields
            KG__document_request__application: application,
            KG__document_request__template: template,
            KG__document_request__request_timestamp: request_timestamp,
            KG__document_request__encrypted_access_token: encrypted_access_token,
            KG__document_request__encrypted_parameters: encrypted_parameters,
            KG__document_request__render_timestamp: render_timestamp
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__document_request__encrypted_access_token,
            KG__document_request__encrypted_parameters
        ]
    )


def document_request__select(
    connection: DBInterface, encryption_key: bytes,
    uuid,
    singleton_code: int = None, singleton_message: str = "document_request does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__document_request_select, 
        {
            # Key Fields
            KG__document_request__uuid: uuid
        }, encryption_key=encryption_key, decrypt_columns=[
            KG__document_request__encrypted_access_token,
            KG__document_request__encrypted_parameters
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def document_request__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__document_request_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__document_request__encrypted_access_token,
            KG__document_request__encrypted_parameters
        ],
        as_objects=True
    )


def document_request__insert(
    connection: DBInterface, encryption_key: bytes,
    application, template, uuid,
    encrypted_access_token,
    encrypted_parameters=None, render_timestamp=None,
    encryption_salts=None
):
    return execute_supplied_statement_singleton(
        connection, QG__document_request_insert,
        {
            KG__document_request__application: application,
            KG__document_request__template: template,
            KG__document_request__uuid: uuid,
            KG__document_request__encrypted_access_token: encrypted_access_token,
            KG__document_request__encrypted_parameters: encrypted_parameters,
            KG__document_request__render_timestamp: render_timestamp
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__document_request__encrypted_access_token,
            KG__document_request__encrypted_parameters
        ], as_objects=True
    )


# Generated keys for table 'account'
KG__account__id = "id"
KG__account__username = "username"
KG__account__deletion_timestamp = "deletion_timestamp"
KG__account__most_recent_password = "most_recent_password"

# Generated queries for table 'account'
QG__account_delete = "DELETE FROM account WHERE id = :id"
QG__account_insert = """
    INSERT INTO account (id, username, deletion_timestamp,
        most_recent_password)
    VALUES (:id, :username, :deletion_timestamp,
        :most_recent_password)
"""
QG__account_select_all = "SELECT * FROM account"
QG__account_select = "SELECT * FROM account WHERE id = :id"
QG__account_update = """
    UPDATE
        account
    SET
        username = COALESCE(:username, username),
        deletion_timestamp = COALESCE(:deletion_timestamp, deletion_timestamp),
        most_recent_password = COALESCE(:most_recent_password, most_recent_password)
    WHERE
        id = :id
"""


# Generated methods for table 'account'
def account__delete(
    connection: DBInterface,
    id
):
    execute_supplied_statement(
        connection, QG__account_delete,
        {
            # Key Fields
            KG__account__id: id
        }
    )


def account__update(
    connection: DBInterface, encryption_key: bytes,
    id,
    username=None, deletion_timestamp=None, most_recent_password=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__account_update,
        {
            # Key Fields
            KG__account__id: id,

            # None Key Fields
            KG__account__username: username,
            KG__account__deletion_timestamp: deletion_timestamp,
            KG__account__most_recent_password: most_recent_password
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__account__username
        ]
    )


def account__select(
    connection: DBInterface, encryption_key: bytes,
    id,
    singleton_code: int = None, singleton_message: str = "account does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__account_select, 
        {
            # Key Fields
            KG__account__id: id
        }, encryption_key=encryption_key, decrypt_columns=[
            KG__account__username
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def account__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__account_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__account__username
        ],
        as_objects=True
    )


def account__insert(
    connection: DBInterface, encryption_key: bytes,
    id, username,
    deletion_timestamp=None, most_recent_password=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__account_insert,
        {
            KG__account__id: id,
            KG__account__username: username,
            KG__account__deletion_timestamp: deletion_timestamp,
            KG__account__most_recent_password: most_recent_password
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__account__username
        ]
    )


# Generated keys for table 'account_password'
KG__account_password__account = "account"
KG__account_password__uuid = "uuid"
KG__account_password__hash = "hash"
KG__account_password__creation_timestamp = "creation_timestamp"

# Generated queries for table 'account_password'
QG__account_password_delete = "DELETE FROM account_password WHERE uuid = :uuid"
QG__account_password_insert = """
    INSERT INTO account_password (account, hash)
    VALUES (:account, :hash)
    RETURNING uuid, creation_timestamp
"""
QG__account_password_select_all = "SELECT * FROM account_password"
QG__account_password_select = "SELECT * FROM account_password WHERE uuid = :uuid"
QG__account_password_update = """
    UPDATE
        account_password
    SET
        account = COALESCE(:account, account),
        hash = COALESCE(:hash, hash),
        creation_timestamp = COALESCE(:creation_timestamp, creation_timestamp)
    WHERE
        uuid = :uuid
"""


# Generated methods for table 'account_password'
def account_password__delete(
    connection: DBInterface,
    uuid
):
    execute_supplied_statement(
        connection, QG__account_password_delete,
        {
            # Key Fields
            KG__account_password__uuid: uuid
        }
    )


def account_password__update(
    connection: DBInterface, encryption_key: bytes,
    uuid,
    account=None, hash=None, creation_timestamp=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__account_password_update,
        {
            # Key Fields
            KG__account_password__uuid: uuid,

            # None Key Fields
            KG__account_password__account: account,
            KG__account_password__hash: hash,
            KG__account_password__creation_timestamp: creation_timestamp
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__account_password__hash
        ]
    )


def account_password__select(
    connection: DBInterface, encryption_key: bytes,
    uuid,
    singleton_code: int = None, singleton_message: str = "account_password does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__account_password_select, 
        {
            # Key Fields
            KG__account_password__uuid: uuid
        }, encryption_key=encryption_key, decrypt_columns=[
            KG__account_password__hash
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def account_password__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__account_password_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__account_password__hash
        ],
        as_objects=True
    )


def account_password__insert(
    connection: DBInterface, encryption_key: bytes,
    account, hash,
    encryption_salts=None
):
    return execute_supplied_statement_singleton(
        connection, QG__account_password_insert,
        {
            KG__account_password__account: account,
            KG__account_password__hash: hash
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__account_password__hash
        ], as_objects=True
    )


# Generated keys for table 'validated_ip_address'
KG__validated_ip_address__account = "account"
KG__validated_ip_address__uuid = "uuid"
KG__validated_ip_address__encrypted_salted_ip_address = "encrypted_salted_ip_address"
KG__validated_ip_address__first_authentication_timestamp = "first_authentication_timestamp"
KG__validated_ip_address__last_authentication_timestamp = "last_authentication_timestamp"

# Generated queries for table 'validated_ip_address'
QG__validated_ip_address_delete = "DELETE FROM validated_ip_address WHERE uuid = :uuid"
QG__validated_ip_address_insert = """
    INSERT INTO validated_ip_address (account, encrypted_salted_ip_address, last_authentication_timestamp)
    VALUES (:account, :encrypted_salted_ip_address, :last_authentication_timestamp)
    RETURNING uuid, first_authentication_timestamp
"""
QG__validated_ip_address_select_all = "SELECT * FROM validated_ip_address"
QG__validated_ip_address_select = "SELECT * FROM validated_ip_address WHERE uuid = :uuid"
QG__validated_ip_address_update = """
    UPDATE
        validated_ip_address
    SET
        account = COALESCE(:account, account),
        encrypted_salted_ip_address = COALESCE(:encrypted_salted_ip_address, encrypted_salted_ip_address),
        first_authentication_timestamp = COALESCE(:first_authentication_timestamp, first_authentication_timestamp),
        last_authentication_timestamp = COALESCE(:last_authentication_timestamp, last_authentication_timestamp)
    WHERE
        uuid = :uuid
"""


# Generated methods for table 'validated_ip_address'
def validated_ip_address__delete(
    connection: DBInterface,
    uuid
):
    execute_supplied_statement(
        connection, QG__validated_ip_address_delete,
        {
            # Key Fields
            KG__validated_ip_address__uuid: uuid
        }
    )


def validated_ip_address__update(
    connection: DBInterface, encryption_key: bytes,
    uuid,
    account=None, encrypted_salted_ip_address=None, first_authentication_timestamp=None,
    last_authentication_timestamp=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__validated_ip_address_update,
        {
            # Key Fields
            KG__validated_ip_address__uuid: uuid,

            # None Key Fields
            KG__validated_ip_address__account: account,
            KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address,
            KG__validated_ip_address__first_authentication_timestamp: first_authentication_timestamp,
            KG__validated_ip_address__last_authentication_timestamp: last_authentication_timestamp
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__validated_ip_address__encrypted_salted_ip_address
        ]
    )


def validated_ip_address__select(
    connection: DBInterface, encryption_key: bytes,
    uuid,
    singleton_code: int = None, singleton_message: str = "validated_ip_address does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__validated_ip_address_select, 
        {
            # Key Fields
            KG__validated_ip_address__uuid: uuid
        }, encryption_key=encryption_key, decrypt_columns=[
            KG__validated_ip_address__encrypted_salted_ip_address
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def validated_ip_address__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__validated_ip_address_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__validated_ip_address__encrypted_salted_ip_address
        ],
        as_objects=True
    )


def validated_ip_address__insert(
    connection: DBInterface, encryption_key: bytes,
    account, encrypted_salted_ip_address, last_authentication_timestamp,
    encryption_salts=None
):
    return execute_supplied_statement_singleton(
        connection, QG__validated_ip_address_insert,
        {
            KG__validated_ip_address__account: account,
            KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address,
            KG__validated_ip_address__last_authentication_timestamp: last_authentication_timestamp
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__validated_ip_address__encrypted_salted_ip_address
        ], as_objects=True
    )


# Generated keys for table 'security_event'
KG__security_event__application = "application"
KG__security_event__event_lock = "event_lock"
KG__security_event__creation_timestamp = "creation_timestamp"
KG__security_event__wrong_key_attempt_count = "wrong_key_attempt_count"
KG__security_event__email_template = "email_template"
KG__security_event__account = "account"
KG__security_event__unlock_key = "unlock_key"
KG__security_event__unlock_code = "unlock_code"
KG__security_event__unlock_timestamp = "unlock_timestamp"

# Generated queries for table 'security_event'
QG__security_event_delete = "DELETE FROM security_event WHERE application = :application AND event_lock = :event_lock"
QG__security_event_insert = """
    INSERT INTO security_event (application, email_template, account,
        unlock_code, unlock_timestamp)
    VALUES (:application, :email_template, :account,
        :unlock_code, :unlock_timestamp)
    RETURNING event_lock, creation_timestamp, wrong_key_attempt_count,
        unlock_key
"""
QG__security_event_select_all = "SELECT * FROM security_event"
QG__security_event_select = "SELECT * FROM security_event WHERE application = :application AND event_lock = :event_lock"
QG__security_event_update = """
    UPDATE
        security_event
    SET
        creation_timestamp = COALESCE(:creation_timestamp, creation_timestamp),
        wrong_key_attempt_count = COALESCE(:wrong_key_attempt_count, wrong_key_attempt_count),
        email_template = COALESCE(:email_template, email_template),
        account = COALESCE(:account, account),
        unlock_key = COALESCE(:unlock_key, unlock_key),
        unlock_code = COALESCE(:unlock_code, unlock_code),
        unlock_timestamp = COALESCE(:unlock_timestamp, unlock_timestamp)
    WHERE
        application = :application AND event_lock = :event_lock
"""


# Generated methods for table 'security_event'
def security_event__delete(
    connection: DBInterface,
    application, event_lock
):
    execute_supplied_statement(
        connection, QG__security_event_delete,
        {
            # Key Fields
            KG__security_event__application: application,
            KG__security_event__event_lock: event_lock
        }
    )


def security_event__update(
    connection: DBInterface,
    application, event_lock,
    creation_timestamp=None, wrong_key_attempt_count=None, email_template=None,
    account=None, unlock_key=None, unlock_code=None,
    unlock_timestamp=None
):
    execute_supplied_statement(
        connection, QG__security_event_update,
        {
            # Key Fields
            KG__security_event__application: application,
            KG__security_event__event_lock: event_lock,

            # None Key Fields
            KG__security_event__creation_timestamp: creation_timestamp,
            KG__security_event__wrong_key_attempt_count: wrong_key_attempt_count,
            KG__security_event__email_template: email_template,
            KG__security_event__account: account,
            KG__security_event__unlock_key: unlock_key,
            KG__security_event__unlock_code: unlock_code,
            KG__security_event__unlock_timestamp: unlock_timestamp
        }
    )


def security_event__select(
    connection: DBInterface,
    application, event_lock,
    singleton_code: int = None, singleton_message: str = "security_event does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__security_event_select, 
        {
            # Key Fields
            KG__security_event__application: application,
            KG__security_event__event_lock: event_lock
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def security_event__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__security_event_select_all,
        as_objects=True
    )


def security_event__insert(
    connection: DBInterface,
    application, email_template, account,
    unlock_code,
    unlock_timestamp=None
):
    return execute_supplied_statement_singleton(
        connection, QG__security_event_insert,
        {
            KG__security_event__application: application,
            KG__security_event__email_template: email_template,
            KG__security_event__account: account,
            KG__security_event__unlock_code: unlock_code,
            KG__security_event__unlock_timestamp: unlock_timestamp
        }, as_objects=True
    )
