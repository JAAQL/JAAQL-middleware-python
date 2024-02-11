/*
**  This installation module was generated from ../../../Packages/DBMS/Postgres/15/jaaql.install for Postgres/15
*/
-- Install script

create type _error_type as (
    table_name character varying(63),
    index integer,
    message character varying(256),
    column_name character varying(63)
);
CREATE DOMAIN _error_record AS _error_type
    CHECK ((VALUE).table_name is not null AND
           (VALUE).message is not null);

create type _status_type as (
    result integer,
    errors _error_record[]
);
CREATE DOMAIN _status_record AS _status_type
    CHECK ((VALUE).result is not null);

create type _error_result as
(
    result integer,
    table_name text,
    index integer,
    message text,
    column_name text
);

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
    create function "application.insert__internal" (
        is_live bool,
        unlock_code_validity_period integer,
        unlock_key_validity_period integer,
        base_url character varying(256),
        name character varying(63),
        artifacts_source character varying(256) default null,
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
                    artifacts_source,
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
                    "application.insert__internal"."artifacts_source",
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
        artifacts_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.insert__internal"(
                name => "application.insert".name,
                base_url => "application.insert".base_url,
                artifacts_source => "application.insert".artifacts_source,
                default_schema => "application.insert".default_schema,
                default_s_et => "application.insert".default_s_et,
                default_a_et => "application.insert".default_a_et,
                default_r_et => "application.insert".default_r_et,
                default_u_et => "application.insert".default_u_et,
                unlock_key_validity_period => "application.insert".unlock_key_validity_period,
                unlock_code_validity_period => "application.insert".unlock_code_validity_period,
                is_live => "application.insert".is_live);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
        END;    
    $$ language plpgsql security definer;
    create function "application.update__internal" (
        name character varying(63),
        base_url character varying(256) default null,
        artifacts_source character varying(256) default null,
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
                artifacts_source = coalesce("application.update__internal".artifacts_source, A.artifacts_source),
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
        artifacts_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null,
        unlock_key_validity_period integer default null,
        unlock_code_validity_period integer default null,
        is_live bool default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.update__internal"(
                name => "application.update".name,
                base_url => "application.update".base_url,
                artifacts_source => "application.update".artifacts_source,
                default_schema => "application.update".default_schema,
                default_s_et => "application.update".default_s_et,
                default_a_et => "application.update".default_a_et,
                default_r_et => "application.update".default_r_et,
                default_u_et => "application.update".default_u_et,
                unlock_key_validity_period => "application.update".unlock_key_validity_period,
                unlock_code_validity_period => "application.update".unlock_code_validity_period,
                is_live => "application.update".is_live);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "application.persist__internal" (
        name character varying(63),
        base_url character varying(256) default null,
        artifacts_source character varying(256) default null,
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
            SELECT COUNT(*) into _count
            FROM application A
            WHERE
                A.name = "application.persist__internal".name;
            if _count = 0 then
                SELECT * INTO strict _status FROM "application.insert__internal"(
                    name => "application.persist__internal".name,
                    base_url => "application.persist__internal".base_url,
                    artifacts_source => "application.persist__internal".artifacts_source,
                    default_schema => "application.persist__internal".default_schema,
                    default_s_et => "application.persist__internal".default_s_et,
                    default_a_et => "application.persist__internal".default_a_et,
                    default_r_et => "application.persist__internal".default_r_et,
                    default_u_et => "application.persist__internal".default_u_et,
                    unlock_key_validity_period => CASE WHEN "application.persist__internal".unlock_key_validity_period = '' THEN null ELSE "application.persist__internal".unlock_key_validity_period END,
                    unlock_code_validity_period => CASE WHEN "application.persist__internal".unlock_code_validity_period = '' THEN null ELSE "application.persist__internal".unlock_code_validity_period END,
                    is_live => CASE WHEN "application.persist__internal".is_live = '' THEN null ELSE "application.persist__internal".is_live END,
                    _index => "application.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "application.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "application.update__internal"(
                    name => "application.persist__internal".name,
                    base_url => "application.persist__internal".base_url,
                    artifacts_source => "application.persist__internal".artifacts_source,
                    default_schema => "application.persist__internal".default_schema,
                    default_s_et => "application.persist__internal".default_s_et,
                    default_a_et => "application.persist__internal".default_a_et,
                    default_r_et => "application.persist__internal".default_r_et,
                    default_u_et => "application.persist__internal".default_u_et,
                    unlock_key_validity_period => CASE WHEN "application.persist__internal".unlock_key_validity_period = '' THEN null ELSE "application.persist__internal".unlock_key_validity_period END,
                    unlock_code_validity_period => CASE WHEN "application.persist__internal".unlock_code_validity_period = '' THEN null ELSE "application.persist__internal".unlock_code_validity_period END,
                    is_live => CASE WHEN "application.persist__internal".is_live = '' THEN null ELSE "application.persist__internal".is_live END,
                    _index => "application.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "application.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('application', _index,
                        'Er is niet verwacht Application gevonden met '
                        'Name',
                        'name'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"application.persist__internal"('
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

    create function "application.persist" (
        name character varying(63),
        base_url character varying(256) default null,
        artifacts_source character varying(256) default null,
        default_schema character varying(63) default null,
        default_s_et character varying(63) default null,
        default_a_et character varying(63) default null,
        default_r_et character varying(63) default null,
        default_u_et character varying(63) default null,
        unlock_key_validity_period integer default null,
        unlock_code_validity_period integer default null,
        is_live bool default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.persist__internal"(
                name => "application.persist".name,
                base_url => "application.persist".base_url,
                artifacts_source => "application.persist".artifacts_source,
                default_schema => "application.persist".default_schema,
                default_s_et => "application.persist".default_s_et,
                default_a_et => "application.persist".default_a_et,
                default_r_et => "application.persist".default_r_et,
                default_u_et => "application.persist".default_u_et,
                unlock_key_validity_period => "application.persist".unlock_key_validity_period,
                unlock_code_validity_period => "application.persist".unlock_code_validity_period,
                is_live => "application.persist".is_live);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        name character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application.delete__internal"(
                name => "application.delete".name);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        application character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.insert__internal"(
                application => "application_schema.insert".application,
                name => "application_schema.insert".name,
                database => "application_schema.insert".database);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        database character varying(63) default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.update__internal"(
                application => "application_schema.update".application,
                name => "application_schema.update".name,
                database => "application_schema.update".database);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "application_schema.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM application_schema A
            WHERE
                A.application = "application_schema.persist__internal".application AND
                A.name = "application_schema.persist__internal".name;
            if _count = 0 then
                SELECT * INTO strict _status FROM "application_schema.insert__internal"(
                    application => "application_schema.persist__internal".application,
                    name => "application_schema.persist__internal".name,
                    database => "application_schema.persist__internal".database,
                    _index => "application_schema.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "application_schema.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "application_schema.update__internal"(
                    application => "application_schema.persist__internal".application,
                    name => "application_schema.persist__internal".name,
                    database => "application_schema.persist__internal".database,
                    _index => "application_schema.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "application_schema.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('application_schema', _index,
                        'Er is niet verwacht Application Schema gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"application_schema.persist__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "application_schema.persist" (
        application character varying(63),
        name character varying(63),
        database character varying(63) default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.persist__internal"(
                application => "application_schema.persist".application,
                name => "application_schema.persist".name,
                database => "application_schema.persist".database);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        name character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "application_schema.delete__internal"(
                application => "application_schema.delete".application,
                name => "application_schema.delete".name);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        whitelist text default null) returns SETOF _error_result as
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

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        whitelist text default null) returns SETOF _error_result as
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

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "email_dispatcher.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM email_dispatcher E
            WHERE
                E.application = "email_dispatcher.persist__internal".application AND
                E.name = "email_dispatcher.persist__internal".name;
            if _count = 0 then
                SELECT * INTO strict _status FROM "email_dispatcher.insert__internal"(
                    application => "email_dispatcher.persist__internal".application,
                    name => "email_dispatcher.persist__internal".name,
                    display_name => "email_dispatcher.persist__internal".display_name,
                    protocol => "email_dispatcher.persist__internal".protocol,
                    url => "email_dispatcher.persist__internal".url,
                    port => CASE WHEN "email_dispatcher.persist__internal".port = '' THEN null ELSE "email_dispatcher.persist__internal".port END,
                    username => "email_dispatcher.persist__internal".username,
                    password => "email_dispatcher.persist__internal".password,
                    whitelist => CASE WHEN "email_dispatcher.persist__internal".whitelist = '' THEN null ELSE "email_dispatcher.persist__internal".whitelist END,
                    _index => "email_dispatcher.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "email_dispatcher.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "email_dispatcher.update__internal"(
                    application => "email_dispatcher.persist__internal".application,
                    name => "email_dispatcher.persist__internal".name,
                    display_name => "email_dispatcher.persist__internal".display_name,
                    protocol => "email_dispatcher.persist__internal".protocol,
                    url => "email_dispatcher.persist__internal".url,
                    port => CASE WHEN "email_dispatcher.persist__internal".port = '' THEN null ELSE "email_dispatcher.persist__internal".port END,
                    username => "email_dispatcher.persist__internal".username,
                    password => "email_dispatcher.persist__internal".password,
                    whitelist => CASE WHEN "email_dispatcher.persist__internal".whitelist = '' THEN null ELSE "email_dispatcher.persist__internal".whitelist END,
                    _index => "email_dispatcher.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "email_dispatcher.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('email_dispatcher', _index,
                        'Er is niet verwacht Email Dispatcher gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"email_dispatcher.persist__internal"('
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

    create function "email_dispatcher.persist" (
        application character varying(63),
        name character varying(63),
        display_name character varying(64) default null,
        protocol character varying(8) default null,
        url character varying(256) default null,
        port integer default null,
        username character varying(255) default null,
        password character varying(256) default null,
        whitelist text default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_dispatcher.persist__internal"(
                application => "email_dispatcher.persist".application,
                name => "email_dispatcher.persist".name,
                display_name => "email_dispatcher.persist".display_name,
                protocol => "email_dispatcher.persist".protocol,
                url => "email_dispatcher.persist".url,
                port => "email_dispatcher.persist".port,
                username => "email_dispatcher.persist".username,
                password => "email_dispatcher.persist".password,
                whitelist => "email_dispatcher.persist".whitelist);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        name character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_dispatcher.delete__internal"(
                application => "email_dispatcher.delete".application,
                name => "email_dispatcher.delete".name);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
-- jaaql...
create table _jaaql (
    the_anonymous_user postgres_role not null,
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
    dbms_user_column_name object_name,
    data_validation_table object_name,
    data_validation_view object_name,
    dispatcher_domain_recipient email_account_username,
    can_be_sent_anonymously bool,
    primary key (application, name) );
    create function "email_template.insert__internal" (
        content_url character varying(255),
        type character varying(1),
        name character varying(63),
        dispatcher character varying(63),
        application character varying(63),
        validation_schema character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        data_validation_table character varying(63) default null,
        data_validation_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
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
                    dbms_user_column_name,
                    data_validation_table,
                    data_validation_view,
                    dispatcher_domain_recipient,
                    can_be_sent_anonymously
                ) VALUES (
                    "email_template.insert__internal"."application",
                    "email_template.insert__internal"."dispatcher",
                    "email_template.insert__internal"."name",
                    "email_template.insert__internal"."type",
                    "email_template.insert__internal"."content_url",
                    "email_template.insert__internal"."validation_schema",
                    "email_template.insert__internal"."dbms_user_column_name",
                    "email_template.insert__internal"."data_validation_table",
                    "email_template.insert__internal"."data_validation_view",
                    "email_template.insert__internal"."dispatcher_domain_recipient",
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
        dbms_user_column_name character varying(63) default null,
        data_validation_table character varying(63) default null,
        data_validation_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        can_be_sent_anonymously bool default null) returns SETOF _error_result as
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
                dbms_user_column_name => "email_template.insert".dbms_user_column_name,
                data_validation_table => "email_template.insert".data_validation_table,
                data_validation_view => "email_template.insert".data_validation_view,
                dispatcher_domain_recipient => "email_template.insert".dispatcher_domain_recipient,
                can_be_sent_anonymously => "email_template.insert".can_be_sent_anonymously);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
        END;    
    $$ language plpgsql security definer;
    create function "email_template.update__internal" (
        application character varying(63),
        name character varying(63),
        dispatcher character varying(63) default null,
        type character varying(1) default null,
        content_url character varying(255) default null,
        validation_schema character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        data_validation_table character varying(63) default null,
        data_validation_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
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
                dbms_user_column_name = coalesce("email_template.update__internal".dbms_user_column_name, E.dbms_user_column_name),
                data_validation_table = coalesce("email_template.update__internal".data_validation_table, E.data_validation_table),
                data_validation_view = coalesce("email_template.update__internal".data_validation_view, E.data_validation_view),
                dispatcher_domain_recipient = coalesce("email_template.update__internal".dispatcher_domain_recipient, E.dispatcher_domain_recipient),
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
        dbms_user_column_name character varying(63) default null,
        data_validation_table character varying(63) default null,
        data_validation_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        can_be_sent_anonymously bool default null) returns SETOF _error_result as
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
                dbms_user_column_name => "email_template.update".dbms_user_column_name,
                data_validation_table => "email_template.update".data_validation_table,
                data_validation_view => "email_template.update".data_validation_view,
                dispatcher_domain_recipient => "email_template.update".dispatcher_domain_recipient,
                can_be_sent_anonymously => "email_template.update".can_be_sent_anonymously);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "email_template.persist__internal" (
        application character varying(63),
        name character varying(63),
        dispatcher character varying(63) default null,
        type character varying(1) default null,
        content_url character varying(255) default null,
        validation_schema character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        data_validation_table character varying(63) default null,
        data_validation_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        can_be_sent_anonymously bool default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
            SELECT COUNT(*) into _count
            FROM email_template E
            WHERE
                E.application = "email_template.persist__internal".application AND
                E.name = "email_template.persist__internal".name;
            if _count = 0 then
                SELECT * INTO strict _status FROM "email_template.insert__internal"(
                    application => "email_template.persist__internal".application,
                    dispatcher => "email_template.persist__internal".dispatcher,
                    name => "email_template.persist__internal".name,
                    type => "email_template.persist__internal".type,
                    content_url => "email_template.persist__internal".content_url,
                    validation_schema => "email_template.persist__internal".validation_schema,
                    dbms_user_column_name => "email_template.persist__internal".dbms_user_column_name,
                    data_validation_table => "email_template.persist__internal".data_validation_table,
                    data_validation_view => "email_template.persist__internal".data_validation_view,
                    dispatcher_domain_recipient => "email_template.persist__internal".dispatcher_domain_recipient,
                    can_be_sent_anonymously => CASE WHEN "email_template.persist__internal".can_be_sent_anonymously = '' THEN null ELSE "email_template.persist__internal".can_be_sent_anonymously END,
                    _index => "email_template.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "email_template.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "email_template.update__internal"(
                    application => "email_template.persist__internal".application,
                    name => "email_template.persist__internal".name,
                    dispatcher => "email_template.persist__internal".dispatcher,
                    type => "email_template.persist__internal".type,
                    content_url => "email_template.persist__internal".content_url,
                    validation_schema => "email_template.persist__internal".validation_schema,
                    dbms_user_column_name => "email_template.persist__internal".dbms_user_column_name,
                    data_validation_table => "email_template.persist__internal".data_validation_table,
                    data_validation_view => "email_template.persist__internal".data_validation_view,
                    dispatcher_domain_recipient => "email_template.persist__internal".dispatcher_domain_recipient,
                    can_be_sent_anonymously => CASE WHEN "email_template.persist__internal".can_be_sent_anonymously = '' THEN null ELSE "email_template.persist__internal".can_be_sent_anonymously END,
                    _index => "email_template.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "email_template.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('email_template', _index,
                        'Er is niet verwacht Email Template gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"email_template.persist__internal"('
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
            'integer,'
            'boolean)'
    );

    create function "email_template.persist" (
        application character varying(63),
        name character varying(63),
        dispatcher character varying(63) default null,
        type character varying(1) default null,
        content_url character varying(255) default null,
        validation_schema character varying(63) default null,
        dbms_user_column_name character varying(63) default null,
        data_validation_table character varying(63) default null,
        data_validation_view character varying(63) default null,
        dispatcher_domain_recipient character varying(64) default null,
        can_be_sent_anonymously bool default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_template.persist__internal"(
                application => "email_template.persist".application,
                dispatcher => "email_template.persist".dispatcher,
                name => "email_template.persist".name,
                type => "email_template.persist".type,
                content_url => "email_template.persist".content_url,
                validation_schema => "email_template.persist".validation_schema,
                dbms_user_column_name => "email_template.persist".dbms_user_column_name,
                data_validation_table => "email_template.persist".data_validation_table,
                data_validation_view => "email_template.persist".data_validation_view,
                dispatcher_domain_recipient => "email_template.persist".dispatcher_domain_recipient,
                can_be_sent_anonymously => "email_template.persist".can_be_sent_anonymously);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        name character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "email_template.delete__internal"(
                application => "email_template.delete".application,
                name => "email_template.delete".name);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        email_template character varying(63) default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.insert__internal"(
                application => "document_template.insert".application,
                name => "document_template.insert".name,
                content_path => "document_template.insert".content_path,
                email_template => "document_template.insert".email_template);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        email_template character varying(63) default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.update__internal"(
                application => "document_template.update".application,
                name => "document_template.update".name,
                content_path => "document_template.update".content_path,
                email_template => "document_template.update".email_template);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "document_template.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM document_template D
            WHERE
                D.application = "document_template.persist__internal".application AND
                D.name = "document_template.persist__internal".name;
            if _count = 0 then
                SELECT * INTO strict _status FROM "document_template.insert__internal"(
                    application => "document_template.persist__internal".application,
                    name => "document_template.persist__internal".name,
                    content_path => "document_template.persist__internal".content_path,
                    email_template => "document_template.persist__internal".email_template,
                    _index => "document_template.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "document_template.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "document_template.update__internal"(
                    application => "document_template.persist__internal".application,
                    name => "document_template.persist__internal".name,
                    content_path => "document_template.persist__internal".content_path,
                    email_template => "document_template.persist__internal".email_template,
                    _index => "document_template.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "document_template.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('document_template', _index,
                        'Er is niet verwacht Document Template gevonden met '
                        'Application, Name',
                        'name'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"document_template.persist__internal"('
            'character varying(63),'
            'character varying(63),'
            'character varying(255),'
            'character varying(63),'
            'integer,'
            'boolean)'
    );

    create function "document_template.persist" (
        application character varying(63),
        name character varying(63),
        content_path character varying(255) default null,
        email_template character varying(63) default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.persist__internal"(
                application => "document_template.persist".application,
                name => "document_template.persist".name,
                content_path => "document_template.persist".content_path,
                email_template => "document_template.persist".email_template);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        name character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_template.delete__internal"(
                application => "document_template.delete".application,
                name => "document_template.delete".name);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        render_timestamp timestamptz default null) returns SETOF _error_result as
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

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        render_timestamp timestamptz default null) returns SETOF _error_result as
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

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "document_request.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM document_request D
            WHERE
                D.uuid = "document_request.persist__internal".uuid;
            if _count = 0 then
                SELECT * INTO strict _status FROM "document_request.insert__internal"(
                    application => "document_request.persist__internal".application,
                    template => "document_request.persist__internal".template,
                    uuid => CASE WHEN "document_request.persist__internal".uuid = '' THEN null ELSE "document_request.persist__internal".uuid END,
                    request_timestamp => CASE WHEN "document_request.persist__internal".request_timestamp = '' THEN null ELSE "document_request.persist__internal".request_timestamp END,
                    encrypted_access_token => "document_request.persist__internal".encrypted_access_token,
                    encrypted_parameters => CASE WHEN "document_request.persist__internal".encrypted_parameters = '' THEN null ELSE "document_request.persist__internal".encrypted_parameters END,
                    render_timestamp => CASE WHEN "document_request.persist__internal".render_timestamp = '' THEN null ELSE "document_request.persist__internal".render_timestamp END,
                    _index => "document_request.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "document_request.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "document_request.update__internal"(
                    uuid => CASE WHEN "document_request.persist__internal".uuid = '' THEN null ELSE "document_request.persist__internal".uuid END,
                    application => "document_request.persist__internal".application,
                    template => "document_request.persist__internal".template,
                    request_timestamp => CASE WHEN "document_request.persist__internal".request_timestamp = '' THEN null ELSE "document_request.persist__internal".request_timestamp END,
                    encrypted_access_token => "document_request.persist__internal".encrypted_access_token,
                    encrypted_parameters => CASE WHEN "document_request.persist__internal".encrypted_parameters = '' THEN null ELSE "document_request.persist__internal".encrypted_parameters END,
                    render_timestamp => CASE WHEN "document_request.persist__internal".render_timestamp = '' THEN null ELSE "document_request.persist__internal".render_timestamp END,
                    _index => "document_request.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "document_request.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('document_request', _index,
                        'Er is niet verwacht Document Request gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"document_request.persist__internal"('
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

    create function "document_request.persist" (
        uuid uuid,
        application character varying(63) default null,
        template character varying(63) default null,
        request_timestamp timestamptz default null,
        encrypted_access_token character varying(64) default null,
        encrypted_parameters text default null,
        render_timestamp timestamptz default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_request.persist__internal"(
                application => "document_request.persist".application,
                template => "document_request.persist".template,
                uuid => "document_request.persist".uuid,
                request_timestamp => "document_request.persist".request_timestamp,
                encrypted_access_token => "document_request.persist".encrypted_access_token,
                encrypted_parameters => "document_request.persist".encrypted_parameters,
                render_timestamp => "document_request.persist".render_timestamp);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        uuid uuid) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "document_request.delete__internal"(
                uuid => "document_request.delete".uuid);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        most_recent_password uuid default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.insert__internal"(
                id => "account.insert".id,
                username => "account.insert".username,
                deletion_timestamp => "account.insert".deletion_timestamp,
                most_recent_password => "account.insert".most_recent_password);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        most_recent_password uuid default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.update__internal"(
                id => "account.update".id,
                username => "account.update".username,
                deletion_timestamp => "account.update".deletion_timestamp,
                most_recent_password => "account.update".most_recent_password);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "account.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM account A
            WHERE
                A.id = "account.persist__internal".id;
            if _count = 0 then
                SELECT * INTO strict _status FROM "account.insert__internal"(
                    id => "account.persist__internal".id,
                    username => "account.persist__internal".username,
                    deletion_timestamp => CASE WHEN "account.persist__internal".deletion_timestamp = '' THEN null ELSE "account.persist__internal".deletion_timestamp END,
                    most_recent_password => CASE WHEN "account.persist__internal".most_recent_password = '' THEN null ELSE "account.persist__internal".most_recent_password END,
                    _index => "account.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "account.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "account.update__internal"(
                    id => "account.persist__internal".id,
                    username => "account.persist__internal".username,
                    deletion_timestamp => CASE WHEN "account.persist__internal".deletion_timestamp = '' THEN null ELSE "account.persist__internal".deletion_timestamp END,
                    most_recent_password => CASE WHEN "account.persist__internal".most_recent_password = '' THEN null ELSE "account.persist__internal".most_recent_password END,
                    _index => "account.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "account.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('account', _index,
                        'Er is niet verwacht Account gevonden met '
                        'Id',
                        'id'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"account.persist__internal"('
            'character varying(63),'
            'character varying(255),'
            'timestamptz,'
            'uuid,'
            'integer,'
            'boolean)'
    );

    create function "account.persist" (
        id character varying(63),
        username character varying(255) default null,
        deletion_timestamp timestamptz default null,
        most_recent_password uuid default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.persist__internal"(
                id => "account.persist".id,
                username => "account.persist".username,
                deletion_timestamp => "account.persist".deletion_timestamp,
                most_recent_password => "account.persist".most_recent_password);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        id character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account.delete__internal"(
                id => "account.delete".id);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        account character varying(63)) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.insert__internal"(
                account => "account_password.insert".account,
                uuid => "account_password.insert".uuid,
                hash => "account_password.insert".hash,
                creation_timestamp => "account_password.insert".creation_timestamp);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        creation_timestamp timestamptz default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.update__internal"(
                account => "account_password.update".account,
                uuid => "account_password.update".uuid,
                hash => "account_password.update".hash,
                creation_timestamp => "account_password.update".creation_timestamp);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "account_password.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM account_password A
            WHERE
                A.uuid = "account_password.persist__internal".uuid;
            if _count = 0 then
                SELECT * INTO strict _status FROM "account_password.insert__internal"(
                    account => "account_password.persist__internal".account,
                    uuid => CASE WHEN "account_password.persist__internal".uuid = '' THEN null ELSE "account_password.persist__internal".uuid END,
                    hash => "account_password.persist__internal".hash,
                    creation_timestamp => CASE WHEN "account_password.persist__internal".creation_timestamp = '' THEN null ELSE "account_password.persist__internal".creation_timestamp END,
                    _index => "account_password.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "account_password.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "account_password.update__internal"(
                    uuid => CASE WHEN "account_password.persist__internal".uuid = '' THEN null ELSE "account_password.persist__internal".uuid END,
                    account => "account_password.persist__internal".account,
                    hash => "account_password.persist__internal".hash,
                    creation_timestamp => CASE WHEN "account_password.persist__internal".creation_timestamp = '' THEN null ELSE "account_password.persist__internal".creation_timestamp END,
                    _index => "account_password.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "account_password.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('account_password', _index,
                        'Er is niet verwacht Account Password gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"account_password.persist__internal"('
            'uuid,'
            'character varying(63),'
            'character varying(512),'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "account_password.persist" (
        uuid uuid,
        account character varying(63) default null,
        hash character varying(512) default null,
        creation_timestamp timestamptz default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.persist__internal"(
                account => "account_password.persist".account,
                uuid => "account_password.persist".uuid,
                hash => "account_password.persist".hash,
                creation_timestamp => "account_password.persist".creation_timestamp);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        uuid uuid) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "account_password.delete__internal"(
                uuid => "account_password.delete".uuid);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        account character varying(63)) returns SETOF _error_result as
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

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
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
        last_authentication_timestamp timestamptz default null) returns SETOF _error_result as
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

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "validated_ip_address.persist__internal" (
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
            SELECT COUNT(*) into _count
            FROM validated_ip_address V
            WHERE
                V.uuid = "validated_ip_address.persist__internal".uuid;
            if _count = 0 then
                SELECT * INTO strict _status FROM "validated_ip_address.insert__internal"(
                    account => "validated_ip_address.persist__internal".account,
                    uuid => CASE WHEN "validated_ip_address.persist__internal".uuid = '' THEN null ELSE "validated_ip_address.persist__internal".uuid END,
                    encrypted_salted_ip_address => "validated_ip_address.persist__internal".encrypted_salted_ip_address,
                    first_authentication_timestamp => CASE WHEN "validated_ip_address.persist__internal".first_authentication_timestamp = '' THEN null ELSE "validated_ip_address.persist__internal".first_authentication_timestamp END,
                    last_authentication_timestamp => CASE WHEN "validated_ip_address.persist__internal".last_authentication_timestamp = '' THEN null ELSE "validated_ip_address.persist__internal".last_authentication_timestamp END,
                    _index => "validated_ip_address.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "validated_ip_address.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "validated_ip_address.update__internal"(
                    uuid => CASE WHEN "validated_ip_address.persist__internal".uuid = '' THEN null ELSE "validated_ip_address.persist__internal".uuid END,
                    account => "validated_ip_address.persist__internal".account,
                    encrypted_salted_ip_address => "validated_ip_address.persist__internal".encrypted_salted_ip_address,
                    first_authentication_timestamp => CASE WHEN "validated_ip_address.persist__internal".first_authentication_timestamp = '' THEN null ELSE "validated_ip_address.persist__internal".first_authentication_timestamp END,
                    last_authentication_timestamp => CASE WHEN "validated_ip_address.persist__internal".last_authentication_timestamp = '' THEN null ELSE "validated_ip_address.persist__internal".last_authentication_timestamp END,
                    _index => "validated_ip_address.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "validated_ip_address.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('validated_ip_address', _index,
                        'Er is niet verwacht Validated Ip Address gevonden met '
                        'Uuid',
                        'uuid'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"validated_ip_address.persist__internal"('
            'uuid,'
            'character varying(63),'
            'character varying(256),'
            'timestamptz,'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "validated_ip_address.persist" (
        uuid uuid,
        account character varying(63) default null,
        encrypted_salted_ip_address character varying(256) default null,
        first_authentication_timestamp timestamptz default null,
        last_authentication_timestamp timestamptz default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "validated_ip_address.persist__internal"(
                account => "validated_ip_address.persist".account,
                uuid => "validated_ip_address.persist".uuid,
                encrypted_salted_ip_address => "validated_ip_address.persist".encrypted_salted_ip_address,
                first_authentication_timestamp => "validated_ip_address.persist".first_authentication_timestamp,
                last_authentication_timestamp => "validated_ip_address.persist".last_authentication_timestamp);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        uuid uuid) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "validated_ip_address.delete__internal"(
                uuid => "validated_ip_address.delete".uuid);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
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
    create function "security_event.insert__internal" (
        unlock_code character varying(10),
        unlock_key uuid,
        account character varying(63),
        email_template character varying(63),
        wrong_key_attempt_count smallint,
        creation_timestamp timestamptz,
        event_lock uuid,
        application character varying(63),
        unlock_timestamp timestamptz default null,
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
            if "security_event.insert__internal".account is null then
                "security_event.insert__internal".account = '';
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
            if "security_event.insert__internal".account = '' then
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er moet een waarde ingevuld worden voor Account',
                        'account'
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
                    unlock_key,
                    unlock_code,
                    unlock_timestamp
                ) VALUES (
                    "security_event.insert__internal"."application",
                    "security_event.insert__internal"."event_lock",
                    "security_event.insert__internal"."creation_timestamp",
                    "security_event.insert__internal"."wrong_key_attempt_count",
                    "security_event.insert__internal"."email_template",
                    "security_event.insert__internal"."account",
                    "security_event.insert__internal"."unlock_key",
                    "security_event.insert__internal"."unlock_code",
                    "security_event.insert__internal"."unlock_timestamp" );
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
            'character varying(63),'
            'smallint,'
            'timestamptz,'
            'uuid,'
            'character varying(63),'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "security_event.insert" (
        unlock_code character varying(10),
        unlock_key uuid,
        account character varying(63),
        email_template character varying(63),
        wrong_key_attempt_count smallint,
        creation_timestamp timestamptz,
        event_lock uuid,
        application character varying(63),
        unlock_timestamp timestamptz default null) returns SETOF _error_result as
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
                unlock_key => "security_event.insert".unlock_key,
                unlock_code => "security_event.insert".unlock_code,
                unlock_timestamp => "security_event.insert".unlock_timestamp);

            if cardinality(_status.errors) <> 0 then
                return QUERY
                    SELECT
                        _status.result::integer as result,
                        unnest.table_name::text as table_name,
                        unnest.index::integer as index,
                        unnest.message::text as message,
                        unnest.column_name::text as column_name
                    FROM unnest(_status.errors);
            end if;
            return QUERY
                SELECT
                    _status.result::integer as result,
                    null::text as table_name,
                    null::integer as index,
                    null::text as message,
                    null::text as column_name;
        END;    
    $$ language plpgsql security definer;
    create function "security_event.update__internal" (
        application character varying(63),
        event_lock uuid,
        creation_timestamp timestamptz default null,
        wrong_key_attempt_count smallint default null,
        email_template character varying(63) default null,
        account character varying(63) default null,
        unlock_key uuid default null,
        unlock_code character varying(10) default null,
        unlock_timestamp timestamptz default null,
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
                unlock_key = coalesce("security_event.update__internal".unlock_key, S.unlock_key),
                unlock_code = coalesce("security_event.update__internal".unlock_code, S.unlock_code),
                unlock_timestamp = coalesce("security_event.update__internal".unlock_timestamp, S.unlock_timestamp)
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
            'uuid,'
            'character varying(10),'
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
        unlock_key uuid default null,
        unlock_code character varying(10) default null,
        unlock_timestamp timestamptz default null) returns SETOF _error_result as
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
                unlock_key => "security_event.update".unlock_key,
                unlock_code => "security_event.update".unlock_code,
                unlock_timestamp => "security_event.update".unlock_timestamp);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;
    create function "security_event.persist__internal" (
        application character varying(63),
        event_lock uuid,
        creation_timestamp timestamptz default null,
        wrong_key_attempt_count smallint default null,
        email_template character varying(63) default null,
        account character varying(63) default null,
        unlock_key uuid default null,
        unlock_code character varying(10) default null,
        unlock_timestamp timestamptz default null,
        _index integer default null,
        _check_only boolean default false) returns _status_record as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
            _count integer not null = 0;
        BEGIN
            SELECT COUNT(*) into _count
            FROM security_event S
            WHERE
                S.application = "security_event.persist__internal".application AND
                S.event_lock = "security_event.persist__internal".event_lock;
            if _count = 0 then
                SELECT * INTO strict _status FROM "security_event.insert__internal"(
                    application => "security_event.persist__internal".application,
                    event_lock => CASE WHEN "security_event.persist__internal".event_lock = '' THEN null ELSE "security_event.persist__internal".event_lock END,
                    creation_timestamp => CASE WHEN "security_event.persist__internal".creation_timestamp = '' THEN null ELSE "security_event.persist__internal".creation_timestamp END,
                    wrong_key_attempt_count => CASE WHEN "security_event.persist__internal".wrong_key_attempt_count = '' THEN null ELSE "security_event.persist__internal".wrong_key_attempt_count END,
                    email_template => "security_event.persist__internal".email_template,
                    account => "security_event.persist__internal".account,
                    unlock_key => CASE WHEN "security_event.persist__internal".unlock_key = '' THEN null ELSE "security_event.persist__internal".unlock_key END,
                    unlock_code => "security_event.persist__internal".unlock_code,
                    unlock_timestamp => CASE WHEN "security_event.persist__internal".unlock_timestamp = '' THEN null ELSE "security_event.persist__internal".unlock_timestamp END,
                    _index => "security_event.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "security_event.persist__internal"._check_only);
            elsif _count = 1 then
                SELECT * INTO strict _status FROM "security_event.update__internal"(
                    application => "security_event.persist__internal".application,
                    event_lock => CASE WHEN "security_event.persist__internal".event_lock = '' THEN null ELSE "security_event.persist__internal".event_lock END,
                    creation_timestamp => CASE WHEN "security_event.persist__internal".creation_timestamp = '' THEN null ELSE "security_event.persist__internal".creation_timestamp END,
                    wrong_key_attempt_count => CASE WHEN "security_event.persist__internal".wrong_key_attempt_count = '' THEN null ELSE "security_event.persist__internal".wrong_key_attempt_count END,
                    email_template => "security_event.persist__internal".email_template,
                    account => "security_event.persist__internal".account,
                    unlock_key => CASE WHEN "security_event.persist__internal".unlock_key = '' THEN null ELSE "security_event.persist__internal".unlock_key END,
                    unlock_code => "security_event.persist__internal".unlock_code,
                    unlock_timestamp => CASE WHEN "security_event.persist__internal".unlock_timestamp = '' THEN null ELSE "security_event.persist__internal".unlock_timestamp END,
                    _index => "security_event.persist__internal"._index,
                    _check_only => cardinality(_status.errors) <> 0 or "security_event.persist__internal"._check_only);
            else
                _status.errors = _status.errors ||
                    ROW('security_event', _index,
                        'Er is niet verwacht Security Event gevonden met '
                        'Application, Event Lock',
                        'event_lock'
                    )::_error_record;
            end if;

            return _status;
        END;
    $$ language plpgsql security definer;

    select * from plpgsql_check_function(
        '"security_event.persist__internal"('
            'character varying(63),'
            'uuid,'
            'timestamptz,'
            'smallint,'
            'character varying(63),'
            'character varying(63),'
            'uuid,'
            'character varying(10),'
            'timestamptz,'
            'integer,'
            'boolean)'
    );

    create function "security_event.persist" (
        application character varying(63),
        event_lock uuid,
        creation_timestamp timestamptz default null,
        wrong_key_attempt_count smallint default null,
        email_template character varying(63) default null,
        account character varying(63) default null,
        unlock_key uuid default null,
        unlock_code character varying(10) default null,
        unlock_timestamp timestamptz default null) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "security_event.persist__internal"(
                application => "security_event.persist".application,
                event_lock => "security_event.persist".event_lock,
                creation_timestamp => "security_event.persist".creation_timestamp,
                wrong_key_attempt_count => "security_event.persist".wrong_key_attempt_count,
                email_template => "security_event.persist".email_template,
                account => "security_event.persist".account,
                unlock_key => "security_event.persist".unlock_key,
                unlock_code => "security_event.persist".unlock_code,
                unlock_timestamp => "security_event.persist".unlock_timestamp);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
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
        event_lock uuid) returns SETOF _error_result as
    $$
        DECLARE
            _status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
        BEGIN
            SELECT * INTO strict _status FROM "security_event.delete__internal"(
                application => "security_event.delete".application,
                event_lock => "security_event.delete".event_lock);

            return QUERY
                SELECT
                    _status.result::integer as result,
                    unnest.table_name::text as table_name,
                    unnest.index::integer as index,
                    unnest.message::text as message,
                    unnest.column_name::text as column_name
                FROM unnest(_status.errors);
        END;
    $$ language plpgsql security definer;


-- (2) References












