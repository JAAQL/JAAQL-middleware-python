-- Audit trail of record changes, one per application database, in schema audit.
--
-- Every INSERT, UPDATE and DELETE on a table of the database is recorded in audit.record_change with the person who made it
-- (session_user: JAAQL runs each request as the database role of the logged-in person, and SECURITY DEFINER procedures do not
-- change it), the time, the table, the primary key of the row, the operation and the old and new values. An UPDATE records only
-- the columns that changed, and an UPDATE that changes nothing is not recorded. Columns that hold secrets (passwords, hashes,
-- tokens, keys, ciphertext; see audit.is_withheld, and audit.withheld_column for more) are never copied: the log shows
-- "(withheld)" instead, and a withheld column that is part of the primary key appears in row_key as a salted hash. A bulk load
-- by a role that may read server files (dba, a superuser) is recorded as one LOAD row with the row count: a COPY, which is how an
-- install loads the reference and test data of the model, and the reload of a wipe-and-reload migration, which puts back every
-- row it saved in migration.*_json. Recorded row by row, that reload would copy the whole database into the log at every release,
-- and an erasure, which follows a row back to its INSERT, would stop at the reload and keep the history before it. Reads are not
-- recorded.
--
-- The schema is outside public, so a DROP SCHEMA public CASCADE (a FIESTA wipe-and-reload migration) leaves it and its rows
-- alone. The event trigger audit_attach attaches the triggers to every table that is created or altered, and audit_reattach puts
-- back an audit trigger that is dropped; audit.attach_all() attaches them to the tables that already exist. Records older than
-- audit.setting.keep_changes (24 months) and the rows of the tables in audit.retention_rule are deleted by audit.purge_expired(),
-- which the JAAQL container runs every night as dba. audit.begin_erasure() turns the rest of a transaction into an erasure: the
-- rows it deletes (also those a foreign key deletes with them) lose their history and leave only an ERASE entry without values,
-- the rows it updates are recorded without their old values, and audit.forget_record() deletes the history of a row that stays
-- (a person pseudonymised in place). audit.forget_actor() pseudonymises a person in the actor column.
--
-- Users have no access to the schema. dba reads the log, sets the exclusions and calls the functions; nobody can change a
-- recorded row except through the purge and the erasure functions. The triggers run as jaaql_audit, a role that can do nothing
-- but write this log, so that no code a table owner adds (a cast, a trigger) ever runs as a superuser.
--
-- Run as a superuser, in the application database. Idempotent: JAAQL runs it when it configures a new database and at every
-- container boot for every existing one. The file must also pass JAAQL /submit (a .jaaql migration): an even number of
-- apostrophes, no colon directly before a name, and no line that starts with a backslash or with WITH USER.

CREATE SCHEMA IF NOT EXISTS audit;
REVOKE ALL ON SCHEMA audit FROM PUBLIC;

DO $do$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'jaaql_audit') THEN
        CREATE ROLE jaaql_audit NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
END
$do$;
GRANT USAGE ON SCHEMA audit TO jaaql_audit;

CREATE TABLE IF NOT EXISTS audit.setting (
    singleton           boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    keep_changes        interval NOT NULL DEFAULT interval '24 months',
    last_purge_at       timestamptz,
    last_purge_rows     bigint,
    last_purge_errors   text
);
-- A later version that adds a column to a table here adds it with ADD COLUMN IF NOT EXISTS as well, as below, so that the
-- install at boot keeps working on every database that has the table already
ALTER TABLE audit.setting ADD COLUMN IF NOT EXISTS last_purge_at timestamptz;
ALTER TABLE audit.setting ADD COLUMN IF NOT EXISTS last_purge_rows bigint;
ALTER TABLE audit.setting ADD COLUMN IF NOT EXISTS last_purge_errors text;
INSERT INTO audit.setting DEFAULT VALUES ON CONFLICT DO NOTHING;

-- Read by the triggers only: the salt of the hashed keys and of the actor pseudonyms
CREATE TABLE IF NOT EXISTS audit.secret (
    singleton           boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    salt                text NOT NULL DEFAULT md5(random()::text || clock_timestamp()::text) || md5(random()::text)
);
INSERT INTO audit.secret DEFAULT VALUES ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS audit.record_change (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    changed_at          timestamptz NOT NULL DEFAULT now(),
    actor               text NOT NULL DEFAULT session_user,
    xact_id             xid8 NOT NULL DEFAULT pg_current_xact_id(),
    table_name          text NOT NULL,
    operation           text NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'LOAD', 'ERASE')),
    row_key             jsonb,
    old_values          jsonb,
    new_values          jsonb
);
CREATE INDEX IF NOT EXISTS record_change__changed_at ON audit.record_change USING brin (changed_at);
CREATE INDEX IF NOT EXISTS record_change__row ON audit.record_change (table_name, row_key);

