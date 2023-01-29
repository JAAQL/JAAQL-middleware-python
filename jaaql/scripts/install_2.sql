CREATE ROLE registered;
CREATE ROLE anonymous;
CREATE DOMAIN safe_path AS varchar(255) CHECK (VALUE ~* '^[a-z0-9_\-\/]+(.[a-zA-Z0-9]+)?$');

-- Install script
-- (1) Create tables

-- Selecting from this table will verify if the connected account can check admin accounts
create table check_admin (
    singleton int primary key not null,
    check (singleton = 0)
);
INSERT INTO check_admin (singleton) VALUES (0);

create table application (
    description varchar(256) not null,
    name character varying(63) not null,
    primary key (name) );

-- application_schema...
create table application_schema (
    application character varying(63) not null,
    name character varying(63) not null,
    is_default boolean not null default false,
    primary key (application, name) );
CREATE UNIQUE INDEX application_schema_one_default ON application_schema (application, is_default) WHERE is_default;

-- application_database...
create table application_database (
    application character varying(63) not null,
    configuration character varying(63) not null,
    schema character varying(63) not null,
    database character varying(63) not null,
    primary key (application, configuration, schema, database) );

create table email_account (
    name varchar(60) not null,
    PRIMARY KEY (name),
    send_name varchar(255) not null,
    protocol varchar(4) not null,
    check (protocol in ('smtp')),
    host varchar(255) not null,
    port integer not null,
    username varchar(255) not null,
    encrypted_password text not null
);

