--  This installation module was generated from ..\..\Packages/DBMS/Postgres/15/jaaql.install for Postgres/15
-- BATON functions

create function "BS.iso_extended_week_number" (
   d date
) returns character varying(8) as
$$
DECLARE
    _result character varying(8) = '';
BEGIN
    SELECT
        EXTRACT(ISOYEAR FROM d)::text ||
        '-W' ||
        lpad(EXTRACT(WEEK FROM d)::text, 2, '0')
    INTO
        _result;

    return _result;
END;
$$ language plpgsql;

SELECT * from plpgsql_check_function(
    '"BS.iso_extended_week_number"(date)'
);

grant execute on function "BS.iso_extended_week_number" to public;

create type _error_type as (
    table_name character varying(63),
    index integer,
    message character varying(256),
    column_name character varying(63)
);
CREATE DOMAIN _error_record AS _error_type
    CHECK ((VALUE).table_name is not null AND
           (VALUE).message is not null);

create domain _jaaql_procedure_result AS integer NOT NULL;

create type _status_type as (
    result integer,
    errors _error_record[]
);

CREATE DOMAIN _status_record AS _status_type
    CHECK ((VALUE).result is not null);

CREATE FUNCTION raise_jaaql_handled_query_exception(_status _status_record)
RETURNS void AS $$
BEGIN
    RAISE EXCEPTION '%',
    (
        SELECT json_agg(row_to_json(t))::text
        FROM (
            SELECT
                e.table_name::text AS table_name,
                e.index::integer AS index,
                e.message::text AS message,
                e.column_name::text AS column_name
            FROM unnest(_status.errors) AS e
        ) t
    )
    USING ERRCODE = 'JQ000';
END;
$$ LANGUAGE plpgsql;

--(0) Check table and column names


-- (1) Create tables

