CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS jaaql;

create or replace function does_user_own_this_database(_user name, database object_name) returns boolean as
$$
DECLARE
    owner boolean;
BEGIN
    SELECT (datdba::regrole)::text = _user::text into owner FROM pg_database WHERE datname = does_user_own_this_database.database;
    return coalesce(owner, false);
END;
$$ language plpgsql;

create or replace function configure_database_for_use_with_jaaql(database object_name) returns void as
$$
BEGIN
    if does_user_own_this_database(session_user, database) then
        PERFORM dblink_exec('dbname=' || database, 'CREATE EXTENSION IF NOT EXISTS pgcrypto;');
        PERFORM dblink_exec('dbname=' || database, 'CREATE EXTENSION IF NOT EXISTS jaaql;');
    else
        raise notice 'You do not own this database'
                 'You cannot install the jaaql extension';

        raise notice '% %', SQLERRM, SQLSTATE;
        return;
    end if;
END
$$ language plpgsql SECURITY DEFINER;
GRANT EXECUTE ON function configure_database_for_use_with_jaaql TO public;

create or replace function setup_jaaql_role_with_password(secure_pass internet_name) returns void as
$$
BEGIN
    CREATE ROLE registered;
    execute 'CREATE ROLE jaaql WITH LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    grant execute on function create_account to jaaql;
    ALTER DEFAULT PRIVILEGES FOR ROLE jaaql REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
    ALTER database jaaql OWNER TO jaaql;
    return;
END
$$ language plpgsql;

create or replace function setup_jaaql_role() returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    PERFORM setup_jaaql_role_with_password(secure_pass::internet_name);
    return secure_pass;
END
$$ language plpgsql;
