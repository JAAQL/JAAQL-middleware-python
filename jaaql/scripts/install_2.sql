CREATE ROLE jaaql__registered;
CREATE DOMAIN safe_path AS varchar(255) CHECK (VALUE ~* '^[a-z0-9_\-\/]+$');

-- Install script
-- (1) Create tables

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

create table singleton (
    singleton int primary key not null,
    override_tenant postgres_addressable_name,
    check (singleton = 0)
);
INSERT INTO singleton (singleton, override_tenant) VALUES (0, null);

create or replace function get_tenant() returns postgres_addressable_name as
$$
DECLARE
    the_tenant postgres_addressable_name;
BEGIN
    SELECT tenant into the_tenant FROM account WHERE user_id = session_user;
    IF the_tenant is null then
        SELECT override_tenant into the_tenant FROM singleton;
    end if;
    return the_tenant;
END;
$$ language plpgsql SECURITY DEFINER;
grant execute on function get_tenant() to public;

-- tenant...
create table tenant (
    deleted timestamptz,
    name postgres_addressable_name not null,
    enc_symmetric_key varchar(255) not null,
    primary key (name) );
-- tenant_database...
create table tenant_database (
    tenant postgres_addressable_name not null,
    name character varying(63) not null,
    primary key (tenant, name) );
create table tenant_role (
    role postgres_addressable_name not null,
    tenant postgres_addressable_name not null,
    PRIMARY KEY (role, tenant),
    FOREIGN KEY (tenant) REFERENCES tenant
);
create table application (
    tenant character varying(63) not null,
    description varchar(256) not null,
    name character varying(63) not null,
    primary key (tenant, name) );

-- application_schema...
create table application_schema (
    tenant character varying(63) not null,
    application character varying(63) not null,
    name character varying(63) not null,
    is_default boolean not null default false,
    primary key (tenant, application, name) );
CREATE UNIQUE INDEX application_schema_one_default ON application_schema (tenant, application, is_default) WHERE is_default;

-- application_database...
create table application_database (
    tenant character varying(63) not null,
    application character varying(63) not null,
    configuration character varying(63) not null,
    schema character varying(63) not null,
    database character varying(63) not null,
    primary key (tenant, application, configuration, schema, database) );