-- application...
create table application (
    name internet_name not null,
    base_url url not null,
    templates_source location,
    default_schema object_name,
    default_s_et object_name,
    default_a_et object_name,
    default_r_et object_name,
    default_u_et object_name,
    unlock_key_validity_period validity_period not null default 1209600,
    unlock_code_validity_period short_validity_period not null default 900,
    is_live bool not null default FALSE,
    primary key (name),
    check (unlock_key_validity_period between 15 and 9999999),
    check (unlock_code_validity_period between 15 and 86400) );
    create function "application.insert__internal" (
        is_live bool,
        unlock_code_validity_period integer,
        unlock_key_validity_period integer,
        base_url character varying(256),
        name character varying(63),
        templates_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "application.insert__internal".name is null then
                "application.insert__internal".name = '';
            end if;
            if "application.insert__internal".base_url is null then
                "application.insert__internal".base_url = '';
            end if;
        -- (A) Check that required values are present
            if "application.insert__internal".base_url = '' then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er moet een waarde ingevuld worden voor Base Url',
                        'base_url'
                    )::_error_record;
            end if;
            if "application.insert__internal".unlock_key_validity_period is null then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er moet een waarde ingevuld worden voor Unlock Key Validity Period',
                        'unlock_key_validity_period'
                    )::_error_record;
            end if;
            if "application.insert__internal".unlock_code_validity_period is null then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er moet een waarde ingevuld worden voor Unlock Code Validity Period',
                        'unlock_code_validity_period'
                    )::_error_record;
            end if;
            if "application.insert__internal".is_live is null then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er moet een waarde ingevuld worden voor Is Live',
                        'is_live'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM application A
            WHERE
                A.name = "application.insert__internal".name;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er is al een Application geregistreed met '
                        'Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "application.insert__internal"._check_only then
                INSERT INTO application (
                    name,
                    base_url,
                    templates_source,
                    default_schema,
                    default_s_et,
                    default_a_et,
                    default_r_et,
                    default_u_et,
                    unlock_key_validity_period,
                    unlock_code_validity_period,
                    is_live
                ) VALUES (
                    "application.insert__internal"."name",
                    "application.insert__internal"."base_url",
                    "application.insert__internal"."templates_source",
                    "application.insert__internal"."default_schema",
                    "application.insert__internal"."default_s_et",
                    "application.insert__internal"."default_a_et",
                    "application.insert__internal"."default_r_et",
                    "application.insert__internal"."default_u_et",
                    "application.insert__internal"."unlock_key_validity_period",
                    "application.insert__internal"."unlock_code_validity_period",
                    "application.insert__internal"."is_live" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"application.insert__internal"('
            'bool,'
            'integer,'
            'integer,'
            'character varying(256),'
            'character varying(63),'
            'character varying(256),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "application.insert" (
        is_live bool,
        unlock_code_validity_period integer,
        unlock_key_validity_period integer,
        base_url character varying(256),
        name character varying(63),
        templates_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.insert__internal"(
                name => "application.insert".name,
                base_url => "application.insert".base_url,
                templates_source => "application.insert".templates_source,
                default_schema => "application.insert".default_schema,
                default_s_et => "application.insert".default_s_et,
                default_a_et => "application.insert".default_a_et,
                default_r_et => "application.insert".default_r_et,
                default_u_et => "application.insert".default_u_et,
                unlock_key_validity_period => "application.insert".unlock_key_validity_period,
                unlock_code_validity_period => "application.insert".unlock_code_validity_period,
                is_live => "application.insert".is_live);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "application.update__internal" (
        name character varying(63),
        base_url character varying(256) default null,
        templates_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null,
        unlock_key_validity_period integer default null,
        unlock_code_validity_period integer default null,
        is_live bool default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM application A
            WHERE
                A.name = "application.update__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er is geen Application gevonden met '
                        'Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE application A
            SET
                base_url = coalesce("application.update__internal".base_url, A.base_url),
                templates_source = coalesce("application.update__internal".templates_source, A.templates_source),
                default_schema = coalesce("application.update__internal".default_schema, A.default_schema),
                default_s_et = coalesce("application.update__internal".default_s_et, A.default_s_et),
                default_a_et = coalesce("application.update__internal".default_a_et, A.default_a_et),
                default_r_et = coalesce("application.update__internal".default_r_et, A.default_r_et),
                default_u_et = coalesce("application.update__internal".default_u_et, A.default_u_et),
                unlock_key_validity_period = coalesce("application.update__internal".unlock_key_validity_period, A.unlock_key_validity_period),
                unlock_code_validity_period = coalesce("application.update__internal".unlock_code_validity_period, A.unlock_code_validity_period),
                is_live = coalesce("application.update__internal".is_live, A.is_live)
            WHERE 
                A.name = "application.update__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"application.update__internal"('
            'character varying(63),'
            'character varying(256),'
            'character varying(256),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'integer,'
            'bool,'
            'integer,'
            'boolean)'
    );

    create function "application.update" (
        name character varying(63),
        base_url character varying(256) default null,
        templates_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null,
        unlock_key_validity_period integer default null,
        unlock_code_validity_period integer default null,
        is_live bool default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.update__internal"(
                name => "application.update".name,
                base_url => "application.update".base_url,
                templates_source => "application.update".templates_source,
                default_schema => "application.update".default_schema,
                default_s_et => "application.update".default_s_et,
                default_a_et => "application.update".default_a_et,
                default_r_et => "application.update".default_r_et,
                default_u_et => "application.update".default_u_et,
                unlock_key_validity_period => "application.update".unlock_key_validity_period,
                unlock_code_validity_period => "application.update".unlock_code_validity_period,
                is_live => "application.update".is_live);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "application.delete__internal" (
        name character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM application A
            WHERE
                A.name = "application.delete__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er is geen Application gevonden met '
                        'Name',
                        'name'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM application A
            WHERE 
                A.name = "application.delete__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"application.delete__internal"('
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "application.delete" (
        name character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.delete__internal"(
                name => "application.delete".name);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- application_schema...
create table application_schema (
    application internet_name not null,
    name object_name not null,
    database object_name not null,
    primary key (application, name) );
    create function "application_schema.insert__internal" (
        database character varying(63),
        name character varying(63),
        application character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "application_schema.insert__internal".application is null then
                "application_schema.insert__internal".application = '';
            end if;
            if "application_schema.insert__internal".name is null then
                "application_schema.insert__internal".name = '';
            end if;
            if "application_schema.insert__internal".database is null then
                "application_schema.insert__internal".database = '';
            end if;
        -- (A) Check that required values are present
            if "application_schema.insert__internal".database = '' then
                _status.errors = _status.errors ||
                    ROW('application_schema', _index,
                        'Er moet een waarde ingevuld worden voor Database',
                        'database'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM application_schema A
            WHERE
                A.application = "application_schema.insert__internal".application AND
                A.name = "application_schema.insert__internal".name;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('application_schema', _index,
                        'Er is al een Application Schema geregistreed met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "application_schema.insert__internal"._check_only then
                INSERT INTO application_schema (
                    application,
                    name,
                    database
                ) VALUES (
                    "application_schema.insert__internal"."application",
                    "application_schema.insert__internal"."name",
                    "application_schema.insert__internal"."database" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"application_schema.insert__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "application_schema.insert" (
        database character varying(63),
        name character varying(63),
        application character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.insert__internal"(
                application => "application_schema.insert".application,
                name => "application_schema.insert".name,
                database => "application_schema.insert".database);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "application_schema.update__internal" (
        application character varying(63),
        name character varying(63),
        database character varying(63) default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM application_schema A
            WHERE
                A.application = "application_schema.update__internal".application AND
                A.name = "application_schema.update__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('application_schema', _index,
                        'Er is geen Application Schema gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE application_schema A
            SET
                database = coalesce("application_schema.update__internal".database, A.database)
            WHERE 
                A.application = "application_schema.update__internal".application AND
                A.name = "application_schema.update__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"application_schema.update__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "application_schema.update" (
        application character varying(63),
        name character varying(63),
        database character varying(63) default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.update__internal"(
                application => "application_schema.update".application,
                name => "application_schema.update".name,
                database => "application_schema.update".database);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "application_schema.delete__internal" (
        application character varying(63),
        name character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM application_schema A
            WHERE
                A.application = "application_schema.delete__internal".application AND
                A.name = "application_schema.delete__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('application_schema', _index,
                        'Er is geen Application Schema gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM application_schema A
            WHERE 
                A.application = "application_schema.delete__internal".application AND
                A.name = "application_schema.delete__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"application_schema.delete__internal"('
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "application_schema.delete" (
        application character varying(63),
        name character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.delete__internal"(
                application => "application_schema.delete".application,
                name => "application_schema.delete".name);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
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
    create function "email_dispatcher.insert__internal" (
        display_name character varying(64),
        name character varying(63),
        application character varying(63),
        protocol character varying(8) default null,
        url character varying(256) default null,
        port integer default null,
        username character varying(255) default null,
        password character varying(256) default null,
        whitelist text default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "email_dispatcher.insert__internal".application is null then
                "email_dispatcher.insert__internal".application = '';
            end if;
            if "email_dispatcher.insert__internal".name is null then
                "email_dispatcher.insert__internal".name = '';
            end if;
            if "email_dispatcher.insert__internal".display_name is null then
                "email_dispatcher.insert__internal".display_name = '';
            end if;
        -- (A) Check that required values are present
            if "email_dispatcher.insert__internal".display_name = '' then
                _status.errors = _status.errors ||
                    ROW('email_dispatcher', _index,
                        'Er moet een waarde ingevuld worden voor Display Name',
                        'display_name'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM email_dispatcher E
            WHERE
                E.application = "email_dispatcher.insert__internal".application AND
                E.name = "email_dispatcher.insert__internal".name;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('email_dispatcher', _index,
                        'Er is al een Email Dispatcher geregistreed met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "email_dispatcher.insert__internal"._check_only then
                INSERT INTO email_dispatcher (
                    application,
                    name,
                    display_name,
                    protocol,
                    url,
                    port,
                    username,
                    password,
                    whitelist
                ) VALUES (
                    "email_dispatcher.insert__internal"."application",
                    "email_dispatcher.insert__internal"."name",
                    "email_dispatcher.insert__internal"."display_name",
                    "email_dispatcher.insert__internal"."protocol",
                    "email_dispatcher.insert__internal"."url",
                    "email_dispatcher.insert__internal"."port",
                    "email_dispatcher.insert__internal"."username",
                    "email_dispatcher.insert__internal"."password",
                    "email_dispatcher.insert__internal"."whitelist" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"email_dispatcher.insert__internal"('
            'character varying(64),'
            'character varying(63),'
            'character varying(63),'
            'character varying(8),'
            'character varying(256),'
            'integer,'
            'character varying(255),'
            'character varying(256),'
            'text,'
            'integer,'
            'boolean)'
    );

    create function "email_dispatcher.insert" (
        display_name character varying(64),
        name character varying(63),
        application character varying(63),
        protocol character varying(8) default null,
        url character varying(256) default null,
        port integer default null,
        username character varying(255) default null,
        password character varying(256) default null,
        whitelist text default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_dispatcher.insert__internal"(
                application => "email_dispatcher.insert".application,
                name => "email_dispatcher.insert".name,
                display_name => "email_dispatcher.insert".display_name,
                protocol => "email_dispatcher.insert".protocol,
                url => "email_dispatcher.insert".url,
                port => "email_dispatcher.insert".port,
                username => "email_dispatcher.insert".username,
                password => "email_dispatcher.insert".password,
                whitelist => "email_dispatcher.insert".whitelist);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "email_dispatcher.update__internal" (
        application character varying(63),
        name character varying(63),
        display_name character varying(64) default null,
        protocol character varying(8) default null,
        url character varying(256) default null,
        port integer default null,
        username character varying(255) default null,
        password character varying(256) default null,
        whitelist text default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM email_dispatcher E
            WHERE
                E.application = "email_dispatcher.update__internal".application AND
                E.name = "email_dispatcher.update__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('email_dispatcher', _index,
                        'Er is geen Email Dispatcher gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE email_dispatcher E
            SET
                display_name = coalesce("email_dispatcher.update__internal".display_name, E.display_name),
                protocol = coalesce("email_dispatcher.update__internal".protocol, E.protocol),
                url = coalesce("email_dispatcher.update__internal".url, E.url),
                port = coalesce("email_dispatcher.update__internal".port, E.port),
                username = coalesce("email_dispatcher.update__internal".username, E.username),
                password = coalesce("email_dispatcher.update__internal".password, E.password),
                whitelist = coalesce("email_dispatcher.update__internal".whitelist, E.whitelist)
            WHERE 
                E.application = "email_dispatcher.update__internal".application AND
                E.name = "email_dispatcher.update__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"email_dispatcher.update__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(64),'
            'character varying(8),'
            'character varying(256),'
            'integer,'
            'character varying(255),'
            'character varying(256),'
            'text,'
            'integer,'
            'boolean)'
    );

    create function "email_dispatcher.update" (
        application character varying(63),
        name character varying(63),
        display_name character varying(64) default null,
        protocol character varying(8) default null,
        url character varying(256) default null,
        port integer default null,
        username character varying(255) default null,
        password character varying(256) default null,
        whitelist text default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_dispatcher.update__internal"(
                application => "email_dispatcher.update".application,
                name => "email_dispatcher.update".name,
                display_name => "email_dispatcher.update".display_name,
                protocol => "email_dispatcher.update".protocol,
                url => "email_dispatcher.update".url,
                port => "email_dispatcher.update".port,
                username => "email_dispatcher.update".username,
                password => "email_dispatcher.update".password,
                whitelist => "email_dispatcher.update".whitelist);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "email_dispatcher.delete__internal" (
        application character varying(63),
        name character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM email_dispatcher E
            WHERE
                E.application = "email_dispatcher.delete__internal".application AND
                E.name = "email_dispatcher.delete__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('email_dispatcher', _index,
                        'Er is geen Email Dispatcher gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM email_dispatcher E
            WHERE 
                E.application = "email_dispatcher.delete__internal".application AND
                E.name = "email_dispatcher.delete__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"email_dispatcher.delete__internal"('
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "email_dispatcher.delete" (
        application character varying(63),
        name character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_dispatcher.delete__internal"(
                application => "email_dispatcher.delete".application,
                name => "email_dispatcher.delete".name);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- jaaql...
create table _jaaql (
    the_anonymous_user postgres_role,
    security_event_attempt_limit attempt_count not null,
    _singleton_key boolean PRIMARY KEY not null default true,
    check(_singleton_key is true),
    check (security_event_attempt_limit between 1 and 3) );
    create view jaaql as select
        the_anonymous_user, security_event_attempt_limit
    from _jaaql
    where _singleton_key;
-- email_template...
create table email_template (
    application internet_name not null,
    dispatcher object_name not null,
    name object_name not null,
    type email_template_type not null,
    content_url safe_path not null,
    validation_schema object_name,
    base_relation object_name,
    dbms_user_column_name object_name,
    permissions_and_data_view object_name,
    dispatcher_domain_recipient email_account_username,
    requires_confirmation bool,
    can_be_sent_anonymously bool,
    primary key (application, name) );
    create function "email_template.insert__internal" (
        content_url character varying(255),
        type character varying(1),
        name character varying(63),
        dispatcher character varying(63),
        application character varying(63),
        validation_schema character varying(63) default null,
        base_relation character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        permissions_and_data_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        requires_confirmation bool default null,
        can_be_sent_anonymously bool default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "email_template.insert__internal".application is null then
                "email_template.insert__internal".application = '';
            end if;
            if "email_template.insert__internal".dispatcher is null then
                "email_template.insert__internal".dispatcher = '';
            end if;
            if "email_template.insert__internal".name is null then
                "email_template.insert__internal".name = '';
            end if;
            if "email_template.insert__internal".type is null then
                "email_template.insert__internal".type = '';
            end if;
            if "email_template.insert__internal".content_url is null then
                "email_template.insert__internal".content_url = '';
            end if;
        -- (A) Check that required values are present
            if "email_template.insert__internal".dispatcher = '' then
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er moet een waarde ingevuld worden voor Dispatcher',
                        'dispatcher'
                    )::_error_record;
            end if;
            if "email_template.insert__internal".type = '' then
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er moet een waarde ingevuld worden voor Type',
                        'type'
                    )::_error_record;
            end if;
            if "email_template.insert__internal".content_url = '' then
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er moet een waarde ingevuld worden voor Content Url',
                        'content_url'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM email_template E
            WHERE
                E.application = "email_template.insert__internal".application AND
                E.name = "email_template.insert__internal".name;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er is al een Email Template geregistreed met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "email_template.insert__internal"._check_only then
                INSERT INTO email_template (
                    application,
                    dispatcher,
                    name,
                    type,
                    content_url,
                    validation_schema,
                    base_relation,
                    dbms_user_column_name,
                    permissions_and_data_view,
                    dispatcher_domain_recipient,
                    requires_confirmation,
                    can_be_sent_anonymously
                ) VALUES (
                    "email_template.insert__internal"."application",
                    "email_template.insert__internal"."dispatcher",
                    "email_template.insert__internal"."name",
                    "email_template.insert__internal"."type",
                    "email_template.insert__internal"."content_url",
                    "email_template.insert__internal"."validation_schema",
                    "email_template.insert__internal"."base_relation",
                    "email_template.insert__internal"."dbms_user_column_name",
                    "email_template.insert__internal"."permissions_and_data_view",
                    "email_template.insert__internal"."dispatcher_domain_recipient",
                    "email_template.insert__internal"."requires_confirmation",
                    "email_template.insert__internal"."can_be_sent_anonymously" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"email_template.insert__internal"('
            'character varying(255),'
            'character varying(1),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(64),'
            'bool,'
            'bool,'
            'integer,'
            'boolean)'
    );

    create function "email_template.insert" (
        content_url character varying(255),
        type character varying(1),
        name character varying(63),
        dispatcher character varying(63),
        application character varying(63),
        validation_schema character varying(63) default null,
        base_relation character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        permissions_and_data_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        requires_confirmation bool default null,
        can_be_sent_anonymously bool default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_template.insert__internal"(
                application => "email_template.insert".application,
                dispatcher => "email_template.insert".dispatcher,
                name => "email_template.insert".name,
                type => "email_template.insert".type,
                content_url => "email_template.insert".content_url,
                validation_schema => "email_template.insert".validation_schema,
                base_relation => "email_template.insert".base_relation,
                dbms_user_column_name => "email_template.insert".dbms_user_column_name,
                permissions_and_data_view => "email_template.insert".permissions_and_data_view,
                dispatcher_domain_recipient => "email_template.insert".dispatcher_domain_recipient,
                requires_confirmation => "email_template.insert".requires_confirmation,
                can_be_sent_anonymously => "email_template.insert".can_be_sent_anonymously);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "email_template.update__internal" (
        application character varying(63),
        name character varying(63),
        dispatcher character varying(63) default null,
        type character varying(1) default null,
        content_url character varying(255) default null,
        validation_schema character varying(63) default null,
        base_relation character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        permissions_and_data_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        requires_confirmation bool default null,
        can_be_sent_anonymously bool default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM email_template E
            WHERE
                E.application = "email_template.update__internal".application AND
                E.name = "email_template.update__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er is geen Email Template gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE email_template E
            SET
                dispatcher = coalesce("email_template.update__internal".dispatcher, E.dispatcher),
                type = coalesce("email_template.update__internal".type, E.type),
                content_url = coalesce("email_template.update__internal".content_url, E.content_url),
                validation_schema = coalesce("email_template.update__internal".validation_schema, E.validation_schema),
                base_relation = coalesce("email_template.update__internal".base_relation, E.base_relation),
                dbms_user_column_name = coalesce("email_template.update__internal".dbms_user_column_name, E.dbms_user_column_name),
                permissions_and_data_view = coalesce("email_template.update__internal".permissions_and_data_view, E.permissions_and_data_view),
                dispatcher_domain_recipient = coalesce("email_template.update__internal".dispatcher_domain_recipient, E.dispatcher_domain_recipient),
                requires_confirmation = coalesce("email_template.update__internal".requires_confirmation, E.requires_confirmation),
                can_be_sent_anonymously = coalesce("email_template.update__internal".can_be_sent_anonymously, E.can_be_sent_anonymously)
            WHERE 
                E.application = "email_template.update__internal".application AND
                E.name = "email_template.update__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"email_template.update__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(1),'
            'character varying(255),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'character varying(64),'
            'bool,'
            'bool,'
            'integer,'
            'boolean)'
    );

    create function "email_template.update" (
        application character varying(63),
        name character varying(63),
        dispatcher character varying(63) default null,
        type character varying(1) default null,
        content_url character varying(255) default null,
        validation_schema character varying(63) default null,
        base_relation character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        permissions_and_data_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        requires_confirmation bool default null,
        can_be_sent_anonymously bool default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_template.update__internal"(
                application => "email_template.update".application,
                dispatcher => "email_template.update".dispatcher,
                name => "email_template.update".name,
                type => "email_template.update".type,
                content_url => "email_template.update".content_url,
                validation_schema => "email_template.update".validation_schema,
                base_relation => "email_template.update".base_relation,
                dbms_user_column_name => "email_template.update".dbms_user_column_name,
                permissions_and_data_view => "email_template.update".permissions_and_data_view,
                dispatcher_domain_recipient => "email_template.update".dispatcher_domain_recipient,
                requires_confirmation => "email_template.update".requires_confirmation,
                can_be_sent_anonymously => "email_template.update".can_be_sent_anonymously);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "email_template.delete__internal" (
        application character varying(63),
        name character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM email_template E
            WHERE
                E.application = "email_template.delete__internal".application AND
                E.name = "email_template.delete__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er is geen Email Template gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM email_template E
            WHERE 
                E.application = "email_template.delete__internal".application AND
                E.name = "email_template.delete__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"email_template.delete__internal"('
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "email_template.delete" (
        application character varying(63),
        name character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_template.delete__internal"(
                application => "email_template.delete".application,
                name => "email_template.delete".name);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- document_template...
create table document_template (
    application internet_name not null,
    name object_name not null,
    content_path safe_path not null,
    email_template object_name,
    primary key (application, name) );
    create function "document_template.insert__internal" (
        content_path character varying(255),
        name character varying(63),
        application character varying(63),
        email_template character varying(63) default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "document_template.insert__internal".application is null then
                "document_template.insert__internal".application = '';
            end if;
            if "document_template.insert__internal".name is null then
                "document_template.insert__internal".name = '';
            end if;
            if "document_template.insert__internal".content_path is null then
                "document_template.insert__internal".content_path = '';
            end if;
        -- (A) Check that required values are present
            if "document_template.insert__internal".content_path = '' then
                _status.errors = _status.errors ||
                    ROW('document_template', _index,
                        'Er moet een waarde ingevuld worden voor Content Path',
                        'content_path'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM document_template D
            WHERE
                D.application = "document_template.insert__internal".application AND
                D.name = "document_template.insert__internal".name;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('document_template', _index,
                        'Er is al een Document Template geregistreed met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "document_template.insert__internal"._check_only then
                INSERT INTO document_template (
                    application,
                    name,
                    content_path,
                    email_template
                ) VALUES (
                    "document_template.insert__internal"."application",
                    "document_template.insert__internal"."name",
                    "document_template.insert__internal"."content_path",
                    "document_template.insert__internal"."email_template" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"document_template.insert__internal"('
            'character varying(255),'
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "document_template.insert" (
        content_path character varying(255),
        name character varying(63),
        application character varying(63),
        email_template character varying(63) default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.insert__internal"(
                application => "document_template.insert".application,
                name => "document_template.insert".name,
                content_path => "document_template.insert".content_path,
                email_template => "document_template.insert".email_template);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "document_template.update__internal" (
        application character varying(63),
        name character varying(63),
        content_path character varying(255) default null,
        email_template character varying(63) default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM document_template D
            WHERE
                D.application = "document_template.update__internal".application AND
                D.name = "document_template.update__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('document_template', _index,
                        'Er is geen Document Template gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE document_template D
            SET
                content_path = coalesce("document_template.update__internal".content_path, D.content_path),
                email_template = coalesce("document_template.update__internal".email_template, D.email_template)
            WHERE 
                D.application = "document_template.update__internal".application AND
                D.name = "document_template.update__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"document_template.update__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(255),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "document_template.update" (
        application character varying(63),
        name character varying(63),
        content_path character varying(255) default null,
        email_template character varying(63) default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.update__internal"(
                application => "document_template.update".application,
                name => "document_template.update".name,
                content_path => "document_template.update".content_path,
                email_template => "document_template.update".email_template);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "document_template.delete__internal" (
        application character varying(63),
        name character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM document_template D
            WHERE
                D.application = "document_template.delete__internal".application AND
                D.name = "document_template.delete__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('document_template', _index,
                        'Er is geen Document Template gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM document_template D
            WHERE 
                D.application = "document_template.delete__internal".application AND
                D.name = "document_template.delete__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"document_template.delete__internal"('
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "document_template.delete" (
        application character varying(63),
        name character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.delete__internal"(
                application => "document_template.delete".application,
                name => "document_template.delete".name);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
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
    create function "document_request.insert__internal" (
        encrypted_access_token character varying(64),
        request_timestamp timestamptz,
        uuid uuid,
        template character varying(63),
        application character varying(63),
        encrypted_parameters text default null,
        render_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "document_request.insert__internal".application is null then
                "document_request.insert__internal".application = '';
            end if;
            if "document_request.insert__internal".template is null then
                "document_request.insert__internal".template = '';
            end if;
            if "document_request.insert__internal".encrypted_access_token is null then
                "document_request.insert__internal".encrypted_access_token = '';
            end if;
        -- (A) Check that required values are present
            if "document_request.insert__internal".application = '' then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er moet een waarde ingevuld worden voor Application',
                        'application'
                    )::_error_record;
            end if;
            if "document_request.insert__internal".template = '' then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er moet een waarde ingevuld worden voor Template',
                        'template'
                    )::_error_record;
            end if;
            if "document_request.insert__internal".request_timestamp is null then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er moet een waarde ingevuld worden voor Request Timestamp',
                        'request_timestamp'
                    )::_error_record;
            end if;
            if "document_request.insert__internal".encrypted_access_token = '' then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er moet een waarde ingevuld worden voor Encrypted Access Token',
                        'encrypted_access_token'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM document_request D
            WHERE
                D.uuid = "document_request.insert__internal".uuid;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er is al een Document Request geregistreed met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "document_request.insert__internal"._check_only then
                INSERT INTO document_request (
                    application,
                    template,
                    uuid,
                    request_timestamp,
                    encrypted_access_token,
                    encrypted_parameters,
                    render_timestamp
                ) VALUES (
                    "document_request.insert__internal"."application",
                    "document_request.insert__internal"."template",
                    "document_request.insert__internal"."uuid",
                    "document_request.insert__internal"."request_timestamp",
                    "document_request.insert__internal"."encrypted_access_token",
                    "document_request.insert__internal"."encrypted_parameters",
                    "document_request.insert__internal"."render_timestamp" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"document_request.insert__internal"('
            'character varying(64),'
            'timestamptz,'
            'uuid,'
            'character varying(63),'
            'character varying(63),'
            'text,'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "document_request.insert" (
        encrypted_access_token character varying(64),
        request_timestamp timestamptz,
        uuid uuid,
        template character varying(63),
        application character varying(63),
        encrypted_parameters text default null,
        render_timestamp timestamptz default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_request.insert__internal"(
                application => "document_request.insert".application,
                template => "document_request.insert".template,
                uuid => "document_request.insert".uuid,
                request_timestamp => "document_request.insert".request_timestamp,
                encrypted_access_token => "document_request.insert".encrypted_access_token,
                encrypted_parameters => "document_request.insert".encrypted_parameters,
                render_timestamp => "document_request.insert".render_timestamp);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "document_request.update__internal" (
        uuid uuid,
        application character varying(63) default null,
        template character varying(63) default null,
        request_timestamp timestamptz default null,
        encrypted_access_token character varying(64) default null,
        encrypted_parameters text default null,
        render_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM document_request D
            WHERE
                D.uuid = "document_request.update__internal".uuid;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er is geen Document Request gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE document_request D
            SET
                application = coalesce("document_request.update__internal".application, D.application),
                template = coalesce("document_request.update__internal".template, D.template),
                request_timestamp = coalesce("document_request.update__internal".request_timestamp, D.request_timestamp),
                encrypted_access_token = coalesce("document_request.update__internal".encrypted_access_token, D.encrypted_access_token),
                encrypted_parameters = coalesce("document_request.update__internal".encrypted_parameters, D.encrypted_parameters),
                render_timestamp = coalesce("document_request.update__internal".render_timestamp, D.render_timestamp)
            WHERE 
                D.uuid = "document_request.update__internal".uuid;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"document_request.update__internal"('
            'uuid,'
            'character varying(63),'
            'character varying(63),'
            'timestamptz,'
            'character varying(64),'
            'text,'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "document_request.update" (
        uuid uuid,
        application character varying(63) default null,
        template character varying(63) default null,
        request_timestamp timestamptz default null,
        encrypted_access_token character varying(64) default null,
        encrypted_parameters text default null,
        render_timestamp timestamptz default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_request.update__internal"(
                application => "document_request.update".application,
                template => "document_request.update".template,
                uuid => "document_request.update".uuid,
                request_timestamp => "document_request.update".request_timestamp,
                encrypted_access_token => "document_request.update".encrypted_access_token,
                encrypted_parameters => "document_request.update".encrypted_parameters,
                render_timestamp => "document_request.update".render_timestamp);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "document_request.delete__internal" (
        uuid uuid,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM document_request D
            WHERE
                D.uuid = "document_request.delete__internal".uuid;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er is geen Document Request gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM document_request D
            WHERE 
                D.uuid = "document_request.delete__internal".uuid;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"document_request.delete__internal"('
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "document_request.delete" (
        uuid uuid) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_request.delete__internal"(
                uuid => "document_request.delete".uuid);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- account...
create table account (
    id postgres_role not null,
    username encrypted__jaaql_username not null,
    deletion_timestamp timestamptz,
    most_recent_password uuid,
    primary key (id),
    unique (username) );
    create function "account.insert__internal" (
        username character varying(255),
        id character varying(63),
        deletion_timestamp timestamptz default null,
        most_recent_password uuid default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "account.insert__internal".id is null then
                "account.insert__internal".id = '';
            end if;
            if "account.insert__internal".username is null then
                "account.insert__internal".username = '';
            end if;
        -- (A) Check that required values are present
            if "account.insert__internal".username = '' then
                _status.errors = _status.errors ||
                    ROW('account', _index,
                        'Er moet een waarde ingevuld worden voor Username',
                        'username'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM account A
            WHERE
                A.id = "account.insert__internal".id;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('account', _index,
                        'Er is al een Account geregistreed met '
                        'Id',
                        'id'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "account.insert__internal"._check_only then
                INSERT INTO account (
                    id,
                    username,
                    deletion_timestamp,
                    most_recent_password
                ) VALUES (
                    "account.insert__internal"."id",
                    "account.insert__internal"."username",
                    "account.insert__internal"."deletion_timestamp",
                    "account.insert__internal"."most_recent_password" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"account.insert__internal"('
            'character varying(255),'
            'character varying(63),'
            'timestamptz,'
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "account.insert" (
        username character varying(255),
        id character varying(63),
        deletion_timestamp timestamptz default null,
        most_recent_password uuid default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.insert__internal"(
                id => "account.insert".id,
                username => "account.insert".username,
                deletion_timestamp => "account.insert".deletion_timestamp,
                most_recent_password => "account.insert".most_recent_password);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "account.update__internal" (
        id character varying(63),
        username character varying(255) default null,
        deletion_timestamp timestamptz default null,
        most_recent_password uuid default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM account A
            WHERE
                A.id = "account.update__internal".id;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('account', _index,
                        'Er is geen Account gevonden met '
                        'Id',
                        'id'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE account A
            SET
                username = coalesce("account.update__internal".username, A.username),
                deletion_timestamp = coalesce("account.update__internal".deletion_timestamp, A.deletion_timestamp),
                most_recent_password = coalesce("account.update__internal".most_recent_password, A.most_recent_password)
            WHERE 
                A.id = "account.update__internal".id;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"account.update__internal"('
            'character varying(63),'
            'character varying(255),'
            'timestamptz,'
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "account.update" (
        id character varying(63),
        username character varying(255) default null,
        deletion_timestamp timestamptz default null,
        most_recent_password uuid default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.update__internal"(
                id => "account.update".id,
                username => "account.update".username,
                deletion_timestamp => "account.update".deletion_timestamp,
                most_recent_password => "account.update".most_recent_password);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "account.delete__internal" (
        id character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM account A
            WHERE
                A.id = "account.delete__internal".id;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('account', _index,
                        'Er is geen Account gevonden met '
                        'Id',
                        'id'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM account A
            WHERE 
                A.id = "account.delete__internal".id;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"account.delete__internal"('
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "account.delete" (
        id character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.delete__internal"(
                id => "account.delete".id);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- account_password...
create table account_password (
    account postgres_role not null,
    uuid uuid not null default gen_random_uuid(),
    hash encrypted__hash not null,
    creation_timestamp timestamptz not null default current_timestamp,
    primary key (uuid),
    unique (hash) );
    create function "account_password.insert__internal" (
        creation_timestamp timestamptz,
        hash character varying(512),
        uuid uuid,
        account character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "account_password.insert__internal".account is null then
                "account_password.insert__internal".account = '';
            end if;
            if "account_password.insert__internal".hash is null then
                "account_password.insert__internal".hash = '';
            end if;
        -- (A) Check that required values are present
            if "account_password.insert__internal".account = '' then
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er moet een waarde ingevuld worden voor Account',
                        'account'
                    )::_error_record;
            end if;
            if "account_password.insert__internal".hash = '' then
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er moet een waarde ingevuld worden voor Hash',
                        'hash'
                    )::_error_record;
            end if;
            if "account_password.insert__internal".creation_timestamp is null then
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er moet een waarde ingevuld worden voor Creation Timestamp',
                        'creation_timestamp'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM account_password A
            WHERE
                A.uuid = "account_password.insert__internal".uuid;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er is al een Account Password geregistreed met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "account_password.insert__internal"._check_only then
                INSERT INTO account_password (
                    account,
                    uuid,
                    hash,
                    creation_timestamp
                ) VALUES (
                    "account_password.insert__internal"."account",
                    "account_password.insert__internal"."uuid",
                    "account_password.insert__internal"."hash",
                    "account_password.insert__internal"."creation_timestamp" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"account_password.insert__internal"('
            'timestamptz,'
            'character varying(512),'
            'uuid,'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "account_password.insert" (
        creation_timestamp timestamptz,
        hash character varying(512),
        uuid uuid,
        account character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.insert__internal"(
                account => "account_password.insert".account,
                uuid => "account_password.insert".uuid,
                hash => "account_password.insert".hash,
                creation_timestamp => "account_password.insert".creation_timestamp);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "account_password.update__internal" (
        uuid uuid,
        account character varying(63) default null,
        hash character varying(512) default null,
        creation_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM account_password A
            WHERE
                A.uuid = "account_password.update__internal".uuid;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er is geen Account Password gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE account_password A
            SET
                account = coalesce("account_password.update__internal".account, A.account),
                hash = coalesce("account_password.update__internal".hash, A.hash),
                creation_timestamp = coalesce("account_password.update__internal".creation_timestamp, A.creation_timestamp)
            WHERE 
                A.uuid = "account_password.update__internal".uuid;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"account_password.update__internal"('
            'uuid,'
            'character varying(63),'
            'character varying(512),'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "account_password.update" (
        uuid uuid,
        account character varying(63) default null,
        hash character varying(512) default null,
        creation_timestamp timestamptz default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.update__internal"(
                account => "account_password.update".account,
                uuid => "account_password.update".uuid,
                hash => "account_password.update".hash,
                creation_timestamp => "account_password.update".creation_timestamp);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "account_password.delete__internal" (
        uuid uuid,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM account_password A
            WHERE
                A.uuid = "account_password.delete__internal".uuid;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er is geen Account Password gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM account_password A
            WHERE 
                A.uuid = "account_password.delete__internal".uuid;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"account_password.delete__internal"('
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "account_password.delete" (
        uuid uuid) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.delete__internal"(
                uuid => "account_password.delete".uuid);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- validated_ip_address...
create table validated_ip_address (
    account postgres_role not null,
    uuid uuid not null default gen_random_uuid(),
    encrypted_salted_ip_address encrypted__salted_ip not null,
    first_authentication_timestamp timestamptz not null default current_timestamp,
    last_authentication_timestamp timestamptz not null,
    primary key (uuid),
    unique (encrypted_salted_ip_address) );
    create function "validated_ip_address.insert__internal" (
        last_authentication_timestamp timestamptz,
        first_authentication_timestamp timestamptz,
        encrypted_salted_ip_address character varying(256),
        uuid uuid,
        account character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "validated_ip_address.insert__internal".account is null then
                "validated_ip_address.insert__internal".account = '';
            end if;
            if "validated_ip_address.insert__internal".encrypted_salted_ip_address is null then
                "validated_ip_address.insert__internal".encrypted_salted_ip_address = '';
            end if;
        -- (A) Check that required values are present
            if "validated_ip_address.insert__internal".account = '' then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er moet een waarde ingevuld worden voor Account',
                        'account'
                    )::_error_record;
            end if;
            if "validated_ip_address.insert__internal".encrypted_salted_ip_address = '' then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er moet een waarde ingevuld worden voor Encrypted Salted Ip Address',
                        'encrypted_salted_ip_address'
                    )::_error_record;
            end if;
            if "validated_ip_address.insert__internal".first_authentication_timestamp is null then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er moet een waarde ingevuld worden voor First Authentication Timestamp',
                        'first_authentication_timestamp'
                    )::_error_record;
            end if;
            if "validated_ip_address.insert__internal".last_authentication_timestamp is null then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er moet een waarde ingevuld worden voor Last Authentication Timestamp',
                        'last_authentication_timestamp'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM validated_ip_address V
            WHERE
                V.uuid = "validated_ip_address.insert__internal".uuid;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er is al een Validated Ip Address geregistreed met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "validated_ip_address.insert__internal"._check_only then
                INSERT INTO validated_ip_address (
                    account,
                    uuid,
                    encrypted_salted_ip_address,
                    first_authentication_timestamp,
                    last_authentication_timestamp
                ) VALUES (
                    "validated_ip_address.insert__internal"."account",
                    "validated_ip_address.insert__internal"."uuid",
                    "validated_ip_address.insert__internal"."encrypted_salted_ip_address",
                    "validated_ip_address.insert__internal"."first_authentication_timestamp",
                    "validated_ip_address.insert__internal"."last_authentication_timestamp" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"validated_ip_address.insert__internal"('
            'timestamptz,'
            'timestamptz,'
            'character varying(256),'
            'uuid,'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "validated_ip_address.insert" (
        last_authentication_timestamp timestamptz,
        first_authentication_timestamp timestamptz,
        encrypted_salted_ip_address character varying(256),
        uuid uuid,
        account character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "validated_ip_address.insert__internal"(
                account => "validated_ip_address.insert".account,
                uuid => "validated_ip_address.insert".uuid,
                encrypted_salted_ip_address => "validated_ip_address.insert".encrypted_salted_ip_address,
                first_authentication_timestamp => "validated_ip_address.insert".first_authentication_timestamp,
                last_authentication_timestamp => "validated_ip_address.insert".last_authentication_timestamp);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "validated_ip_address.update__internal" (
        uuid uuid,
        account character varying(63) default null,
        encrypted_salted_ip_address character varying(256) default null,
        first_authentication_timestamp timestamptz default null,
        last_authentication_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM validated_ip_address V
            WHERE
                V.uuid = "validated_ip_address.update__internal".uuid;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er is geen Validated Ip Address gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE validated_ip_address V
            SET
                account = coalesce("validated_ip_address.update__internal".account, V.account),
                encrypted_salted_ip_address = coalesce("validated_ip_address.update__internal".encrypted_salted_ip_address, V.encrypted_salted_ip_address),
                first_authentication_timestamp = coalesce("validated_ip_address.update__internal".first_authentication_timestamp, V.first_authentication_timestamp),
                last_authentication_timestamp = coalesce("validated_ip_address.update__internal".last_authentication_timestamp, V.last_authentication_timestamp)
            WHERE 
                V.uuid = "validated_ip_address.update__internal".uuid;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"validated_ip_address.update__internal"('
            'uuid,'
            'character varying(63),'
            'character varying(256),'
            'timestamptz,'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "validated_ip_address.update" (
        uuid uuid,
        account character varying(63) default null,
        encrypted_salted_ip_address character varying(256) default null,
        first_authentication_timestamp timestamptz default null,
        last_authentication_timestamp timestamptz default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "validated_ip_address.update__internal"(
                account => "validated_ip_address.update".account,
                uuid => "validated_ip_address.update".uuid,
                encrypted_salted_ip_address => "validated_ip_address.update".encrypted_salted_ip_address,
                first_authentication_timestamp => "validated_ip_address.update".first_authentication_timestamp,
                last_authentication_timestamp => "validated_ip_address.update".last_authentication_timestamp);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "validated_ip_address.delete__internal" (
        uuid uuid,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM validated_ip_address V
            WHERE
                V.uuid = "validated_ip_address.delete__internal".uuid;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er is geen Validated Ip Address gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM validated_ip_address V
            WHERE 
                V.uuid = "validated_ip_address.delete__internal".uuid;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"validated_ip_address.delete__internal"('
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "validated_ip_address.delete" (
        uuid uuid) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "validated_ip_address.delete__internal"(
                uuid => "validated_ip_address.delete".uuid);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- security_event...
create table security_event (
    application internet_name not null,
    event_lock uuid not null default gen_random_uuid(),
    creation_timestamp timestamptz not null default current_timestamp,
    wrong_key_attempt_count current_attempt_count not null default 0,
    email_template object_name not null,
    account postgres_role,
    fake_account encrypted__jaaql_username,
    unlock_key uuid not null default gen_random_uuid(),
    unlock_code unlock_code not null,
    unlock_timestamp timestamptz,
    finish_timestamp timestamptz,
    primary key (application, event_lock),
    check (wrong_key_attempt_count between 0 and 3) );
    create function "security_event.insert__internal" (
        unlock_code character varying(10),
        unlock_key uuid,
        email_template character varying(63),
        wrong_key_attempt_count smallint,
        creation_timestamp timestamptz,
        event_lock uuid,
        application character varying(63),
        account character varying(63) default null,
        fake_account character varying(255) default null,
        unlock_timestamp timestamptz default null,
        finish_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "security_event.insert__internal".application is null then
                "security_event.insert__internal".application = '';
            end if;
            if "security_event.insert__internal".email_template is null then
                "security_event.insert__internal".email_template = '';
            end if;
            if "security_event.insert__internal".unlock_code is null then
                "security_event.insert__internal".unlock_code = '';
            end if;
        -- (A) Check that required values are present
            if "security_event.insert__internal".creation_timestamp is null then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er moet een waarde ingevuld worden voor Creation Timestamp',
                        'creation_timestamp'
                    )::_error_record;
            end if;
            if "security_event.insert__internal".wrong_key_attempt_count is null then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er moet een waarde ingevuld worden voor Wrong Key Attempt Count',
                        'wrong_key_attempt_count'
                    )::_error_record;
            end if;
            if "security_event.insert__internal".email_template = '' then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er moet een waarde ingevuld worden voor Email Template',
                        'email_template'
                    )::_error_record;
            end if;
            if "security_event.insert__internal".unlock_key is null then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er moet een waarde ingevuld worden voor Unlock Key',
                        'unlock_key'
                    )::_error_record;
            end if;
            if "security_event.insert__internal".unlock_code = '' then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er moet een waarde ingevuld worden voor Unlock Code',
                        'unlock_code'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM security_event S
            WHERE
                S.application = "security_event.insert__internal".application AND
                S.event_lock = "security_event.insert__internal".event_lock;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er is al een Security Event geregistreed met '
                        'Application, Event Lock',
                        'event_lock'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "security_event.insert__internal"._check_only then
                INSERT INTO security_event (
                    application,
                    event_lock,
                    creation_timestamp,
                    wrong_key_attempt_count,
                    email_template,
                    account,
                    fake_account,
                    unlock_key,
                    unlock_code,
                    unlock_timestamp,
                    finish_timestamp
                ) VALUES (
                    "security_event.insert__internal"."application",
                    "security_event.insert__internal"."event_lock",
                    "security_event.insert__internal"."creation_timestamp",
                    "security_event.insert__internal"."wrong_key_attempt_count",
                    "security_event.insert__internal"."email_template",
                    "security_event.insert__internal"."account",
                    "security_event.insert__internal"."fake_account",
                    "security_event.insert__internal"."unlock_key",
                    "security_event.insert__internal"."unlock_code",
                    "security_event.insert__internal"."unlock_timestamp",
                    "security_event.insert__internal"."finish_timestamp" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"security_event.insert__internal"('
            'character varying(10),'
            'uuid,'
            'character varying(63),'
            'smallint,'
            'timestamptz,'
            'uuid,'
            'character varying(63),'
            'character varying(63),'
            'character varying(255),'
            'timestamptz,'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "security_event.insert" (
        unlock_code character varying(10),
        unlock_key uuid,
        email_template character varying(63),
        wrong_key_attempt_count smallint,
        creation_timestamp timestamptz,
        event_lock uuid,
        application character varying(63),
        account character varying(63) default null,
        fake_account character varying(255) default null,
        unlock_timestamp timestamptz default null,
        finish_timestamp timestamptz default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "security_event.insert__internal"(
                application => "security_event.insert".application,
                event_lock => "security_event.insert".event_lock,
                creation_timestamp => "security_event.insert".creation_timestamp,
                wrong_key_attempt_count => "security_event.insert".wrong_key_attempt_count,
                email_template => "security_event.insert".email_template,
                account => "security_event.insert".account,
                fake_account => "security_event.insert".fake_account,
                unlock_key => "security_event.insert".unlock_key,
                unlock_code => "security_event.insert".unlock_code,
                unlock_timestamp => "security_event.insert".unlock_timestamp,
                finish_timestamp => "security_event.insert".finish_timestamp);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "security_event.update__internal" (
        application character varying(63),
        event_lock uuid,
        creation_timestamp timestamptz default null,
        wrong_key_attempt_count smallint default null,
        email_template character varying(63) default null,
        account character varying(63) default null,
        fake_account character varying(255) default null,
        unlock_key uuid default null,
        unlock_code character varying(10) default null,
        unlock_timestamp timestamptz default null,
        finish_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM security_event S
            WHERE
                S.application = "security_event.update__internal".application AND
                S.event_lock = "security_event.update__internal".event_lock;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er is geen Security Event gevonden met '
                        'Application, Event Lock',
                        'event_lock'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE security_event S
            SET
                creation_timestamp = coalesce("security_event.update__internal".creation_timestamp, S.creation_timestamp),
                wrong_key_attempt_count = coalesce("security_event.update__internal".wrong_key_attempt_count, S.wrong_key_attempt_count),
                email_template = coalesce("security_event.update__internal".email_template, S.email_template),
                account = coalesce("security_event.update__internal".account, S.account),
                fake_account = coalesce("security_event.update__internal".fake_account, S.fake_account),
                unlock_key = coalesce("security_event.update__internal".unlock_key, S.unlock_key),
                unlock_code = coalesce("security_event.update__internal".unlock_code, S.unlock_code),
                unlock_timestamp = coalesce("security_event.update__internal".unlock_timestamp, S.unlock_timestamp),
                finish_timestamp = coalesce("security_event.update__internal".finish_timestamp, S.finish_timestamp)
            WHERE 
                S.application = "security_event.update__internal".application AND
                S.event_lock = "security_event.update__internal".event_lock;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"security_event.update__internal"('
            'character varying(63),'
            'uuid,'
            'timestamptz,'
            'smallint,'
            'character varying(63),'
            'character varying(63),'
            'character varying(255),'
            'uuid,'
            'character varying(10),'
            'timestamptz,'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "security_event.update" (
        application character varying(63),
        event_lock uuid,
        creation_timestamp timestamptz default null,
        wrong_key_attempt_count smallint default null,
        email_template character varying(63) default null,
        account character varying(63) default null,
        fake_account character varying(255) default null,
        unlock_key uuid default null,
        unlock_code character varying(10) default null,
        unlock_timestamp timestamptz default null,
        finish_timestamp timestamptz default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "security_event.update__internal"(
                application => "security_event.update".application,
                event_lock => "security_event.update".event_lock,
                creation_timestamp => "security_event.update".creation_timestamp,
                wrong_key_attempt_count => "security_event.update".wrong_key_attempt_count,
                email_template => "security_event.update".email_template,
                account => "security_event.update".account,
                fake_account => "security_event.update".fake_account,
                unlock_key => "security_event.update".unlock_key,
                unlock_code => "security_event.update".unlock_code,
                unlock_timestamp => "security_event.update".unlock_timestamp,
                finish_timestamp => "security_event.update".finish_timestamp);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "security_event.delete__internal" (
        application character varying(63),
        event_lock uuid,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM security_event S
            WHERE
                S.application = "security_event.delete__internal".application AND
                S.event_lock = "security_event.delete__internal".event_lock;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er is geen Security Event gevonden met '
                        'Application, Event Lock',
                        'event_lock'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM security_event S
            WHERE 
                S.application = "security_event.delete__internal".application AND
                S.event_lock = "security_event.delete__internal".event_lock;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"security_event.delete__internal"('
            'character varying(63),'
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "security_event.delete" (
        application character varying(63),
        event_lock uuid) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "security_event.delete__internal"(
                application => "security_event.delete".application,
                event_lock => "security_event.delete".event_lock);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- handled_error...
create table handled_error (
    code error_code not null,
    error_name error_name,
    is_arrayed bool not null,
    table_name object_name,
    table_name_required bool,
    table_possible bool,
    column_possible bool,
    has_associated_set bool,
    column_name object_name,
    http_response_code http_response_code default 422,
    message text,
    description text not null,
    primary key (code),
    check (code between 1001 and 1999),
    check (http_response_code between 100 and 599) );
    create function "handled_error.insert__internal" (
        description text,
        is_arrayed bool,
        code numeric,
        error_name character varying(45) default null,
        table_name character varying(63) default null,
        table_name_required bool default null,
        table_possible bool default null,
        column_possible bool default null,
        has_associated_set bool default null,
        column_name character varying(63) default null,
        http_response_code numeric default null,
        message text default null,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
        -- (A) Check that required values are present
            if "handled_error.insert__internal".is_arrayed is null then
                _status.errors = _status.errors ||
                    ROW('handled_error', _index,
                        'Er moet een waarde ingevuld worden voor Is Arrayed',
                        'is_arrayed'
                    )::_error_record;
            end if;
            if "handled_error.insert__internal".description is null then
                _status.errors = _status.errors ||
                    ROW('handled_error', _index,
                        'Er moet een waarde ingevuld worden voor Description',
                        'description'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM handled_error H
            WHERE
                H.code = "handled_error.insert__internal".code;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('handled_error', _index,
                        'Er is al een Handled Error geregistreed met '
                        'Code',
                        'code'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "handled_error.insert__internal"._check_only then
                INSERT INTO handled_error (
                    code,
                    error_name,
                    is_arrayed,
                    table_name,
                    table_name_required,
                    table_possible,
                    column_possible,
                    has_associated_set,
                    column_name,
                    http_response_code,
                    message,
                    description
                ) VALUES (
                    "handled_error.insert__internal"."code",
                    "handled_error.insert__internal"."error_name",
                    "handled_error.insert__internal"."is_arrayed",
                    "handled_error.insert__internal"."table_name",
                    "handled_error.insert__internal"."table_name_required",
                    "handled_error.insert__internal"."table_possible",
                    "handled_error.insert__internal"."column_possible",
                    "handled_error.insert__internal"."has_associated_set",
                    "handled_error.insert__internal"."column_name",
                    "handled_error.insert__internal"."http_response_code",
                    "handled_error.insert__internal"."message",
                    "handled_error.insert__internal"."description" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"handled_error.insert__internal"('
            'text,'
            'bool,'
            'numeric,'
            'character varying(45),'
            'character varying(63),'
            'bool,'
            'bool,'
            'bool,'
            'bool,'
            'character varying(63),'
            'numeric,'
            'text,'
            'integer,'
            'boolean)'
    );

    create function "handled_error.insert" (
        description text,
        is_arrayed bool,
        code numeric,
        error_name character varying(45) default null,
        table_name character varying(63) default null,
        table_name_required bool default null,
        table_possible bool default null,
        column_possible bool default null,
        has_associated_set bool default null,
        column_name character varying(63) default null,
        http_response_code numeric default null,
        message text default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "handled_error.insert__internal"(
                code => "handled_error.insert".code,
                error_name => "handled_error.insert".error_name,
                is_arrayed => "handled_error.insert".is_arrayed,
                table_name => "handled_error.insert".table_name,
                table_name_required => "handled_error.insert".table_name_required,
                table_possible => "handled_error.insert".table_possible,
                column_possible => "handled_error.insert".column_possible,
                has_associated_set => "handled_error.insert".has_associated_set,
                column_name => "handled_error.insert".column_name,
                http_response_code => "handled_error.insert".http_response_code,
                message => "handled_error.insert".message,
                description => "handled_error.insert".description);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "handled_error.update__internal" (
        code numeric,
        error_name character varying(45) default null,
        is_arrayed bool default null,
        table_name character varying(63) default null,
        table_name_required bool default null,
        table_possible bool default null,
        column_possible bool default null,
        has_associated_set bool default null,
        column_name character varying(63) default null,
        http_response_code numeric default null,
        message text default null,
        description text default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM handled_error H
            WHERE
                H.code = "handled_error.update__internal".code;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('handled_error', _index,
                        'Er is geen Handled Error gevonden met '
                        'Code',
                        'code'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE handled_error H
            SET
                error_name = coalesce("handled_error.update__internal".error_name, H.error_name),
                is_arrayed = coalesce("handled_error.update__internal".is_arrayed, H.is_arrayed),
                table_name = coalesce("handled_error.update__internal".table_name, H.table_name),
                table_name_required = coalesce("handled_error.update__internal".table_name_required, H.table_name_required),
                table_possible = coalesce("handled_error.update__internal".table_possible, H.table_possible),
                column_possible = coalesce("handled_error.update__internal".column_possible, H.column_possible),
                has_associated_set = coalesce("handled_error.update__internal".has_associated_set, H.has_associated_set),
                column_name = coalesce("handled_error.update__internal".column_name, H.column_name),
                http_response_code = coalesce("handled_error.update__internal".http_response_code, H.http_response_code),
                message = coalesce("handled_error.update__internal".message, H.message),
                description = coalesce("handled_error.update__internal".description, H.description)
            WHERE 
                H.code = "handled_error.update__internal".code;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"handled_error.update__internal"('
            'numeric,'
            'character varying(45),'
            'bool,'
            'character varying(63),'
            'bool,'
            'bool,'
            'bool,'
            'bool,'
            'character varying(63),'
            'numeric,'
            'text,'
            'text,'
            'integer,'
            'boolean)'
    );

    create function "handled_error.update" (
        code numeric,
        error_name character varying(45) default null,
        is_arrayed bool default null,
        table_name character varying(63) default null,
        table_name_required bool default null,
        table_possible bool default null,
        column_possible bool default null,
        has_associated_set bool default null,
        column_name character varying(63) default null,
        http_response_code numeric default null,
        message text default null,
        description text default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "handled_error.update__internal"(
                code => "handled_error.update".code,
                error_name => "handled_error.update".error_name,
                is_arrayed => "handled_error.update".is_arrayed,
                table_name => "handled_error.update".table_name,
                table_name_required => "handled_error.update".table_name_required,
                table_possible => "handled_error.update".table_possible,
                column_possible => "handled_error.update".column_possible,
                has_associated_set => "handled_error.update".has_associated_set,
                column_name => "handled_error.update".column_name,
                http_response_code => "handled_error.update".http_response_code,
                message => "handled_error.update".message,
                description => "handled_error.update".description);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "handled_error.delete__internal" (
        code numeric,
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM handled_error H
            WHERE
                H.code = "handled_error.delete__internal".code;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('handled_error', _index,
                        'Er is geen Handled Error gevonden met '
                        'Code',
                        'code'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM handled_error H
            WHERE 
                H.code = "handled_error.delete__internal".code;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"handled_error.delete__internal"('
            'numeric,'
            'integer,'
            'boolean)'
    );

    create function "handled_error.delete" (
        code numeric) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "handled_error.delete__internal"(
                code => "handled_error.delete".code);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
-- pg_base_exception...
create table pg_base_exception (
    name pg_base_exception_name not null,
    primary key (name) );
-- pg_error_class...
create table pg_error_class (
    code pg_error_class_code not null,
    name pg_error_class_name not null,
    description pg_error_class_description,
    primary key (code) );
-- pg_exception...
create table pg_exception (
    pg_class pg_error_class_code not null,
    sqlstate pg_sqlstate not null,
    name pg_exception_name not null,
    base_exception pg_base_exception_name not null,
    primary key (sqlstate) );
-- remote_procedure...
create table remote_procedure (
    application internet_name not null,
    name object_name not null,
    command text not null,
    access procedure_access_level not null,
    primary key (application, name) );
    create function "remote_procedure.insert__internal" (
        access character varying(1),
        command text,
        name character varying(63),
        application character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (1) Coercion
            if "remote_procedure.insert__internal".application is null then
                "remote_procedure.insert__internal".application = '';
            end if;
            if "remote_procedure.insert__internal".name is null then
                "remote_procedure.insert__internal".name = '';
            end if;
            if "remote_procedure.insert__internal".access is null then
                "remote_procedure.insert__internal".access = '';
            end if;
        -- (A) Check that required values are present
            if "remote_procedure.insert__internal".command is null then
                _status.errors = _status.errors ||
                    ROW('remote_procedure', _index,
                        'Er moet een waarde ingevuld worden voor Command',
                        'command'
                    )::_error_record;
            end if;
            if "remote_procedure.insert__internal".access = '' then
                _status.errors = _status.errors ||
                    ROW('remote_procedure', _index,
                        'Er moet een waarde ingevuld worden voor Access',
                        'access'
                    )::_error_record;
            end if;
        -- (D) Check that there is no record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM remote_procedure R
            WHERE
                R.application = "remote_procedure.insert__internal".application AND
                R.name = "remote_procedure.insert__internal".name;
            if _count <> 0 then
                _status.errors = _status.errors ||
                    ROW('remote_procedure', _index,
                        'Er is al een Remote Procedure geregistreed met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            -- Now do the work
            if not "remote_procedure.insert__internal"._check_only then
                INSERT INTO remote_procedure (
                    application,
                    name,
                    command,
                    access
                ) VALUES (
                    "remote_procedure.insert__internal"."application",
                    "remote_procedure.insert__internal"."name",
                    "remote_procedure.insert__internal"."command",
                    "remote_procedure.insert__internal"."access" );
                _status.result = 1;
            end if;
            return _status;
        END;
    $$ language plpgsql security definer;
    select * from plpgsql_check_function(
        '"remote_procedure.insert__internal"('
            'character varying(1),'
            'text,'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "remote_procedure.insert" (
        access character varying(1),
        command text,
        name character varying(63),
        application character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "remote_procedure.insert__internal"(
                application => "remote_procedure.insert".application,
                name => "remote_procedure.insert".name,
                command => "remote_procedure.insert".command,
                access => "remote_procedure.insert".access);

        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "remote_procedure.update__internal" (
        application character varying(63),
        name character varying(63),
        command text default null,
        access character varying(1) default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM remote_procedure R
            WHERE
                R.application = "remote_procedure.update__internal".application AND
                R.name = "remote_procedure.update__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('remote_procedure', _index,
                        'Er is geen Remote Procedure gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;
            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            UPDATE remote_procedure R
            SET
                command = coalesce("remote_procedure.update__internal".command, R.command),
                access = coalesce("remote_procedure.update__internal".access, R.access)
            WHERE 
                R.application = "remote_procedure.update__internal".application AND
                R.name = "remote_procedure.update__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"remote_procedure.update__internal"('
            'character varying(63),'
            'character varying(63),'
            'text,'
            'character varying(1),'
            'integer,'
            'boolean)'
    );

    create function "remote_procedure.update" (
        application character varying(63),
        name character varying(63),
        command text default null,
        access character varying(1) default null) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "remote_procedure.update__internal"(
                application => "remote_procedure.update".application,
                name => "remote_procedure.update".name,
                command => "remote_procedure.update".command,
                access => "remote_procedure.update".access);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;
    create function "remote_procedure.delete__internal" (
        application character varying(63),
        name character varying(63),
        _index integer default null,
        _check_only boolean default false ) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
        -- (D) Check that there is a record in the table with the same prime key
            SELECT COUNT(*) into _count
            FROM remote_procedure R
            WHERE
                R.application = "remote_procedure.delete__internal".application AND
                R.name = "remote_procedure.delete__internal".name;
            if _count <> 1 then
                _status.errors = _status.errors ||
                    ROW('remote_procedure', _index,
                        'Er is geen Remote Procedure gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;            -- Get out quick if there are errors
            if cardinality(_status.errors) <> 0 then
                return _status;
            end if;
            if _check_only then
                return _status;
            end if;

            DELETE FROM remote_procedure R
            WHERE 
                R.application = "remote_procedure.delete__internal".application AND
                R.name = "remote_procedure.delete__internal".name;
            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"remote_procedure.delete__internal"('
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "remote_procedure.delete" (
        application character varying(63),
        name character varying(63)) returns _jaaql_procedure_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "remote_procedure.delete__internal"(
                application => "remote_procedure.delete".application,
                name => "remote_procedure.delete".name);
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
        END;
    $$ language plpgsql security definer;

-- (1a) Create view to give current date/time, possibly read from a table

create view _current as
    SELECT
        CURRENT_DATE as date_,
        LOCALTIMESTAMP as time_;

grant select on "_current" to public;

create view _current_date_parts as (
    SELECT
        "BS.iso_extended_week_number"(date_) as iso_extended_week_number_,
        to_char(time_, 'HH24:MI') as hour_,
        extract(isodow from date_) - 1 as dow_
    FROM
        _current
);

grant select on "_current_date_parts" to public;



-- (2) Create super functions

-- application...

-- application_schema...

create function "application_schema.insert+" (
    use_as_default jsonb,
    database character varying(63),
    name character varying(63),
    application character varying(63)
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "application_schema.insert__internal"(
            application => "application_schema.insert+".application,
            name => "application_schema.insert+".name,
            database => "application_schema.insert+".database );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        for _r in SELECT * FROM jsonb_array_elements(use_as_default) loop
            SELECT * INTO strict _returned_status FROM "application.insert__internal"(
                name => "application_schema.insert+".application,
                default_schema => "application_schema.insert+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"application_schema.insert+"('
        'jsonb,'
        'character varying(63),'
        'character varying(63),'
        'character varying(63))'
);

grant execute on function "application_schema.insert+" to registered;
create function "application_schema.persist+" (
    application character varying(63),
    name character varying(63),
    use_as_default jsonb,
    database character varying(63) default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "application_schema.persist__internal"(
            application => "application_schema.persist+".application,
            name => "application_schema.persist+".name,
            database => "application_schema.persist+".database );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM application A WHERE
            A.name = "application_schema.persist+".application AND
            A.default_schema = "application_schema.persist+".name;

        for _r in SELECT * FROM jsonb_array_elements(use_as_default) loop
            SELECT * INTO strict _returned_status FROM "application.persist__internal"(
                name => "application_schema.persist+".application,
                default_schema => "application_schema.persist+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"application_schema.persist+"('
        'character varying(63),'
        'character varying(63),'
        'jsonb,'
        'character varying(63))'
);

grant execute on function "application_schema.persist+" to registered;
create function "application_schema.update+" (
    application character varying(63),
    name character varying(63),
    use_as_default jsonb,
    database character varying(63) default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "application_schema.update__internal"(
            application => "application_schema.update+".application,
            name => "application_schema.update+".name,
            database => "application_schema.update+".database );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM application A WHERE
            A.name = "application_schema.update+".application AND
            A.default_schema = "application_schema.update+".name;

        for _r in SELECT * FROM jsonb_array_elements(use_as_default) loop
            SELECT * INTO strict _returned_status FROM "application.update__internal"(
                name => "application_schema.update+".application,
                default_schema => "application_schema.update+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"application_schema.update+"('
        'character varying(63),'
        'character varying(63),'
        'jsonb,'
        'character varying(63))'
);

grant execute on function "application_schema.update+" to registered;
-- email_dispatcher...

-- jaaql...

-- email_template...

create function "email_template.insert+" (
    use_as_default_sign_up jsonb,
    use_as_default_already_signed_up jsonb,
    use_as_default_reset_password jsonb,
    use_as_default_unregisted_password_reset jsonb,
    content_url character varying(255),
    type character varying(1),
    name character varying(63),
    dispatcher character varying(63),
    application character varying(63),
    validation_schema character varying(63) default null,
    base_relation character varying(63) default null,
    dbms_user_column_name character varying(63) default null,
    permissions_and_data_view character varying(63) default null,
    dispatcher_domain_recipient character varying(64) default null,
    requires_confirmation bool default null,
    can_be_sent_anonymously bool default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "email_template.insert__internal"(
            application => "email_template.insert+".application,
            dispatcher => "email_template.insert+".dispatcher,
            name => "email_template.insert+".name,
            type => "email_template.insert+".type,
            content_url => "email_template.insert+".content_url,
            validation_schema => "email_template.insert+".validation_schema,
            base_relation => "email_template.insert+".base_relation,
            dbms_user_column_name => "email_template.insert+".dbms_user_column_name,
            permissions_and_data_view => "email_template.insert+".permissions_and_data_view,
            dispatcher_domain_recipient => "email_template.insert+".dispatcher_domain_recipient,
            requires_confirmation => "email_template.insert+".requires_confirmation,
            can_be_sent_anonymously => "email_template.insert+".can_be_sent_anonymously );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        for _r in SELECT * FROM jsonb_array_elements(use_as_default_sign_up) loop
            SELECT * INTO strict _returned_status FROM "application.insert__internal"(
                name => "email_template.insert+".application,
                default_s_et => "email_template.insert+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_already_signed_up) loop
            SELECT * INTO strict _returned_status FROM "application.insert__internal"(
                name => "email_template.insert+".application,
                default_a_et => "email_template.insert+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_reset_password) loop
            SELECT * INTO strict _returned_status FROM "application.insert__internal"(
                name => "email_template.insert+".application,
                default_r_et => "email_template.insert+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_unregisted_password_reset) loop
            SELECT * INTO strict _returned_status FROM "application.insert__internal"(
                name => "email_template.insert+".application,
                default_u_et => "email_template.insert+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"email_template.insert+"('
        'jsonb,'
        'jsonb,'
        'jsonb,'
        'jsonb,'
        'character varying(255),'
        'character varying(1),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(64),'
        'bool,'
        'bool)'
);

grant execute on function "email_template.insert+" to registered;
create function "email_template.persist+" (
    application character varying(63),
    name character varying(63),
    use_as_default_sign_up jsonb,
    use_as_default_already_signed_up jsonb,
    use_as_default_reset_password jsonb,
    use_as_default_unregisted_password_reset jsonb,
    dispatcher character varying(63) default null,
    type character varying(1) default null,
    content_url character varying(255) default null,
    validation_schema character varying(63) default null,
    base_relation character varying(63) default null,
    dbms_user_column_name character varying(63) default null,
    permissions_and_data_view character varying(63) default null,
    dispatcher_domain_recipient character varying(64) default null,
    requires_confirmation bool default null,
    can_be_sent_anonymously bool default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "email_template.persist__internal"(
            application => "email_template.persist+".application,
            dispatcher => "email_template.persist+".dispatcher,
            name => "email_template.persist+".name,
            type => "email_template.persist+".type,
            content_url => "email_template.persist+".content_url,
            validation_schema => "email_template.persist+".validation_schema,
            base_relation => "email_template.persist+".base_relation,
            dbms_user_column_name => "email_template.persist+".dbms_user_column_name,
            permissions_and_data_view => "email_template.persist+".permissions_and_data_view,
            dispatcher_domain_recipient => "email_template.persist+".dispatcher_domain_recipient,
            requires_confirmation => "email_template.persist+".requires_confirmation,
            can_be_sent_anonymously => "email_template.persist+".can_be_sent_anonymously );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM application A WHERE
            A.name = "email_template.persist+".application AND
            A.default_s_et = "email_template.persist+".name;
        DELETE FROM application A WHERE
            A.name = "email_template.persist+".application AND
            A.default_a_et = "email_template.persist+".name;
        DELETE FROM application A WHERE
            A.name = "email_template.persist+".application AND
            A.default_r_et = "email_template.persist+".name;
        DELETE FROM application A WHERE
            A.name = "email_template.persist+".application AND
            A.default_u_et = "email_template.persist+".name;

        for _r in SELECT * FROM jsonb_array_elements(use_as_default_sign_up) loop
            SELECT * INTO strict _returned_status FROM "application.persist__internal"(
                name => "email_template.persist+".application,
                default_s_et => "email_template.persist+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_already_signed_up) loop
            SELECT * INTO strict _returned_status FROM "application.persist__internal"(
                name => "email_template.persist+".application,
                default_a_et => "email_template.persist+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_reset_password) loop
            SELECT * INTO strict _returned_status FROM "application.persist__internal"(
                name => "email_template.persist+".application,
                default_r_et => "email_template.persist+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_unregisted_password_reset) loop
            SELECT * INTO strict _returned_status FROM "application.persist__internal"(
                name => "email_template.persist+".application,
                default_u_et => "email_template.persist+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"email_template.persist+"('
        'character varying(63),'
        'character varying(63),'
        'jsonb,'
        'jsonb,'
        'jsonb,'
        'jsonb,'
        'character varying(63),'
        'character varying(1),'
        'character varying(255),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(64),'
        'bool,'
        'bool)'
);

grant execute on function "email_template.persist+" to registered;
create function "email_template.update+" (
    application character varying(63),
    name character varying(63),
    use_as_default_sign_up jsonb,
    use_as_default_already_signed_up jsonb,
    use_as_default_reset_password jsonb,
    use_as_default_unregisted_password_reset jsonb,
    dispatcher character varying(63) default null,
    type character varying(1) default null,
    content_url character varying(255) default null,
    validation_schema character varying(63) default null,
    base_relation character varying(63) default null,
    dbms_user_column_name character varying(63) default null,
    permissions_and_data_view character varying(63) default null,
    dispatcher_domain_recipient character varying(64) default null,
    requires_confirmation bool default null,
    can_be_sent_anonymously bool default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "email_template.update__internal"(
            application => "email_template.update+".application,
            dispatcher => "email_template.update+".dispatcher,
            name => "email_template.update+".name,
            type => "email_template.update+".type,
            content_url => "email_template.update+".content_url,
            validation_schema => "email_template.update+".validation_schema,
            base_relation => "email_template.update+".base_relation,
            dbms_user_column_name => "email_template.update+".dbms_user_column_name,
            permissions_and_data_view => "email_template.update+".permissions_and_data_view,
            dispatcher_domain_recipient => "email_template.update+".dispatcher_domain_recipient,
            requires_confirmation => "email_template.update+".requires_confirmation,
            can_be_sent_anonymously => "email_template.update+".can_be_sent_anonymously );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM application A WHERE
            A.name = "email_template.update+".application AND
            A.default_s_et = "email_template.update+".name;
        DELETE FROM application A WHERE
            A.name = "email_template.update+".application AND
            A.default_a_et = "email_template.update+".name;
        DELETE FROM application A WHERE
            A.name = "email_template.update+".application AND
            A.default_r_et = "email_template.update+".name;
        DELETE FROM application A WHERE
            A.name = "email_template.update+".application AND
            A.default_u_et = "email_template.update+".name;

        for _r in SELECT * FROM jsonb_array_elements(use_as_default_sign_up) loop
            SELECT * INTO strict _returned_status FROM "application.update__internal"(
                name => "email_template.update+".application,
                default_s_et => "email_template.update+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_already_signed_up) loop
            SELECT * INTO strict _returned_status FROM "application.update__internal"(
                name => "email_template.update+".application,
                default_a_et => "email_template.update+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_reset_password) loop
            SELECT * INTO strict _returned_status FROM "application.update__internal"(
                name => "email_template.update+".application,
                default_r_et => "email_template.update+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_u_et => (_r->>'default_u_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        for _r in SELECT * FROM jsonb_array_elements(use_as_default_unregisted_password_reset) loop
            SELECT * INTO strict _returned_status FROM "application.update__internal"(
                name => "email_template.update+".application,
                default_u_et => "email_template.update+".name,
                base_url => (_r->>'base_url')::character varying(256),
                templates_source => (_r->>'templates_source')::character varying(256),
                default_schema => (_r->>'default_schema')::character varying(63),
                default_s_et => (_r->>'default_s_et')::character varying(63),
                default_a_et => (_r->>'default_a_et')::character varying(63),
                default_r_et => (_r->>'default_r_et')::character varying(63),
                unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::integer END,
                unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::integer END,
                is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"email_template.update+"('
        'character varying(63),'
        'character varying(63),'
        'jsonb,'
        'jsonb,'
        'jsonb,'
        'jsonb,'
        'character varying(63),'
        'character varying(1),'
        'character varying(255),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(63),'
        'character varying(64),'
        'bool,'
        'bool)'
);

grant execute on function "email_template.update+" to registered;
-- document_template...

-- document_request...

-- account...

create function "account.insert+" (
    use_as_the_anonymous_user jsonb,
    username character varying(255),
    id character varying(63),
    deletion_timestamp timestamptz default null,
    most_recent_password uuid default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "account.insert__internal"(
            id => "account.insert+".id,
            username => "account.insert+".username,
            deletion_timestamp => "account.insert+".deletion_timestamp,
            most_recent_password => "account.insert+".most_recent_password );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        for _r in SELECT * FROM jsonb_array_elements(use_as_the_anonymous_user) loop
            SELECT * INTO strict _returned_status FROM "jaaql.insert__internal"(
                the_anonymous_user => "account.insert+".id,
                security_event_attempt_limit => CASE WHEN _r->>'security_event_attempt_limit' = '' THEN null ELSE (_r->>'security_event_attempt_limit')::smallint END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"account.insert+"('
        'jsonb,'
        'character varying(255),'
        'character varying(63),'
        'timestamptz,'
        'uuid)'
);

grant execute on function "account.insert+" to registered;
create function "account.persist+" (
    id character varying(63),
    use_as_the_anonymous_user jsonb,
    username character varying(255) default null,
    deletion_timestamp timestamptz default null,
    most_recent_password uuid default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "account.persist__internal"(
            id => "account.persist+".id,
            username => "account.persist+".username,
            deletion_timestamp => "account.persist+".deletion_timestamp,
            most_recent_password => "account.persist+".most_recent_password );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM jaaql J WHERE
            J.the_anonymous_user = "account.persist+".id;

        for _r in SELECT * FROM jsonb_array_elements(use_as_the_anonymous_user) loop
            SELECT * INTO strict _returned_status FROM "jaaql.persist__internal"(
                the_anonymous_user => "account.persist+".id,
                security_event_attempt_limit => CASE WHEN _r->>'security_event_attempt_limit' = '' THEN null ELSE (_r->>'security_event_attempt_limit')::smallint END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"account.persist+"('
        'character varying(63),'
        'jsonb,'
        'character varying(255),'
        'timestamptz,'
        'uuid)'
);

grant execute on function "account.persist+" to registered;
create function "account.update+" (
    id character varying(63),
    use_as_the_anonymous_user jsonb,
    username character varying(255) default null,
    deletion_timestamp timestamptz default null,
    most_recent_password uuid default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "account.update__internal"(
            id => "account.update+".id,
            username => "account.update+".username,
            deletion_timestamp => "account.update+".deletion_timestamp,
            most_recent_password => "account.update+".most_recent_password );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM jaaql J WHERE
            J.the_anonymous_user = "account.update+".id;

        for _r in SELECT * FROM jsonb_array_elements(use_as_the_anonymous_user) loop
            SELECT * INTO strict _returned_status FROM "jaaql.update__internal"(
                the_anonymous_user => "account.update+".id,
                security_event_attempt_limit => CASE WHEN _r->>'security_event_attempt_limit' = '' THEN null ELSE (_r->>'security_event_attempt_limit')::smallint END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"account.update+"('
        'character varying(63),'
        'jsonb,'
        'character varying(255),'
        'timestamptz,'
        'uuid)'
);

grant execute on function "account.update+" to registered;
-- account_password...

create function "account_password.insert+" (
    use_as_most_recent_password jsonb,
    creation_timestamp timestamptz,
    hash character varying(512),
    uuid uuid,
    account character varying(63)
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "account_password.insert__internal"(
            account => "account_password.insert+".account,
            uuid => "account_password.insert+".uuid,
            hash => "account_password.insert+".hash,
            creation_timestamp => "account_password.insert+".creation_timestamp );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        for _r in SELECT * FROM jsonb_array_elements(use_as_most_recent_password) loop
            SELECT * INTO strict _returned_status FROM "account.insert__internal"(
                most_recent_password => "account_password.insert+".uuid,
                id => (_r->>'id')::character varying(63),
                username => (_r->>'username')::character varying(255),
                deletion_timestamp => CASE WHEN _r->>'deletion_timestamp' = '' THEN null ELSE (_r->>'deletion_timestamp')::timestamptz END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"account_password.insert+"('
        'jsonb,'
        'timestamptz,'
        'character varying(512),'
        'uuid,'
        'character varying(63))'
);

grant execute on function "account_password.insert+" to registered;
create function "account_password.persist+" (
    uuid uuid,
    use_as_most_recent_password jsonb,
    account character varying(63) default null,
    hash character varying(512) default null,
    creation_timestamp timestamptz default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "account_password.persist__internal"(
            account => "account_password.persist+".account,
            uuid => "account_password.persist+".uuid,
            hash => "account_password.persist+".hash,
            creation_timestamp => "account_password.persist+".creation_timestamp );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM account A WHERE
            A.most_recent_password = "account_password.persist+".uuid;

        for _r in SELECT * FROM jsonb_array_elements(use_as_most_recent_password) loop
            SELECT * INTO strict _returned_status FROM "account.persist__internal"(
                most_recent_password => "account_password.persist+".uuid,
                id => (_r->>'id')::character varying(63),
                username => (_r->>'username')::character varying(255),
                deletion_timestamp => CASE WHEN _r->>'deletion_timestamp' = '' THEN null ELSE (_r->>'deletion_timestamp')::timestamptz END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"account_password.persist+"('
        'uuid,'
        'jsonb,'
        'character varying(63),'
        'character varying(512),'
        'timestamptz)'
);

grant execute on function "account_password.persist+" to registered;
create function "account_password.update+" (
    uuid uuid,
    use_as_most_recent_password jsonb,
    account character varying(63) default null,
    hash character varying(512) default null,
    creation_timestamp timestamptz default null
) returns _jaaql_procedure_result as
$$
    DECLARE
        _returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        _r jsonb;
    BEGIN
        SELECT * INTO strict _returned_status FROM "account_password.update__internal"(
            account => "account_password.update+".account,
            uuid => "account_password.update+".uuid,
            hash => "account_password.update+".hash,
            creation_timestamp => "account_password.update+".creation_timestamp );
        _status.result = _returned_status.result;
        _status.errors = _status.errors || _returned_status.errors;

        DELETE FROM account A WHERE
            A.most_recent_password = "account_password.update+".uuid;

        for _r in SELECT * FROM jsonb_array_elements(use_as_most_recent_password) loop
            SELECT * INTO strict _returned_status FROM "account.update__internal"(
                most_recent_password => "account_password.update+".uuid,
                id => (_r->>'id')::character varying(63),
                username => (_r->>'username')::character varying(255),
                deletion_timestamp => CASE WHEN _r->>'deletion_timestamp' = '' THEN null ELSE (_r->>'deletion_timestamp')::timestamptz END,
                _index => (_r->>'_index')::integer,
                _check_only => cardinality(_status.errors) <> 0);
            _status.errors = _status.errors || _returned_status.errors;
        end loop;
        -- Throw exception, which triggers a rollback if errors
        if cardinality(_status.errors) <> 0 then
            SELECT raise_jaaql_handled_query_exception(_status);
        end if;
        return _status.result::_jaaql_procedure_result;
    END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
    '"account_password.update+"('
        'uuid,'
        'jsonb,'
        'character varying(63),'
        'character varying(512),'
        'timestamptz)'
);

grant execute on function "account_password.update+" to registered;
-- validated_ip_address...

-- security_event...

-- handled_error...

-- pg_base_exception...

-- pg_error_class...

-- pg_exception...

-- remote_procedure...



-- (3) Populate tables

-- jaaql...
insert into jaaql (the_anonymous_user, security_event_attempt_limit)
values (NULL, 3);

-- pg_base_exception...
insert into pg_base_exception (name)
values ('DatabaseError'),
       ('OperationalError'),
       ('NotSupportedError'),
       ('ProgrammingError'),
       ('DataError'),
       ('IntegrityError'),
       ('InternalError');

-- pg_error_class...
insert into pg_error_class (code, name, description)
values ('02', 'NO_DATA', 'this is also a warning class per the SQL standard'),
       ('03', 'SQL_STATEMENT_NOT_YET_COMPLETE', NULL),
       ('08', 'CONNECTION_EXCEPTION', NULL),
       ('09', 'TRIGGERED_ACTION_EXCEPTION', NULL),
       ('0A', 'FEATURE_NOT_SUPPORTED', NULL),
       ('0B', 'INVALID_TRANSACTION_INITIATION', NULL),
       ('0F', 'LOCATOR_EXCEPTION', NULL),
       ('0L', 'INVALID_GRANTOR', NULL),
       ('0P', 'INVALID_ROLE_SPECIFICATION', NULL),
       ('0Z', 'DIAGNOSTICS_EXCEPTION', NULL),
       ('20', 'CASE_NOT_FOUND', NULL),
       ('21', 'CARDINALITY_VIOLATION', NULL),
       ('22', 'DATA_EXCEPTION', NULL),
       ('23', 'INTEGRITY_CONSTRAINT_VIOLATION', NULL),
       ('24', 'INVALID_CURSOR_STATE', NULL),
       ('25', 'INVALID_TRANSACTION_STATE', NULL),
       ('26', 'INVALID_SQL_STATEMENT_NAME', NULL),
       ('27', 'TRIGGERED_DATA_CHANGE_VIOLATION', NULL),
       ('28', 'INVALID_AUTHORIZATION_SPECIFICATION', NULL),
       ('2B', 'DEPENDENT_PRIVILEGE_DESCRIPTORS_STILL_EXIST', NULL);
insert into pg_error_class (code, name, description)
values ('2D', 'INVALID_TRANSACTION_TERMINATION', NULL),
       ('2F', 'SQL_ROUTINE_EXCEPTION', NULL),
       ('34', 'INVALID_CURSOR_NAME', NULL),
       ('38', 'EXTERNAL_ROUTINE_EXCEPTION', NULL),
       ('39', 'EXTERNAL_ROUTINE_INVOCATION_EXCEPTION', NULL),
       ('3B', 'SAVEPOINT_EXCEPTION', NULL),
       ('3D', 'INVALID_CATALOG_NAME', NULL),
       ('3F', 'INVALID_SCHEMA_NAME', NULL),
       ('40', 'TRANSACTION_ROLLBACK', NULL),
       ('42', 'SYNTAX_ERROR_OR_ACCESS_RULE_VIOLATION', NULL),
       ('44', 'WITH_CHECK_OPTION_VIOLATION', NULL),
       ('53', 'INSUFFICIENT_RESOURCES', NULL),
       ('54', 'PROGRAM_LIMIT_EXCEEDED', NULL),
       ('55', 'OBJECT_NOT_IN_PREREQUISITE_STATE', NULL),
       ('57', 'OPERATOR_INTERVENTION', NULL),
       ('58', 'SYSTEM_ERROR', 'errors external to PostgreSQL itself'),
       ('72', 'SNAPSHOT_FAILURE', NULL),
       ('F0', 'CONFIGURATION_FILE_ERROR', NULL),
       ('HV', 'FOREIGN_DATA_WRAPPER_ERROR', 'SQL/MED'),
       ('P0', 'PL/PGSQL_ERROR', NULL);
insert into pg_error_class (code, name, description)
values ('XX', 'INTERNAL_ERROR', NULL);


-- pg_exception...
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('02', '02000', 'NoData', 'DatabaseError'),
       ('02', '02001', 'NoAdditionalDynamicResultSetsReturned', 'DatabaseError'),
       ('03', '03000', 'SqlStatementNotYetComplete', 'DatabaseError'),
       ('08', '08000', 'ConnectionException', 'OperationalError'),
       ('08', '08001', 'SqlclientUnableToEstablishSqlconnection', 'OperationalError'),
       ('08', '08003', 'ConnectionDoesNotExist', 'OperationalError'),
       ('08', '08004', 'SqlserverRejectedEstablishmentOfSqlconnection', 'OperationalError'),
       ('08', '08006', 'ConnectionFailure', 'OperationalError'),
       ('08', '08007', 'TransactionResolutionUnknown', 'OperationalError'),
       ('08', '08P01', 'ProtocolViolation', 'OperationalError'),
       ('09', '09000', 'TriggeredActionException', 'DatabaseError'),
       ('0A', '0A000', 'FeatureNotSupported', 'NotSupportedError'),
       ('0B', '0B000', 'InvalidTransactionInitiation', 'DatabaseError'),
       ('0F', '0F000', 'LocatorException', 'DatabaseError'),
       ('0F', '0F001', 'InvalidLocatorSpecification', 'DatabaseError'),
       ('0L', '0L000', 'InvalidGrantor', 'DatabaseError'),
       ('0L', '0LP01', 'InvalidGrantOperation', 'DatabaseError'),
       ('0P', '0P000', 'InvalidRoleSpecification', 'DatabaseError'),
       ('0Z', '0Z000', 'DiagnosticsException', 'DatabaseError'),
       ('0Z', '0Z002', 'StackedDiagnosticsAccessedWithoutActiveHandler', 'DatabaseError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('20', '20000', 'CaseNotFound', 'ProgrammingError'),
       ('21', '21000', 'CardinalityViolation', 'ProgrammingError'),
       ('22', '22000', 'DataException', 'DataError'),
       ('22', '22001', 'StringDataRightTruncation', 'DataError'),
       ('22', '22002', 'NullValueNoIndicatorParameter', 'DataError'),
       ('22', '22003', 'NumericValueOutOfRange', 'DataError'),
       ('22', '22004', 'NullValueNotAllowed', 'DataError'),
       ('22', '22005', 'ErrorInAssignment', 'DataError'),
       ('22', '22007', 'InvalidDatetimeFormat', 'DataError'),
       ('22', '22008', 'DatetimeFieldOverflow', 'DataError'),
       ('22', '22009', 'InvalidTimeZoneDisplacementValue', 'DataError'),
       ('22', '2200B', 'EscapeCharacterConflict', 'DataError'),
       ('22', '2200C', 'InvalidUseOfEscapeCharacter', 'DataError'),
       ('22', '2200D', 'InvalidEscapeOctet', 'DataError'),
       ('22', '2200F', 'ZeroLengthCharacterString', 'DataError'),
       ('22', '2200G', 'MostSpecificTypeMismatch', 'DataError'),
       ('22', '2200H', 'SequenceGeneratorLimitExceeded', 'DataError'),
       ('22', '2200L', 'NotAnXmlDocument', 'DataError'),
       ('22', '2200M', 'InvalidXmlDocument', 'DataError'),
       ('22', '2200N', 'InvalidXmlContent', 'DataError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('22', '2200S', 'InvalidXmlComment', 'DataError'),
       ('22', '2200T', 'InvalidXmlProcessingInstruction', 'DataError'),
       ('22', '22010', 'InvalidIndicatorParameterValue', 'DataError'),
       ('22', '22011', 'SubstringError', 'DataError'),
       ('22', '22012', 'DivisionByZero', 'DataError'),
       ('22', '22013', 'InvalidPrecedingOrFollowingSize', 'DataError'),
       ('22', '22014', 'InvalidArgumentForNtileFunction', 'DataError'),
       ('22', '22015', 'IntervalFieldOverflow', 'DataError'),
       ('22', '22016', 'InvalidArgumentForNthValueFunction', 'DataError'),
       ('22', '22018', 'InvalidCharacterValueForCast', 'DataError'),
       ('22', '22019', 'InvalidEscapeCharacter', 'DataError'),
       ('22', '2201B', 'InvalidRegularExpression', 'DataError'),
       ('22', '2201E', 'InvalidArgumentForLogarithm', 'DataError'),
       ('22', '2201F', 'InvalidArgumentForPowerFunction', 'DataError'),
       ('22', '2201G', 'InvalidArgumentForWidthBucketFunction', 'DataError'),
       ('22', '2201W', 'InvalidRowCountInLimitClause', 'DataError'),
       ('22', '2201X', 'InvalidRowCountInResultOffsetClause', 'DataError'),
       ('22', '22021', 'CharacterNotInRepertoire', 'DataError'),
       ('22', '22022', 'IndicatorOverflow', 'DataError'),
       ('22', '22023', 'InvalidParameterValue', 'DataError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('22', '22024', 'UnterminatedCString', 'DataError'),
       ('22', '22025', 'InvalidEscapeSequence', 'DataError'),
       ('22', '22026', 'StringDataLengthMismatch', 'DataError'),
       ('22', '22027', 'TrimError', 'DataError'),
       ('22', '2202E', 'ArraySubscriptError', 'DataError'),
       ('22', '2202G', 'InvalidTablesampleRepeat', 'DataError'),
       ('22', '2202H', 'InvalidTablesampleArgument', 'DataError'),
       ('22', '22030', 'DuplicateJsonObjectKeyValue', 'DataError'),
       ('22', '22031', 'InvalidArgumentForSqlJsonDatetimeFunction', 'DataError'),
       ('22', '22032', 'InvalidJsonText', 'DataError'),
       ('22', '22033', 'InvalidSqlJsonSubscript', 'DataError'),
       ('22', '22034', 'MoreThanOneSqlJsonItem', 'DataError'),
       ('22', '22035', 'NoSqlJsonItem', 'DataError'),
       ('22', '22036', 'NonNumericSqlJsonItem', 'DataError'),
       ('22', '22037', 'NonUniqueKeysInAJsonObject', 'DataError'),
       ('22', '22038', 'SingletonSqlJsonItemRequired', 'DataError'),
       ('22', '22039', 'SqlJsonArrayNotFound', 'DataError'),
       ('22', '2203A', 'SqlJsonMemberNotFound', 'DataError'),
       ('22', '2203B', 'SqlJsonNumberNotFound', 'DataError'),
       ('22', '2203C', 'SqlJsonObjectNotFound', 'DataError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('22', '2203D', 'TooManyJsonArrayElements', 'DataError'),
       ('22', '2203E', 'TooManyJsonObjectMembers', 'DataError'),
       ('22', '2203F', 'SqlJsonScalarRequired', 'DataError'),
       ('22', '2203G', 'SqlJsonItemCannotBeCastToTargetType', 'DataError'),
       ('22', '22P01', 'FloatingPointException', 'DataError'),
       ('22', '22P02', 'InvalidTextRepresentation', 'DataError'),
       ('22', '22P03', 'InvalidBinaryRepresentation', 'DataError'),
       ('22', '22P04', 'BadCopyFileFormat', 'DataError'),
       ('22', '22P05', 'UntranslatableCharacter', 'DataError'),
       ('22', '22P06', 'NonstandardUseOfEscapeCharacter', 'DataError'),
       ('23', '23000', 'IntegrityConstraintViolation', 'IntegrityError'),
       ('23', '23001', 'RestrictViolation', 'IntegrityError'),
       ('23', '23502', 'NotNullViolation', 'IntegrityError'),
       ('23', '23503', 'ForeignKeyViolation', 'IntegrityError'),
       ('23', '23505', 'UniqueViolation', 'IntegrityError'),
       ('23', '23514', 'CheckViolation', 'IntegrityError'),
       ('23', '23P01', 'ExclusionViolation', 'IntegrityError'),
       ('24', '24000', 'InvalidCursorState', 'InternalError'),
       ('25', '25000', 'InvalidTransactionState', 'InternalError'),
       ('25', '25001', 'ActiveSqlTransaction', 'InternalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('25', '25002', 'BranchTransactionAlreadyActive', 'InternalError'),
       ('25', '25003', 'InappropriateAccessModeForBranchTransaction', 'InternalError'),
       ('25', '25004', 'InappropriateIsolationLevelForBranchTransaction', 'InternalError'),
       ('25', '25005', 'NoActiveSqlTransactionForBranchTransaction', 'InternalError'),
       ('25', '25006', 'ReadOnlySqlTransaction', 'InternalError'),
       ('25', '25007', 'SchemaAndDataStatementMixingNotSupported', 'InternalError'),
       ('25', '25008', 'HeldCursorRequiresSameIsolationLevel', 'InternalError'),
       ('25', '25P01', 'NoActiveSqlTransaction', 'InternalError'),
       ('25', '25P02', 'InFailedSqlTransaction', 'InternalError'),
       ('25', '25P03', 'IdleInTransactionSessionTimeout', 'InternalError'),
       ('26', '26000', 'InvalidSqlStatementName', 'ProgrammingError'),
       ('27', '27000', 'TriggeredDataChangeViolation', 'OperationalError'),
       ('28', '28000', 'InvalidAuthorizationSpecification', 'OperationalError'),
       ('28', '28P01', 'InvalidPassword', 'OperationalError'),
       ('2B', '2B000', 'DependentPrivilegeDescriptorsStillExist', 'InternalError'),
       ('2B', '2BP01', 'DependentObjectsStillExist', 'InternalError'),
       ('2D', '2D000', 'InvalidTransactionTermination', 'InternalError'),
       ('2F', '2F000', 'SqlRoutineException', 'OperationalError'),
       ('2F', '2F002', 'ModifyingSqlDataNotPermitted', 'OperationalError'),
       ('2F', '2F003', 'ProhibitedSqlStatementAttempted', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('2F', '2F004', 'ReadingSqlDataNotPermitted', 'OperationalError'),
       ('2F', '2F005', 'FunctionExecutedNoReturnStatement', 'OperationalError'),
       ('34', '34000', 'InvalidCursorName', 'ProgrammingError'),
       ('38', '38000', 'ExternalRoutineException', 'OperationalError'),
       ('38', '38001', 'ContainingSqlNotPermitted', 'OperationalError'),
       ('38', '38002', 'ModifyingSqlDataNotPermittedExt', 'OperationalError'),
       ('38', '38003', 'ProhibitedSqlStatementAttemptedExt', 'OperationalError'),
       ('38', '38004', 'ReadingSqlDataNotPermittedExt', 'OperationalError'),
       ('39', '39000', 'ExternalRoutineInvocationException', 'OperationalError'),
       ('39', '39001', 'InvalidSqlstateReturned', 'OperationalError'),
       ('39', '39004', 'NullValueNotAllowedExt', 'OperationalError'),
       ('39', '39P01', 'TriggerProtocolViolated', 'OperationalError'),
       ('39', '39P02', 'SrfProtocolViolated', 'OperationalError'),
       ('39', '39P03', 'EventTriggerProtocolViolated', 'OperationalError'),
       ('3B', '3B000', 'SavepointException', 'OperationalError'),
       ('3B', '3B001', 'InvalidSavepointSpecification', 'OperationalError'),
       ('3D', '3D000', 'InvalidCatalogName', 'ProgrammingError'),
       ('3F', '3F000', 'InvalidSchemaName', 'ProgrammingError'),
       ('40', '40000', 'TransactionRollback', 'OperationalError'),
       ('40', '40001', 'SerializationFailure', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('40', '40002', 'TransactionIntegrityConstraintViolation', 'OperationalError'),
       ('40', '40003', 'StatementCompletionUnknown', 'OperationalError'),
       ('40', '40P01', 'DeadlockDetected', 'OperationalError'),
       ('42', '42000', 'SyntaxErrorOrAccessRuleViolation', 'ProgrammingError'),
       ('42', '42501', 'InsufficientPrivilege', 'ProgrammingError'),
       ('42', '42601', 'SyntaxError', 'ProgrammingError'),
       ('42', '42602', 'InvalidName', 'ProgrammingError'),
       ('42', '42611', 'InvalidColumnDefinition', 'ProgrammingError'),
       ('42', '42622', 'NameTooLong', 'ProgrammingError'),
       ('42', '42701', 'DuplicateColumn', 'ProgrammingError'),
       ('42', '42702', 'AmbiguousColumn', 'ProgrammingError'),
       ('42', '42703', 'UndefinedColumn', 'ProgrammingError'),
       ('42', '42704', 'UndefinedObject', 'ProgrammingError'),
       ('42', '42710', 'DuplicateObject', 'ProgrammingError'),
       ('42', '42712', 'DuplicateAlias', 'ProgrammingError'),
       ('42', '42723', 'DuplicateFunction', 'ProgrammingError'),
       ('42', '42725', 'AmbiguousFunction', 'ProgrammingError'),
       ('42', '42803', 'GroupingError', 'ProgrammingError'),
       ('42', '42804', 'DatatypeMismatch', 'ProgrammingError'),
       ('42', '42809', 'WrongObjectType', 'ProgrammingError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('42', '42830', 'InvalidForeignKey', 'ProgrammingError'),
       ('42', '42846', 'CannotCoerce', 'ProgrammingError'),
       ('42', '42883', 'UndefinedFunction', 'ProgrammingError'),
       ('42', '428C9', 'GeneratedAlways', 'ProgrammingError'),
       ('42', '42939', 'ReservedName', 'ProgrammingError'),
       ('42', '42P01', 'UndefinedTable', 'ProgrammingError'),
       ('42', '42P02', 'UndefinedParameter', 'ProgrammingError'),
       ('42', '42P03', 'DuplicateCursor', 'ProgrammingError'),
       ('42', '42P04', 'DuplicateDatabase', 'ProgrammingError'),
       ('42', '42P05', 'DuplicatePreparedStatement', 'ProgrammingError'),
       ('42', '42P06', 'DuplicateSchema', 'ProgrammingError'),
       ('42', '42P07', 'DuplicateTable', 'ProgrammingError'),
       ('42', '42P08', 'AmbiguousParameter', 'ProgrammingError'),
       ('42', '42P09', 'AmbiguousAlias', 'ProgrammingError'),
       ('42', '42P10', 'InvalidColumnReference', 'ProgrammingError'),
       ('42', '42P11', 'InvalidCursorDefinition', 'ProgrammingError'),
       ('42', '42P12', 'InvalidDatabaseDefinition', 'ProgrammingError'),
       ('42', '42P13', 'InvalidFunctionDefinition', 'ProgrammingError'),
       ('42', '42P14', 'InvalidPreparedStatementDefinition', 'ProgrammingError'),
       ('42', '42P15', 'InvalidSchemaDefinition', 'ProgrammingError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('42', '42P16', 'InvalidTableDefinition', 'ProgrammingError'),
       ('42', '42P17', 'InvalidObjectDefinition', 'ProgrammingError'),
       ('42', '42P18', 'IndeterminateDatatype', 'ProgrammingError'),
       ('42', '42P19', 'InvalidRecursion', 'ProgrammingError'),
       ('42', '42P20', 'WindowingError', 'ProgrammingError'),
       ('42', '42P21', 'CollationMismatch', 'ProgrammingError'),
       ('42', '42P22', 'IndeterminateCollation', 'ProgrammingError'),
       ('44', '44000', 'WithCheckOptionViolation', 'ProgrammingError'),
       ('53', '53000', 'InsufficientResources', 'OperationalError'),
       ('53', '53100', 'DiskFull', 'OperationalError'),
       ('53', '53200', 'OutOfMemory', 'OperationalError'),
       ('53', '53300', 'TooManyConnections', 'OperationalError'),
       ('53', '53400', 'ConfigurationLimitExceeded', 'OperationalError'),
       ('54', '54000', 'ProgramLimitExceeded', 'OperationalError'),
       ('54', '54001', 'StatementTooComplex', 'OperationalError'),
       ('54', '54011', 'TooManyColumns', 'OperationalError'),
       ('54', '54023', 'TooManyArguments', 'OperationalError'),
       ('55', '55000', 'ObjectNotInPrerequisiteState', 'OperationalError'),
       ('55', '55006', 'ObjectInUse', 'OperationalError'),
       ('55', '55P02', 'CantChangeRuntimeParam', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('55', '55P03', 'LockNotAvailable', 'OperationalError'),
       ('55', '55P04', 'UnsafeNewEnumValueUsage', 'OperationalError'),
       ('57', '57000', 'OperatorIntervention', 'OperationalError'),
       ('57', '57014', 'QueryCanceled', 'OperationalError'),
       ('57', '57P01', 'AdminShutdown', 'OperationalError'),
       ('57', '57P02', 'CrashShutdown', 'OperationalError'),
       ('57', '57P03', 'CannotConnectNow', 'OperationalError'),
       ('57', '57P04', 'DatabaseDropped', 'OperationalError'),
       ('57', '57P05', 'IdleSessionTimeout', 'OperationalError'),
       ('58', '58000', 'SystemError', 'OperationalError'),
       ('58', '58030', 'IoError', 'OperationalError'),
       ('58', '58P01', 'UndefinedFile', 'OperationalError'),
       ('58', '58P02', 'DuplicateFile', 'OperationalError'),
       ('72', '72000', 'SnapshotTooOld', 'DatabaseError'),
       ('F0', 'F0000', 'ConfigFileError', 'OperationalError'),
       ('F0', 'F0001', 'LockFileExists', 'OperationalError'),
       ('HV', 'HV000', 'FdwError', 'OperationalError'),
       ('HV', 'HV001', 'FdwOutOfMemory', 'OperationalError'),
       ('HV', 'HV002', 'FdwDynamicParameterValueNeeded', 'OperationalError'),
       ('HV', 'HV004', 'FdwInvalidDataType', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('HV', 'HV005', 'FdwColumnNameNotFound', 'OperationalError'),
       ('HV', 'HV006', 'FdwInvalidDataTypeDescriptors', 'OperationalError'),
       ('HV', 'HV007', 'FdwInvalidColumnName', 'OperationalError'),
       ('HV', 'HV008', 'FdwInvalidColumnNumber', 'OperationalError'),
       ('HV', 'HV009', 'FdwInvalidUseOfNullPointer', 'OperationalError'),
       ('HV', 'HV00A', 'FdwInvalidStringFormat', 'OperationalError'),
       ('HV', 'HV00B', 'FdwInvalidHandle', 'OperationalError'),
       ('HV', 'HV00C', 'FdwInvalidOptionIndex', 'OperationalError'),
       ('HV', 'HV00D', 'FdwInvalidOptionName', 'OperationalError'),
       ('HV', 'HV00J', 'FdwOptionNameNotFound', 'OperationalError'),
       ('HV', 'HV00K', 'FdwReplyHandle', 'OperationalError'),
       ('HV', 'HV00L', 'FdwUnableToCreateExecution', 'OperationalError'),
       ('HV', 'HV00M', 'FdwUnableToCreateReply', 'OperationalError'),
       ('HV', 'HV00N', 'FdwUnableToEstablishConnection', 'OperationalError'),
       ('HV', 'HV00P', 'FdwNoSchemas', 'OperationalError'),
       ('HV', 'HV00Q', 'FdwSchemaNotFound', 'OperationalError'),
       ('HV', 'HV00R', 'FdwTableNotFound', 'OperationalError'),
       ('HV', 'HV010', 'FdwFunctionSequenceError', 'OperationalError'),
       ('HV', 'HV014', 'FdwTooManyHandles', 'OperationalError'),
       ('HV', 'HV021', 'FdwInconsistentDescriptorInformation', 'OperationalError');
insert into pg_exception (pg_class, sqlstate, name, base_exception)
values ('HV', 'HV024', 'FdwInvalidAttributeValue', 'OperationalError'),
       ('HV', 'HV090', 'FdwInvalidStringLengthOrBufferLength', 'OperationalError'),
       ('HV', 'HV091', 'FdwInvalidDescriptorFieldIdentifier', 'OperationalError'),
       ('P0', 'P0000', 'PlpgsqlError', 'ProgrammingError'),
       ('P0', 'P0001', 'RaiseException', 'ProgrammingError'),
       ('P0', 'P0002', 'NoDataFound', 'ProgrammingError'),
       ('P0', 'P0003', 'TooManyRows', 'ProgrammingError'),
       ('P0', 'P0004', 'AssertFailure', 'ProgrammingError'),
       ('XX', 'XX000', 'InternalError_', 'InternalError'),
       ('XX', 'XX001', 'DataCorrupted', 'InternalError');



-- (4) References

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
alter table _jaaql add constraint jaaql__the_anonymous_user
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



-- pg_exception...
alter table pg_exception add constraint pg_exception__pg_error_class
    foreign key (pg_class)
        references pg_error_class (code);
alter table pg_exception add constraint pg_exception__pg_base_exception
    foreign key (base_exception)
        references pg_base_exception (name);
-- remote_procedure...
alter table remote_procedure add constraint remote_procedure__application
    foreign key (application)
        references application (name);

-- (5) Grant access to tables

    grant select, insert, update, delete on application to registered;
    grant select, insert, update, delete on application_schema to registered;
    grant select, insert, update, delete on email_dispatcher to registered;
    grant select, insert, update, delete on jaaql to registered;
    grant select, insert, update, delete on email_template to registered;
    grant select, insert, update, delete on document_template to registered;
    grant select, insert, update, delete on document_request to registered;
    grant select, insert, update, delete on account to registered;
    grant select, insert, update, delete on account_password to registered;
    grant select, insert, update, delete on validated_ip_address to registered;
    grant select, insert, update, delete on security_event to registered;
    grant select, insert, update, delete on handled_error to registered;
    grant select, insert, update, delete on pg_base_exception to registered;
    grant select, insert, update, delete on pg_error_class to registered;
    grant select, insert, update, delete on pg_exception to registered;
    grant select, insert, update, delete on remote_procedure to registered;


-- (6) Grant access to functions

    grant execute on function "application.insert" to registered;
    grant execute on function "application.delete" to registered;
    grant execute on function "application.update" to registered;
    grant execute on function "application_schema.insert" to registered;
    grant execute on function "application_schema.delete" to registered;
    grant execute on function "application_schema.update" to registered;
    grant execute on function "email_dispatcher.insert" to registered;
    grant execute on function "email_dispatcher.delete" to registered;
    grant execute on function "email_dispatcher.update" to registered;
    grant execute on function "email_template.insert" to registered;
    grant execute on function "email_template.delete" to registered;
    grant execute on function "email_template.update" to registered;
    grant execute on function "document_template.insert" to registered;
    grant execute on function "document_template.delete" to registered;
    grant execute on function "document_template.update" to registered;
    grant execute on function "document_request.insert" to registered;
    grant execute on function "document_request.delete" to registered;
    grant execute on function "document_request.update" to registered;
    grant execute on function "account.insert" to registered;
    grant execute on function "account.delete" to registered;
    grant execute on function "account.update" to registered;
    grant execute on function "account_password.insert" to registered;
    grant execute on function "account_password.delete" to registered;
    grant execute on function "account_password.update" to registered;
    grant execute on function "validated_ip_address.insert" to registered;
    grant execute on function "validated_ip_address.delete" to registered;
    grant execute on function "validated_ip_address.update" to registered;
    grant execute on function "security_event.insert" to registered;
    grant execute on function "security_event.delete" to registered;
    grant execute on function "security_event.update" to registered;
    grant execute on function "handled_error.insert" to registered;
    grant execute on function "handled_error.delete" to registered;
    grant execute on function "handled_error.update" to registered;
    grant execute on function "remote_procedure.insert" to registered;
    grant execute on function "remote_procedure.delete" to registered;
    grant execute on function "remote_procedure.update" to registered;

