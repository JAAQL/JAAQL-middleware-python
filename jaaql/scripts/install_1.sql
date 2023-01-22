CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS jaaql;
CREATE DOMAIN postgres_addressable_name AS varchar(64) CHECK (VALUE ~* '^[a-z0-9_\-]+$');
CREATE DOMAIN jaaql_account_id AS varchar(36) CHECK (VALUE = 'postgres' OR VALUE = 'jaaql' OR value::uuid = value::uuid);
CREATE DOMAIN email_address AS varchar(255) CHECK ((VALUE ~* '^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$' AND lower(VALUE) = VALUE));

create or replace function does_user_own_this_database(_user name, database postgres_addressable_name) returns boolean as
$$
DECLARE
    owner boolean;
BEGIN
    SELECT (datdba::regrole)::text = _user::text into owner FROM pg_database WHERE datname = does_user_own_this_database.database;
    return coalesce(owner, false);
END;
$$ language plpgsql;

create or replace function configure_database_for_use_with_jaaql(database postgres_addressable_name) returns void as
$$
BEGIN
    if does_user_own_this_database(session_user, database) then
        PERFORM dblink_exec('dbname=' || database, 'CREATE EXTENSION IF NOT EXISTS pgcrypto;');
        PERFORM dblink_exec('dbname=' || database, 'CREATE EXTENSION IF NOT EXISTS jaaql;');
        PERFORM dblink_exec('dbname=' || database, 'CREATE DOMAIN jaaql__account_id AS varchar(36) CHECK (VALUE = ''postgres'' OR VALUE = ''jaaql'' OR value::uuid = value::uuid);');
        PERFORM dblink_exec('dbname=' || database, 'CREATE DOMAIN jaaql__email_address AS varchar(255) CHECK ((VALUE ~* ''^[A-Za-z0-9._%-]+([+][A-Za-z0-9._%-]+){0,1}@[A-Za-z0-9.-]+[.][A-Za-z]+$'' AND lower(VALUE) = VALUE));');
    else
        raise notice 'You do not own this database'
                 'You cannot install the jaaql extension';

        raise notice '% %', SQLERRM, SQLSTATE;
        return;
    end if;
END
$$ language plpgsql SECURITY DEFINER;
GRANT EXECUTE ON function configure_database_for_use_with_jaaql(postgres_addressable_name) TO public;


create or replace function setup_jaaql_role() returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    execute 'CREATE ROLE jaaql WITH CREATEROLE LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    ALTER DEFAULT PRIVILEGES FOR ROLE jaaql REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
    ALTER database jaaql OWNER TO jaaql;
    return secure_pass;
END
$$ language plpgsql;
