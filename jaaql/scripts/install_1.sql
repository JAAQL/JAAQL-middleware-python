CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE DOMAIN postgres_addressable_name AS varchar(64) CHECK (VALUE ~* '^[a-z0-9_\-]+$');
CREATE DOMAIN jaaql_account_id AS varchar(36) CHECK (VALUE = 'postgres' OR VALUE = 'jaaql' OR value::uuid = value::uuid);
CREATE DOMAIN email_address AS varchar(255) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$' AND lower(VALUE) = VALUE));

create or replace function drop_tenant_database(db_name postgres_addressable_name, _tenant postgres_addressable_name) returns void as
$$
BEGIN
    if db_name = 'jaaql' then
        RAISE EXCEPTION 'Cannot delete the jaaql database';
    end if;
    DELETE FROM tenant_database WHERE name = db_name AND tenant = _tenant;
    PERFORM pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = _tenant || '__' || db_name AND pid <> pg_backend_pid();
    PERFORM dblink_exec('dbname=' || current_database() || ' user=postgres password=123456', 'DROP DATABASE ' || _tenant  || '__' || db_name);
END
$$ language plpgsql SECURITY DEFINER;

create or replace function create_tenant_database(db_name postgres_addressable_name, skip_db boolean = false) returns void as
$$
DECLARE
    the_tenant text;
BEGIN
    SELECT get_tenant() into the_tenant;
    if the_tenant <> 'jaaql' AND db_name = 'jaaql' then
        RAISE EXCEPTION '"jaaql" is a reserved database name. Please use a different one';
    end if;

    if not skip_db then
        PERFORM dblink_exec('dbname=' || current_database() || ' user=postgres password=123456', 'CREATE DATABASE ' || the_tenant  || '__' || db_name || ' with ENCODING = ''UTF8'' TABLESPACE = pg_default CONNECTION LIMIT = -1;');
        PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'create view jaaql__table_primary_cols as (SELECT c.column_name, tc.table_name
        FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
            JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema
            AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
        WHERE constraint_type = ''PRIMARY KEY'' AND c.table_schema = ''public''
            );');
        PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'create view jaaql__table_cols_marked_primary as (
        SELECT
            col.table_name,
            col.column_name,
            CASE WHEN tpc.column_name is not null then true else false end as is_primary
        FROM information_schema.columns col
            LEFT JOIN jaaql__table_primary_cols tpc ON tpc.table_name = col.table_name AND col.column_name = tpc.column_name
        WHERE col.table_schema = ''public''
            );');
        if the_tenant = 'jaaql' then
            PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'GRANT select on jaaql__table_primary_cols to jaaql');
            PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'GRANT select on jaaql__table_cols_marked_primary to jaaql');
        else
            PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'GRANT select on jaaql__table_primary_cols to ' || the_tenant || '__admin');
            PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'GRANT select on jaaql__table_cols_marked_primary to ' || the_tenant || '__admin');
        end if;
        PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'CREATE DOMAIN jaaql_account_id AS varchar(36) CHECK (VALUE = ''postgres'' OR VALUE = ''jaaql'' OR value::uuid = value::uuid);');
        PERFORM dblink_exec('dbname=' || the_tenant  || '__' || db_name || ' user=postgres password=123456', 'CREATE DOMAIN email_address AS varchar(255) CHECK ((VALUE ~* ''^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$'' AND lower(VALUE) = VALUE));');
    end if;
    raise notice 'Checking in here';
    EXECUTE 'alter database "' || the_tenant || '__' || db_name || '" owner to "' || the_tenant || '__admin"';
    EXECUTE 'GRANT CONNECT ON DATABASE "' || the_tenant || '__' || db_name || '" TO "' || the_tenant || '__public"';
    INSERT INTO tenant_database (tenant, name) VALUES (the_tenant, db_name) ON CONFLICT DO NOTHING;
END
$$ language plpgsql SECURITY DEFINER;

create or replace function setup_jaaql_role() returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    execute 'CREATE ROLE jaaql WITH CREATEROLE LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    GRANT execute on function drop_tenant_database(postgres_addressable_name, postgres_addressable_name) to jaaql with grant option;
    GRANT execute on function create_tenant_database(postgres_addressable_name, boolean) to jaaql with grant option;
    return secure_pass;
END
$$ language plpgsql;
