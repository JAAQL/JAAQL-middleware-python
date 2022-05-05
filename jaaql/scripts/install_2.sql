CREATE DOMAIN jaaql__email AS varchar(254) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$' OR VALUE IN ('jaaql', 'superjaaql')) AND lower(VALUE) = VALUE);

create table jaaql__user (
    id uuid primary key not null default gen_random_uuid(),
    email    jaaql__email not null,
    created timestamptz not null default current_timestamp,
    mobile   bigint,                 -- with null [allows for SMS-based 2FA login later] )
    deleted timestamptz,
    enc_totp_iv varchar(254),
    last_totp varchar(6),
    alias varchar(32)
);
CREATE UNIQUE INDEX jaaql__user_unq_email ON jaaql__user (email) WHERE (deleted is null);

create table jaaql__user_ip (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    the_user uuid not null,
    address_hash varchar(254),
    encrypted_address varchar(255),
    first_use timestamptz not null default current_timestamp,
    most_recent_use timestamptz not null default current_timestamp,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    constraint jaaql__user_ip_unq unique (the_user, address_hash)
);

create table jaaql__user_ua (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    the_user uuid not null,
    ua_hash varchar(254),
    encrypted_ua varchar(512),
    first_use timestamptz not null default current_timestamp,
    most_recent_use timestamptz not null default current_timestamp,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    constraint jaaql__user_ua_unq unique (the_user, ua_hash)
);

create table jaaql__user_password (
    the_user uuid not null,
    created timestamptz not null default current_timestamp,
    password_hash varchar(254) not null,
    PRIMARY KEY (the_user, created),
    FOREIGN KEY (the_user) REFERENCES jaaql__user
);

create view jaaql__user_latest_password as (
    SELECT
        us.id,
        us.email,
        password_hash,
        us.enc_totp_iv,
        us.last_totp
    FROM
        (SELECT
            the_user,
            password_hash,
            row_number() over (PARTITION BY the_user) as change_count
        FROM jaaql__user_password
        ORDER BY created desc) as sub
    INNER JOIN
        jaaql__user us ON us.id = the_user
    WHERE
        sub.change_count <= 1 AND us.deleted is null
);

create table jaaql__node (
    name varchar(255) primary key not null,
    description varchar(255) not null,
    port integer not null,
	address varchar(255) not null,
	interface_class varchar(20) not null,
	deleted timestamptz
);

CREATE UNIQUE INDEX jaaql__node_unq
    ON jaaql__node (address, port) WHERE (deleted is null);

create table jaaql__database (
    node varchar(255) not null references jaaql__node on update cascade on delete cascade,
	name varchar(255) not null,
	deleted timestamptz,
	PRIMARY KEY (node, name)
);

create table jaaql__application (
    name varchar(64) not null primary key,
    description varchar(256) not null,
    url text not null,
    created timestamptz not null default current_timestamp
);

INSERT INTO jaaql__application (name, description, url) VALUES ('console', 'The console application', '');
INSERT INTO jaaql__application (name, description, url) VALUES ('manager', 'The administration panel for JAAQL', '');
INSERT INTO jaaql__application (name, description, url) VALUES ('playground', 'Allows testing for new JAAQL/JEQL features', '');

create table jaaql__application_dataset (
    application varchar(64) not null,
    name varchar(64) not null,
    description varchar(255) not null,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);
INSERT INTO jaaql__application_dataset (application, name, description) VALUES ('console', 'node', 'The node which the console will run against');
INSERT INTO jaaql__application_dataset (application, name, description) VALUES ('manager', 'node', 'A jaaql node which the app can manage');
INSERT INTO jaaql__application_dataset (application, name, description) VALUES ('playground', 'node', 'A jaaql node which the app can manage');

create table jaaql__application_configuration (
    application varchar(64) not null,
    name varchar(64) not null,
    description varchar(256) not null,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);
INSERT INTO jaaql__application_configuration (application, name, description) VALUES ('manager', 'host', 'The host jaaql node');
INSERT INTO jaaql__application_configuration (application, name, description) VALUES ('playground', 'host', 'The host jaaql node');

