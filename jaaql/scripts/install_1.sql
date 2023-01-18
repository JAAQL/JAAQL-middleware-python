CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS jaaql;
CREATE DOMAIN postgres_addressable_name AS varchar(64) CHECK (VALUE ~* '^[a-z0-9_\-]+$');
CREATE DOMAIN jaaql_account_id AS varchar(36) CHECK (VALUE = 'postgres' OR VALUE = 'jaaql' OR value::uuid = value::uuid);
CREATE DOMAIN email_address AS varchar(255) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$' AND lower(VALUE) = VALUE));

create or replace function drop_database(name postgres_addressable_name) returns void as
$$
BEGIN
    if db_name = 'jaaql' then
        RAISE EXCEPTION 'Cannot delete the jaaql database';
    end if;
    DELETE FROM database WHERE name = drop_database.name;
END
$$ language plpgsql SECURITY DEFINER;

create or replace function create_database(name postgres_addressable_name, skip_db boolean = false, insert_record boolean = true) returns void as
$$
BEGIN
    if create_database.name = 'jaaql' then
        RAISE EXCEPTION '"jaaql" is a reserved database name. Please use a different one';
    end if;

    if not skip_db then
        PERFORM dblink_exec('dbname=' || current_database(), 'CREATE DATABASE "' || create_database.name || '" with ENCODING = ''UTF8'' TABLESPACE = pg_default CONNECTION LIMIT = -1;');
        PERFORM dblink_exec('dbname=' || create_database.name, 'create view jaaql__table_primary_cols as (SELECT c.column_name, tc.table_name
        FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
            JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema
            AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
        WHERE constraint_type = ''PRIMARY KEY'' AND c.table_schema = ''public''
            );');
        PERFORM dblink_exec('dbname=' || create_database.name, 'create view jaaql__table_cols_marked_primary as (
        SELECT
            col.table_name,
            col.column_name,
            CASE WHEN tpc.column_name is not null then true else false end as is_primary
        FROM information_schema.columns col
            LEFT JOIN jaaql__table_primary_cols tpc ON tpc.table_name = col.table_name AND col.column_name = tpc.column_name
        WHERE col.table_schema = ''public''
            );');

        PERFORM dblink_exec('dbname=' ||  create_database.name, 'GRANT select on jaaql__table_primary_cols to jaaql__admin');
        PERFORM dblink_exec('dbname=' ||  create_database.name, 'GRANT select on jaaql__table_cols_marked_primary to jaaql__admin');

        PERFORM dblink_exec('dbname=' ||  create_database.name, 'CREATE DOMAIN jaaql_account_id AS varchar(36) CHECK (VALUE = ''postgres'' OR VALUE = ''jaaql'' OR value::uuid = value::uuid);');
        PERFORM dblink_exec('dbname=' ||  create_database.name, 'CREATE DOMAIN email_address AS varchar(255) CHECK ((VALUE ~* ''^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$'' AND lower(VALUE) = VALUE));');
        PERFORM dblink_exec('dbname=' ||  create_database.name, 'CREATE EXTENSION IF NOT EXISTS pgcrypto;');
        PERFORM dblink_exec('dbname=' ||  create_database.name, 'CREATE EXTENSION IF NOT EXISTS jaaql;');
    end if;
    raise notice 'Checking in here';
    EXECUTE 'alter database "' || create_database.name || '" owner to "jaaql__admin"';
    EXECUTE 'GRANT CONNECT ON DATABASE "' || create_database.name || '" TO "jaaql__public"';
    if insert_record then
        INSERT INTO database (name) VALUES (create_database.name) ON CONFLICT DO NOTHING;
    end if;
END
$$ language plpgsql SECURITY DEFINER;

create or replace function setup_jaaql_role() returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    execute 'CREATE ROLE jaaql WITH CREATEROLE LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    ALTER DEFAULT PRIVILEGES FOR ROLE jaaql REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
    CREATE ROLE jaaql__admin;
    GRANT jaaql__admin TO jaaql with admin option;
    ALTER database jaaql OWNER TO jaaql;
    GRANT execute on function drop_database(postgres_addressable_name) to jaaql with grant option;
    GRANT execute on function create_database(postgres_addressable_name, boolean, boolean) to jaaql with grant option;
    return secure_pass;
END
$$ language plpgsql;
