create extension if not exists dblink;
CREATE SCHEMA IF NOT EXISTS jaaql_extension;
GRANT USAGE ON SCHEMA jaaql_extension TO PUBLIC;
create extension if not exists jaaql;
create extension if not exists plpgsql_check;

DO
$do$
BEGIN
   IF EXISTS (SELECT FROM pg_database WHERE datname = 'jaaql') THEN
      RAISE NOTICE 'Database already exists';  -- optional
   ELSE
      PERFORM dblink_exec('dbname=' || current_database(),  -- current db
                        'create database jaaql
                            with
                            ENCODING = ''UTF8''
                            TABLESPACE = pg_default
                            TEMPLATE = template0
                            CONNECTION LIMIT = -1;');
      PERFORM dblink_exec('dbname=jaaql', 'CREATE SCHEMA jaaql_extension;');
      PERFORM dblink_exec('dbname=jaaql', 'GRANT USAGE ON SCHEMA jaaql_extension TO PUBLIC;');
      PERFORM dblink_exec('dbname=jaaql', 'create extension jaaql;');
      PERFORM dblink_exec('dbname=jaaql', 'create extension plpgsql_check;');
      PERFORM dblink_exec('dbname=jaaql', 'ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;');
   END IF;
END
$do$;

ALTER SYSTEM SET max_connections = 300;
