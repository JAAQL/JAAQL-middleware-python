create function create_account(username text, attach_as postgres_role = null, already_exists boolean = false, is_the_anonymous_user boolean = false, allow_already_exists boolean = false) returns postgres_role as
$$
DECLARE
    account_id postgres_role;
BEGIN
    if attach_as is not null then
        if not already_exists then
            BEGIN
                EXECUTE 'CREATE ROLE ' || quote_ident(attach_as);
            EXCEPTION WHEN duplicate_object THEN
                IF NOT allow_already_exists THEN
                    RAISE;
                END IF;
                return 'account_already_existed';
            END;
        end if;
        INSERT INTO account (id, username) VALUES (attach_as, create_account.username) RETURNING id INTO account_id;
    else
        INSERT INTO account (id, username) VALUES (gen_random_uuid(), create_account.username) RETURNING id INTO account_id;
        EXECUTE 'CREATE ROLE ' || quote_ident(account_id);
    end if;
    if not is_the_anonymous_user then
        EXECUTE 'GRANT unconfirmed TO ' || quote_ident(account_id);
    else
        UPDATE jaaql SET the_anonymous_user = account_id;
    end if;
    return account_id;
END
$$ language plpgsql SECURITY DEFINER;

create function mark_account_registered(id postgres_role) returns void as
$$
DECLARE
    has_unconfirmed BOOLEAN;
    lacks_registered BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM pg_auth_members
        JOIN pg_roles ON pg_roles.oid = pg_auth_members.roleid
        WHERE pg_roles.rolname = 'unconfirmed'
        AND member = (SELECT oid FROM pg_roles WHERE rolname = mark_account_registered.id)
    ) INTO has_unconfirmed;
    IF has_unconfirmed THEN
        EXECUTE 'REVOKE unconfirmed FROM ' || quote_ident(mark_account_registered.id);
    END IF;

    SELECT NOT EXISTS (
        SELECT 1
        FROM pg_auth_members
        JOIN pg_roles ON pg_roles.oid = pg_auth_members.roleid
        WHERE pg_roles.rolname = 'registered'
        AND member = (SELECT oid FROM pg_roles WHERE rolname = mark_account_registered.id)
    ) INTO lacks_registered;
    
    IF lacks_registered THEN
        EXECUTE 'GRANT registered TO ' || quote_ident(mark_account_registered.id);
    END IF;
END
$$ language plpgsql SECURITY DEFINER;
