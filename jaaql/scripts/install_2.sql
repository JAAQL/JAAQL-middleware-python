CREATE DOMAIN jaaql__email AS varchar(254) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$' OR VALUE = 'jaaql') AND lower(VALUE) = VALUE);

create table jaaql__user (
    id uuid primary key not null default gen_random_uuid(),
    email    jaaql__email not null,
    created timestamptz not null default current_timestamp,
    mobile   bigint,                 -- with null [allows for SMS-based 2FA login later] )
    deleted timestamptz,
    enc_totp_iv varchar(254) not null,
    last_totp varchar(6)
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

create table jaaql__database (
    id uuid primary key not null default gen_random_uuid(),
	name varchar(256) not null,
	description varchar(256) not null,
	port varchar(256) not null,
	address varchar(256) not null,
	jaaql_name varchar(64) not null,
	interface_class varchar(20) not null,
	is_console_level boolean not null,
	deleted timestamptz
);
CREATE UNIQUE INDEX jaaql__database_unq
    ON jaaql__database (jaaql_name) WHERE (deleted is null);

create table jaaql__application (
    name varchar(64) not null primary key,
    description varchar(256) not null,
    url text not null,
    created timestamptz not null default current_timestamp
);

create table jaaql__application_database_parameter (
    application varchar(64) not null,
    name varchar(64) not null,
    description varchar(255) not null,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);

create table jaaql__application_database_configuration (
    application varchar(64) not null,
    name varchar(64) not null,
    description varchar(256) not null,
    PRIMARY KEY (application, name),
    FOREIGN KEY (application) references jaaql__application on delete cascade on update cascade
);

create table jaaql__application_database_argument (
    application varchar(64) not null,
    configuration varchar(64) not null,
    database uuid not null,
    parameter varchar(64) not null,
    PRIMARY KEY (application, parameter, configuration),
    FOREIGN KEY (application, configuration) references jaaql__application_database_configuration
        on delete cascade on update cascade,
    FOREIGN KEY (application, parameter) references jaaql__application_database_parameter
        on delete cascade on update cascade,
    FOREIGN KEY (database) references jaaql__database
);

--Configurations with any missing parameters highlighted
create view jaaql__configuration_argument as (
    SELECT
        db_conf.application as application,
    	db_conf.name as configuration,
    	db_param.name as parameter_name,
        db_param.description as parameter_description,
    	db_arg.database as database
    FROM
    	jaaql__application_database_configuration db_conf
    INNER JOIN jaaql__application_database_parameter db_param ON db_conf.application = db_param.application
    LEFT JOIN jaaql__application_database_argument db_arg
        ON db_conf.application = db_arg.application AND
           db_conf.name = db_arg.configuration AND
           db_arg.parameter = db_param.name
    LEFT JOIN jaaql__database jd on db_arg.database = jd.id
    WHERE jd.deleted is null
);

-- Complete configurations. Where each parameter for the application has an associated argument
create view jaaql__complete_configuration as (
    SELECT
        *
    FROM
         jaaql__configuration_argument
    WHERE (application, configuration, true) IN (
        SELECT
            application, configuration, bool_and(database is not null)
        FROM
             jaaql__configuration_argument
        GROUP BY
            application, configuration
    )
);

create table jaaql__authorization_application (
    application varchar(64) not null references jaaql__application on delete cascade on update cascade,
    role        varchar(31) not null,
    primary key (application, role)
);

create table jaaql__authorization_database (
    id uuid PRIMARY KEY not null default gen_random_uuid(),
    database uuid not null references jaaql__database,
    role varchar(254) not null,
    deleted timestamptz,
    db_encrypted_username varchar(254) not null,
	db_encrypted_password varchar(254) not null,
	precedence int not null default 0
);
CREATE UNIQUE INDEX jaaql__authorization_database_unq
    ON jaaql__authorization_database (database, role) WHERE (deleted is null);

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
    FOREIGN KEY (auth) REFERENCES jaaql__authorization_database
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
        db_conf.application as application,
        db_conf.name as configuration,
        ap.description as application_description,
        ac.description as configuration_description
    FROM
         jaaql__application_database_configuration db_conf
    INNER JOIN jaaql__application ap on ap.name = db_conf.application
    INNER JOIN jaaql__application_database_configuration ac on ac.name = db_conf.name AND ac.application = db_conf.application
    WHERE
        (db_conf.application, db_conf.name, true, true) IN (
            SELECT conf_arg.application,
                   conf_arg.configuration,
                   bool_and(db_auth.database is not null),
                   bool_and(app_auth.application is not null)
            FROM jaaql__complete_configuration conf_arg
            LEFT JOIN jaaql__authorization_database db_auth ON
                    conf_arg.database = db_auth.database AND pg_has_role(db_auth.role, 'MEMBER')
            LEFT JOIN jaaql__authorization_application app_auth ON
                    conf_arg.database = db_auth.database AND pg_has_role(db_auth.role, 'MEMBER')
            LEFT JOIN jaaql__database db ON db_auth.database = db.id
            WHERE db_auth.deleted is null AND db.deleted is null
            GROUP BY conf_arg.application, conf_arg.configuration
        )
);
grant select on jaaql__my_configurations to public;

create or replace view jaaql__authorized_configuration as (
    SELECT
        comc.application,
        comc.configuration,
        comc.parameter_name,
        comc.parameter_description,
        ad.role as database_role,
        ja.role as application_role,
        ad.database
    FROM jaaql__complete_configuration comc
        INNER JOIN jaaql__authorization_database ad ON comc.database = ad.database
        INNER JOIN jaaql__database jd on ad.database = jd.id
        INNER JOIN jaaql__authorization_application ja on comc.application = ja.application
    WHERE ad.deleted is null AND jd.deleted is null
);

-- Not my. Called through jaaql connection
create view jaaql__their_authorized_configurations as (
    SELECT
        ac.application,
        ac.configuration,
        ac.parameter_name,
        ac.parameter_description,
        jad.db_encrypted_username as username,
        jad.db_encrypted_password as password,
        jd.name,
        jd.port,
        jd.address,
        jd.id as database,
        jad.precedence,
        jd.is_console_level,
        ac.database_role,
        ac.application_role
    FROM
        jaaql__authorized_configuration ac
    INNER JOIN
        jaaql__authorization_database jad on ac.database = jad.database AND pg_has_role(ac.database_role, jad.role, 'MEMBER')
    INNER JOIN
        jaaql__database jd on jad.database = jd.id
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
--Do we even need this?
--create function jaaql__grant_role(perm_role text, to_role text) returns void as
--$$
--BEGIN
--    EXECUTE 'GRANT ' || quote_ident(perm_role) || ' TO ' || quote_ident(to_role);
--END
--$$ language plpgsql;

--Same security concerns as above
create function jaaql__delete_user(delete_email text) returns void as
$$
BEGIN
    EXECUTE 'DROP ROLE ' || quote_ident(delete_email);
    UPDATE jaaql__user SET deleted = current_timestamp WHERE email = delete_email;
    UPDATE jaaql__authorization_database SET deleted = current_timestamp WHERE role = delete_email;
END
$$ language plpgsql;