create table jaaql__assigned_database (
    application varchar(64) not null,
    configuration varchar(64) not null,
    database varchar(255) not null,
    node varchar(255) not null,
    dataset varchar(64) not null,
    PRIMARY KEY (application, dataset, configuration),
    FOREIGN KEY (application, configuration) references jaaql__application_configuration(application, name)
        on delete cascade on update cascade,
    FOREIGN KEY (application, dataset) references jaaql__application_dataset(application, name) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (database, node) references jaaql__database(name, node) on delete cascade on update cascade,
    FOREIGN KEY (node) references jaaql__node (name) on delete cascade on update cascade
);

create view jaaql__configuration_assigned_database as (
    SELECT
        db_conf.application as application,
    	db_conf.name as configuration,
    	db_dataset.name as dataset,
        db_dataset.description as dataset_description,
    	db_arg.database as database,
        db_arg.node as node
    FROM
    	jaaql__application_configuration db_conf
    INNER JOIN jaaql__application_dataset db_dataset ON db_conf.application = db_dataset.application
    LEFT JOIN jaaql__assigned_database db_arg
        ON db_conf.application = db_arg.application AND
           db_conf.name = db_arg.configuration AND
           db_arg.dataset = db_dataset.name
    LEFT JOIN jaaql__database jd on db_arg.database = jd.name AND db_arg.node = jd.node AND jd.deleted is null
);

-- Complete configurations. Where each dataset for the application has an assigned database
create view jaaql__complete_configuration as (
    SELECT
        *
    FROM
         jaaql__configuration_assigned_database
    WHERE (application, configuration, true) IN (
        SELECT
            application, configuration, bool_and(database is not null)
        FROM
             jaaql__configuration_assigned_database
        GROUP BY
            application, configuration
    )
);

create table jaaql__authorization_configuration (
    application varchar(64) not null references jaaql__application on delete cascade on update cascade,
    configuration varchar(64) not null,
    role        varchar(254) not null default '',
    primary key (application, configuration, role),
    foreign key (application, configuration) references jaaql__application_configuration on delete cascade on update cascade
);

