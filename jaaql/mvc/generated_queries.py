"""
This script was generated from build_and_run.fxls at 2025-11-06, 06:34:38
"""

from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement, execute_supplied_statement_singleton


# Generated keys for table 'application'
KG__application__name = "name"
KG__application__base_url = "base_url"
KG__application__templates_source = "templates_source"
KG__application__default_schema = "default_schema"
KG__application__unlock_key_validity_period = "unlock_key_validity_period"
KG__application__unlock_code_validity_period = "unlock_code_validity_period"
KG__application__is_live = "is_live"

# Generated queries for table 'application'
QG__application_delete = "DELETE FROM application WHERE name = :name"
QG__application_insert = """
    INSERT INTO application (name, base_url, templates_source,
        default_schema)
    VALUES (:name, :base_url, :templates_source,
        :default_schema)
    RETURNING unlock_key_validity_period, unlock_code_validity_period, is_live
"""
QG__application_select_all = "SELECT * FROM application"
QG__application_select = "SELECT * FROM application WHERE name = :name"
QG__application_update = """
    UPDATE
        application
    SET
        base_url = COALESCE(:base_url, base_url),
        templates_source = COALESCE(:templates_source, templates_source),
        default_schema = COALESCE(:default_schema, default_schema),
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
    base_url=None, templates_source=None, default_schema=None,
    unlock_key_validity_period=None, unlock_code_validity_period=None, is_live=None
):
    execute_supplied_statement(
        connection, QG__application_update,
        {
            # Key Fields
            KG__application__name: name,

            # None Key Fields
            KG__application__base_url: base_url,
            KG__application__templates_source: templates_source,
            KG__application__default_schema: default_schema,
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
    templates_source=None, default_schema=None
):
    return execute_supplied_statement_singleton(
        connection, QG__application_insert,
        {
            KG__application__name: name,
            KG__application__base_url: base_url,
            KG__application__templates_source: templates_source,
            KG__application__default_schema: default_schema
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
KG__jaaql__migration_version = "migration_version"
KG__jaaql__last_successful_build_time = "last_successful_build_time"

# Generated queries for table 'jaaql'
QG__jaaql_delete = "DELETE FROM jaaql"
QG__jaaql_insert = """
    INSERT INTO jaaql (migration_version, last_successful_build_time)
    VALUES (:migration_version, :last_successful_build_time)
"""
QG__jaaql_select_all = "SELECT * FROM jaaql"
QG__jaaql_select = "SELECT * FROM jaaql"
QG__jaaql_update = """
    UPDATE
        jaaql
    SET
        migration_version = COALESCE(:migration_version, migration_version),
        last_successful_build_time = COALESCE(:last_successful_build_time, last_successful_build_time)
"""


# Generated methods for table 'jaaql'
def jaaql__delete(
    connection: DBInterface
):
    execute_supplied_statement(
        connection, QG__jaaql_delete)


def jaaql__update(
    connection: DBInterface,
    migration_version=None, last_successful_build_time=None
):
    execute_supplied_statement(
        connection, QG__jaaql_update,
        {
            # None Key Fields
            KG__jaaql__migration_version: migration_version,
            KG__jaaql__last_successful_build_time: last_successful_build_time
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
    migration_version, last_successful_build_time
):
    execute_supplied_statement(
        connection, QG__jaaql_insert,
        {
            KG__jaaql__migration_version: migration_version,
            KG__jaaql__last_successful_build_time: last_successful_build_time
        }
    )


# Generated keys for table 'email_template'
KG__email_template__application = "application"
KG__email_template__dispatcher = "dispatcher"
KG__email_template__name = "name"
KG__email_template__content_url = "content_url"
KG__email_template__validation_schema = "validation_schema"
KG__email_template__base_relation = "base_relation"
KG__email_template__permissions_view = "permissions_view"
KG__email_template__data_view = "data_view"
KG__email_template__dispatcher_domain_recipient = "dispatcher_domain_recipient"
KG__email_template__fixed_address = "fixed_address"
KG__email_template__can_be_sent_anonymously = "can_be_sent_anonymously"

# Generated queries for table 'email_template'
QG__email_template_delete = "DELETE FROM email_template WHERE application = :application AND name = :name"
QG__email_template_insert = """
    INSERT INTO email_template (application, dispatcher, name,
        content_url, validation_schema, base_relation,
        permissions_view, data_view, dispatcher_domain_recipient,
        fixed_address, can_be_sent_anonymously)
    VALUES (:application, :dispatcher, :name,
        :content_url, :validation_schema, :base_relation,
        :permissions_view, :data_view, :dispatcher_domain_recipient,
        :fixed_address, :can_be_sent_anonymously)