CREATE TABLE IF NOT EXISTS audit.erasure (
    xact_id             xid8 PRIMARY KEY DEFAULT pg_current_xact_id(),
    started_at          timestamptz NOT NULL DEFAULT now(),
    actor               text NOT NULL DEFAULT session_user,
    reason              text NOT NULL
);

CREATE TABLE IF NOT EXISTS audit.withheld_column (
    table_name          text NOT NULL,
    column_name         text NOT NULL,
    PRIMARY KEY (table_name, column_name)
);

CREATE TABLE IF NOT EXISTS audit.excluded_table (
    table_name          text PRIMARY KEY,
    reason              text NOT NULL
);

CREATE TABLE IF NOT EXISTS audit.retention_rule (
    table_name          text PRIMARY KEY,
    timestamp_column    text NOT NULL,
    keep                interval NOT NULL CHECK (keep > interval '0'),
    reason              text NOT NULL
);

-- Schemas whose tables are never audited: the system schemas, this one, the jaaql extension and the transient copy that a
-- wipe-and-reload migration makes of every row
CREATE OR REPLACE FUNCTION audit.is_skipped_schema(schema_name text) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path = pg_catalog, pg_temp AS $body$
    SELECT schema_name IN ('audit', 'pg_catalog', 'information_schema', 'jaaql_extension', 'migration')
        OR schema_name LIKE 'pg\_%'
$body$;

-- Tables are named schema.table as written, without quotes, in every audit table and in the log
CREATE OR REPLACE FUNCTION audit.table_oid(table_name text) RETURNS regclass
LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $body$
    SELECT C.oid::regclass FROM pg_class C JOIN pg_namespace N ON N.oid = C.relnamespace
     WHERE N.nspname || '.' || C.relname = table_oid.table_name AND C.relkind IN ('r', 'p')
     LIMIT 1
$body$;

CREATE OR REPLACE FUNCTION audit.is_withheld(table_name text, column_name text, type_name text) RETURNS boolean
LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $body$
    SELECT lower(column_name) ~ '(^|_)(pass(word|wd)?s?|pwd|wachtwoord|secrets?|geheim|tokens?|salt|hash(ed)?|credentials?|api_?keys?|private_?keys?|secret_?keys?|otp|totp|mfa|pin|cipher(text)?|signature|encrypted)(_|$)'
        OR lower(type_name) ~ '(encrypt|secret|password|token)'
        OR EXISTS (SELECT FROM audit.withheld_column W WHERE W.table_name = is_withheld.table_name AND W.column_name = is_withheld.column_name)
$body$;

-- The two trigger arguments of a table: its primary-key columns and its withheld columns, each as a text[] literal
CREATE OR REPLACE FUNCTION audit.trigger_args(rel regclass) RETURNS text[]
LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $body$
    SELECT ARRAY[
        (SELECT coalesce(array_agg(A.attname::text ORDER BY array_position(I.indkey::int2[], A.attnum)), '{}')::text
           FROM pg_index I JOIN pg_attribute A ON A.attrelid = I.indrelid AND A.attnum = ANY (I.indkey)
          WHERE I.indrelid = rel AND I.indisprimary),
        (SELECT coalesce(array_agg(A.attname::text ORDER BY A.attnum), '{}')::text
           FROM pg_attribute A JOIN pg_class C ON C.oid = A.attrelid JOIN pg_namespace N ON N.oid = C.relnamespace
          WHERE A.attrelid = rel AND A.attnum > 0 AND NOT A.attisdropped
            AND audit.is_withheld(N.nspname || '.' || C.relname, A.attname, format_type(A.atttypid, NULL)))]
$body$;

-- The tgargs bytes PostgreSQL stores for those arguments, compared byte for byte (any column name, any encoding)
CREATE OR REPLACE FUNCTION audit.trigger_args_bytes(args text[]) RETURNS bytea
LANGUAGE sql STABLE SET search_path = pg_catalog, pg_temp AS $body$
    SELECT convert_to(args[1], current_setting('server_encoding')) || '\x00'::bytea
        || convert_to(args[2], current_setting('server_encoding')) || '\x00'::bytea
$body$;

-- A role that may read server files: dba or a superuser, who load the data of a model in an install (COPY) and in a
-- wipe-and-reload migration (INSERT ... SELECT from migration.*_json); no application user is one. Called only for those
-- two kinds of statement
CREATE OR REPLACE FUNCTION audit.is_bulk_loader() RETURNS boolean
LANGUAGE sql STABLE AS $body$
    SELECT coalesce((SELECT R.rolsuper FROM pg_catalog.pg_roles R WHERE R.rolname = session_user), false)
        OR pg_catalog.pg_has_role(session_user, 'pg_read_server_files', 'MEMBER')
$body$;

CREATE OR REPLACE FUNCTION audit.withheld_marks(present jsonb, withheld text[]) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $body$
    SELECT CASE WHEN pg_catalog.cardinality(withheld) = 0 OR present IS NULL THEN '{}'::jsonb
                ELSE coalesce((SELECT pg_catalog.jsonb_object_agg(W, '"(withheld)"'::jsonb) FROM pg_catalog.unnest(withheld) W
                                WHERE present OPERATOR(pg_catalog.?) W), '{}'::jsonb) END
