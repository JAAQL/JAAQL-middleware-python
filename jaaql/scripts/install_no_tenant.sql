CREATE DOMAIN postgres_table_view_name AS varchar(64) CHECK (VALUE ~* '^[A-Za-z*0-9_\-]+$');
CREATE DOMAIN email_address AS varchar(255) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$' AND lower(VALUE) = VALUE) OR VALUE IN ('jaaql', 'superjaaql'));
CREATE DOMAIN jaaql_user_id AS uuid;

create table jaaql__email_account (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    name varchar(255) not null,
    send_name varchar(255) not null,
    protocol varchar(4) not null,
    check (protocol in ('smtp', 'imap')),
    host varchar(255) not null,
    port integer not null,
    username varchar(255) not null,
    encrypted_password text not null,
    deleted timestamptz default null
);
CREATE UNIQUE INDEX jaaql__email_account_unq
    ON jaaql__email_account (name) WHERE (deleted is null);

create table jaaql__node (
    name varchar(255) primary key not null,
    description varchar(255) not null,
    port integer not null,
    address varchar(255) not null,
    interface_class varchar(20) not null,
    deleted timestamptz,
    --Used to create new databases
    super_user_username varchar(254),
    super_user_password varchar(254),
    check ((super_user_username is null) = (super_user_password is null))
);

CREATE UNIQUE INDEX jaaql__node_unq
    ON jaaql__node (address, port) WHERE (deleted is null);

create table jaaql__database (
    node varchar(255) not null references jaaql__node on update cascade on delete cascade,
    name postgres_table_view_name not null,
    pooling_user_username varchar(254) not null,
    pooling_user_password varchar(254) not null,
    deleted timestamptz,
    PRIMARY KEY (node, name)
);

create table jaaql__email_template (
    id   uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    name varchar(60) NOT NULL,
    subject varchar(255),
    description text,
    app_relative_path postgres_table_view_name,  -- Not a mistake for this domain type
    check ((subject is null) = (app_relative_path is null)),
    data_validation_table postgres_table_view_name,
    data_validation_view postgres_table_view_name,
    CHECK ((data_validation_table is null and data_validation_view is null) or data_validation_table is not null),
    recipient_validation_view postgres_table_view_name,
    allow_signup boolean default false not null,
    allow_confirm_signup_attempt boolean default false not null,
    allow_reset_password boolean default false not null,
    check (allow_signup::int + allow_confirm_signup_attempt::int + allow_reset_password::int < 2),
    deleted timestamptz default null,
    node varchar(255) not null,
    database postgres_table_view_name not null,  -- This is not a mistake. Type is meant to mismatch
    FOREIGN KEY (node, database) REFERENCES jaaql__database,
    FOREIGN KEY (node) REFERENCES jaaql__node,
    account uuid NOT NULL,
    FOREIGN KEY (account) REFERENCES jaaql__email_account
);
CREATE UNIQUE INDEX jaaql__email_template_unq
    ON jaaql__email_template (name) WHERE (deleted is null);

create table jaaql__application (
    name postgres_table_view_name not null primary key,
    description varchar(256) not null,
    created timestamptz not null default current_timestamp,
    default_email_signup_template uuid,
    FOREIGN KEY (default_email_signup_template) REFERENCES jaaql__email_template,
    default_email_already_signed_up_template uuid,
    FOREIGN KEY (default_email_already_signed_up_template) REFERENCES jaaql__email_template,
    default_reset_password_template uuid,
    FOREIGN KEY (default_reset_password_template) REFERENCES jaaql__email_template
);

create table jaaql__application_configuration (
    application postgres_table_view_name not null,
    name varchar(64) not null,
    description varchar(256) not null,
    url text not null,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);

create table jaaql__user (
    id       jaaql_user_id primary key not null default gen_random_uuid(),
    email    text not null,
    created timestamptz not null default current_timestamp,
    mobile   bigint,                 -- with null [allows for SMS-based 2FA login later] )
    deleted timestamptz,
    enc_totp_iv varchar(254),
    last_totp varchar(6),
    alias varchar(32),
    public_credentials text,
    application postgres_table_view_name,
    configuration varchar(64),
    check (((public_credentials is null) = (application is null)) or public_credentials is null),
    check ((public_credentials is null) = (configuration is null)),
    FOREIGN KEY (application) REFERENCES jaaql__application,
    FOREIGN KEY (application, configuration) REFERENCES jaaql__application_configuration (application, name)
);
CREATE UNIQUE INDEX jaaql__user_unq_email ON jaaql__user (email) WHERE (deleted is null);
CREATE UNIQUE INDEX jaaql__user_public_application ON jaaql__user (application) WHERE (deleted is null);

create table jaaql__user_ip (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    the_user jaaql_user_id not null,
    encrypted_address varchar(255),
    first_use timestamptz not null default current_timestamp,
    most_recent_use timestamptz not null default current_timestamp,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    constraint jaaql__user_ip_unq unique (the_user, encrypted_address)
);

create table jaaql__user_password (
    the_user jaaql_user_id not null,
    created timestamptz not null default current_timestamp,
    password_hash varchar(254) not null,
    PRIMARY KEY (the_user, password_hash),
    FOREIGN KEY (the_user) REFERENCES jaaql__user
);

