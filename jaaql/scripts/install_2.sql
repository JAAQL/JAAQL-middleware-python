CREATE DOMAIN safe_path AS varchar(255) CHECK (VALUE ~* '^[a-z0-9_\-\/]+(\.[a-zA-Z0-9]+)?$');

-- Install script
-- (1) Create tables

-- Selecting from this table will verify if the connected account can check admin accounts
create table check_admin (
    singleton int primary key not null,
    check (singleton = 0)
);
INSERT INTO check_admin (singleton) VALUES (0);

create table application (
    description varchar(256),
    name postgres_addressable_name not null,
    base_url varchar(254) not null,
    artifacts_source varchar(254),  --Used to load templates and renderable documents
    primary key (name) );

-- application_schema...
create table application_schema (
    application character varying(63) not null,
    name character varying(63) not null,
    is_default boolean not null default false,
    database character varying(63) not null,
    primary key (application, name) );
CREATE UNIQUE INDEX application_schema_one_default ON application_schema (application, is_default) WHERE is_default;

create table email_dispatcher (
    application character varying(63) not null,
    name varchar(60) not null,
    PRIMARY KEY (application, name),
    display_name varchar(255) not null,
    protocol varchar(4) default 'smtp',
    check (protocol in ('smtp')),
    mail_server varchar(255),
    port integer,
    username varchar(255),
    encrypted_password text,
    destination_whitelist varchar(2047)
);

create table email_template (
    application character varying(63) not null,
    name postgres_addressable_name NOT NULL,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) REFERENCES application (name) ON UPDATE CASCADE ON DELETE CASCADE,
    description text,
    content_url safe_path,  -- Not a mistake for this domain type. Means app_relative_path cannot be ../../secret. Also secured at application level code in case db is tampered with
    validation_schema character varying(63),
    FOREIGN KEY (validation_schema, application) REFERENCES application_schema(name, application),
    type varchar(10) not null,
    check (type = 'S' or type = 'A' or type = 'R'),
    dispatcher varchar(60) NOT NULL,
    FOREIGN KEY (application, dispatcher) REFERENCES email_dispatcher(application, name) ON DELETE CASCADE ON UPDATE CASCADE,

    default_email_signup boolean,
    check (default_email_signup is not false),
    default_email_already_signed_up boolean,
    check (default_email_already_signed_up is not false),
    default_reset_password boolean,
    check (default_reset_password is not false)
);
CREATE UNIQUE INDEX template_unq_signup ON email_template (name, application, default_email_signup);
CREATE UNIQUE INDEX template_unq_already_signed_up ON email_template (name, application, default_email_already_signed_up);
CREATE UNIQUE INDEX template_unq_reset_password ON email_template (name, application, default_reset_password);

-- account...
create table account (
    user_id postgres_addressable_name not null default gen_random_uuid(),
    username character varying(255) not null,
    deleted boolean default false,
    password uuid,
    primary key (user_id));
CREATE UNIQUE INDEX account_unq_email ON account (username);
-- account_password...
create table account_password (
    id uuid primary key not null default gen_random_uuid(),
    account postgres_addressable_name not null,
    password_hash character varying(512) not null,
    created timestamp not null default current_timestamp,
    unique(account, password_hash)
);

alter table account add constraint account_current_password__account
    foreign key (password)
        references account_password (id);

-- account_password...
alter table account_password add constraint account_password__account
    foreign key (account)
        references account (user_id) ON DELETE CASCADE;
-- application_schema...
alter table application_schema add constraint application_schema__application
    foreign key (application)
        references application (name) ON DELETE CASCADE ON UPDATE CASCADE;

create function account_id_from_username(enc_username text) returns postgres_addressable_name as
$$
DECLARE
    account_id postgres_addressable_name;
BEGIN
    SELECT user_id INTO account_id FROM account WHERE username = enc_username;
    return account_id;
END
$$ language plpgsql;

create function attach_account(account_id postgres_addressable_name, enc_username text) returns void as
$$
BEGIN
    INSERT INTO account (username, user_id) VALUES (enc_username, account_id);
END
$$ language plpgsql;

create function close_my_account() returns void as
$$
BEGIN
    UPDATE account SET deleted = current_timestamp WHERE user_id = session_user;
END
$$ language plpgsql SECURITY DEFINER;
GRANT execute on function close_my_account() to registered;

create table renderable_document (
    name      varchar(40) NOT null,
    application character varying(63) not null,
    PRIMARY KEY (name, application),
    FOREIGN KEY (application) REFERENCES application(name) ON UPDATE CASCADE ON DELETE CASCADE,
    url       text not null,
    render_as varchar(10) default 'pdf' not null,
    check (render_as in ('pdf'))
);

create table renderable_document_template (
    attachment varchar(40) not null,
    template   varchar(60) not null,
    application character varying(63) not null,
    PRIMARY KEY (attachment, template, application),
    FOREIGN KEY (template, application) references email_template(name, application) ON DELETE CASCADE,
    FOREIGN KEY (attachment, application) references renderable_document(name, application) ON DELETE CASCADE
);