$body$;

-- row_key of a table whose primary key has a withheld column: that column holds a salted hash instead of its value
CREATE OR REPLACE FUNCTION audit.masked_key(j jsonb, key_columns text[], withheld text[], salt text) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $body$
    SELECT pg_catalog.jsonb_object_agg(K, CASE WHEN K = ANY (withheld)
                                               THEN pg_catalog.to_jsonb('(withheld ' || pg_catalog.left(pg_catalog.md5(salt || coalesce(j OPERATOR(pg_catalog.->>) K, '')), 16) || ')')
                                               ELSE j OPERATOR(pg_catalog.->) K END)
      FROM pg_catalog.unnest(key_columns) K
$body$;

-- Deletes the history of the given rows of a table. A row is followed back through its own life only: from its latest entry back
-- to the entry where it got its current key (its INSERT, or an UPDATE that changed the key), then on under the old key before
-- that entry, so that the history of another row that held the same key at another time is left alone.
-- keep_current keeps what the current transaction itself recorded
CREATE OR REPLACE FUNCTION audit.forget_rows(tname text, key_columns text[], row_keys jsonb[], keep_current boolean) RETURNS bigint
LANGUAGE plpgsql AS $body$
DECLARE
    start_key       jsonb;
    cur_key         jsonb;
    upper_id        bigint;
    origin          record;
    deleted         bigint;
    total           bigint := 0;
    current_xact    xid8 := pg_catalog.pg_current_xact_id();
BEGIN
    FOR start_key IN SELECT DISTINCT K FROM pg_catalog.unnest(row_keys) K WHERE K IS NOT NULL LOOP
        cur_key := start_key;
        upper_id := NULL;
        LOOP
            SELECT R.id, R.operation, R.old_values INTO origin
              FROM audit.record_change R
             WHERE R.table_name = tname AND R.row_key = cur_key AND (upper_id IS NULL OR R.id < upper_id)
               AND (R.operation = 'INSERT' OR (R.operation = 'UPDATE' AND R.old_values OPERATOR(pg_catalog.?|) key_columns))
             ORDER BY R.id DESC
             LIMIT 1;
            DELETE FROM audit.record_change R
             WHERE R.table_name = tname AND R.row_key = cur_key AND (upper_id IS NULL OR R.id < upper_id)
               AND (origin.id IS NULL OR R.id >= origin.id)
               AND NOT (keep_current AND R.xact_id = current_xact);
            GET DIAGNOSTICS deleted = ROW_COUNT;
            total := total + deleted;
            EXIT WHEN origin.id IS NULL OR origin.operation = 'INSERT';
            cur_key := cur_key OPERATOR(pg_catalog.||) (SELECT pg_catalog.jsonb_object_agg(C, origin.old_values OPERATOR(pg_catalog.->) C)
                                               FROM pg_catalog.unnest(key_columns) C WHERE origin.old_values OPERATOR(pg_catalog.?) C);
            upper_id := origin.id;
        END LOOP;
    END LOOP;
    RETURN total;
END
$body$;

-- The statement trigger. TG_ARGV[0] holds the primary-key columns and TG_ARGV[1] the withheld columns, both worked out by
-- audit.attach when the table was created or last altered, so that a write costs no catalog lookups. Rows are referred to as
-- N.*, O.* and X.*: a bare N would mean a column of that name. Old and new rows of an UPDATE are paired by position, which is
-- the order PostgreSQL stores them in, so a key change, a swap of keys between rows or a cascaded key change is paired right.
-- OFFSET 0 keeps the planner from inlining to_jsonb into every place the row is used, so it runs once per row
CREATE OR REPLACE FUNCTION audit.record_statement() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    key_columns     text[] := TG_ARGV[0]::text[];
    withheld        text[] := TG_ARGV[1]::text[];
    tname           text := TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME;
    single_key      text;
    marks           jsonb := '{}'::jsonb;
    salt            text;
    erasing         boolean := false;
    loaded          bigint;