create table jaaql__application_dataset (
    application postgres_table_view_name not null,
    name varchar(64) not null,
    description varchar(255) not null,
    is_user_dataset boolean,
    check (is_user_dataset is null or is_user_dataset),
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);
CREATE UNIQUE INDEX jaaql__application_dataset_unq ON jaaql__application_dataset (application, is_user_dataset);
INSERT INTO jaaql__application_dataset (application, name, description) VALUES ('console', 'node', 'The node which the console will run against');
INSERT INTO jaaql__application_dataset (application, name, description) VALUES ('manager', 'node', 'A jaaql node which the app can manage');
INSERT INTO jaaql__application_dataset (application, name, description) VALUES ('playground', 'node', 'A jaaql node which the app can manage');

create table jaaql__assigned_database (
    application postgres_table_view_name not null,
    configuration varchar(64) not null,
    database postgres_table_view_name not null,
    node varchar(255) not null,
    dataset varchar(64) not null,
    PRIMARY KEY (application, dataset, configuration),
    FOREIGN KEY (application, configuration) references jaaql__application_configuration(application, name)
        on delete cascade on update cascade,
    FOREIGN KEY (application, dataset) references jaaql__application_dataset(application, name) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (database, node) references jaaql__database(name, node) on delete cascade on update cascade,
    FOREIGN KEY (node) references jaaql__node (name) on delete cascade on update cascade
);

create table jaaql__authorization_configuration (
    application postgres_table_view_name not null references jaaql__application on delete cascade on update cascade,
    configuration varchar(64) not null,
    role        varchar(254) not null default '',
    primary key (application, configuration, role),
    foreign key (application, configuration) references jaaql__application_configuration on delete cascade on update cascade
);

create table jaaql__default_role (
    application postgres_table_view_name not null,
    FOREIGN KEY (application) REFERENCES jaaql__application,
    the_role varchar(255) not null,
    PRIMARY KEY (application, the_role)
);

create table jaaql__credentials_node (
    id uuid PRIMARY KEY not null default gen_random_uuid(),
    node varchar(255) not null references jaaql__node,
    role varchar(254),
    deleted timestamptz,
    db_encrypted_username varchar(254) not null,
	precedence int not null default 0
);

create table jaaql__log (
    id uuid primary key not null default gen_random_uuid(),
    the_user jaaql_user_id,
    occurred timestamptz not null default current_timestamp,
    duration_ms integer not null,
    encrypted_exception text,
    encrypted_input text,
    ip uuid not null,
    status int not null,
    endpoint varchar(64) not null,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    FOREIGN KEY (ip) REFERENCES jaaql__user_ip
);

create table jaaql__log_db_auth (
    log uuid not null,
    credentials uuid not null,
    PRIMARY KEY (log, credentials),
    FOREIGN KEY (log) REFERENCES jaaql__log,
    FOREIGN KEY (credentials) REFERENCES jaaql__credentials_node
);

create table jaaql__email_history (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    template uuid not null,
    FOREIGN KEY (template) REFERENCES jaaql__email_template,
    sender jaaql_user_id not null,
    FOREIGN KEY (sender) REFERENCES jaaql__user,
    sent timestamptz not null default current_timestamp,
    encrypted_subject text,
    encrypted_recipients text not null,
    encrypted_recipients_keys text not null,
    encrypted_body text,
    encrypted_attachments text
);

create table jaaql__fake_reset_password (
    key_b uuid PRIMARY KEY not null default gen_random_uuid(),
    email text NOT NULL,
    created timestamptz default current_timestamp not null,
    code_attempts int default 0 not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 2, -- 2 hours
    code_expiry_ms integer not null default 1000 * 60 * 15 -- 15 minutes
);

create table jaaql__reset_password (
    key_a uuid PRIMARY KEY not null default gen_random_uuid(),
    key_b uuid not null default gen_random_uuid(),
    reset_code varchar(8) not null,
    code_attempts int default 0 not null,
    activated boolean not null default false,
    used_key_a boolean not null default false,
    the_user jaaql_user_id not null,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 2, -- 2 hours. Important this is the same as above fake table
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes. Important this is the same as above fake table
    email_template uuid,
    data_lookup_json text,
    FOREIGN KEY (email_template) REFERENCES jaaql__email_template
);

create table jaaql__sign_up (
    key_a uuid PRIMARY KEY not null default gen_random_uuid(),
    key_b uuid not null default gen_random_uuid(),
    invite_code varchar(5) not null,
    code_attempts int default 0 not null,
    activated boolean not null default false,
    used_key_a boolean not null default false,
    the_user jaaql_user_id not null,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 24 * 14, -- 2 weeks
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes
    email_template uuid,
    FOREIGN KEY (email_template) REFERENCES jaaql__email_template,
    data_lookup_json text,
    check ((data_lookup_json is null and email_template is null) or email_template is not null)
);

CREATE UNIQUE INDEX jaaql__sign_up_unq_key_b ON jaaql__sign_up (key_b);

create table jaaql__renderable_document (
    name      varchar(40) PRIMARY KEY NOT null,
    url       text not null,
    render_as varchar(10) default 'pdf' not null,
    check (render_as in ('pdf'))
);

create table jaaql__rendered_document (
    document_id uuid PRIMARY KEY not null default gen_random_uuid(),
    document varchar(40) NOT NULL,
    created timestamptz not null default current_timestamp,
    encrypted_parameters text,
    encrypted_access_token text,
    create_file boolean not null,
    FOREIGN KEY (document) REFERENCES jaaql__renderable_document,
    completed timestamptz,
    content bytea,
    filename varchar(100),
    check ((completed is null) or (filename is not null))
);

create table jaaql__renderable_document_template (
    attachment varchar(40),
    template   uuid not null,
    PRIMARY KEY (attachment, template),
    FOREIGN KEY (template) references jaaql__email_template,
    FOREIGN KEY (attachment) references jaaql__renderable_document
);