create function create_account(
    username text, sub text, provider text = NULL, tenant text = NULL,
    email text = NULL, api_key text = NULL, attach_as postgres_role = NULL,
    already_exists boolean = false, allow_already_exists boolean = false
) returns postgres_role as
$$
DECLARE
    requires_email_verification boolean = false;
    account_id postgres_role;
BEGIN
    if create_account.provider is not null then
        SELECT X.requires_email_verification INTO requires_email_verification
        FROM identity_provider_service X
        WHERE name = create_account.provider;
    end if;

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
        INSERT INTO account
        (id, username, sub, provider, tenant, email, email_verified, api_key)
        VALUES (attach_as, create_account.username, create_account.sub, create_account.provider, create_account.tenant, create_account.email, not requires_email_verification, create_account.api_key)
        RETURNING id INTO account_id;
    else
        INSERT INTO account
        (id, username, sub, provider, tenant, email, email_verified, api_key)
        VALUES (gen_random_uuid(), create_account.username, create_account.sub, create_account.provider, create_account.tenant, create_account.email, not requires_email_verification, create_account.api_key)
        RETURNING id INTO account_id;

        EXECUTE 'CREATE ROLE ' || quote_ident(account_id);
    end if;

    IF requires_email_verification THEN
        EXECUTE 'GRANT unconfirmed TO ' || quote_ident(account_id);
    ELSE
        EXECUTE 'GRANT registered TO ' || quote_ident(account_id);
    END IF;

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

    UPDATE account A SET email_verified = true WHERE A.id = mark_account_registered.id;
END
$$ language plpgsql SECURITY DEFINER;