BEGIN
    IF key_columns && withheld THEN
        SELECT S.salt INTO salt FROM audit.secret S;
    ELSIF cardinality(key_columns) = 1 THEN
        single_key := key_columns[1];
    END IF;
    IF cardinality(withheld) > 0 THEN
        SELECT jsonb_object_agg(W, '"(withheld)"'::jsonb) INTO marks FROM unnest(withheld) W;
    END IF;

    IF TG_OP = 'INSERT' THEN
        IF (left(current_query(), 4000) ~* '^\s*((--[^\n]*\n|/\*.*?\*/)\s*)*copy\s' OR current_query() ~* '\mfrom\s+migration\.\w+_json\M')
           AND audit.is_bulk_loader() THEN
            SELECT count(*) INTO loaded FROM new_rows;
            INSERT INTO audit.record_change (table_name, operation, new_values) VALUES (tname, 'LOAD', jsonb_build_object('rows', loaded));
            RETURN NULL;
        END IF;
        INSERT INTO audit.record_change (table_name, operation, row_key, new_values)
        SELECT tname, 'INSERT',
               CASE WHEN single_key IS NOT NULL THEN jsonb_build_object(single_key, S.J -> single_key)
                    WHEN salt IS NOT NULL THEN audit.masked_key(S.J, key_columns, withheld, salt)
                    WHEN cardinality(key_columns) > 1 THEN (SELECT jsonb_object_agg(K, S.J -> K) FROM unnest(key_columns) K) END,
               (S.J - withheld) || marks
          FROM (SELECT to_jsonb(N.*) AS J FROM new_rows N OFFSET 0) S;
        RETURN NULL;
    END IF;

    erasing := EXISTS (SELECT FROM audit.erasure E WHERE E.xact_id = pg_current_xact_id());

    IF TG_OP = 'DELETE' THEN
        IF erasing THEN
            PERFORM audit.forget_rows(tname, key_columns, ARRAY(
                SELECT CASE WHEN single_key IS NOT NULL THEN jsonb_build_object(single_key, S.J -> single_key)
                            WHEN salt IS NOT NULL THEN audit.masked_key(S.J, key_columns, withheld, salt)
                            WHEN cardinality(key_columns) > 1 THEN (SELECT jsonb_object_agg(K, S.J -> K) FROM unnest(key_columns) K) END
                  FROM (SELECT to_jsonb(O.*) AS J FROM old_rows O OFFSET 0) S), false);
            INSERT INTO audit.record_change (table_name, operation) SELECT tname, 'ERASE' FROM old_rows;
        ELSE
            INSERT INTO audit.record_change (table_name, operation, row_key, old_values)
            SELECT tname, 'DELETE',
                   CASE WHEN single_key IS NOT NULL THEN jsonb_build_object(single_key, S.J -> single_key)
                        WHEN salt IS NOT NULL THEN audit.masked_key(S.J, key_columns, withheld, salt)
                        WHEN cardinality(key_columns) > 1 THEN (SELECT jsonb_object_agg(K, S.J -> K) FROM unnest(key_columns) K) END,
                   (S.J - withheld) || marks
              FROM (SELECT to_jsonb(O.*) AS J FROM old_rows O OFFSET 0) S;
        END IF;
        RETURN NULL;
    END IF;

    -- UPDATE. During an erasure the old values are left out
    INSERT INTO audit.record_change (table_name, operation, row_key, old_values, new_values)
    SELECT tname, CASE WHEN erasing THEN 'ERASE' ELSE 'UPDATE' END, D.RK,
           CASE WHEN NOT erasing THEN (D.OD - withheld) || audit.withheld_marks(D.OD, withheld) END,
           (D.ND - withheld) || audit.withheld_marks(D.ND, withheld)
      FROM (SELECT CASE WHEN single_key IS NOT NULL THEN jsonb_build_object(single_key, P.NJ -> single_key)
                        WHEN salt IS NOT NULL THEN audit.masked_key(P.NJ, key_columns, withheld, salt)
                        WHEN cardinality(key_columns) > 1 THEN (SELECT jsonb_object_agg(K, P.NJ -> K) FROM unnest(key_columns) K) END AS RK,
                   (SELECT jsonb_object_agg(E.key, E.value) FROM jsonb_each(P.OJ) E WHERE E.value IS DISTINCT FROM P.NJ -> E.key) AS OD,
                   (SELECT jsonb_object_agg(E.key, E.value) FROM jsonb_each(P.NJ) E WHERE E.value IS DISTINCT FROM P.OJ -> E.key) AS ND
              FROM unnest((SELECT array_agg(to_jsonb(X.*)) FROM old_rows X), (SELECT array_agg(to_jsonb(X.*)) FROM new_rows X)) AS P(OJ, NJ)) D
     WHERE D.ND IS NOT NULL;
    RETURN NULL;
END
$body$;

CREATE OR REPLACE FUNCTION audit.record_truncate() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    tname           text := TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME;
BEGIN
    IF EXISTS (SELECT FROM audit.erasure E WHERE E.xact_id = pg_current_xact_id()) THEN
        DELETE FROM audit.record_change R WHERE R.table_name = tname;
        INSERT INTO audit.record_change (table_name, operation) VALUES (tname, 'ERASE');
    ELSE
        INSERT INTO audit.record_change (table_name, operation) VALUES (tname, 'TRUNCATE');
    END IF;
    RETURN NULL;
END
$body$;

-- Attaches (or refreshes) the four triggers of one table. Returns attached, unchanged, excluded or skipped
CREATE OR REPLACE FUNCTION audit.attach(rel regclass) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    info            record;
    args            text[];
    present         integer;
    trigger_name    name;
