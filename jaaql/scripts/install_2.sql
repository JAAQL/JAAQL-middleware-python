CREATE DOMAIN jaaql__email AS varchar(254) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$' OR VALUE IN ('jaaql', 'superjaaql')) AND lower(VALUE) = VALUE);

create table jaaql__user (
    id uuid primary key not null default gen_random_uuid(),
    email    jaaql__email not null,
    created timestamptz not null default current_timestamp,
    mobile   bigint,                 -- with null [allows for SMS-based 2FA login later] )
    deleted timestamptz,
    enc_totp_iv varchar(254) not null,
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
    id uuid primary key not null default gen_random_uuid(),
    name varchar(255) not null,
    description varchar(255) not null,
    port integer not null,
	address varchar(255) not null,
	interface_class varchar(20) not null,
	deleted timestamptz
);
CREATE UNIQUE INDEX jaaql__node_unq_name
    ON jaaql__node (name) WHERE (deleted is null);
CREATE UNIQUE INDEX jaaql__node_unq
    ON jaaql__node (address, port) WHERE (deleted is null);

create table jaaql__database (
    id uuid primary key not null default gen_random_uuid(),
    node uuid not null references jaaql__node,
	name varchar(255) not null,
	deleted timestamptz
);
--Cannot duplicate name on node
CREATE UNIQUE INDEX jaaql__database_unq
    ON jaaql__database (name, node) WHERE (deleted is null);

create table jaaql__application (
    name varchar(64) not null primary key,
    description varchar(256) not null,
    url text not null,
    created timestamptz not null default current_timestamp
);

INSERT INTO jaaql__application (name, description, url) VALUES ('console', 'The console application', '');

create table jaaql__application_parameter (
    application varchar(64) not null,
    name varchar(64) not null,
    description varchar(255) not null,
    is_node boolean not null default false,
    PRIMARY KEY (application, name, is_node),  -- Fake primary key used for checking node match
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);
-- Real primary key here. Alternative solution is to use a trigger which is messy
CREATE UNIQUE INDEX jaaql__application_parameter_unq ON jaaql__application_parameter (application, name);

create table jaaql__application_configuration (
    application varchar(64) not null,
    name varchar(64) not null,
    description varchar(256) not null,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);

create table jaaql__application_argument (
    application varchar(64) not null,
    configuration varchar(64) not null,
    database uuid,
    node uuid,

    -- generated column to avoid trigger. Can now use a foreign key
    is_node boolean GENERATED ALWAYS AS (node is not null) STORED,

    CHECK ((database is null) <> (node is null)),
    parameter varchar(64) not null,
    PRIMARY KEY (application, parameter, configuration),
    FOREIGN KEY (application, configuration) references jaaql__application_configuration
        on delete cascade on update cascade,
    FOREIGN KEY (application, parameter) references jaaql__application_parameter(application, name) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (application, parameter, is_node) references jaaql__application_parameter(application, name, is_node),
    FOREIGN KEY (database) references jaaql__database,
    FOREIGN KEY (node) references jaaql__node
);

--Configurations with any missing parameters highlighted
create view jaaql__configuration_argument as (
    SELECT
        db_conf.application as application,
    	db_conf.name as configuration,
    	db_param.name as parameter_name,
        db_param.description as parameter_description,
    	coalesce(db_arg.database, db_arg.node) as argument,
        db_arg.is_node
    FROM
    	jaaql__application_configuration db_conf
    INNER JOIN jaaql__application_parameter db_param ON db_conf.application = db_param.application
    LEFT JOIN jaaql__application_argument db_arg
        ON db_conf.application = db_arg.application AND
           db_conf.name = db_arg.configuration AND
           db_arg.parameter = db_param.name
    LEFT JOIN jaaql__database jd on db_arg.database = jd.id AND jd.deleted is null
    LEFT JOIN jaaql__node jn on db_arg.node = jn.id AND jn.deleted is null
);

-- Complete configurations. Where each parameter for the application has an associated argument
create view jaaql__complete_configuration as (
    SELECT
        *
    FROM
         jaaql__configuration_argument
    WHERE (application, configuration, true) IN (
        SELECT
            application, configuration, bool_and(argument is not null)
        FROM
             jaaql__configuration_argument
        GROUP BY
            application, configuration
    )
);

create table jaaql__authorization_application (
    application varchar(64) not null references jaaql__application on delete cascade on update cascade,
    role        varchar(254) not null default '',
    primary key (application, role)
);

INSERT INTO jaaql__authorization_application (application) VALUES ('console');