"""
QG__email_template_select_all = "SELECT * FROM email_template"
QG__email_template_select = "SELECT * FROM email_template WHERE application = :application AND name = :name"
QG__email_template_update = """
    UPDATE
        email_template
    SET
        dispatcher = COALESCE(:dispatcher, dispatcher),
        content_url = COALESCE(:content_url, content_url),
        validation_schema = COALESCE(:validation_schema, validation_schema),
        base_relation = COALESCE(:base_relation, base_relation),
        permissions_view = COALESCE(:permissions_view, permissions_view),
        data_view = COALESCE(:data_view, data_view),
        dispatcher_domain_recipient = COALESCE(:dispatcher_domain_recipient, dispatcher_domain_recipient),
        fixed_address = COALESCE(:fixed_address, fixed_address),
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
    dispatcher=None, content_url=None, validation_schema=None,
    base_relation=None, permissions_view=None, data_view=None,
    dispatcher_domain_recipient=None, fixed_address=None, can_be_sent_anonymously=None
):
    execute_supplied_statement(
        connection, QG__email_template_update,
        {
            # Key Fields
            KG__email_template__application: application,
            KG__email_template__name: name,

            # None Key Fields
            KG__email_template__dispatcher: dispatcher,
            KG__email_template__content_url: content_url,
            KG__email_template__validation_schema: validation_schema,
            KG__email_template__base_relation: base_relation,
            KG__email_template__permissions_view: permissions_view,
            KG__email_template__data_view: data_view,
            KG__email_template__dispatcher_domain_recipient: dispatcher_domain_recipient,
            KG__email_template__fixed_address: fixed_address,
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
    content_url,
    validation_schema=None, base_relation=None, permissions_view=None,
    data_view=None, dispatcher_domain_recipient=None, fixed_address=None,
    can_be_sent_anonymously=None
):
    execute_supplied_statement(
        connection, QG__email_template_insert,
        {
            KG__email_template__application: application,
            KG__email_template__dispatcher: dispatcher,
            KG__email_template__name: name,
            KG__email_template__content_url: content_url,
            KG__email_template__validation_schema: validation_schema,
            KG__email_template__base_relation: base_relation,
            KG__email_template__permissions_view: permissions_view,
            KG__email_template__data_view: data_view,
            KG__email_template__dispatcher_domain_recipient: dispatcher_domain_recipient,
            KG__email_template__fixed_address: fixed_address,
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
KG__document_request__create_file = "create_file"
KG__document_request__file_name = "file_name"
KG__document_request__content = "content"
KG__document_request__completed = "completed"

# Generated queries for table 'document_request'
QG__document_request_delete = "DELETE FROM document_request WHERE uuid = :uuid"
QG__document_request_insert = """
    INSERT INTO document_request (application, template, encrypted_access_token,
        encrypted_parameters, render_timestamp, create_file,
        file_name, content, completed)
    VALUES (:application, :template, :encrypted_access_token,
        :encrypted_parameters, :render_timestamp, :create_file,
        :file_name, :content, :completed)
    RETURNING uuid, request_timestamp
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
        render_timestamp = COALESCE(:render_timestamp, render_timestamp),
        create_file = COALESCE(:create_file, create_file),
        file_name = COALESCE(:file_name, file_name),
        content = COALESCE(:content, content),
        completed = COALESCE(:completed, completed)
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
    create_file=None, file_name=None, content=None,
    completed=None,
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
            KG__document_request__render_timestamp: render_timestamp,
            KG__document_request__create_file: create_file,
            KG__document_request__file_name: file_name,
            KG__document_request__content: content,
            KG__document_request__completed: completed
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
    application, template, encrypted_access_token,
    create_file,
    encrypted_parameters=None, render_timestamp=None, file_name=None,
    content=None, completed=None,
    encryption_salts=None
):
    return execute_supplied_statement_singleton(
        connection, QG__document_request_insert,
        {
            KG__document_request__application: application,
            KG__document_request__template: template,
            KG__document_request__encrypted_access_token: encrypted_access_token,
            KG__document_request__encrypted_parameters: encrypted_parameters,
            KG__document_request__render_timestamp: render_timestamp,
            KG__document_request__create_file: create_file,
            KG__document_request__file_name: file_name,
            KG__document_request__content: content,
            KG__document_request__completed: completed
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__document_request__encrypted_access_token,
            KG__document_request__encrypted_parameters
        ], as_objects=True
    )


# Generated keys for table 'federation_procedure'
KG__federation_procedure__name = "name"

# Generated queries for table 'federation_procedure'
QG__federation_procedure_delete = "DELETE FROM federation_procedure WHERE name = :name"
QG__federation_procedure_insert = """
    INSERT INTO federation_procedure (name)
    VALUES (:name)
"""
QG__federation_procedure_select_all = "SELECT * FROM federation_procedure"
QG__federation_procedure_select = "SELECT * FROM federation_procedure WHERE name = :name"
QG__federation_procedure_update = """
    UPDATE
        federation_procedure
    SET
        
    WHERE
        name = :name
"""


# Generated methods for table 'federation_procedure'
def federation_procedure__delete(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__federation_procedure_delete,
        {
            # Key Fields
            KG__federation_procedure__name: name
        }
    )


def federation_procedure__update(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__federation_procedure_update,
        {
            # Key Fields
            KG__federation_procedure__name: name
        }
    )


def federation_procedure__select(
    connection: DBInterface,
    name,
    singleton_code: int = None, singleton_message: str = "federation_procedure does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__federation_procedure_select, 
        {
            # Key Fields
            KG__federation_procedure__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def federation_procedure__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__federation_procedure_select_all,
        as_objects=True
    )


def federation_procedure__insert(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__federation_procedure_insert,
        {
            KG__federation_procedure__name: name
        }
    )


# Generated keys for table 'federation_procedure_parameter'
KG__federation_procedure_parameter__procedure = "procedure"
KG__federation_procedure_parameter__name = "name"

# Generated queries for table 'federation_procedure_parameter'
QG__federation_procedure_parameter_delete = "DELETE FROM federation_procedure_parameter WHERE procedure = :procedure AND name = :name"
QG__federation_procedure_parameter_insert = """
    INSERT INTO federation_procedure_parameter (procedure, name)
    VALUES (:procedure, :name)
"""
QG__federation_procedure_parameter_select_all = "SELECT * FROM federation_procedure_parameter"
QG__federation_procedure_parameter_select = "SELECT * FROM federation_procedure_parameter WHERE procedure = :procedure AND name = :name"
QG__federation_procedure_parameter_update = """
    UPDATE
        federation_procedure_parameter
    SET
        
    WHERE
        procedure = :procedure AND name = :name
"""


# Generated methods for table 'federation_procedure_parameter'
def federation_procedure_parameter__delete(
    connection: DBInterface,
    procedure, name
):
    execute_supplied_statement(
        connection, QG__federation_procedure_parameter_delete,
        {
            # Key Fields
            KG__federation_procedure_parameter__procedure: procedure,
            KG__federation_procedure_parameter__name: name
        }
    )


def federation_procedure_parameter__update(
    connection: DBInterface,
    procedure, name
):
    execute_supplied_statement(
        connection, QG__federation_procedure_parameter_update,
        {
            # Key Fields
            KG__federation_procedure_parameter__procedure: procedure,
            KG__federation_procedure_parameter__name: name
        }
    )


def federation_procedure_parameter__select(
    connection: DBInterface,
    procedure, name,
    singleton_code: int = None, singleton_message: str = "federation_procedure_parameter does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__federation_procedure_parameter_select, 
        {
            # Key Fields
            KG__federation_procedure_parameter__procedure: procedure,
            KG__federation_procedure_parameter__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def federation_procedure_parameter__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__federation_procedure_parameter_select_all,
        as_objects=True
    )


def federation_procedure_parameter__insert(
    connection: DBInterface,
    procedure, name
):
    execute_supplied_statement(
        connection, QG__federation_procedure_parameter_insert,
        {
            KG__federation_procedure_parameter__procedure: procedure,
            KG__federation_procedure_parameter__name: name
        }
    )


# Generated keys for table 'identity_provider_service'
KG__identity_provider_service__name = "name"
KG__identity_provider_service__logo_url = "logo_url"
KG__identity_provider_service__requires_email_verification = "requires_email_verification"

# Generated queries for table 'identity_provider_service'
QG__identity_provider_service_delete = "DELETE FROM identity_provider_service WHERE name = :name"
QG__identity_provider_service_insert = """
    INSERT INTO identity_provider_service (name, logo_url, requires_email_verification)
    VALUES (:name, :logo_url, :requires_email_verification)
"""
QG__identity_provider_service_select_all = "SELECT * FROM identity_provider_service"
QG__identity_provider_service_select = "SELECT * FROM identity_provider_service WHERE name = :name"
QG__identity_provider_service_update = """
    UPDATE
        identity_provider_service
    SET
        logo_url = COALESCE(:logo_url, logo_url),
        requires_email_verification = COALESCE(:requires_email_verification, requires_email_verification)
    WHERE
        name = :name
"""


# Generated methods for table 'identity_provider_service'
def identity_provider_service__delete(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__identity_provider_service_delete,
        {
            # Key Fields
            KG__identity_provider_service__name: name
        }
    )


def identity_provider_service__update(
    connection: DBInterface,
    name,
    logo_url=None, requires_email_verification=None
):
    execute_supplied_statement(
        connection, QG__identity_provider_service_update,
        {
            # Key Fields
            KG__identity_provider_service__name: name,

            # None Key Fields
            KG__identity_provider_service__logo_url: logo_url,
            KG__identity_provider_service__requires_email_verification: requires_email_verification
        }
    )


def identity_provider_service__select(
    connection: DBInterface,
    name,
    singleton_code: int = None, singleton_message: str = "identity_provider_service does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__identity_provider_service_select, 
        {
            # Key Fields
            KG__identity_provider_service__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def identity_provider_service__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__identity_provider_service_select_all,
        as_objects=True
    )


def identity_provider_service__insert(
    connection: DBInterface,
    name, logo_url, requires_email_verification
):
    execute_supplied_statement(
        connection, QG__identity_provider_service_insert,
        {
            KG__identity_provider_service__name: name,
            KG__identity_provider_service__logo_url: logo_url,
            KG__identity_provider_service__requires_email_verification: requires_email_verification
        }
    )


# Generated keys for table 'user_registry'
KG__user_registry__provider = "provider"
KG__user_registry__tenant = "tenant"
KG__user_registry__discovery_url = "discovery_url"

# Generated queries for table 'user_registry'
QG__user_registry_delete = "DELETE FROM user_registry WHERE provider = :provider AND tenant = :tenant"
QG__user_registry_insert = """
    INSERT INTO user_registry (provider, tenant, discovery_url)
    VALUES (:provider, :tenant, :discovery_url)
"""
QG__user_registry_select_all = "SELECT * FROM user_registry"
QG__user_registry_select = "SELECT * FROM user_registry WHERE provider = :provider AND tenant = :tenant"
QG__user_registry_update = """
    UPDATE
        user_registry
    SET
        discovery_url = COALESCE(:discovery_url, discovery_url)
    WHERE
        provider = :provider AND tenant = :tenant
"""


# Generated methods for table 'user_registry'
def user_registry__delete(
    connection: DBInterface,
    provider, tenant
):
    execute_supplied_statement(
        connection, QG__user_registry_delete,
        {
            # Key Fields
            KG__user_registry__provider: provider,
            KG__user_registry__tenant: tenant
        }
    )


def user_registry__update(
    connection: DBInterface,
    provider, tenant,
    discovery_url=None
):
    execute_supplied_statement(
        connection, QG__user_registry_update,
        {
            # Key Fields
            KG__user_registry__provider: provider,
            KG__user_registry__tenant: tenant,

            # None Key Fields
            KG__user_registry__discovery_url: discovery_url
        }
    )


def user_registry__select(
    connection: DBInterface,
    provider, tenant,
    singleton_code: int = None, singleton_message: str = "user_registry does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__user_registry_select, 
        {
            # Key Fields
            KG__user_registry__provider: provider,
            KG__user_registry__tenant: tenant
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def user_registry__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__user_registry_select_all,
        as_objects=True
    )


def user_registry__insert(
    connection: DBInterface,
    provider, tenant, discovery_url
):
    execute_supplied_statement(
        connection, QG__user_registry_insert,
        {
            KG__user_registry__provider: provider,
            KG__user_registry__tenant: tenant,
            KG__user_registry__discovery_url: discovery_url
        }
    )


# Generated keys for table 'database_user_registry'
KG__database_user_registry__provider = "provider"
KG__database_user_registry__tenant = "tenant"
KG__database_user_registry__database = "database"
KG__database_user_registry__federation_procedure = "federation_procedure"
KG__database_user_registry__client_id = "client_id"
KG__database_user_registry__client_secret = "client_secret"

# Generated queries for table 'database_user_registry'
QG__database_user_registry_delete = "DELETE FROM database_user_registry WHERE provider = :provider AND tenant = :tenant AND database = :database"
QG__database_user_registry_insert = """
    INSERT INTO database_user_registry (provider, tenant, database,
        federation_procedure, client_id, client_secret)
    VALUES (:provider, :tenant, :database,
        :federation_procedure, :client_id, :client_secret)
"""
QG__database_user_registry_select_all = "SELECT * FROM database_user_registry"
QG__database_user_registry_select = "SELECT * FROM database_user_registry WHERE provider = :provider AND tenant = :tenant AND database = :database"
QG__database_user_registry_update = """
    UPDATE
        database_user_registry
    SET
        federation_procedure = COALESCE(:federation_procedure, federation_procedure),
        client_id = COALESCE(:client_id, client_id),
        client_secret = COALESCE(:client_secret, client_secret)
    WHERE
        provider = :provider AND tenant = :tenant AND database = :database
"""


# Generated methods for table 'database_user_registry'
def database_user_registry__delete(
    connection: DBInterface,
    provider, tenant, database
):
    execute_supplied_statement(
        connection, QG__database_user_registry_delete,
        {
            # Key Fields
            KG__database_user_registry__provider: provider,
            KG__database_user_registry__tenant: tenant,
            KG__database_user_registry__database: database
        }
    )


def database_user_registry__update(
    connection: DBInterface, encryption_key: bytes,
    provider, tenant, database,
    federation_procedure=None, client_id=None, client_secret=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__database_user_registry_update,
        {
            # Key Fields
            KG__database_user_registry__provider: provider,
            KG__database_user_registry__tenant: tenant,
            KG__database_user_registry__database: database,

            # None Key Fields
            KG__database_user_registry__federation_procedure: federation_procedure,
            KG__database_user_registry__client_id: client_id,
            KG__database_user_registry__client_secret: client_secret
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__database_user_registry__client_id,
            KG__database_user_registry__client_secret
        ]
    )


def database_user_registry__select(
    connection: DBInterface, encryption_key: bytes,
    provider, tenant, database,
    singleton_code: int = None, singleton_message: str = "database_user_registry does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__database_user_registry_select, 
        {
            # Key Fields
            KG__database_user_registry__provider: provider,
            KG__database_user_registry__tenant: tenant,
            KG__database_user_registry__database: database
        }, encryption_key=encryption_key, decrypt_columns=[
            KG__database_user_registry__client_id,
            KG__database_user_registry__client_secret
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def database_user_registry__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__database_user_registry_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__database_user_registry__client_id,
            KG__database_user_registry__client_secret
        ],
        as_objects=True
    )


def database_user_registry__insert(
    connection: DBInterface, encryption_key: bytes,
    provider, tenant, database,
    federation_procedure, client_id,
    client_secret=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__database_user_registry_insert,
        {
            KG__database_user_registry__provider: provider,
            KG__database_user_registry__tenant: tenant,
            KG__database_user_registry__database: database,
            KG__database_user_registry__federation_procedure: federation_procedure,
            KG__database_user_registry__client_id: client_id,
            KG__database_user_registry__client_secret: client_secret
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__database_user_registry__client_id,
            KG__database_user_registry__client_secret
        ]
    )


# Generated keys for table 'account'
KG__account__id = "id"
KG__account__sub = "sub"
KG__account__username = "username"
KG__account__email = "email"
KG__account__email_verified = "email_verified"
KG__account__deletion_timestamp = "deletion_timestamp"
KG__account__provider = "provider"
KG__account__tenant = "tenant"
KG__account__api_key = "api_key"

# Generated queries for table 'account'
QG__account_delete = "DELETE FROM account WHERE id = :id"
QG__account_insert = """
    INSERT INTO account (id, sub, username,
        email, email_verified, deletion_timestamp,
        provider, tenant, api_key)
    VALUES (:id, :sub, :username,
        :email, :email_verified, :deletion_timestamp,
        :provider, :tenant, :api_key)
"""
QG__account_select_all = "SELECT * FROM account"
QG__account_select = "SELECT * FROM account WHERE id = :id"
QG__account_update = """
    UPDATE
        account
    SET
        sub = COALESCE(:sub, sub),
        username = COALESCE(:username, username),
        email = COALESCE(:email, email),
        email_verified = COALESCE(:email_verified, email_verified),
        deletion_timestamp = COALESCE(:deletion_timestamp, deletion_timestamp),
        provider = COALESCE(:provider, provider),
        tenant = COALESCE(:tenant, tenant),
        api_key = COALESCE(:api_key, api_key)
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
    sub=None, username=None, email=None,
    email_verified=None, deletion_timestamp=None, provider=None,
    tenant=None, api_key=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__account_update,
        {
            # Key Fields
            KG__account__id: id,

            # None Key Fields
            KG__account__sub: sub,
            KG__account__username: username,
            KG__account__email: email,
            KG__account__email_verified: email_verified,
            KG__account__deletion_timestamp: deletion_timestamp,
            KG__account__provider: provider,
            KG__account__tenant: tenant,
            KG__account__api_key: api_key
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__account__sub,
            KG__account__email
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
            KG__account__sub,
            KG__account__email
        ],
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def account__select_all(
    connection: DBInterface, encryption_key: bytes
):
    return execute_supplied_statement(
        connection, QG__account_select_all, encryption_key=encryption_key, decrypt_columns=[
            KG__account__sub,
            KG__account__email
        ],
        as_objects=True
    )


def account__insert(
    connection: DBInterface, encryption_key: bytes,
    id, sub, email_verified,
    username=None, email=None, deletion_timestamp=None,
    provider=None, tenant=None, api_key=None,
    encryption_salts=None
):
    execute_supplied_statement(
        connection, QG__account_insert,
        {
            KG__account__id: id,
            KG__account__sub: sub,
            KG__account__username: username,
            KG__account__email: email,
            KG__account__email_verified: email_verified,
            KG__account__deletion_timestamp: deletion_timestamp,
            KG__account__provider: provider,
            KG__account__tenant: tenant,
            KG__account__api_key: api_key
        }, encryption_key=encryption_key, encryption_salts=encryption_salts, encrypt_parameters=[
            KG__account__sub,
            KG__account__email
        ]
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
KG__security_event__name = "name"
KG__security_event__type = "type"
KG__security_event__database_procedure = "database_procedure"

# Generated queries for table 'security_event'
QG__security_event_delete = "DELETE FROM security_event WHERE application = :application AND name = :name AND type = :type"
QG__security_event_insert = """
    INSERT INTO security_event (application, name, type,
        database_procedure)
    VALUES (:application, :name, :type,
        :database_procedure)
"""
QG__security_event_select_all = "SELECT * FROM security_event"
QG__security_event_select = "SELECT * FROM security_event WHERE application = :application AND name = :name AND type = :type"
QG__security_event_update = """
    UPDATE
        security_event
    SET
        database_procedure = COALESCE(:database_procedure, database_procedure)
    WHERE
        application = :application AND name = :name AND type = :type
"""


# Generated methods for table 'security_event'
def security_event__delete(
    connection: DBInterface,
    application, name, type
):
    execute_supplied_statement(
        connection, QG__security_event_delete,
        {
            # Key Fields
            KG__security_event__application: application,
            KG__security_event__name: name,
            KG__security_event__type: type
        }
    )


def security_event__update(
    connection: DBInterface,
    application, name, type,
    database_procedure=None
):
    execute_supplied_statement(
        connection, QG__security_event_update,
        {
            # Key Fields
            KG__security_event__application: application,
            KG__security_event__name: name,
            KG__security_event__type: type,

            # None Key Fields
            KG__security_event__database_procedure: database_procedure
        }
    )


def security_event__select(
    connection: DBInterface,
    application, name, type,
    singleton_code: int = None, singleton_message: str = "security_event does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__security_event_select, 
        {
            # Key Fields
            KG__security_event__application: application,
            KG__security_event__name: name,
            KG__security_event__type: type
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
    application, name, type,
    database_procedure
):
    execute_supplied_statement(
        connection, QG__security_event_insert,
        {
            KG__security_event__application: application,
            KG__security_event__name: name,
            KG__security_event__type: type,
            KG__security_event__database_procedure: database_procedure
        }
    )


# Generated keys for table 'handled_error'
KG__handled_error__code = "code"
KG__handled_error__error_name = "error_name"
KG__handled_error__is_arrayed = "is_arrayed"
KG__handled_error__table_name = "table_name"
KG__handled_error__table_name_required = "table_name_required"
KG__handled_error__table_possible = "table_possible"
KG__handled_error__column_possible = "column_possible"
KG__handled_error__has_associated_set = "has_associated_set"
KG__handled_error__has_sub_code = "has_sub_code"
KG__handled_error__column_name = "column_name"
KG__handled_error__http_response_code = "http_response_code"
KG__handled_error__message = "message"
KG__handled_error__description = "description"

# Generated queries for table 'handled_error'
QG__handled_error_delete = "DELETE FROM handled_error WHERE code = :code"
QG__handled_error_insert = """
    INSERT INTO handled_error (code, error_name, is_arrayed,
        table_name, table_name_required, table_possible,
        column_possible, has_associated_set, has_sub_code,
        column_name, message, description)
    VALUES (:code, :error_name, :is_arrayed,
        :table_name, :table_name_required, :table_possible,
        :column_possible, :has_associated_set, :has_sub_code,
        :column_name, :message, :description)
    RETURNING http_response_code
"""
QG__handled_error_select_all = "SELECT * FROM handled_error"
QG__handled_error_select = "SELECT * FROM handled_error WHERE code = :code"
QG__handled_error_update = """
    UPDATE
        handled_error
    SET
        error_name = COALESCE(:error_name, error_name),
        is_arrayed = COALESCE(:is_arrayed, is_arrayed),
        table_name = COALESCE(:table_name, table_name),
        table_name_required = COALESCE(:table_name_required, table_name_required),
        table_possible = COALESCE(:table_possible, table_possible),
        column_possible = COALESCE(:column_possible, column_possible),
        has_associated_set = COALESCE(:has_associated_set, has_associated_set),
        has_sub_code = COALESCE(:has_sub_code, has_sub_code),
        column_name = COALESCE(:column_name, column_name),
        http_response_code = COALESCE(:http_response_code, http_response_code),
        message = COALESCE(:message, message),
        description = COALESCE(:description, description)
    WHERE
        code = :code
"""


# Generated methods for table 'handled_error'
def handled_error__delete(
    connection: DBInterface,
    code
):
    execute_supplied_statement(
        connection, QG__handled_error_delete,
        {
            # Key Fields
            KG__handled_error__code: code
        }
    )


def handled_error__update(
    connection: DBInterface,
    code,
    error_name=None, is_arrayed=None, table_name=None,
    table_name_required=None, table_possible=None, column_possible=None,
    has_associated_set=None, has_sub_code=None, column_name=None,
    http_response_code=None, message=None, description=None
):
    execute_supplied_statement(
        connection, QG__handled_error_update,
        {
            # Key Fields
            KG__handled_error__code: code,

            # None Key Fields
            KG__handled_error__error_name: error_name,
            KG__handled_error__is_arrayed: is_arrayed,
            KG__handled_error__table_name: table_name,
            KG__handled_error__table_name_required: table_name_required,
            KG__handled_error__table_possible: table_possible,
            KG__handled_error__column_possible: column_possible,
            KG__handled_error__has_associated_set: has_associated_set,
            KG__handled_error__has_sub_code: has_sub_code,
            KG__handled_error__column_name: column_name,
            KG__handled_error__http_response_code: http_response_code,
            KG__handled_error__message: message,
            KG__handled_error__description: description
        }
    )


def handled_error__select(
    connection: DBInterface,
    code,
    singleton_code: int = None, singleton_message: str = "handled_error does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__handled_error_select, 
        {
            # Key Fields
            KG__handled_error__code: code
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def handled_error__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__handled_error_select_all,
        as_objects=True
    )


def handled_error__insert(
    connection: DBInterface,
    code, is_arrayed, description,
    error_name=None, table_name=None, table_name_required=None,
    table_possible=None, column_possible=None, has_associated_set=None,
    has_sub_code=None, column_name=None, message=None
):
    return execute_supplied_statement_singleton(
        connection, QG__handled_error_insert,
        {
            KG__handled_error__code: code,
            KG__handled_error__error_name: error_name,
            KG__handled_error__is_arrayed: is_arrayed,
            KG__handled_error__table_name: table_name,
            KG__handled_error__table_name_required: table_name_required,
            KG__handled_error__table_possible: table_possible,
            KG__handled_error__column_possible: column_possible,
            KG__handled_error__has_associated_set: has_associated_set,
            KG__handled_error__has_sub_code: has_sub_code,
            KG__handled_error__column_name: column_name,
            KG__handled_error__message: message,
            KG__handled_error__description: description
        }, as_objects=True
    )


# Generated keys for table 'pg_base_exception'
KG__pg_base_exception__name = "name"

# Generated queries for table 'pg_base_exception'
QG__pg_base_exception_delete = "DELETE FROM pg_base_exception WHERE name = :name"
QG__pg_base_exception_insert = """
    INSERT INTO pg_base_exception (name)
    VALUES (:name)
"""
QG__pg_base_exception_select_all = "SELECT * FROM pg_base_exception"
QG__pg_base_exception_select = "SELECT * FROM pg_base_exception WHERE name = :name"
QG__pg_base_exception_update = """
    UPDATE
        pg_base_exception
    SET
        
    WHERE
        name = :name
"""


# Generated methods for table 'pg_base_exception'
def pg_base_exception__delete(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__pg_base_exception_delete,
        {
            # Key Fields
            KG__pg_base_exception__name: name
        }
    )


def pg_base_exception__update(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__pg_base_exception_update,
        {
            # Key Fields
            KG__pg_base_exception__name: name
        }
    )


def pg_base_exception__select(
    connection: DBInterface,
    name,
    singleton_code: int = None, singleton_message: str = "pg_base_exception does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__pg_base_exception_select, 
        {
            # Key Fields
            KG__pg_base_exception__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def pg_base_exception__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__pg_base_exception_select_all,
        as_objects=True
    )


def pg_base_exception__insert(
    connection: DBInterface,
    name
):
    execute_supplied_statement(
        connection, QG__pg_base_exception_insert,
        {
            KG__pg_base_exception__name: name
        }
    )


# Generated keys for table 'pg_error_class'
KG__pg_error_class__code = "code"
KG__pg_error_class__name = "name"
KG__pg_error_class__description = "description"

# Generated queries for table 'pg_error_class'
QG__pg_error_class_delete = "DELETE FROM pg_error_class WHERE code = :code"
QG__pg_error_class_insert = """
    INSERT INTO pg_error_class (code, name, description)
    VALUES (:code, :name, :description)
"""
QG__pg_error_class_select_all = "SELECT * FROM pg_error_class"
QG__pg_error_class_select = "SELECT * FROM pg_error_class WHERE code = :code"
QG__pg_error_class_update = """
    UPDATE
        pg_error_class
    SET
        name = COALESCE(:name, name),
        description = COALESCE(:description, description)
    WHERE
        code = :code
"""


# Generated methods for table 'pg_error_class'
def pg_error_class__delete(
    connection: DBInterface,
    code
):
    execute_supplied_statement(
        connection, QG__pg_error_class_delete,
        {
            # Key Fields
            KG__pg_error_class__code: code
        }
    )


def pg_error_class__update(
    connection: DBInterface,
    code,
    name=None, description=None
):
    execute_supplied_statement(
        connection, QG__pg_error_class_update,
        {
            # Key Fields
            KG__pg_error_class__code: code,

            # None Key Fields
            KG__pg_error_class__name: name,
            KG__pg_error_class__description: description
        }
    )


def pg_error_class__select(
    connection: DBInterface,
    code,
    singleton_code: int = None, singleton_message: str = "pg_error_class does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__pg_error_class_select, 
        {
            # Key Fields
            KG__pg_error_class__code: code
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def pg_error_class__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__pg_error_class_select_all,
        as_objects=True
    )


def pg_error_class__insert(
    connection: DBInterface,
    code, name,
    description=None
):
    execute_supplied_statement(
        connection, QG__pg_error_class_insert,
        {
            KG__pg_error_class__code: code,
            KG__pg_error_class__name: name,
            KG__pg_error_class__description: description
        }
    )


# Generated keys for table 'pg_exception'
KG__pg_exception__pg_class = "pg_class"
KG__pg_exception__sqlstate = "sqlstate"
KG__pg_exception__name = "name"
KG__pg_exception__base_exception = "base_exception"

# Generated queries for table 'pg_exception'
QG__pg_exception_delete = "DELETE FROM pg_exception WHERE sqlstate = :sqlstate"
QG__pg_exception_insert = """
    INSERT INTO pg_exception (pg_class, sqlstate, name,
        base_exception)
    VALUES (:pg_class, :sqlstate, :name,
        :base_exception)
"""
QG__pg_exception_select_all = "SELECT * FROM pg_exception"
QG__pg_exception_select = "SELECT * FROM pg_exception WHERE sqlstate = :sqlstate"
QG__pg_exception_update = """
    UPDATE
        pg_exception
    SET
        pg_class = COALESCE(:pg_class, pg_class),
        name = COALESCE(:name, name),
        base_exception = COALESCE(:base_exception, base_exception)
    WHERE
        sqlstate = :sqlstate
"""


# Generated methods for table 'pg_exception'
def pg_exception__delete(
    connection: DBInterface,
    sqlstate
):
    execute_supplied_statement(
        connection, QG__pg_exception_delete,
        {
            # Key Fields
            KG__pg_exception__sqlstate: sqlstate
        }
    )


def pg_exception__update(
    connection: DBInterface,
    sqlstate,
    pg_class=None, name=None, base_exception=None
):
    execute_supplied_statement(
        connection, QG__pg_exception_update,
        {
            # Key Fields
            KG__pg_exception__sqlstate: sqlstate,

            # None Key Fields
            KG__pg_exception__pg_class: pg_class,
            KG__pg_exception__name: name,
            KG__pg_exception__base_exception: base_exception
        }
    )


def pg_exception__select(
    connection: DBInterface,
    sqlstate,
    singleton_code: int = None, singleton_message: str = "pg_exception does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__pg_exception_select, 
        {
            # Key Fields
            KG__pg_exception__sqlstate: sqlstate
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def pg_exception__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__pg_exception_select_all,
        as_objects=True
    )


def pg_exception__insert(
    connection: DBInterface,
    pg_class, sqlstate, name,
    base_exception
):
    execute_supplied_statement(
        connection, QG__pg_exception_insert,
        {
            KG__pg_exception__pg_class: pg_class,
            KG__pg_exception__sqlstate: sqlstate,
            KG__pg_exception__name: name,
            KG__pg_exception__base_exception: base_exception
        }
    )


# Generated keys for table 'remote_procedure'
KG__remote_procedure__application = "application"
KG__remote_procedure__name = "name"
KG__remote_procedure__command = "command"
KG__remote_procedure__access = "access"
KG__remote_procedure__cron = "cron"

# Generated queries for table 'remote_procedure'
QG__remote_procedure_delete = "DELETE FROM remote_procedure WHERE application = :application AND name = :name"
QG__remote_procedure_insert = """
    INSERT INTO remote_procedure (application, name, command,
        access, cron)
    VALUES (:application, :name, :command,
        :access, :cron)
"""
QG__remote_procedure_select_all = "SELECT * FROM remote_procedure"
QG__remote_procedure_select = "SELECT * FROM remote_procedure WHERE application = :application AND name = :name"
QG__remote_procedure_update = """
    UPDATE
        remote_procedure
    SET
        command = COALESCE(:command, command),
        access = COALESCE(:access, access),
        cron = COALESCE(:cron, cron)
    WHERE
        application = :application AND name = :name
"""


# Generated methods for table 'remote_procedure'
def remote_procedure__delete(
    connection: DBInterface,
    application, name
):
    execute_supplied_statement(
        connection, QG__remote_procedure_delete,
        {
            # Key Fields
            KG__remote_procedure__application: application,
            KG__remote_procedure__name: name
        }
    )


def remote_procedure__update(
    connection: DBInterface,
    application, name,
    command=None, access=None, cron=None
):
    execute_supplied_statement(
        connection, QG__remote_procedure_update,
        {
            # Key Fields
            KG__remote_procedure__application: application,
            KG__remote_procedure__name: name,

            # None Key Fields
            KG__remote_procedure__command: command,
            KG__remote_procedure__access: access,
            KG__remote_procedure__cron: cron
        }
    )


def remote_procedure__select(
    connection: DBInterface,
    application, name,
    singleton_code: int = None, singleton_message: str = "remote_procedure does not exist"
):
    return execute_supplied_statement_singleton(
        connection, QG__remote_procedure_select, 
        {
            # Key Fields
            KG__remote_procedure__application: application,
            KG__remote_procedure__name: name
        },
        as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


def remote_procedure__select_all(
    connection: DBInterface
):
    return execute_supplied_statement(
        connection, QG__remote_procedure_select_all,
        as_objects=True
    )


def remote_procedure__insert(
    connection: DBInterface,
    application, name, command,
    access,
    cron=None
):
    execute_supplied_statement(
        connection, QG__remote_procedure_insert,
        {
            KG__remote_procedure__application: application,
            KG__remote_procedure__name: name,
            KG__remote_procedure__command: command,
            KG__remote_procedure__access: access,
            KG__remote_procedure__cron: cron
        }
    )