BEGIN
    SELECT N.nspname, C.relname, C.relkind, C.relispartition, C.relpersistence INTO info
      FROM pg_class C JOIN pg_namespace N ON N.oid = C.relnamespace
     WHERE C.oid = rel;
    IF NOT FOUND OR info.relkind NOT IN ('r', 'p') OR info.relispartition OR info.relpersistence = 't' OR audit.is_skipped_schema(info.nspname) THEN
        RETURN 'skipped';
    END IF;
    IF EXISTS (SELECT FROM audit.excluded_table X WHERE X.table_name = info.nspname || '.' || info.relname) THEN
        FOR trigger_name IN SELECT T.tgname FROM pg_trigger T
                             WHERE T.tgrelid = rel AND T.tgname IN ('zzz_audit_insert', 'zzz_audit_update', 'zzz_audit_delete', 'zzz_audit_truncate')
        LOOP
            EXECUTE format('DROP TRIGGER %I ON %s', trigger_name, rel);
        END LOOP;
        RETURN 'excluded';
    END IF;

    args := audit.trigger_args(rel);
    SELECT count(*) INTO present
      FROM pg_trigger T
     WHERE T.tgrelid = rel AND T.tgenabled = 'O'
       AND ((T.tgname IN ('zzz_audit_insert', 'zzz_audit_update', 'zzz_audit_delete')
             AND T.tgfoid = 'audit.record_statement()'::regprocedure AND T.tgnargs = 2 AND T.tgargs = audit.trigger_args_bytes(args))
         OR (T.tgname = 'zzz_audit_truncate' AND T.tgfoid = 'audit.record_truncate()'::regprocedure));
    IF present = 4 THEN
        RETURN 'unchanged';
    END IF;

    -- CREATE OR REPLACE TRIGGER also enables a trigger that was disabled
    EXECUTE format('CREATE OR REPLACE TRIGGER zzz_audit_insert AFTER INSERT ON %s REFERENCING NEW TABLE AS new_rows '
                   'FOR EACH STATEMENT EXECUTE FUNCTION audit.record_statement(%L, %L)', rel, args[1], args[2]);
    EXECUTE format('CREATE OR REPLACE TRIGGER zzz_audit_update AFTER UPDATE ON %s REFERENCING OLD TABLE AS old_rows NEW TABLE AS new_rows '
                   'FOR EACH STATEMENT EXECUTE FUNCTION audit.record_statement(%L, %L)', rel, args[1], args[2]);
    EXECUTE format('CREATE OR REPLACE TRIGGER zzz_audit_delete AFTER DELETE ON %s REFERENCING OLD TABLE AS old_rows '
                   'FOR EACH STATEMENT EXECUTE FUNCTION audit.record_statement(%L, %L)', rel, args[1], args[2]);
    EXECUTE format('CREATE OR REPLACE TRIGGER zzz_audit_truncate AFTER TRUNCATE ON %s '
                   'FOR EACH STATEMENT EXECUTE FUNCTION audit.record_truncate()', rel);
    RETURN 'attached';
END
$body$;

-- A table the triggers cannot be attached to is reported as a warning and shows up as missing in audit.coverage; it never
-- stops an install or the boot
CREATE OR REPLACE FUNCTION audit.attach_all() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    r               record;
    attached        integer := 0;
BEGIN
    FOR r IN SELECT C.oid FROM pg_class C JOIN pg_namespace N ON N.oid = C.relnamespace
              WHERE C.relkind IN ('r', 'p') AND NOT C.relispartition AND C.relpersistence <> 't' AND NOT audit.is_skipped_schema(N.nspname)
              ORDER BY N.nspname, C.relname
    LOOP
        BEGIN
            IF audit.attach(r.oid::regclass) = 'attached' THEN
                attached := attached + 1;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'audit trail: could not attach to %: %', r.oid::regclass, SQLERRM;
        END;
    END LOOP;
    RETURN attached;
END
$body$;

CREATE OR REPLACE FUNCTION audit.on_ddl_command_end() RETURNS event_trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    r               record;
BEGIN
    FOR r IN SELECT DISTINCT D.objid FROM pg_event_trigger_ddl_commands() D WHERE D.classid = 'pg_class'::regclass AND D.object_type IN ('table', 'table column')
    LOOP
        BEGIN
            PERFORM audit.attach(r.objid::regclass);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'audit trail: could not attach to %: %', r.objid::regclass, SQLERRM;
        END;
    END LOOP;
END
$body$;

-- Puts back an audit trigger that someone dropped (an excluded table is left without them)
CREATE OR REPLACE FUNCTION audit.on_sql_drop() RETURNS event_trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    r               record;
    rel             regclass;
BEGIN
    FOR r IN SELECT DISTINCT D.address_names[1] AS schema_name, D.address_names[2] AS table_name
               FROM pg_event_trigger_dropped_objects() D
              WHERE D.object_type = 'trigger' AND D.address_names[3] IN ('zzz_audit_insert', 'zzz_audit_update', 'zzz_audit_delete', 'zzz_audit_truncate')
    LOOP
        rel := to_regclass(quote_ident(r.schema_name) || '.' || quote_ident(r.table_name));
        IF rel IS NOT NULL AND NOT EXISTS (SELECT FROM audit.excluded_table X WHERE X.table_name = r.schema_name || '.' || r.table_name) THEN
            BEGIN
                PERFORM audit.attach(rel);
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'audit trail: could not attach to %: %', rel, SQLERRM;
            END;
        END IF;
    END LOOP;
