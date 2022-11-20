\echo Use "CREATE EXTENSION jaaql" to load this file. \quit

SET LOCAL search_path to @extschema@;

CREATE FUNCTION @extschema@.jaaql__set_session_authorization(text, text)
RETURNS text
AS 'MODULE_PATHNAME', 'jaaql__set_session_authorization'
LANGUAGE C STRICT;

CREATE FUNCTION @extschema@.jaaql__reset_session_authorization(text)
RETURNS text
AS 'MODULE_PATHNAME', 'jaaql__reset_session_authorization'
LANGUAGE C STRICT;

REVOKE EXECUTE ON FUNCTION @extschema@.jaaql__set_session_authorization(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION @extschema@.jaaql__reset_session_authorization(text) TO PUBLIC;
