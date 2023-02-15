create function create_account(username text, attach_as postgres_role = null, already_exists boolean = false, is_the_anonymous_user boolean = false) returns postgres_role as
$$
DECLARE
    account_id postgres_role;
BEGIN
    if attach_as is not null then
        if not already_exists then
            EXECUTE 'CREATE ROLE ' || quote_ident(attach_as);
        end if;
        INSERT INTO account (id, username) VALUES (attach_as, create_account.username) RETURNING id INTO account_id;
    else
        INSERT INTO account (id, username) VALUES (gen_random_uuid(), create_account.username) RETURNING id INTO account_id;
        EXECUTE 'CREATE ROLE ' || quote_ident(account_id);
    end if;
    if not is_the_anonymous_user then
        EXECUTE 'GRANT registered TO ' || quote_ident(account_id);
    else
        UPDATE jaaql SET the_anonymous_user = account_id;
    end if;
    return account_id;
END
$$ language plpgsql SECURITY DEFINER;
