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

create table jaaql__email_template (
    id   uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    name varchar(60) NOT NULL,
    subject varchar(255),
    account uuid NOT NULL,
    FOREIGN KEY (account) REFERENCES jaaql__email_account,
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
    deleted timestamptz default null
);
CREATE UNIQUE INDEX jaaql__email_template_unq
    ON jaaql__email_template (name) WHERE (deleted is null);

create table jaaql__tenant (
    name varchar(64) PRIMARY KEY not null,
    parent varchar(64),
    FOREIGN KEY (parent) REFERENCES jaaql__tenant
);

INSERT INTO jaaql__tenant (name) VALUES ('default');

create table jaaql__application (
    name varchar(64) PRIMARY KEY not null,
    description varchar(256) not null,
    url text not null,
    created timestamptz not null default current_timestamp
);

create table jaaql__application_tenant (
    application varchar(64),
    tenant varchar(64) not null default 'default',
    PRIMARY KEY (application, tenant),
    FOREIGN KEY (tenant) REFERENCES jaaql__tenant,
    FOREIGN KEY (application) REFERENCES jaaql__application,
    created timestamptz not null default current_timestamp,
    default_email_signup_template uuid,
    FOREIGN KEY (default_email_signup_template) REFERENCES jaaql__email_template,
    default_email_already_signed_up_template uuid,
    FOREIGN KEY (default_email_already_signed_up_template) REFERENCES jaaql__email_template,
    default_reset_password_template uuid,
    FOREIGN KEY (default_reset_password_template) REFERENCES jaaql__email_template
)

create table jaaql__user (
    id       jaaql_user_id primary key not null default gen_random_uuid(),
    email    text not null,
    created timestamptz not null default current_timestamp,
    mobile   bigint,                 -- with null [allows for SMS-based 2FA login later] )
    deleted timestamptz,
    enc_totp_iv varchar(254),
    last_totp varchar(6),
    alias varchar(32),
    is_public boolean default false not null,
    public_credentials text,
    application varchar(64),
    check (not is_public = (public_credentials is null)),
    check (not is_public = (application is null)),
    FOREIGN KEY (application) REFERENCES jaaql__application ON DELETE CASCADE ON UPDATE CASCADE
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

create view jaaql__user_latest_password as (
    SELECT
        us.id,
        us.email,
        password_hash,
        password_created,
        us.enc_totp_iv,
        us.last_totp,
        us.is_public
    FROM
        (SELECT
            the_user,
            password_hash,
            created as password_created,
            row_number() over (PARTITION BY the_user) as change_count
        FROM jaaql__user_password
        ORDER BY created desc) as sub
    INNER JOIN
        jaaql__user us ON us.id = the_user
    WHERE
        sub.change_count <= 1 AND us.deleted is null
);

create view jaaql__user_latest_credentials as (
    SELECT
        julp.*,
        juip.id as ip_id,
        juip.encrypted_address
    FROM
        jaaql__user_latest_password julp
    INNER JOIN
        jaaql__user_ip juip ON juip.the_user = julp.id
);

create table jaaql__node (
    name varchar(255) primary key not null,
    description varchar(255) not null,
    port integer not null,
	address varchar(255) not null,
	interface_class varchar(20) not null,
	deleted timestamptz
);

create table jaaql__database (
    node varchar(255) not null references jaaql__node on update cascade on delete cascade,
	name postgres_table_view_name not null,
	deleted timestamptz,
	PRIMARY KEY (node, name)
);

create table jaaql__default_role (
    the_role postgres_table_view_name PRIMARY KEY not null
);

create table jaaql__credentials_node (
    id uuid PRIMARY KEY not null default gen_random_uuid(),
    node varchar(255) not null references jaaql__node,
    role varchar(254),
    deleted timestamptz,
    db_encrypted_username varchar(254) not null,
	db_encrypted_password varchar(254) not null,
	precedence int not null default 0
);
CREATE UNIQUE INDEX jaaql__credentials_node_unq
    ON jaaql__credentials_node (node, role) WHERE (deleted is null);

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

create view jaaql__my_logs as (
    SELECT
        log.occurred,
        ip.encrypted_address,
        log.status,
        log.endpoint,
        log.duration_ms,
        log.encrypted_exception
    FROM
         jaaql__log log
    INNER JOIN jaaql__user us ON us.id = log.the_user AND us.deleted is null AND us.email = current_user
    INNER JOIN jaaql__user_ip ip ON log.ip = ip.id
    ORDER BY occurred DESC
);
grant select on jaaql__my_logs to public;

create view jaaql__my_ips as (
    SELECT
        encrypted_address,
        first_use,
        most_recent_use
    FROM
         jaaql__user_ip ip
    INNER JOIN jaaql__user us ON us.id = ip.the_user AND us.deleted is null AND us.email = current_user
    ORDER BY first_use DESC
);
grant select on jaaql__my_ips to public;

create function jaaql__create_role(username text, password text) returns void as
$$
BEGIN
    IF NOT EXISTS (
      SELECT
      FROM   pg_catalog.pg_roles
      WHERE  rolname = username) THEN
      EXECUTE 'CREATE ROLE ' || quote_ident(username) || ' WITH LOGIN ENCRYPTED PASSWORD ' || quote_literal(password);
    END IF;
END
$$ language plpgsql;

create function jaaql__delete_user(delete_email text) returns void as
$$
BEGIN
    EXECUTE 'DROP ROLE ' || quote_ident(delete_email);
    UPDATE jaaql__user SET deleted = current_timestamp WHERE email = delete_email;
    UPDATE jaaql__credentials_node SET deleted = current_timestamp WHERE role = delete_email;
END
$$ language plpgsql;

create function jaaql__fetch_alias_from_id(userid text) returns text as
$$
DECLARE
    actual_alias text;
BEGIN
    SELECT coalesce(alias, userid) into actual_alias FROM jaaql__user WHERE id = userid::jaaql_user_id;
    return actual_alias;
END
$$ language plpgsql;

create view jaaql__email_templates as (
    SELECT
        jet.deleted,
        jet.name,
        jea.name as account,
        jet.description,
        jet.app_relative_path,
        jet.subject,
        jet.allow_signup,
        jet.allow_confirm_signup_attempt,
        jet.allow_reset_password,
        jet.data_validation_table,
        jet.data_validation_view,
        jet.recipient_validation_view
    FROM jaaql__email_template jet
        INNER JOIN jaaql__email_account jea ON jea.id = jet.account
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

create or replace view jaaql__my_email_history as (
    SELECT
        jeh.id,
        jet.name as template,
        sent,
        encrypted_subject as subject,
        encrypted_recipients_keys as recipient
    FROM jaaql__email_history jeh
    INNER JOIN jaaql__email_template jet on jeh.template = jet.id
    INNER JOIN jaaql__user ju on jeh.sender = ju.id
    WHERE ju.email = current_user
);
grant select on jaaql__my_email_history to public;

create view table_primary_cols as (
    SELECT c.column_name, tc.table_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
    JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema
      AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
    WHERE constraint_type = 'PRIMARY KEY' AND c.table_schema = 'public'
);

create view table_cols_marked_primary as (
    SELECT
        col.table_name,
        col.column_name,
        CASE WHEN tpc.column_name is not null then true else false end as is_primary
    FROM information_schema.columns col
    LEFT JOIN table_primary_cols tpc ON tpc.table_name = col.table_name AND col.column_name = tpc.column_name
    WHERE col.table_schema = 'public'
);

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