create table email_account (
    tenant postgres_addressable_name not null,
    name varchar(60) not null,
    PRIMARY KEY (tenant, name),
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
    tenant postgres_addressable_name not null,
    PRIMARY KEY (tenant, name, application),
    FOREIGN KEY (tenant) REFERENCES tenant,
    FOREIGN KEY (tenant, application) REFERENCES application(tenant, name) ON UPDATE CASCADE ON DELETE CASCADE,
    subject varchar(255),
    description text,
    app_relative_path safe_path,  -- Not a mistake for this domain type. Means app_relative_path cannot be ../../secret. Also secured at application level code in case db is tampered with
    check ((subject is null) = (app_relative_path is null)),
    schema character varying(63),
    FOREIGN KEY (tenant, schema, application) REFERENCES application_schema(tenant, name, application),
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
CREATE UNIQUE INDEX template_unq_signup ON email_template (tenant, name, application, default_email_signup);
CREATE UNIQUE INDEX template_unq_already_signed_up ON email_template (tenant, name, application, default_email_already_signed_up);
CREATE UNIQUE INDEX template_unq_reset_password ON email_template (tenant, name, application, default_reset_password);

-- application_configuration...
create table application_configuration (
    tenant character varying(63) not null,
    application character varying(63) not null,
    url varchar(254) not null,
    artifact_base_uri varchar(254) not null,  --Used to load templates and renderable documents
    name character varying(63) not null,
    primary key (tenant, application, name)
);

create table email_template_configuration (
    tenant postgres_addressable_name not null,
    application character varying(63) not null,
    configuration character varying(63) not null,
    template varchar(60) not null,
    account varchar(60) NOT NULL,
    override_send_name varchar(255),
    primary key (tenant, application, configuration, template),
    FOREIGN KEY (tenant, account) REFERENCES email_account(tenant, name) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (tenant, application, template) REFERENCES email_template(tenant, application, name) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (tenant, application) REFERENCES application(tenant, name) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (tenant, application, configuration) REFERENCES application_configuration(tenant, application, name) ON UPDATE CASCADE ON DELETE CASCADE
);

-- account...
create table account (
    tenant character varying(63) not null,
    user_id jaaql_account_id not null default gen_random_uuid(),
    username character varying(255) not null,
    deleted boolean default false,
    application varchar(63),
    password uuid,
    configuration varchar(63),
    FOREIGN KEY (application, tenant) REFERENCES application(name, tenant) ON DELETE CASCADE,
    FOREIGN KEY (application, tenant, configuration) REFERENCES application_configuration(application, tenant, name) ON DELETE CASCADE,
    public_password text,
    CHECK ((application is null) = (public_password is null)),
    CHECK((application is null) = (configuration is null)),
    primary key (user_id));  -- Technically unique (tenant, username) but we are encrypting the username in such a way that it's unique for tenant
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

create view tenant_application_schemas as (
    SELECT
        app.tenant,
        app.name,
        ac.name as configuration_name,
        ac.url as configuration_url,
        asch.name as schema_name,
        ad.database as schema_database,
        asch.is_default as schema_is_default
    FROM
        application app
    INNER JOIN application_configuration ac ON app.name = ac.application AND app.tenant = ac.tenant
    INNER JOIN application_schema asch ON app.name = asch.application AND app.tenant = asch.tenant
    LEFT JOIN application_database ad ON asch.application = ad.application AND asch.name = ad.schema AND asch.tenant = ad.tenant AND ac.name = ad.configuration
    ORDER BY app.tenant, app.name, configuration, schema
);

create view my_email_template_defaults as (
    SELECT
        app.name as application,
        etds.name as default_email_signup_template,
        etdas.name as default_email_already_signed_up_template,
        etdr.name as default_reset_password_template
    FROM
        application app
    LEFT JOIN email_template etds on app.tenant = etds.tenant and app.name = etds.application AND etds.default_email_signup
    LEFT JOIN email_template etdas on app.tenant = etdas.tenant and app.name = etdas.application AND etdas.default_email_already_signed_up
    LEFT JOIN email_template etdr on app.tenant = etdr.tenant and app.name = etdr.application AND etdr.default_reset_password
    WHERE app.tenant = get_tenant()
    ORDER BY app.name
);
GRANT SELECT ON my_email_template_defaults TO PUBLIC;

create function add_email_account(_name varchar(60), _send_name varchar(255), _host varchar(255), _port integer, _username varchar(255), _encrypted_password text) returns void as
$$
BEGIN
    INSERT INTO email_account (tenant, name, send_name, protocol, host, port, username, encrypted_password) VALUES (get_tenant(), _name, _send_name, 'smtp', _host, _port, _username, _encrypted_password);
END
$$ language plpgsql SECURITY DEFINER;

create function drop_email_account(_name varchar(60), _tenant postgres_addressable_name) returns void as
$$
BEGIN
    DELETE FROM email_account WHERE tenant = _tenant AND name = _name;
END
$$ language plpgsql SECURITY DEFINER;

create function register_email_template(_name varchar(60), _application character varying(63), _subject varchar(255),
                                        _description text, _app_relative_path safe_path = null, _schema character varying(63) = null,
                                        _data_validation_table postgres_addressable_name = null, _data_validation_view postgres_addressable_name = null, _recipient_validation_view postgres_addressable_name = null,
                                        _allow_signup boolean = false, _allow_confirm_signup_attempt boolean = false, _allow_reset_password boolean = false,
                                        _default_email_signup boolean = null, _default_email_already_signed_up boolean = null, _default_reset_password boolean = null) returns void as
$$
BEGIN
    if _default_email_signup is false then
        _default_email_signup = null;
    end if;
    if _default_email_already_signed_up is false then
        _default_email_already_signed_up = null;
    end if;
    if _default_reset_password is false then
        _default_reset_password = null;
    end if;
    INSERT INTO email_template(name, tenant, application,
                               subject, description, app_relative_path,
                               schema, data_validation_table, data_validation_view,
                               recipient_validation_view, allow_signup, allow_confirm_signup_attempt,
                               allow_reset_password, default_email_signup, default_email_already_signed_up,
                               default_reset_password) VALUES (
                                                                                           _name, get_tenant(), _application,
                                                                                           _subject, _description, _app_relative_path,
                                                                                           _schema, _data_validation_table, _data_validation_view,
                                                                                           _recipient_validation_view, _allow_signup, _allow_confirm_signup_attempt,
                                                                                           _allow_reset_password, _default_email_signup, _default_email_already_signed_up,
                                                                                           _default_reset_password);
END
$$ language plpgsql SECURITY DEFINER;

create function deregister_email_template(_name varchar(60)) returns void as
$$
BEGIN
    DELETE FROM email_template WHERE name = _name and tenant = get_tenant();
END
$$ language plpgsql SECURITY DEFINER;

create function associate_email_template_with_application_configuration(_template varchar(60), _application character varying(63), _configuration varchar(63),
                                                                        _account varchar(60), _override_send_name varchar(255) = null) returns void as
$$
BEGIN
    INSERT INTO email_template_configuration(tenant, application, configuration,
                                             template, account, override_send_name) VALUES (get_tenant(), _application, _configuration,
                                                                                            _template, _account, _override_send_name);
END
$$ language plpgsql SECURITY DEFINER;

create function disassociate_email_template_with_application_configuration(_template varchar(60), _application character varying(63), _configuration varchar(63)) returns void as
$$
BEGIN
    DELETE FROM email_template_configuration WHERE tenant = get_tenant() AND application = _application AND template = _template AND configuration = _configuration;
END
$$ language plpgsql SECURITY DEFINER;

-- tenant_database...
alter table tenant_database add constraint tenant_database__tenant
    foreign key (tenant)
        references tenant (name);
-- account...
alter table account add constraint account__tenant
    foreign key (tenant)
        references tenant (name);
-- account_password...
alter table account_password add constraint account_password__account
    foreign key (account)
        references account (user_id) ON DELETE CASCADE;
-- application...
alter table application add constraint application__tenant
    foreign key (tenant)
        references tenant (name) ON DELETE CASCADE ON UPDATE CASCADE;
-- application_schema...
alter table application_schema add constraint application_schema__application
    foreign key (tenant, application)
        references application (tenant, name) ON DELETE CASCADE ON UPDATE CASCADE;
-- application_configuration...
alter table application_configuration add constraint application_configuration__application
    foreign key (tenant, application)
        references application (tenant, name) ON DELETE CASCADE ON UPDATE CASCADE;
-- application_database...
alter table application_database add constraint application_database__configuration
    foreign key (tenant, application, configuration)
        references application_configuration (tenant, application, name) ON DELETE CASCADE ON UPDATE CASCADE;
alter table application_database add constraint application_database__schema
    foreign key (tenant, application, schema)
        references application_schema (tenant, application, name) ON DELETE CASCADE ON UPDATE CASCADE;
alter table application_database add constraint application_database__tenant_database
    foreign key (tenant, database)
        references tenant_database (tenant, name) ON DELETE CASCADE ON UPDATE CASCADE;

create function account_id_from_username(enc_username text) returns jaaql_account_id as
$$
DECLARE
    account_id jaaql_account_id;
BEGIN
    SELECT user_id INTO account_id FROM account WHERE tenant = get_tenant() AND username = enc_username;
    return account_id;
END
$$ language plpgsql SECURITY DEFINER;

create function attach_account(the_tenant text, account_id jaaql_account_id, enc_username text) returns void as
$$
BEGIN
    INSERT INTO account (tenant, username, user_id) VALUES (the_tenant, enc_username, account_id);
END
$$ language plpgsql;

create function create_account_specifying_tenant(the_tenant postgres_addressable_name, enc_username text, _application character varying(63) = null,
                                                 _configuration character varying(63) = null, _password text = null) returns jaaql_account_id as
$$
DECLARE
    account_id jaaql_account_id;
BEGIN
    INSERT INTO account (tenant, username, application, configuration, public_password) VALUES (the_tenant, enc_username, _application, _configuration, _password) RETURNING user_id INTO account_id;
    EXECUTE 'CREATE ROLE ' || quote_ident(account_id);
    if _application is null then
        EXECUTE 'GRANT ' || the_tenant || '__user TO ' || quote_ident(account_id);
    end if;
    EXECUTE 'GRANT ' || the_tenant || '__public TO ' || quote_ident(account_id);
    return account_id;
END
$$ language plpgsql;

create function create_tenant_account(enc_username text, _application character varying(63) = null,
                                      _configuration character varying(63) = null, _password text = null) returns jaaql_account_id as
$$
DECLARE
    account_id jaaql_account_id;
BEGIN
    SELECT create_account_specifying_tenant(get_tenant(), enc_username, _application, _configuration, _password) INTO account_id;
    return account_id;
END
$$ language plpgsql SECURITY DEFINER;

create function close_tenant_account(enc_username text) returns void as
$$
BEGIN
    UPDATE account SET deleted = current_timestamp WHERE user_id = account_id_from_username(enc_username) AND tenant = get_tenant();
END
$$ language plpgsql SECURITY DEFINER;

create function close_my_account() returns void as
$$
BEGIN
    UPDATE account SET deleted = current_timestamp WHERE user_id = session_user AND tenant = get_tenant();
END
$$ language plpgsql SECURITY DEFINER;
GRANT execute on function close_my_account() to jaaql__registered;

create function drop_tenant_role(the_role postgres_addressable_name) returns void as
$$
DECLARE
    the_tenant text;
BEGIN
    SELECT get_tenant() into the_tenant;
    EXECUTE 'DROP ROLE ' || the_tenant || '__' || the_role;
    DELETE FROM tenant_role WHERE role = the_role AND tenant = the_tenant;
END;
$$ language plpgsql SECURITY DEFINER;

create function create_tenant_role(the_role postgres_addressable_name) returns void as
$$
DECLARE
    the_tenant text;
BEGIN
    SELECT get_tenant() into the_tenant;
    INSERT INTO tenant_role (role, tenant) VALUES (the_role, the_tenant);
    EXECUTE 'CREATE ROLE ' || the_tenant || '__' || the_role;
    EXECUTE 'GRANT ' || the_tenant || '__' || the_role || ' TO ' || the_tenant || '__' || 'admin WITH ADMIN OPTION';
END
$$ language plpgsql SECURITY DEFINER;

create function create_tenant_application(app_name postgres_addressable_name, app_description text) returns void as
$$
BEGIN
    INSERT INTO application (tenant, description, name) VALUES (get_tenant(), app_description, app_name);
END
$$ language plpgsql SECURITY DEFINER;

create function drop_tenant_application(app_name postgres_addressable_name) returns void as
$$
BEGIN
    DELETE FROM application WHERE tenant = get_tenant() and name = app_name;
END
$$ language plpgsql SECURITY DEFINER;

create function add_to_application_schema(app_name postgres_addressable_name, entry postgres_addressable_name, _is_default boolean = false) returns void as
$$
BEGIN
    INSERT INTO application_schema (tenant, application, name, is_default) VALUES (get_tenant(), app_name, entry, _is_default);
END;
$$ language plpgsql SECURITY DEFINER;

create function drop_from_application_schema(app_name postgres_addressable_name, entry postgres_addressable_name) returns void as
$$
BEGIN
    DELETE FROM application_schema WHERE application = app_name AND name = entry AND tenant = get_tenant();
END;
$$ language plpgsql SECURITY DEFINER;

create function associate_database_to_application_configuration(app_name postgres_addressable_name, config_name postgres_addressable_name, entry postgres_addressable_name, the_database postgres_addressable_name) returns void as
$$
BEGIN
    INSERT INTO application_database (tenant, application, configuration, schema, database) VALUES (get_tenant(), app_name, config_name, entry, the_database);
END;
$$ language plpgsql SECURITY DEFINER;

create function dissociate_database_from_application_configuration(app_name postgres_addressable_name, config_name postgres_addressable_name, entry postgres_addressable_name, the_database postgres_addressable_name) returns void as
$$
BEGIN
    DELETE FROM application_database WHERE application = app_name AND database = the_database AND configuration = config_name AND schema = entry AND tenant = get_tenant();
END;
$$ language plpgsql SECURITY DEFINER;

create function create_application_configuration(app_name postgres_addressable_name, config_name postgres_addressable_name, _url text, _artifact_base_uri text) returns void as
$$
BEGIN
    INSERT INTO application_configuration (tenant, application, url, name, artifact_base_uri) VALUES (get_tenant(), app_name, _url, config_name, _artifact_base_uri);
END;
$$ language plpgsql SECURITY DEFINER;

create function drop_application_configuration(app_name postgres_addressable_name, config_name postgres_addressable_name) returns void as
$$
BEGIN
    DELETE FROM application_configuration WHERE application = app_name AND name = config_name AND tenant = get_tenant();
END;
$$ language plpgsql SECURITY DEFINER;

create function revoke_tenant_role_from_role(the_role postgres_addressable_name, from_role postgres_addressable_name) returns void as
$$
DECLARE
    the_tenant text;
BEGIN
    SELECT get_tenant() INTO the_tenant;
    EXECUTE 'REVOKE ' || the_tenant || '__' || the_role || ' FROM ' || the_tenant || '__' || from_role;
END
$$ language plpgsql;
GRANT execute on function revoke_tenant_role_from_role(postgres_addressable_name, postgres_addressable_name) to jaaql__registered;

create function grant_tenant_role_to_role(the_role postgres_addressable_name, to_role postgres_addressable_name, with_admin boolean) returns void as
$$
DECLARE
    additional text;
    the_tenant text;
BEGIN
    SELECT get_tenant() INTO the_tenant;
    IF with_admin THEN
        additional = ' WITH ADMIN OPTION';
    END IF;

    EXECUTE 'GRANT ' || the_tenant || '__' || the_role || ' TO ' || the_tenant || '__' || to_role || additional;
END
$$ language plpgsql;
GRANT execute on function grant_tenant_role_to_role(postgres_addressable_name, postgres_addressable_name, boolean) to jaaql__registered;

create function revoke_tenant_role_from_account(the_role postgres_addressable_name, enc_username text) returns void as
$$
DECLARE
    the_tenant text;
BEGIN
    SELECT get_tenant() INTO the_tenant;

    EXECUTE 'REVOKE ' || the_tenant || '__' || the_role || ' FROM ' || account_id_from_username(enc_username)::text;
END
$$ language plpgsql;
GRANT execute on function revoke_tenant_role_from_account(postgres_addressable_name, text) to jaaql__registered;

create function grant_tenant_role_to_account(the_role postgres_addressable_name, enc_username text, with_admin boolean) returns void as
$$
DECLARE
    additional text;
    the_tenant text;
BEGIN
    SELECT get_tenant() INTO the_tenant;
    IF with_admin THEN
        additional = ' WITH ADMIN OPTION';
    END IF;

    EXECUTE 'GRANT ' || the_tenant || '__' || the_role || ' TO ' || account_id_from_username(enc_username)::text || additional;
END
$$ language plpgsql;
GRANT execute on function grant_tenant_role_to_account(postgres_addressable_name, text, boolean) to jaaql__registered;

create table renderable_document (
    tenant    postgres_addressable_name not null,
    name      varchar(40) NOT null,
    application character varying(63) not null,
    PRIMARY KEY (name, application, tenant),
    FOREIGN KEY (tenant, application) REFERENCES application(tenant, name) ON UPDATE CASCADE ON DELETE CASCADE,
    url       text not null,
    render_as varchar(10) default 'pdf' not null,
    check (render_as in ('pdf'))
);

create function register_renderable_document(_application character varying(63), _name varchar(40), _url text, _render_as varchar(10)) returns void as
$$
BEGIN
    INSERT INTO renderable_document(application, name, tenant, url, render_as) VALUES (_application, _name, get_tenant(), _url, _render_as);
END
$$ language plpgsql SECURITY DEFINER;

create function deregister_renderable_document(_name varchar(60)) returns void as
$$
BEGIN
    DELETE FROM renderable_document WHERE name = _name and tenant = get_tenant();
END
$$ language plpgsql SECURITY DEFINER;

create table renderable_document_template (
    attachment varchar(40) not null,
    tenant postgres_addressable_name not null,
    template   varchar(60) not null,
    application character varying(63) not null,
    PRIMARY KEY (attachment, template, tenant, application),
    FOREIGN KEY (template, tenant, application) references email_template(name, tenant, application) ON DELETE CASCADE,
    FOREIGN KEY (attachment, tenant, application) references renderable_document(name, tenant, application) ON DELETE CASCADE
);

create function associate_renderable_document_with_template(_application character varying(63), _attachment varchar(40), _template varchar(60)) returns void as
$$
BEGIN
    INSERT INTO renderable_document_template(attachment, tenant, template, application) VALUES (_attachment, get_tenant(), _template, _application);
END
$$ language plpgsql SECURITY DEFINER;

create function disassociate_renderable_document_from_template(_name varchar(60)) returns void as
$$
BEGIN
    DELETE FROM renderable_document WHERE name = _name and tenant = get_tenant();
END
$$ language plpgsql SECURITY DEFINER;

create view check_drop_database as (SELECT true);
create view check_refresh_application_config as (SELECT true);
create view check_drop_email_account as (SELECT true);

create function create_tenant(the_tenant postgres_addressable_name, _enc_symmetric_key varchar(255), super_role jaaql_account_id = null) returns jaaql_account_id as
$$
BEGIN
    INSERT INTO tenant (name, enc_symmetric_key) VALUES (the_tenant, _enc_symmetric_key);

    if super_role is null then
        SELECT gen_random_uuid() INTO super_role;
        EXECUTE 'CREATE ROLE ' || quote_ident(super_role);
    end if;

    INSERT INTO tenant_role (role, tenant) VALUES ('user', the_tenant);
    INSERT INTO tenant_role (role, tenant) VALUES ('admin', the_tenant);
    INSERT INTO tenant_role (role, tenant) VALUES ('super', the_tenant);

    EXECUTE 'CREATE ROLE ' || the_tenant || '__public';
    EXECUTE 'CREATE ROLE ' || the_tenant || '__user';
    if the_tenant <> 'jaaql' then
        EXECUTE 'CREATE ROLE ' || the_tenant || '__admin';
    end if;
    EXECUTE 'CREATE ROLE ' || the_tenant || '__super';
    EXECUTE 'GRANT ' || the_tenant || '__super' || ' to "' || super_role::text || '" with admin option';
    EXECUTE 'GRANT ' || the_tenant || '__admin' || ' to ' || the_tenant || '__super' || ' with admin option';
    EXECUTE 'GRANT ' || the_tenant || '__user' || ' to ' || the_tenant || '__admin' || ' with admin option';
    EXECUTE 'GRANT ' || the_tenant || '__public' || ' to ' || the_tenant || '__user';
    EXECUTE 'GRANT jaaql__registered' || ' to ' || the_tenant || '__user';
    EXECUTE 'GRANT ' || the_tenant || '__public' || ' to ' || the_tenant || '__admin' || ' with admin option';

    EXECUTE 'GRANT CONNECT ON DATABASE "jaaql__jaaql" TO "' || the_tenant || '__public"';
    EXECUTE 'GRANT select on check_drop_database to ' || the_tenant || '__admin' || ' with grant option';
    EXECUTE 'GRANT select on check_refresh_application_config to ' || the_tenant || '__admin' || ' with grant option';
    EXECUTE 'GRANT select on check_drop_email_account to ' || the_tenant || '__admin' || ' with grant option';

    EXECUTE 'GRANT execute on function account_id_from_username(text) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function associate_email_template_with_application_configuration to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function disassociate_email_template_with_application_configuration to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function register_renderable_document to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function deregister_renderable_document to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function associate_renderable_document_with_template to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function disassociate_renderable_document_from_template to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function create_tenant_account to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function close_tenant_account(text) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function create_tenant_database(postgres_addressable_name, boolean, boolean) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function create_tenant_role(postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function drop_tenant_role(postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function create_tenant_application(postgres_addressable_name, text) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function drop_tenant_application(postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function create_application_configuration to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function drop_application_configuration(postgres_addressable_name, postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function add_to_application_schema(app_name postgres_addressable_name, entry postgres_addressable_name, _is_default boolean) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function drop_from_application_schema(postgres_addressable_name, postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function associate_database_to_application_configuration(postgres_addressable_name, postgres_addressable_name, postgres_addressable_name, postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function dissociate_database_from_application_configuration(postgres_addressable_name, postgres_addressable_name, postgres_addressable_name, postgres_addressable_name) to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function add_email_account to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function register_email_template to ' || the_tenant || '__admin with grant option';
    EXECUTE 'GRANT execute on function deregister_email_template to ' || the_tenant || '__admin with grant option';

    return super_role;
END
$$ language plpgsql;

create function setup(jaaql_enc_symmetric_key varchar(256), default_enc_symmetric_key varchar(256)) returns jaaql_account_id as
$$
DECLARE
    account_id jaaql_account_id;
BEGIN
    PERFORM create_tenant('jaaql', jaaql_enc_symmetric_key);
    GRANT jaaql__super to postgres with admin option;
    GRANT jaaql__super to jaaql with admin option;
    SELECT create_tenant('default', default_enc_symmetric_key) INTO account_id;

    UPDATE singleton SET override_tenant = 'jaaql';
    PERFORM create_tenant_database('jaaql', true);
    PERFORM create_tenant_database('play_db');
    PERFORM create_tenant_application('console', 'The console application');

    PERFORM create_tenant_application('manager', 'The administration panel for JAAQL');
    PERFORM add_to_application_schema('manager', 'default');
    PERFORM create_application_configuration('manager', 'main', '', '');
    PERFORM associate_database_to_application_configuration('manager', 'main', 'default', 'jaaql');

    PERFORM create_tenant_application('playground', 'Allows testing for new JAAQL/JEQL features');
    PERFORM add_to_application_schema('playground', 'default');
    PERFORM create_application_configuration('playground', 'main', '', '');
    PERFORM associate_database_to_application_configuration('playground', 'main', 'default', 'play_db');

    return account_id;
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
grant select on my_logs to jaaql__registered;

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
grant select on my_ips to jaaql__registered;

create view fetch_recent_passwords as (
    SELECT
        a.user_id,
        a.application,
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
        application,
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
    tenant postgres_addressable_name not null,
    closed timestamptz,
    created timestamptz default current_timestamp not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 24 * 14, -- 2 weeks
    code_expiry_ms integer not null default 1000 * 60 * 15, -- 15 minutes
    email_template varchar(60),
    configuration varchar(63),
    application character varying(63),
    check ((application is null) = (configuration is null)),
    FOREIGN KEY (email_template, tenant, application) REFERENCES email_template (name, tenant, application) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (email_template, tenant, application, configuration) REFERENCES email_template_configuration (template, tenant, application, configuration) ON DELETE CASCADE ON UPDATE CASCADE,
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
    tenant postgres_addressable_name not null,
    data_lookup_json text,
    FOREIGN KEY (email_template, tenant, application) REFERENCES email_template(name, tenant, application) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (email_template, tenant, application, configuration) REFERENCES email_template_configuration (template, tenant, application, configuration) ON DELETE CASCADE ON UPDATE CASCADE
);

create table fake_reset_password (
    key_b uuid PRIMARY KEY not null default gen_random_uuid(),
    email text NOT NULL,
    tenant postgres_addressable_name,
    created timestamptz default current_timestamp not null,
    code_attempts int default 0 not null,
    expiry_ms integer not null default 1000 * 60 * 60 * 2, -- 2 hours
    code_expiry_ms integer not null default 1000 * 60 * 15 -- 15 minutes
);

create table email_history (
    id uuid PRIMARY KEY NOT NULL default gen_random_uuid(),
    template varchar(60) not null,
    tenant postgres_addressable_name not null,
    application character varying(63) not null,
    override_send_name varchar(255),
    FOREIGN KEY (template, tenant, application) REFERENCES email_template(name, tenant, application) ON DELETE SET NULL,
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
    tenant postgres_addressable_name not null,
    application character varying(63) not null,
    configuration character varying(63) not null,
    FOREIGN KEY (application, tenant) REFERENCES application(name, tenant) ON DELETE CASCADE,
    FOREIGN KEY (application, configuration, tenant) REFERENCES application_configuration (application, name, tenant),
    created timestamptz not null default current_timestamp,
    encrypted_parameters text,
    encrypted_access_token text,
    create_file boolean not null,
    FOREIGN KEY (document, tenant, application) REFERENCES renderable_document(name, tenant, application) ON DELETE CASCADE,
    completed timestamptz,
    content bytea,
    filename varchar(100),
    check ((completed is null) or (filename is not null))
);
