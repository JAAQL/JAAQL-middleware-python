CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE DOMAIN postgres_table_view_name AS varchar(64) CHECK (VALUE ~* '^[A-Za-z*0-9_\-]+$');

create table jaaql__system (
    name varchar(100) not null,
    encrypted_superuser_password varchar(255) not null
);

create or replace function setup_system_role(name postgres_table_view_name) returns text as
$$
DECLARE
    secure_pass text;
BEGIN
    SELECT gen_random_uuid()::varchar INTO secure_pass;
    execute 'CREATE ROLE ' || name || ' WITH LOGIN ENCRYPTED PASSWORD ''' || secure_pass || '''';
    return secure_pass;
END
$$ language plpgsql;

create or replace function create_system(name postgres_table_view_name, superuser_password text) returns void as
$$
BEGIN
    execute 'CREATE DATABASE "' || name || '"';
    execute 'ALTER DATABASE "'|| name || '" OWNER TO "' || name || '"';
    INSERT INTO jaaql__system (name, encrypted_superuser_password) VALUES (name, superuser_password);
END
$$ language plpgsql;