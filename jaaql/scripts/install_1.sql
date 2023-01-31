CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS dblink;
CREATE EXTENSION IF NOT EXISTS jaaql;
CREATE DOMAIN postgres_addressable_name AS varchar(64) CHECK (VALUE ~* '^[a-z0-9_\-]+$');
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

create function create_account(enc_username text, is_public boolean = false, attach_as postgres_addressable_name = null) returns postgres_addressable_name as
$$
DECLARE
    account_id postgres_addressable_name;
BEGIN
    if attach_as is not null then
        EXECUTE 'CREATE ROLE ' || quote_ident(attach_as);
        INSERT INTO account (username, user_id) VALUES (enc_username, attach_as) RETURNING user_id INTO account_id;
    else
        INSERT INTO account (username) VALUES (enc_username) RETURNING user_id INTO account_id;
        EXECUTE 'CREATE ROLE ' || quote_ident(account_id);
    end if;
    if is_public then
        EXECUTE 'GRANT anonymous TO ' || quote_ident(account_id);
    else
        EXECUTE 'GRANT registered TO ' || quote_ident(account_id);
    end if;
    return account_id;
END
$$ language plpgsql SECURITY DEFINER;

create or replace function setup_jaaql_role() returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    CREATE ROLE anonymous;
    CREATE ROLE registered;
    GRANT anonymous to registered;
    execute 'CREATE ROLE jaaql WITH LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    grant execute on function create_account(text, boolean, postgres_addressable_name) to jaaql;
    ALTER DEFAULT PRIVILEGES FOR ROLE jaaql REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
    ALTER database jaaql OWNER TO jaaql;
    return secure_pass;
END
$$ language plpgsql;