END
$body$;

DO $do$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_event_trigger WHERE evtname = 'audit_attach') THEN
        CREATE EVENT TRIGGER audit_attach ON ddl_command_end
            WHEN TAG IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE')
            EXECUTE FUNCTION audit.on_ddl_command_end();
    END IF;
    ALTER EVENT TRIGGER audit_attach ENABLE;
    IF NOT EXISTS (SELECT FROM pg_event_trigger WHERE evtname = 'audit_reattach') THEN
        CREATE EVENT TRIGGER audit_reattach ON sql_drop
            WHEN TAG IN ('DROP TRIGGER')
            EXECUTE FUNCTION audit.on_sql_drop();
    END IF;
    ALTER EVENT TRIGGER audit_reattach ENABLE;
END
$do$;

-- A change to the withheld columns or excluded tables takes effect at once
CREATE OR REPLACE FUNCTION audit.on_config_change() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    rel             regclass;
BEGIN
    rel := audit.table_oid(CASE WHEN TG_OP = 'DELETE' THEN OLD.table_name ELSE NEW.table_name END);
    IF rel IS NOT NULL THEN
        PERFORM audit.attach(rel);
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.table_name IS DISTINCT FROM NEW.table_name THEN
        rel := audit.table_oid(OLD.table_name);
        IF rel IS NOT NULL THEN
            PERFORM audit.attach(rel);
        END IF;
    END IF;
    RETURN NULL;
END
$body$;
CREATE OR REPLACE TRIGGER on_change AFTER INSERT OR UPDATE OR DELETE ON audit.withheld_column FOR EACH ROW EXECUTE FUNCTION audit.on_config_change();
CREATE OR REPLACE TRIGGER on_change AFTER INSERT OR UPDATE OR DELETE ON audit.excluded_table FOR EACH ROW EXECUTE FUNCTION audit.on_config_change();

-- A retention rule must name an ordinary application table and a date or timestamp column of it
CREATE OR REPLACE FUNCTION audit.check_retention_rule() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    rel             regclass := audit.table_oid(NEW.table_name);
BEGIN
    IF rel IS NULL THEN
        RAISE EXCEPTION 'audit retention rule: no table %', NEW.table_name;
    END IF;
    IF audit.is_skipped_schema((SELECT N.nspname FROM pg_class C JOIN pg_namespace N ON N.oid = C.relnamespace WHERE C.oid = rel)) THEN
        RAISE EXCEPTION 'audit retention rule: % is not an application table', NEW.table_name;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_attribute A WHERE A.attrelid = rel AND A.attname = NEW.timestamp_column AND A.attnum > 0 AND NOT A.attisdropped
                      AND A.atttypid IN ('date'::regtype, 'timestamp'::regtype, 'timestamptz'::regtype)) THEN
        RAISE EXCEPTION 'audit retention rule: % has no date or timestamp column %', NEW.table_name, NEW.timestamp_column;
    END IF;
    RETURN NEW;
END
$body$;
CREATE OR REPLACE TRIGGER check_rule BEFORE INSERT OR UPDATE ON audit.retention_rule FOR EACH ROW EXECUTE FUNCTION audit.check_retention_rule();

-- Makes the rest of the current transaction an erasure (right to erasure, or a retention delete): every row it deletes loses
-- its history and leaves an ERASE entry that holds no values, and every row it updates is recorded without its old values
CREATE OR REPLACE FUNCTION audit.begin_erasure(reason text) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
    INSERT INTO audit.erasure AS E (reason) VALUES (begin_erasure.reason)
    ON CONFLICT (xact_id) DO UPDATE SET reason = E.reason || '; ' || EXCLUDED.reason WHERE NOT EXCLUDED.reason = ANY (string_to_array(E.reason, '; '))
$body$;

-- During an erasure: deletes the history of a row that stays, for example a person pseudonymised in place. row_key is the key
-- as the log writes it, such as {"number": 100015}. What the current transaction recorded is kept
CREATE OR REPLACE FUNCTION audit.forget_record(table_name text, row_key jsonb) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    rel             regclass := audit.table_oid(forget_record.table_name);
BEGIN
    IF NOT EXISTS (SELECT FROM audit.erasure E WHERE E.xact_id = pg_current_xact_id()) THEN
        RAISE EXCEPTION 'audit.forget_record needs an erasure: call audit.begin_erasure(reason) first, in the same transaction';
    END IF;
    RETURN audit.forget_rows(forget_record.table_name,
                             coalesce((audit.trigger_args(rel))[1]::text[], ARRAY(SELECT jsonb_object_keys(forget_record.row_key))),
                             ARRAY[forget_record.row_key], true);
