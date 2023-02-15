create function attach_account(account_id object_name, enc_username text) returns void as
$$
BEGIN
    INSERT INTO account (username, id) VALUES (enc_username, account_id);
END
$$ language plpgsql;

create function close_my_account() returns void as
$$
BEGIN
    UPDATE account SET deleted = current_timestamp WHERE id = session_user;
END
$$ language plpgsql SECURITY DEFINER;
GRANT execute on function close_my_account to registered;

create view fetch_recent_passwords as (
    SELECT
        a.id as id,
        ap.uuid as password_id,
        a.username,
        ap.hash
    FROM
        account a
    INNER JOIN
        account_password ap on ap.uuid = a.most_recent_password
);

create view fetch_recent_passwords_with_ips as (
    SELECT
        id,
        password_id,
        username,
        hash,
        juip.encrypted_salted_ip_address as encrypted_address
    FROM
        fetch_recent_passwords frp
    INNER JOIN
        validated_ip_address juip ON juip.account = id
);

