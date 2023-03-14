/*
**  This installation module was generated from ../../../Packages/DBMS/Postgres/15/jaaql.install for Postgres/15
*/
-- Install script

--(0) Check table and column names


-- (1) Create tables

-- application...
create table application (
    name internet_name not null,
    base_url url not null,
    artifacts_source location,
    default_schema object_name,
    default_s_et object_name,
    default_a_et object_name,
    default_r_et object_name,
    default_u_et object_name,
    unlock_key_validity_period validity_period not null default 1209600,
    unlock_code_validity_period short_validity_period not null default 900,
    is_live bool not null default false,
    primary key (name),
    check (unlock_key_validity_period between 15 and 9999999),
    check (unlock_code_validity_period between 15 and 86400) );
-- application_schema...
create table application_schema (
    application internet_name not null,
    name object_name not null,
    database object_name not null,
    primary key (application, name) );
-- email_dispatcher...
create table email_dispatcher (
    application internet_name not null,
    name object_name not null,
    display_name person_name not null,
    protocol email_dispatch_protocol,
    url url,
    port internet_port,
    username email_server_username,
    password encrypted__email_server_password,
    whitelist text,
    primary key (application, name),
    check (port between 1 and 65536) );
-- jaaql...
create table jaaql (
    the_anonymous_user postgres_role not null,
    security_event_attempt_limit attempt_count not null,
    check (security_event_attempt_limit between 1 and 3) );
-- email_template...
create table email_template (
    application internet_name not null,
    dispatcher object_name not null,
    name object_name not null,
    type email_template_type not null,
    content_url safe_path not null,
    validation_schema object_name,
    data_validation_table object_name,
    data_validation_view object_name,
    primary key (application, name) );
-- document_template...
create table document_template (
    application internet_name not null,
    name object_name not null,
    content_path safe_path not null,
    email_template object_name,
    primary key (application, name) );
-- document_request...
create table document_request (
    application internet_name not null,
    template object_name not null,
    uuid uuid not null,
    request_timestamp timestamptz not null default current_timestamp,
    encrypted_access_token encrypted__access_token not null,
    encrypted_parameters text,
    render_timestamp timestamptz,
    primary key (uuid) );
-- account...
create table account (
    id postgres_role not null,
    username encrypted__jaaql_username not null,
    deletion_timestamp timestamptz,
    most_recent_password uuid,
    primary key (id),
    unique (username) );
-- account_password...
create table account_password (
    account postgres_role not null,
    uuid uuid not null default gen_random_uuid(),
    hash encrypted__hash not null,
    creation_timestamp timestamptz not null default current_timestamp,
    primary key (uuid),
    unique (hash) );
-- validated_ip_address...
create table validated_ip_address (
    account postgres_role not null,
    uuid uuid not null default gen_random_uuid(),
    encrypted_salted_ip_address encrypted__salted_ip not null,
    first_authentication_timestamp timestamptz not null default current_timestamp,
    last_authentication_timestamp timestamptz not null,
    primary key (uuid),
    unique (encrypted_salted_ip_address) );
-- security_event...
create table security_event (
    application internet_name not null,
    event_lock uuid not null default gen_random_uuid(),
    creation_timestamp timestamptz not null default current_timestamp,
    wrong_key_attempt_count current_attempt_count not null default 0,
    email_template object_name not null,
    account postgres_role not null,
    unlock_key uuid not null default gen_random_uuid(),
    unlock_code unlock_code not null,
    unlock_timestamp timestamptz,
    primary key (application, event_lock),
    check (wrong_key_attempt_count between 0 and 3) );

-- (2) References

-- application...
alter table application add constraint application__default_schema
    foreign key (name, default_schema)
        references application_schema (application, name);
alter table application add constraint application__default_sign_up_email_template
    foreign key (name, default_s_et)
        references email_template (application, name);
alter table application add constraint application__default_already_signed_up_email_template
    foreign key (name, default_a_et)
        references email_template (application, name);
alter table application add constraint application__default_reset_password_email_template
    foreign key (name, default_r_et)
        references email_template (application, name);
alter table application add constraint application__default_unregistered_password_reset_email_template
    foreign key (name, default_u_et)
        references email_template (application, name);
-- application_schema...
alter table application_schema add constraint application_schema__application
    foreign key (application)
        references application (name);
-- email_dispatcher...
alter table email_dispatcher add constraint email_dispatcher__application
    foreign key (application)
        references application (name);
-- jaaql...
alter table jaaql add constraint jaaql__the_anonymous_user
    foreign key (the_anonymous_user)
        references account (id);
-- email_template...
alter table email_template add constraint email_template__dispatcher
    foreign key (application, dispatcher)
        references email_dispatcher (application, name);
alter table email_template add constraint email_template__validation_schema
    foreign key (application, validation_schema)
        references application_schema (application, name);
-- document_template...
alter table document_template add constraint document_template__application
    foreign key (application)
        references application (name);
alter table document_template add constraint document_template__email_template
    foreign key (application, email_template)
        references email_template (application, name);
-- document_request...
alter table document_request add constraint document_request__template
    foreign key (application, template)
        references document_template (application, name);
-- account...
alter table account add constraint account__most_recent_password
    foreign key (most_recent_password)
        references account_password (uuid);
-- account_password...
alter table account_password add constraint account_password__account
    foreign key (account)
        references account (id);
-- validated_ip_address...
alter table validated_ip_address add constraint validated_ip_address__account
    foreign key (account)
        references account (id);
-- security_event...
alter table security_event add constraint security_event__application
    foreign key (application)
        references application (name);
alter table security_event add constraint security_event__email_template
    foreign key (application, email_template)
        references email_template (application, name);
alter table security_event add constraint security_event__account
    foreign key (account)
        references account (id);

-- (3) Triggers

-- No tables have triggers