END
$body$;

-- Replaces a person in the actor column by a pseudonym that is the same for all of that person but cannot be traced back
CREATE OR REPLACE FUNCTION audit.forget_actor(actor text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    pseudonym       text;
    changed         bigint;
BEGIN
    SELECT 'erased-' || left(md5(S.salt || forget_actor.actor), 12) INTO pseudonym FROM audit.secret S;
    UPDATE audit.record_change R SET actor = pseudonym WHERE R.actor = forget_actor.actor;
    GET DIAGNOSTICS changed = ROW_COUNT;
    UPDATE audit.erasure E SET actor = pseudonym WHERE E.actor = forget_actor.actor;
    PERFORM audit.begin_erasure('actor pseudonymised as ' || pseudonym);
    RETURN changed;
END
$body$;

-- Deletes the records older than keep_changes
CREATE OR REPLACE FUNCTION audit.purge_log() RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    keep            interval;
    deleted         bigint;
BEGIN
    SELECT S.keep_changes INTO keep FROM audit.setting S;
    DELETE FROM audit.record_change R WHERE R.changed_at < now() - keep;
    GET DIAGNOSTICS deleted = ROW_COUNT;
    DELETE FROM audit.erasure E WHERE E.started_at < now() - keep;
    RETURN deleted;
END
$body$;

CREATE OR REPLACE FUNCTION audit.note_purge(total bigint, errors text) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
    UPDATE audit.setting SET last_purge_at = now(), last_purge_rows = note_purge.total, last_purge_errors = note_purge.errors
$body$;

-- The nightly purge: the 24-month cut of the log, then each retention rule on its own (as an erasure), so that one failing
-- rule is reported and never stops the others. It runs as the role that calls it (dba, the owner of the application tables),
-- never as a superuser, so a trigger of an application table runs with the rights of that table.
CREATE OR REPLACE FUNCTION audit.purge_expired() RETURNS bigint
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $body$
DECLARE
    rule            record;
    rel             regclass;
    expired_row     tid;
    deleted         bigint;
    skipped         bigint;
    total           bigint;
    errors          text := '';
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('audit.purge_expired'));
    total := audit.purge_log();
    IF EXISTS (SELECT FROM audit.retention_rule) THEN
        PERFORM audit.begin_erasure('retention');
    END IF;
    FOR rule IN SELECT * FROM audit.retention_rule ORDER BY table_name LOOP
        BEGIN
            rel := audit.table_oid(rule.table_name);
            IF rel IS NULL THEN
                RAISE EXCEPTION 'no such table';
            END IF;
            EXECUTE format('DELETE FROM %s WHERE %I < now() - $1', rel, rule.timestamp_column) USING rule.keep;
            GET DIAGNOSTICS deleted = ROW_COUNT;
            total := total + deleted;
        EXCEPTION
            -- A row another table still refers to (ON DELETE RESTRICT) stops a set delete as a whole: delete the expired rows
            -- one by one instead, and leave only those that are still referred to for a later night
            WHEN foreign_key_violation OR restrict_violation THEN
                skipped := 0;
                FOR expired_row IN EXECUTE format('SELECT ctid FROM %s WHERE %I < now() - $1', rel, rule.timestamp_column) USING rule.keep LOOP
                    BEGIN
                        EXECUTE format('DELETE FROM %s WHERE ctid = $1', rel) USING expired_row;
                        total := total + 1;
                    EXCEPTION WHEN foreign_key_violation OR restrict_violation THEN
                        skipped := skipped + 1;
                    END;
                END LOOP;
                errors := errors || rule.table_name || ': ' || skipped || ' expired rows kept, still referred to by another table; ';
                RAISE WARNING 'audit trail: retention rule for %: % expired rows kept, still referred to by another table', rule.table_name, skipped;
            WHEN OTHERS THEN
                errors := errors || rule.table_name || ': ' || SQLERRM || '; ';
                RAISE WARNING 'audit trail: retention rule for % failed: %', rule.table_name, SQLERRM;
        END;
    END LOOP;
    PERFORM audit.note_purge(total, nullif(errors, ''));
    RETURN total;
END
$body$;

-- The log as a customer reads it. actor_label_query, when given, returns (actor, label) pairs that name the people, for
-- example the persons of LesBij by their username. It runs as the caller, so it can read no more than the caller can
CREATE OR REPLACE FUNCTION audit.export(since timestamptz, until timestamptz, actor_label_query text DEFAULT NULL)
RETURNS TABLE (changed_at timestamptz, actor text, actor_label text, table_name text, operation text, row_key jsonb, old_values jsonb,
               new_values jsonb, xact_id xid8)