create table account_ip (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    account postgres_addressable_name not null,
    encrypted_address varchar(255),
    first_login timestamptz not null default current_timestamp,
    most_recent_login timestamptz not null default current_timestamp,
    FOREIGN KEY (account) REFERENCES account ON DELETE CASCADE,
    constraint user_ip_unq unique (encrypted_address)  -- Technically unique (user, address) but we are encrypting the ip in such a way that it's unique for the user
);

create table log (
    id uuid primary key not null default gen_random_uuid(),
    the_user postgres_addressable_name,
    occurred timestamptz not null default current_timestamp,
    duration_ms integer not null,
    encrypted_exception text,
    encrypted_input text,
    login_ip uuid not null,
    status int not null,
    endpoint varchar(64) not null,
    FOREIGN KEY (the_user) REFERENCES account ON DELETE CASCADE,
    FOREIGN KEY (login_ip) REFERENCES account_ip
);

create view my_logs as (
    SELECT
        log.occurred,
        ip.encrypted_address,
        log.status,
        log.endpoint,
        log.duration_ms,
        log.encrypted_exception
    FROM
         log
    INNER JOIN account us ON us.user_id = log.the_user AND us.deleted is null AND us.user_id = session_user
    INNER JOIN account_ip ip ON log.login_ip = ip.id
    ORDER BY occurred DESC
);
grant select on my_logs to registered;

create view my_ips as (
    SELECT
        encrypted_address,
        first_login,
        most_recent_login
    FROM
         account_ip ip
    INNER JOIN account us ON us.user_id = ip.account AND us.deleted is null AND us.user_id = session_user
    ORDER BY first_login DESC
);
grant select on my_ips to registered;

create view fetch_recent_passwords as (
    SELECT
        a.user_id,
        ap.id as password_id,
        a.username,
        password_hash
    FROM
         account a
    INNER JOIN
        account_password ap on ap.id = a.password
);

create view fetch_recent_passwords_with_ips as (
    SELECT
        user_id,
        password_id,
        username,
        password_hash,
        juip.encrypted_address
    FROM
         fetch_recent_passwords frp
    INNER JOIN
        account_ip juip ON juip.account = user_id
);

create table sign_up (
    key_a uuid PRIMARY KEY not null default gen_random_uuid(),
    key_b uuid not null default gen_random_uuid(),
    invite_code varchar(5) not null,
    code_attempts int default 0 not null,
    activated boolean not null default false,
    used_key_a boolean not null default false,
    account postgres_addressable_name not null,
    FOREIGN KEY (account) REFERENCES account ON DELETE CASCADE,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 24 * 14, -- 2 weeks
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes
    email_template varchar(60),
    application character varying(63) not null,
    FOREIGN KEY (email_template, application) REFERENCES email_template (name, application) ON DELETE CASCADE ON UPDATE CASCADE,
    data_lookup_json text,
    check ((data_lookup_json is null and email_template is null) or email_template is not null)
);
CREATE UNIQUE INDEX sign_up_unq_key_b ON sign_up (key_b);

create table reset_password (
    key_a uuid PRIMARY KEY not null default gen_random_uuid(),
    key_b uuid not null default gen_random_uuid(),
    reset_code varchar(8) not null,
    code_attempts int default 0 not null,
    activated boolean not null default false,
    used_key_a boolean not null default false,
    the_user postgres_addressable_name not null,
    FOREIGN KEY (the_user) REFERENCES account ON DELETE CASCADE,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 2, -- 2 hours. Important this is the same as above fake table
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes. Important this is the same as above fake table
    email_template varchar(60),  -- Deliberately null as we can have a reset password managed by the admin
    application character varying(63) not null,
    data_lookup_json text,
    FOREIGN KEY (email_template, application) REFERENCES email_template(name, application) ON DELETE CASCADE ON UPDATE CASCADE,
);

create table fake_reset_password (
    key_b uuid PRIMARY KEY not null default gen_random_uuid(),
    email text NOT NULL,
    created timestamptz default current_timestamp not null,
    code_attempts int default 0 not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 2, -- 2 hours
    code_expiry_ms integer not null default 1000 * 60 * 15 -- 15 minutes
);

create table email_history (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    template varchar(60) not null,
    application character varying(63) not null,
    override_send_name varchar(255),
    FOREIGN KEY (template, application) REFERENCES email_template(name, application) ON DELETE SET NULL,
    sender postgres_addressable_name not null,
    FOREIGN KEY (sender) REFERENCES account ON DELETE CASCADE,
    sent timestamptz not null default current_timestamp,
    encrypted_subject text,
    encrypted_recipients text not null,
    encrypted_recipients_keys text not null,
    encrypted_body text,
    encrypted_attachments text
);

create table rendered_document (
    document_id uuid PRIMARY KEY not null default gen_random_uuid(),
    document varchar(40) NOT NULL,
    application character varying(63) not null,
    FOREIGN KEY (application) REFERENCES application(name) ON DELETE CASCADE,
    created timestamptz not null default current_timestamp,
    encrypted_parameters text,
    encrypted_access_token text,
    create_file boolean not null,
    FOREIGN KEY (document, application) REFERENCES renderable_document(name, application) ON DELETE CASCADE,
    completed timestamptz,
    content bytea,
    filename varchar(100),
    check ((completed is null) or (filename is not null))
);
