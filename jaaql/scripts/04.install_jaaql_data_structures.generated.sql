-- BATON functions

create function "BS.iso_extended_week_number" (
	d date
) returns character varying(8) as
$$
DECLARE
	_result character varying(8) = '';
BEGIN
	SELECT
		EXTRACT(ISOYEAR FROM d)::text ||
		'-W' ||
		lpad(EXTRACT(WEEK FROM d)::text, 2, '0')
	INTO
		_result;

	return _result;
END;
$$ language plpgsql;

SELECT * from plpgsql_check_function(
	'"BS.iso_extended_week_number"(date)'
);

grant execute on function "BS.iso_extended_week_number" to public;

create type _error_type as (
	table_name character varying(63),
	index integer,
	error_code character varying(20),
	message character varying(256),
	column_name character varying(63)
);
CREATE DOMAIN _error_record AS _error_type
	CHECK ((VALUE).table_name is not null AND
			(VALUE).message is not null);

create domain _jaaql_procedure_result AS integer NOT NULL;

create type _status_type as (
	result integer,
	errors _error_record[]
);

CREATE DOMAIN _status_record AS _status_type
	CHECK ((VALUE).result is not null);

CREATE FUNCTION raise_jaaql_handled_query_exception(_status _status_record)
RETURNS void AS $$
BEGIN
	RAISE EXCEPTION '%',
	(
		SELECT json_agg(row_to_json(t))::text
		FROM (
			SELECT
				e.table_name::text AS table_name,
				e.index::integer AS index,
				e.message::text AS message,
				e.column_name::text AS column_name
			FROM unnest(_status.errors) AS e
		) t
	)
	USING ERRCODE = 'JQ000';
END;
$$ LANGUAGE plpgsql;

--(0) Check table and column names


-- (1) Create tables

-- application...
create table application (
	name internet_name not null,
	base_url url not null,
	templates_source location,
	default_schema object_name,
	unlock_key_validity_period validity_period not null default 1209600,
	unlock_code_validity_period short_validity_period not null default 900,
	is_live bool not null default FALSE,
	primary key (name),
	check (unlock_key_validity_period between 15 and 9999999),
	check (unlock_code_validity_period between 15 and 86400) );
-- application_schema...
create table application_schema (
	application internet_name not null,
	name object_name not null,
	database object_name not null,
	primary key (application, name) );
-- email_dispatcher...
create table email_dispatcher (
	application internet_name not null,
	name object_name not null,
	display_name person_name not null,
	protocol email_dispatch_protocol,
	url url,
	port internet_port,
	username email_server_username,
	password encrypted__email_server_password,
	whitelist text,
	primary key (application, name),
	check (port between 1 and 65536) );
-- jaaql...
create table _jaaql (
	migration_version semantic_version not null,
	last_successful_build_time build_time not null,
	_singleton_key boolean PRIMARY KEY not null default true,
	check(_singleton_key is true) );
	create view jaaql as select
		migration_version, last_successful_build_time
	from _jaaql
	where _singleton_key;
-- email_template...
create table email_template (
	application internet_name not null,
	dispatcher object_name not null,
	name object_name not null,
	content_url safe_path not null,
	validation_schema object_name,
	base_relation object_name,
	permissions_view object_name,
	data_view object_name,
	dispatcher_domain_recipient email_account_username,
	fixed_address character varying(254),
	can_be_sent_anonymously bool,
	primary key (application, name) );
-- document_template...
create table document_template (
	application internet_name not null,
	name object_name not null,
	content_path safe_path not null,
	email_template object_name,
	primary key (application, name) );
-- document_request...
create table document_request (
	application internet_name not null,
	template object_name not null,
	uuid uuid not null default gen_random_uuid(),
	request_timestamp timestamptz not null default current_timestamp,
	encrypted_access_token encrypted__access_token not null,
	encrypted_parameters text,
	render_timestamp timestamptz,
	create_file bool not null,
	file_name file_name,
	content bytea,
	completed timestamptz,
	primary key (uuid) );
-- federation_procedure...
create table federation_procedure (
	name procedure_name not null,
	primary key (name) );
-- federation_procedure_parameter...
create table federation_procedure_parameter (
	procedure procedure_name not null,
	name scope_name not null,
	primary key (procedure, name) );
-- identity_provider_service...
create table identity_provider_service (
	name provider_name not null,
	logo_url url not null,
	requires_email_verification bool not null,
	primary key (name) );
-- user_registry...
create table user_registry (
	provider provider_name not null,
	tenant tenant_name not null,
	discovery_url url not null,
	primary key (provider, tenant),
	unique (discovery_url) );
-- database_user_registry...
create table database_user_registry (
	provider provider_name not null,
	tenant tenant_name not null,
	database object_name not null,
	federation_procedure procedure_name not null,
	client_id encrypted__oidc_client_id not null,
	client_secret encrypted__oidc_client_secret,
	primary key (provider, tenant, database) );
-- account...
create table account (
	id postgres_role not null,
	sub encrypted__oidc_sub not null,
	username username,
	email encrypted__email,
	email_verified bool not null,
	deletion_timestamp timestamptz,
	provider provider_name,
	tenant tenant_name,
	api_key api_key,
	primary key (id),
	unique (username),
	unique (sub, provider, tenant) );
-- validated_ip_address...
create table validated_ip_address (
	account postgres_role not null,
	uuid uuid not null default gen_random_uuid(),
	encrypted_salted_ip_address encrypted__salted_ip not null,
	first_authentication_timestamp timestamptz not null default current_timestamp,
	last_authentication_timestamp timestamptz not null,
	primary key (uuid),
	unique (encrypted_salted_ip_address) );
-- security_event...
create table security_event (
	application internet_name not null,
	name security_event_name not null,
	type security_event_type not null,
	database_procedure procedure_name not null,
	primary key (application, name, type) );
-- handled_error...
create table handled_error (
	code error_code not null,
	error_name error_name,
	is_arrayed bool not null,
	table_name object_name,
	table_name_required bool,
	table_possible bool,
	column_possible bool,
	has_associated_set bool,
	has_sub_code bool,
	column_name object_name,
	http_response_code http_response_code default 422,
	message text,
	description text not null,
	primary key (code),
	check (code between 1001 and 1999),
	check (http_response_code between 100 and 599) );
-- pg_base_exception...
create table pg_base_exception (
	name pg_base_exception_name not null,
	primary key (name) );
-- pg_error_class...
create table pg_error_class (
	code pg_error_class_code not null,
	name pg_error_class_name not null,
	description pg_error_class_description,
	primary key (code) );
-- pg_exception...
create table pg_exception (
	pg_class pg_error_class_code not null,
	sqlstate pg_sqlstate not null,
	name pg_exception_name not null,
	base_exception pg_base_exception_name not null,
	primary key (sqlstate) );
-- remote_procedure...
create table remote_procedure (
	application internet_name not null,
	name object_name not null,
	command text not null,
	access procedure_access_level not null,
	cron text,
	primary key (application, name) );

-- (1a) Create view to give current date/time, possibly read from a table

create view _current as
	SELECT
		CURRENT_DATE as date_,
		LOCALTIMESTAMP as time_;

grant select on "_current" to public;

create view _current_date_parts as (
	SELECT
		"BS.iso_extended_week_number"(date_) as iso_extended_week_number_,
		to_char(time_, 'HH24:MI') as hour_,
		extract(isodow from date_) - 1 as dow_
	FROM
		_current
);

grant select on "_current_date_parts" to public;

