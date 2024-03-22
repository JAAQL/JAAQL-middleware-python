CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS jaaql;
CREATE EXTENSION IF NOT EXISTS plpgsql_check;

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
        PERFORM dblink_exec('dbname=' || database, 'CREATE EXTENSION IF NOT EXISTS plpgsql_check;');
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
    CREATE ROLE unconfirmed;
    execute 'CREATE ROLE jaaql WITH LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    grant execute on function create_account to jaaql;
    grant execute on function mark_account_registered to jaaql;
    grant execute on function check_user_role TO jaaql;
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

CREATE OR REPLACE FUNCTION check_user_role(role_name text, user_name text)
RETURNS TABLE(has_role boolean) AS $$
BEGIN
    RETURN QUERY
        SELECT EXISTS (
            SELECT 1
            FROM pg_roles r
            JOIN pg_auth_members m ON r.oid = m.roleid
            JOIN pg_roles ur ON m.member = ur.oid
            WHERE r.rolname = role_name
            AND ur.rolname = user_name
        );
END;
$$ LANGUAGE plpgsql security definer;
