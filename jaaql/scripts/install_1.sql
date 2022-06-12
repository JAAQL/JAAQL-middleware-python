CREATE EXTENSION IF NOT EXISTS pgcrypto;

create or replace function setup_jaaql_role() returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    execute 'CREATE ROLE jaaql WITH CREATEROLE LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    return secure_pass;
END
$$ language plpgsql;