create table email_template (
    name varchar(60) NOT NULL,
    application character varying(63) not null,
    PRIMARY KEY (name, application),
    FOREIGN KEY (application) REFERENCES application(name) ON UPDATE CASCADE ON DELETE CASCADE,
    subject varchar(255),
    description text,
    app_relative_path safe_path,  -- Not a mistake for this domain type. Means app_relative_path cannot be ../../secret. Also secured at application level code in case db is tampered with
    check ((subject is null) = (app_relative_path is null)),
    schema character varying(63),
    FOREIGN KEY (schema, application) REFERENCES application_schema(name, application),
    data_validation_table postgres_addressable_name,
    data_validation_view postgres_addressable_name,
    CHECK ((data_validation_table is null and data_validation_view is null) or data_validation_table is not null),
    recipient_validation_view postgres_addressable_name,
    check ((recipient_validation_view is null and data_validation_table is null) or schema is not null),
    allow_signup boolean default false not null,
    allow_confirm_signup_attempt boolean default false not null,
    allow_reset_password boolean default false not null,
    check (allow_signup::int + allow_confirm_signup_attempt::int + allow_reset_password::int < 2),
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

-- application_configuration...
create table application_configuration (
    application character varying(63) not null,
    url varchar(254) not null,
    artifact_base_uri varchar(254) not null,  --Used to load templates and renderable documents
    name character varying(63) not null,
    primary key (application, name)
);

create table email_template_configuration (
    application character varying(63) not null,
    configuration character varying(63) not null,
    template varchar(60) not null,
    account varchar(60) NOT NULL,
    override_send_name varchar(255),
    primary key (application, configuration, template),
    FOREIGN KEY (account) REFERENCES email_account(name) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (application, template) REFERENCES email_template(application, name) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (application) REFERENCES application(name) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (application, configuration) REFERENCES application_configuration(application, name) ON UPDATE CASCADE ON DELETE CASCADE
);

-- account...
create table account (
    user_id jaaql_account_id not null default gen_random_uuid(),
    username character varying(255) not null,
    deleted boolean default false,
    password uuid,
    public_password text,
    primary key (user_id));
CREATE UNIQUE INDEX account_unq_email ON account (username);
-- account_password...
create table account_password (
    id uuid primary key not null default gen_random_uuid(),
    account jaaql_account_id not null,
    password_hash character varying(512) not null,
    created timestamp not null default current_timestamp,
    unique(account, password_hash)
);

alter table account add constraint account_current_password__account
    foreign key (password)
        references account_password (id);

create view application_schemas as (
    SELECT
        app.name,
        ac.name as configuration_name,
        ac.url as configuration_url,
        asch.name as schema_name,
        ad.database as schema_database,
        asch.is_default as schema_is_default
    FROM
        application app
    INNER JOIN application_configuration ac ON app.name = ac.application
    INNER JOIN application_schema asch ON app.name = asch.application
    LEFT JOIN application_database ad ON asch.application = ad.application AND asch.name = ad.schema AND ac.name = ad.configuration
    ORDER BY app.name, configuration, schema
);

create view my_email_template_defaults as (
    SELECT
        app.name as application,
        etds.name as default_email_signup_template,
        etdas.name as default_email_already_signed_up_template,
        etdr.name as default_reset_password_template
    FROM
        application app
    LEFT JOIN email_template etds on app.name = etds.application AND etds.default_email_signup
    LEFT JOIN email_template etdas on app.name = etdas.application AND etdas.default_email_already_signed_up
    LEFT JOIN email_template etdr on app.name = etdr.application AND etdr.default_reset_password
    ORDER BY app.name
);
GRANT SELECT ON my_email_template_defaults TO PUBLIC;

create function add_email_account(name varchar(60), send_name varchar(255), host varchar(255), port integer, username varchar(255), encrypted_password text) returns void as
$$
BEGIN
    INSERT INTO email_account (name, send_name, protocol, host, port, username, encrypted_password)
    VALUES (add_email_account.name, add_email_account.send_name, 'smtp',
            add_email_account.host, add_email_account.port, add_email_account.username,
            add_email_account.encrypted_password);
END
$$ language plpgsql SECURITY DEFINER;

create function drop_email_account(name varchar(60)) returns void as
$$
BEGIN
    DELETE FROM email_account WHERE email_account.name = drop_email_account.name;
END
$$ language plpgsql SECURITY DEFINER;

create function register_email_template(name varchar(60), application character varying(63), subject varchar(255),
                                        description text, app_relative_path safe_path = null, schema character varying(63) = null,
                                        data_validation_table postgres_addressable_name = null, data_validation_view postgres_addressable_name = null, recipient_validation_view postgres_addressable_name = null,
                                        allow_signup boolean = false, allow_confirm_signup_attempt boolean = false, allow_reset_password boolean = false,
                                        default_email_signup boolean = null, _default_email_already_signed_up boolean = null, default_reset_password boolean = null) returns void as
$$
BEGIN
    if register_email_template.default_email_signup is false then
        register_email_template.default_email_signup = null;
    end if;
    if _default_email_already_signed_up is false then
        _default_email_already_signed_up = null;
    end if;
    if register_email_template.default_reset_password is false then
        register_email_template.default_reset_password = null;
    end if;
    INSERT INTO email_template(name, application,
                               subject, description, app_relative_path,
                               schema, data_validation_table, data_validation_view,
                               recipient_validation_view, allow_signup, allow_confirm_signup_attempt,
                               allow_reset_password, default_email_signup, default_email_already_signed_up,
                               default_reset_password) VALUES (
                                                                                           register_email_template.name, register_email_template.application,
                                                                                           register_email_template.subject, register_email_template.description, register_email_template.app_relative_path,
                                                                                           register_email_template.schema, register_email_template.data_validation_table, register_email_template.data_validation_view,
                                                                                           register_email_template.recipient_validation_view, register_email_template.allow_signup, register_email_template.allow_confirm_signup_attempt,
                                                                                           register_email_template.allow_reset_password, register_email_template.default_email_signup, _default_email_already_signed_up,
                                                                                           register_email_template.default_reset_password);
END
$$ language plpgsql SECURITY DEFINER;

create function deregister_email_template(_name varchar(60)) returns void as
$$
BEGIN
    DELETE FROM email_template WHERE name = _name;
END
$$ language plpgsql SECURITY DEFINER;

create function associate_email_template_with_application_configuration(template varchar(60), application character varying(63), configuration varchar(63),
                                                                        account varchar(60), override_send_name varchar(255) = null) returns void as
$$
BEGIN
    INSERT INTO email_template_configuration(application, configuration,
                                             template, account, override_send_name)
                                             VALUES (associate_email_template_with_application_configuration.application, associate_email_template_with_application_configuration.configuration,
                                                     associate_email_template_with_application_configuration.template, associate_email_template_with_application_configuration.account,
                                                     associate_email_template_with_application_configuration.override_send_name);
END
$$ language plpgsql SECURITY DEFINER;

create function disassociate_email_template_with_application_configuration(template varchar(60), application character varying(63), configuration varchar(63)) returns void as
$$
BEGIN
    DELETE FROM email_template_configuration etc WHERE etc.application = disassociate_email_template_with_application_configuration.application
                                                 AND etc.template = disassociate_email_template_with_application_configuration.template
                                                 AND etc.configuration = disassociate_email_template_with_application_configuration.configuration;
END
$$ language plpgsql SECURITY DEFINER;

-- account_password...
alter table account_password add constraint account_password__account
    foreign key (account)
        references account (user_id) ON DELETE CASCADE;
-- application_schema...
alter table application_schema add constraint application_schema__application
    foreign key (application)
        references application (name) ON DELETE CASCADE ON UPDATE CASCADE;
-- application_configuration...
alter table application_configuration add constraint application_configuration__application
    foreign key (application)
        references application (name) ON DELETE CASCADE ON UPDATE CASCADE;
-- application_database...
alter table application_database add constraint application_database__configuration
    foreign key (application, configuration)
        references application_configuration (application, name) ON DELETE CASCADE ON UPDATE CASCADE;
alter table application_database add constraint application_database__schema
    foreign key (application, schema)
        references application_schema (application, name) ON DELETE CASCADE ON UPDATE CASCADE;

create function account_id_from_username(enc_username text) returns jaaql_account_id as
$$
DECLARE
    account_id jaaql_account_id;
BEGIN
    SELECT user_id INTO account_id FROM account WHERE username = enc_username;
    return account_id;
END
$$ language plpgsql;

create function attach_account(account_id jaaql_account_id, enc_username text) returns void as
$$
BEGIN
    INSERT INTO account (username, user_id) VALUES (enc_username, account_id);
END
$$ language plpgsql;

create function create_account(enc_username text, is_public boolean = false) returns jaaql_account_id as
$$
DECLARE
    account_id jaaql_account_id;
BEGIN
    INSERT INTO account (username) VALUES (enc_username) RETURNING user_id INTO account_id;
    EXECUTE 'CREATE ROLE ' || quote_ident(account_id);
    if is_public then
        EXECUTE 'GRANT anonymous TO ' || quote_ident(account_id);
    else
        EXECUTE 'GRANT registered TO ' || quote_ident(account_id);
    end if;
    return account_id;
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

create function setup() returns void as
$$
BEGIN
    INSERT INTO application (name, description) VALUES ('console', 'The console application');

    INSERT INTO application (name, description) VALUES ('manager', 'The administration panel for JAAQL');
    INSERT INTO application_schema (application, name) VALUES ('manager', 'default');
    INSERT INTO application_configuration (application, name, url, artifact_base_uri) VALUES ('manager', 'default', '', '');
    INSERT INTO application_database (application, configuration, schema, database) VALUES ('manager', 'default', 'default', 'jaaql');

    INSERT INTO application (name, description) VALUES ('playground', 'Allows testing for new JAAQL/JEQL features');
    INSERT INTO application_schema (application, name) VALUES ('playground', 'default');
    INSERT INTO application_configuration (application, name, url, artifact_base_uri) VALUES ('playground', 'default', '', '');
    INSERT INTO application_database (application, configuration, schema, database) VALUES ('playground', 'default', 'default', 'play_db');
END
$$ language plpgsql;

create table account_ip (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    account jaaql_account_id not null,
    encrypted_address varchar(255),
    first_login timestamptz not null default current_timestamp,
    most_recent_login timestamptz not null default current_timestamp,
    FOREIGN KEY (account) REFERENCES account ON DELETE CASCADE,
    constraint user_ip_unq unique (encrypted_address)  -- Technically unique (user, address) but we are encrypting the ip in such a way that it's unique for the user
);

create table log (
    id uuid primary key not null default gen_random_uuid(),
    the_user jaaql_account_id,
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
    account jaaql_account_id not null,
    FOREIGN KEY (account) REFERENCES account ON DELETE CASCADE,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 24 * 14, -- 2 weeks
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes
    email_template varchar(60),
    configuration varchar(63),
    application character varying(63),
    check ((application is null) = (configuration is null)),
    FOREIGN KEY (email_template, application) REFERENCES email_template (name, application) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (email_template, application, configuration) REFERENCES email_template_configuration (template, application, configuration) ON DELETE CASCADE ON UPDATE CASCADE,
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
    the_user jaaql_account_id not null,
    FOREIGN KEY (the_user) REFERENCES account ON DELETE CASCADE,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 2, -- 2 hours. Important this is the same as above fake table
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes. Important this is the same as above fake table
    email_template varchar(60),  -- Deliberately null as we can have a reset password managed by the admin
    application character varying(63),
    configuration varchar(63),
    check ((application is null) = (configuration is null)),
    data_lookup_json text,
    FOREIGN KEY (email_template, application) REFERENCES email_template(name, application) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (email_template, application, configuration) REFERENCES email_template_configuration (template, application, configuration) ON DELETE CASCADE ON UPDATE CASCADE
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
    sender jaaql_account_id not null,
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
    configuration character varying(63) not null,
    FOREIGN KEY (application) REFERENCES application(name) ON DELETE CASCADE,
    FOREIGN KEY (application, configuration) REFERENCES application_configuration (application, name),
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