create table jaaql__authorization_node (
    id uuid PRIMARY KEY not null default gen_random_uuid(),
    node uuid not null references jaaql__node,
    role varchar(254),
    deleted timestamptz,
    db_encrypted_username varchar(254) not null,
	db_encrypted_password varchar(254) not null,
	precedence int not null default 0
);
CREATE UNIQUE INDEX jaaql__authorization_node_unq
    ON jaaql__authorization_node (node, role) WHERE (deleted is null);

create table jaaql__authorization_node_database (
    "authorization" uuid not null references jaaql__authorization_node,
    "database" uuid not null references jaaql__database,
    PRIMARY KEY ("authorization", "database")
);

create table jaaql__authorization_node_database_upsert (
    "authorization" uuid not null references jaaql__authorization_node,
    "database" uuid not null references jaaql__database,
    PRIMARY KEY ("authorization", "database")
);

--TODO add node authorization and nullable db associated
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
    auth uuid not null,
    PRIMARY KEY (log, auth),
    FOREIGN KEY (log) REFERENCES jaaql__log,
    FOREIGN KEY (auth) REFERENCES jaaql__authorization_node
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
        sub.application,
        sub.configuration,
        ap.description as application_description,
        ac.description as configuration_description
    FROM
        (SELECT
            app_conf.application as application,
            app_conf.name as configuration
        FROM
             jaaql__authorization_application app_auth
        INNER JOIN jaaql__application_configuration app_conf ON app_auth.application = app_conf.application
        WHERE
            (app_conf.application, app_conf.name, true) IN (
                SELECT conf_arg.application,
                       conf_arg.configuration,
                       bool_and(node_auth.id is not null)
                FROM jaaql__complete_configuration conf_arg
                LEFT JOIN jaaql__authorization_node_database acd ON
                    conf_arg.argument = acd.database
                LEFT JOIN jaaql__authorization_node node_auth ON
                    ((acd."authorization" is not null AND acd."authorization" = node_auth.id) or
                    (conf_arg.argument = node_auth.node)) AND node_auth.deleted is null AND (node_auth.role = '' or pg_has_role(node_auth.role, 'MEMBER'))
                INNER JOIN jaaql__authorization_application app_auth ON app_auth.application = conf_arg.application AND (app_auth.role = '' or pg_has_role(app_auth.role, 'MEMBER'))
                GROUP BY conf_arg.application, conf_arg.configuration
            )
        GROUP BY app_conf.application, app_conf.name) as sub
    INNER JOIN jaaql__application_configuration ac ON ac.name = sub.configuration
    INNER JOIN jaaql__application ap on ap.name = sub.application);
grant select on jaaql__my_configurations to public;

-- Not my. Called through jaaql connection. Need to keep username and password secret
create view jaaql__their_authorized_configurations as (
    SELECT
        comc.application,
        comc.configuration,
        comc.parameter_name,
        comc.parameter_description,
        jand.db_encrypted_username as username,
        jand.db_encrypted_password as password,
        jd.id as database,
        jd.name as name,
        jand.node as node,
        jn.port,
        jn.address,
        jand.precedence,
        jand.role as node_role,
        ja.role as application_role
    FROM jaaql__complete_configuration comc
        LEFT JOIN jaaql__authorization_node_database jandat ON comc.argument = jandat.database
        LEFT JOIN jaaql__database jd ON jandat.database = jd.id
        INNER JOIN jaaql__authorization_node jand ON (jand.node = comc.argument or jand.id = jandat."authorization") AND jand.deleted is null
        INNER JOIN jaaql__authorization_application ja on comc.application = ja.application
        INNER JOIN jaaql__node jn on jand.node = jn.id
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
    UPDATE jaaql__authorization_node SET deleted = current_timestamp WHERE role = delete_email;
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
    SELECT coalesce(alias, email) into actual_alias FROM jaaql__user WHERE id = userid;
    return actual_alias;
END
$$ language plpgsql;

create function jaaql__create_node(node_name text, node_address text, node_port integer, node_description text) returns uuid as
$$
DECLARE
    node_id uuid;
BEGIN
    INSERT INTO jaaql__node (name, description, port, address, interface_class) VALUES (node_name, coalesce(node_description, 'The ' || node_name || ' node'), node_port, node_address, 'DBPGInterface') RETURNING id into node_id;
    INSERT INTO jaaql__application_configuration (application, name, description) VALUES ('console', 'Console ' || node_name || ' node', 'Console access to the ' || node_name || ' node');
    INSERT INTO jaaql__application_parameter (application, name, description, is_node) VALUES ('console', 'node', 'The node which the console will run against', true);
    INSERT INTO jaaql__application_argument (application, configuration, node, parameter) SELECT 'console', 'Console ' || node_name || ' node', id, 'node' FROM jaaql__node;
    return node_id;
END
$$ language plpgsql;