LANGUAGE plpgsql STABLE SET search_path = pg_catalog, pg_temp AS $body$
BEGIN
    RETURN QUERY EXECUTE format(
        'WITH L(actor, label) AS (%s) '
        'SELECT R.changed_at, R.actor, (SELECT string_agg(DISTINCT L.label::text, $3) FROM L WHERE L.actor::text = R.actor), '
        '       R.table_name, R.operation, R.row_key, R.old_values, R.new_values, R.xact_id '
        '  FROM audit.record_change R WHERE R.changed_at >= $1 AND R.changed_at < $2 ORDER BY R.id',
        coalesce(actor_label_query, 'SELECT NULL::text, NULL::text WHERE false')) USING since, until, ', ';
END
$body$;

-- Per table: audited (four triggers, enabled, with the arguments its current columns call for), stale (the triggers carry other
-- arguments: run audit.attach_all()), partial, missing or excluded
CREATE OR REPLACE VIEW audit.coverage AS
SELECT N.nspname || '.' || C.relname AS table_name,
       CASE WHEN X.table_name IS NOT NULL THEN 'excluded'
            WHEN count(T.oid) FILTER (WHERE T.tgenabled = 'O') = 4
             AND count(T.oid) FILTER (WHERE T.tgname <> 'zzz_audit_truncate' AND T.tgargs = audit.trigger_args_bytes(audit.trigger_args(C.oid::regclass))) = 3 THEN 'audited'
            WHEN count(T.oid) FILTER (WHERE T.tgenabled = 'O') = 4 THEN 'stale'
            WHEN count(T.oid) > 0 THEN 'partial'
            ELSE 'missing' END AS status,
       X.reason AS excluded_because,
       (audit.trigger_args(C.oid::regclass))[2] AS withheld_columns,
       RR.keep AS retention
  FROM pg_class C
  JOIN pg_namespace N ON N.oid = C.relnamespace
  LEFT JOIN pg_trigger T ON T.tgrelid = C.oid AND T.tgname IN ('zzz_audit_insert', 'zzz_audit_update', 'zzz_audit_delete', 'zzz_audit_truncate')
  LEFT JOIN audit.excluded_table X ON X.table_name = N.nspname || '.' || C.relname
  LEFT JOIN audit.retention_rule RR ON RR.table_name = N.nspname || '.' || C.relname
 WHERE C.relkind IN ('r', 'p') AND NOT C.relispartition AND C.relpersistence <> 't' AND NOT audit.is_skipped_schema(N.nspname)
 GROUP BY C.oid, N.nspname, C.relname, X.table_name, X.reason, RR.keep;

-- The functions on the path of a write and of the purge belong to jaaql_audit, which can only read the settings and write the
-- log; the ones that attach triggers stay with the superuser that installs this file
ALTER FUNCTION audit.is_bulk_loader() OWNER TO jaaql_audit;
ALTER FUNCTION audit.withheld_marks(jsonb, text[]) OWNER TO jaaql_audit;
ALTER FUNCTION audit.masked_key(jsonb, text[], text[], text) OWNER TO jaaql_audit;
ALTER FUNCTION audit.forget_rows(text, text[], jsonb[], boolean) OWNER TO jaaql_audit;
ALTER FUNCTION audit.record_statement() OWNER TO jaaql_audit;
ALTER FUNCTION audit.record_truncate() OWNER TO jaaql_audit;
ALTER FUNCTION audit.begin_erasure(text) OWNER TO jaaql_audit;
ALTER FUNCTION audit.forget_actor(text) OWNER TO jaaql_audit;
ALTER FUNCTION audit.purge_log() OWNER TO jaaql_audit;
ALTER FUNCTION audit.note_purge(bigint, text) OWNER TO jaaql_audit;

REVOKE ALL ON ALL TABLES IN SCHEMA audit FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA audit FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit.record_change, audit.erasure TO jaaql_audit;
GRANT SELECT, UPDATE ON audit.setting TO jaaql_audit;
GRANT SELECT ON audit.secret TO jaaql_audit;
GRANT EXECUTE ON FUNCTION audit.table_oid(text), audit.trigger_args(regclass), audit.is_withheld(text, text, text),
                          audit.is_skipped_schema(text) TO jaaql_audit;

DO $do$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'dba') THEN
        GRANT USAGE ON SCHEMA audit TO dba;
        GRANT SELECT ON audit.record_change, audit.erasure, audit.setting, audit.coverage TO dba;
        GRANT SELECT, INSERT, UPDATE, DELETE ON audit.withheld_column, audit.excluded_table, audit.retention_rule TO dba;
        GRANT EXECUTE ON FUNCTION audit.attach(regclass), audit.attach_all(), audit.begin_erasure(text), audit.forget_record(text, jsonb),
                                  audit.forget_actor(text), audit.purge_expired(), audit.purge_log(), audit.note_purge(bigint, text),
                                  audit.export(timestamptz, timestamptz, text), audit.is_withheld(text, text, text),
                                  audit.is_skipped_schema(text), audit.table_oid(text), audit.trigger_args(regclass),
                                  audit.trigger_args_bytes(text[]) TO dba;
    END IF;
END
$do$;

DO $do$
BEGIN
    PERFORM audit.attach_all();
END
$do$;