create table jaaql__default_role (
    the_role varchar(255) PRIMARY KEY not null
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
    the_user uuid,
    occurred timestamptz not null default current_timestamp,
    duration_ms integer not null,
    encrypted_exception text,
    encrypted_input text,
    ip uuid not null,
    ua uuid,
    status int not null,
    endpoint varchar(64) not null,
    FOREIGN KEY (the_user) REFERENCES jaaql__user,
    FOREIGN KEY (ua) REFERENCES jaaql__user_ua,
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
        ua.encrypted_ua,
        log.status,
        log.endpoint,
        log.duration_ms,
        log.encrypted_exception
    FROM
         jaaql__log log
    INNER JOIN jaaql__user us ON us.id = log.the_user AND us.deleted is null AND us.email = current_user
    INNER JOIN jaaql__user_ip ip ON log.ip = ip.id
    LEFT JOIN jaaql__user_ua ua ON log.ua = ua.id
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

create view jaaql__my_configurations as (
    SELECT
        DISTINCT
        ac.application,
        ac.name as configuration,
        ap.description as application_description,
        ac.description as configuration_description
    FROM
         jaaql__application_configuration ac
    INNER JOIN jaaql__authorization_configuration auth_conf ON ac.name = auth_conf.configuration AND ac.application = auth_conf.application AND (auth_conf.role = '' or pg_has_role(auth_conf.role, 'MEMBER'))
    INNER JOIN jaaql__application ap on ap.name = ac.application);
grant select on jaaql__my_configurations to public;

create view jaaql__my_applications as (
    SELECT
        DISTINCT
        ap.name,
        ap.description,
        ap.url
    FROM jaaql__application ap
    INNER JOIN jaaql__my_configurations mc ON mc.application = ap.name
);
grant select on jaaql__my_applications to public;

create view jaaql__their_authorized_app_only_configurations as (
    SELECT
        comc.application,
        comc.configuration,
        auth_conf.role as conf_role
    FROM jaaql__complete_configuration comc
    INNER JOIN jaaql__authorization_configuration auth_conf on comc.application = auth_conf.application AND comc.configuration = auth_conf.configuration
);

-- Not my. Called through jaaql connection. Need to keep username and password secret
create view jaaql__their_authorized_configurations as (
    SELECT
        comc.application,
        comc.configuration,
        comc.dataset,
        comc.dataset_description,
        jcred.db_encrypted_username as username,
        jcred.db_encrypted_password as password,
        comc.database,
        comc.node as node,
        jcred.id as cred_id,
        jn.port,
        jn.address,
        jcred.precedence,
        jcred.role as node_role
    FROM jaaql__complete_configuration comc
        INNER JOIN jaaql__credentials_node jcred ON (jcred.node = comc.node) AND jcred.deleted is null
        INNER JOIN jaaql__node jn on comc.node = jn.name AND jn.deleted is null
);

create view jaaql__their_single_authorized_wildcard_node as (
    SELECT
        jn.name as node,
        jn.address,
        jn.port,
        cred.role,
        cred.precedence,
        cred.db_encrypted_username as username,
        cred.db_encrypted_password as password
    FROM
        jaaql__credentials_node cred
    INNER JOIN
        jaaql__database jd on cred.node = jd.node
    INNER JOIN
        jaaql__node jn on cred.node = jn.name
    WHERE jd.name = '*' AND jd.deleted is null AND cred.deleted is null AND jn.deleted is null
);

-- DO NOT CHANGE FUNCTION BELOW WITHOUT CONSIDERING SECURITY!!!
-- We require this function as 'CREATE ROLE IF NOT EXISTS' is not a postgres thing
-- Despite the fact that we use parameters for the SELECT call to this in __attach_or_add_user
-- If the variables username and password are strings, they can contain SQL injectable strings
-- To prevent this we use 'quote_ident' and 'quote_literal'.
-- 'quote_ident' forces everything to be within "" (and will escape any double quotes within)
-- 'quote_literal' is similar but forces everything to be within '' (and will escape any single quotes within)
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

--Same security concerns as above
create function jaaql__delete_user(delete_email text) returns void as
$$
BEGIN
    EXECUTE 'DROP ROLE ' || quote_ident(delete_email);
    UPDATE jaaql__user SET deleted = current_timestamp WHERE email = delete_email;
    UPDATE jaaql__credentials_node SET deleted = current_timestamp WHERE role = delete_email;
END
$$ language plpgsql;

create function jaaql__fetch_alias(username text) returns text as
$$
DECLARE
    actual_alias text;
BEGIN
    SELECT coalesce(alias, email) into actual_alias FROM jaaql__user WHERE email = username;
    return actual_alias;
END
$$ language plpgsql;

create function jaaql__fetch_alias_from_id(userid text) returns text as
$$
DECLARE
    actual_alias text;
BEGIN
    SELECT coalesce(alias, email) into actual_alias FROM jaaql__user WHERE id = userid::uuid;
    return actual_alias;
END
$$ language plpgsql;

create function jaaql__create_node(node_name text, node_address text, node_port integer, node_description text) returns character varying as
$$
DECLARE
    node_id character varying;
BEGIN
    INSERT INTO jaaql__node (name, description, port, address, interface_class) VALUES (coalesce(node_name, node_address || node_port), coalesce(node_description, 'The ' || node_name || ' node'), node_port, node_address, 'DBPGInterface') RETURNING name into node_id;
    INSERT INTO jaaql__database (node, name) VALUES (node_id, '*');
    INSERT INTO jaaql__application_configuration (application, name, description) VALUES ('console', node_id, 'Console access to the ' || node_id || ' node');
    INSERT INTO jaaql__assigned_database (application, configuration, node, database, dataset) VALUES ('console', node_id, node_id, '*', 'node');
    return node_id;
END
$$ language plpgsql;

create or replace function jaaql__delete_node(node_name text) returns void as
$$
BEGIN
    UPDATE jaaql__node SET "name" = (left("name", 180) || '_deleted_') || current_timestamp::text, deleted = current_timestamp WHERE name = node_name;
END
$$ language plpgsql;

create table jaaql__email_accounts (
    account_name varchar(255) PRIMARY KEY not null,
    send_name varchar(255) not null,
    protocol varchar(4) not null,
    check (protocol in ('smtp', 'imap')),
    host varchar(255) not null,
    port integer not null,
    username varchar(255) not null,
    deleted timestamptz default null
);

create table jaaql__email_history (
    email_account varchar(255) not null,
    FOREIGN KEY (email_account) references jaaql__email_accounts,
    sent timestamptz not null default current_timestamp,
    encrypted_subject text,
    encrypted_recipients text,
    encrypted_body text,
    encrypted_attachments text
);

INSERT INTO jaaql__email_accounts (account_name, send_name, protocol, host, port, username) VALUES ('jaaql', 'JAAQL Emails', 'smtp', 'web119.shared.hosting-login.net', 587, 'aaron.tasker@sqmi.nl');