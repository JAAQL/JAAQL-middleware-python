

-- (a) User Partition Columns and Username Columns






















-- (b) User Partition Views


-- (c) Grant access to user partition views


-- (d) Create super functions

-- application...

-- application_schema...

drop function if exists "application_schema.insert+";
create function "application_schema.insert+" (
	database object_name,
	name object_name,
	application internet_name,
	use_as_default jsonb default '[]'::jsonb
) returns _jaaql_procedure_result as
$$
	DECLARE
		_returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_r jsonb;
	BEGIN
		SELECT * INTO strict _returned_status FROM "application_schema.insert__internal"(
			application => "application_schema.insert+".application,
			name => "application_schema.insert+".name,
			database => "application_schema.insert+".database );
		_status.result = _returned_status.result;
		_status.errors = _status.errors || _returned_status.errors;

		for _r in SELECT * FROM jsonb_array_elements(use_as_default) loop
			SELECT * INTO strict _returned_status FROM "application.insert__internal"(
				name => "application_schema.insert+".application,
				default_schema => "application_schema.insert+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
	END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"application_schema.insert+"('
		'object_name,'
		'object_name,'
		'internet_name,'
		'jsonb)'
);

grant execute on function "application_schema.insert+" to registered;
drop function if exists "application_schema.persist+";
create function "application_schema.persist+" (
	application internet_name,
	name object_name,
	database object_name default null,
	use_as_default jsonb default '[]'::jsonb
) returns _jaaql_procedure_result as
$$
	DECLARE
		_returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_r jsonb;
	BEGIN
		DELETE FROM application A WHERE
			A.name = "application_schema.persist+".application AND
			A.default_schema = "application_schema.persist+".name;
		DELETE FROM email_template E WHERE
			E.application = "application_schema.persist+".application AND
			E.validation_schema = "application_schema.persist+".name;

		for _r in SELECT * FROM jsonb_array_elements(use_as_default) loop
			SELECT * INTO strict _returned_status FROM "application.persist__internal"(
				name => "application_schema.persist+".application,
				default_schema => "application_schema.persist+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
	END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"application_schema.persist+"('
		'internet_name,'
		'object_name,'
		'object_name,'
		'jsonb)'
);

grant execute on function "application_schema.persist+" to registered;
drop function if exists "application_schema.update+";
create function "application_schema.update+" (
	application internet_name,
	name object_name,
	database object_name default null,
	use_as_default jsonb default '[]'::jsonb
) returns _jaaql_procedure_result as
$$
	DECLARE
		_returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_r jsonb;
	BEGIN
		DELETE FROM application A WHERE
			A.name = "application_schema.update+".application AND
			A.default_schema = "application_schema.update+".name;
		DELETE FROM email_template E WHERE
			E.application = "application_schema.update+".application AND
			E.validation_schema = "application_schema.update+".name;

		for _r in SELECT * FROM jsonb_array_elements(use_as_default) loop
			SELECT * INTO strict _returned_status FROM "application.update__internal"(
				name => "application_schema.update+".application,
				default_schema => "application_schema.update+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
	END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"application_schema.update+"('
		'internet_name,'
		'object_name,'
		'object_name,'
		'jsonb)'
);

grant execute on function "application_schema.update+" to registered;
-- email_dispatcher...

-- jaaql...

-- email_template...

drop function if exists "email_template.insert+";
create function "email_template.insert+" (
	content_url safe_path,
	type email_template_type,
	name object_name,
	dispatcher object_name,
	application internet_name,
	validation_schema object_name default null,
	base_relation object_name default null,
	dbms_user_column_name object_name default null,
	permissions_view object_name default null,
	data_view object_name default null,
	dispatcher_domain_recipient email_account_username default null,
	requires_confirmation bool default null,
	can_be_sent_anonymously bool default null,
	use_as_default_sign_up jsonb default '[]'::jsonb,
	use_as_default_already_signed_up jsonb default '[]'::jsonb,
	use_as_default_reset_password jsonb default '[]'::jsonb,
	use_as_default_unregisted_password_reset jsonb default '[]'::jsonb
) returns _jaaql_procedure_result as
$$
	DECLARE
		_returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_r jsonb;
	BEGIN
		SELECT * INTO strict _returned_status FROM "email_template.insert__internal"(
			application => "email_template.insert+".application,
			dispatcher => "email_template.insert+".dispatcher,
			name => "email_template.insert+".name,
			type => "email_template.insert+".type,
			content_url => "email_template.insert+".content_url,
			validation_schema => "email_template.insert+".validation_schema,
			base_relation => "email_template.insert+".base_relation,
			dbms_user_column_name => "email_template.insert+".dbms_user_column_name,
			permissions_view => "email_template.insert+".permissions_view,
			data_view => "email_template.insert+".data_view,
			dispatcher_domain_recipient => "email_template.insert+".dispatcher_domain_recipient,
			requires_confirmation => "email_template.insert+".requires_confirmation,
			can_be_sent_anonymously => "email_template.insert+".can_be_sent_anonymously );
		_status.result = _returned_status.result;
		_status.errors = _status.errors || _returned_status.errors;

		for _r in SELECT * FROM jsonb_array_elements(use_as_default_sign_up) loop
			SELECT * INTO strict _returned_status FROM "application.insert__internal"(
				name => "email_template.insert+".application,
				default_s_et => "email_template.insert+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_already_signed_up) loop
			SELECT * INTO strict _returned_status FROM "application.insert__internal"(
				name => "email_template.insert+".application,
				default_a_et => "email_template.insert+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_reset_password) loop
			SELECT * INTO strict _returned_status FROM "application.insert__internal"(
				name => "email_template.insert+".application,
				default_r_et => "email_template.insert+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_unregisted_password_reset) loop
			SELECT * INTO strict _returned_status FROM "application.insert__internal"(
				name => "email_template.insert+".application,
				default_u_et => "email_template.insert+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
	END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"email_template.insert+"('
		'safe_path,'
		'email_template_type,'
		'object_name,'
		'object_name,'
		'internet_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'email_account_username,'
		'bool,'
		'bool,'
		'jsonb,'
		'jsonb,'
		'jsonb,'
		'jsonb)'
);

grant execute on function "email_template.insert+" to registered;
drop function if exists "email_template.persist+";
create function "email_template.persist+" (
	application internet_name,
	name object_name,
	dispatcher object_name default null,
	type email_template_type default null,
	content_url safe_path default null,
	validation_schema object_name default null,
	base_relation object_name default null,
	dbms_user_column_name object_name default null,
	permissions_view object_name default null,
	data_view object_name default null,
	dispatcher_domain_recipient email_account_username default null,
	requires_confirmation bool default null,
	can_be_sent_anonymously bool default null,
	use_as_default_sign_up jsonb default '[]'::jsonb,
	use_as_default_already_signed_up jsonb default '[]'::jsonb,
	use_as_default_reset_password jsonb default '[]'::jsonb,
	use_as_default_unregisted_password_reset jsonb default '[]'::jsonb
) returns _jaaql_procedure_result as
$$
	DECLARE
		_returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_r jsonb;
	BEGIN
		DELETE FROM document_template D WHERE
			D.application = "email_template.persist+".application AND
			D.email_template = "email_template.persist+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.persist+".application AND
			A.default_s_et = "email_template.persist+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.persist+".application AND
			A.default_a_et = "email_template.persist+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.persist+".application AND
			A.default_r_et = "email_template.persist+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.persist+".application AND
			A.default_u_et = "email_template.persist+".name;
		DELETE FROM security_event S WHERE
			S.application = "email_template.persist+".application AND
			S.email_template = "email_template.persist+".name;

		for _r in SELECT * FROM jsonb_array_elements(use_as_default_sign_up) loop
			SELECT * INTO strict _returned_status FROM "application.persist__internal"(
				name => "email_template.persist+".application,
				default_s_et => "email_template.persist+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_already_signed_up) loop
			SELECT * INTO strict _returned_status FROM "application.persist__internal"(
				name => "email_template.persist+".application,
				default_a_et => "email_template.persist+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_reset_password) loop
			SELECT * INTO strict _returned_status FROM "application.persist__internal"(
				name => "email_template.persist+".application,
				default_r_et => "email_template.persist+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_unregisted_password_reset) loop
			SELECT * INTO strict _returned_status FROM "application.persist__internal"(
				name => "email_template.persist+".application,
				default_u_et => "email_template.persist+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
	END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"email_template.persist+"('
		'internet_name,'
		'object_name,'
		'object_name,'
		'email_template_type,'
		'safe_path,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'email_account_username,'
		'bool,'
		'bool,'
		'jsonb,'
		'jsonb,'
		'jsonb,'
		'jsonb)'
);

grant execute on function "email_template.persist+" to registered;
drop function if exists "email_template.update+";
create function "email_template.update+" (
	application internet_name,
	name object_name,
	dispatcher object_name default null,
	type email_template_type default null,
	content_url safe_path default null,
	validation_schema object_name default null,
	base_relation object_name default null,
	dbms_user_column_name object_name default null,
	permissions_view object_name default null,
	data_view object_name default null,
	dispatcher_domain_recipient email_account_username default null,
	requires_confirmation bool default null,
	can_be_sent_anonymously bool default null,
	use_as_default_sign_up jsonb default '[]'::jsonb,
	use_as_default_already_signed_up jsonb default '[]'::jsonb,
	use_as_default_reset_password jsonb default '[]'::jsonb,
	use_as_default_unregisted_password_reset jsonb default '[]'::jsonb
) returns _jaaql_procedure_result as
$$
	DECLARE
		_returned_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		_r jsonb;
	BEGIN
		DELETE FROM document_template D WHERE
			D.application = "email_template.update+".application AND
			D.email_template = "email_template.update+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.update+".application AND
			A.default_s_et = "email_template.update+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.update+".application AND
			A.default_a_et = "email_template.update+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.update+".application AND
			A.default_r_et = "email_template.update+".name;
		DELETE FROM application A WHERE
			A.name = "email_template.update+".application AND
			A.default_u_et = "email_template.update+".name;
		DELETE FROM security_event S WHERE
			S.application = "email_template.update+".application AND
			S.email_template = "email_template.update+".name;

		for _r in SELECT * FROM jsonb_array_elements(use_as_default_sign_up) loop
			SELECT * INTO strict _returned_status FROM "application.update__internal"(
				name => "email_template.update+".application,
				default_s_et => "email_template.update+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_already_signed_up) loop
			SELECT * INTO strict _returned_status FROM "application.update__internal"(
				name => "email_template.update+".application,
				default_a_et => "email_template.update+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_reset_password) loop
			SELECT * INTO strict _returned_status FROM "application.update__internal"(
				name => "email_template.update+".application,
				default_r_et => "email_template.update+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_u_et => (_r->>'default_u_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		for _r in SELECT * FROM jsonb_array_elements(use_as_default_unregisted_password_reset) loop
			SELECT * INTO strict _returned_status FROM "application.update__internal"(
				name => "email_template.update+".application,
				default_u_et => "email_template.update+".name,
				base_url => (_r->>'base_url')::url,
				templates_source => (_r->>'templates_source')::location,
				default_schema => (_r->>'default_schema')::object_name,
				default_s_et => (_r->>'default_s_et')::object_name,
				default_a_et => (_r->>'default_a_et')::object_name,
				default_r_et => (_r->>'default_r_et')::object_name,
				unlock_key_validity_period => CASE WHEN _r->>'unlock_key_validity_period' = '' THEN null ELSE (_r->>'unlock_key_validity_period')::validity_period END,
				unlock_code_validity_period => CASE WHEN _r->>'unlock_code_validity_period' = '' THEN null ELSE (_r->>'unlock_code_validity_period')::short_validity_period END,
				is_live => CASE WHEN _r->>'is_live' = '' THEN null ELSE (_r->>'is_live')::bool END,
				_index => (_r->>'_index')::integer,
				_check_only => cardinality(_status.errors) <> 0);
			_status.errors = _status.errors || _returned_status.errors;
		end loop;
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
	END
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"email_template.update+"('
		'internet_name,'
		'object_name,'
		'object_name,'
		'email_template_type,'
		'safe_path,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'email_account_username,'
		'bool,'
		'bool,'
		'jsonb,'
		'jsonb,'
		'jsonb,'
		'jsonb)'
);

grant execute on function "email_template.update+" to registered;
-- document_template...

-- document_request...

-- federation_procedure...

-- federation_procedure_parameter...

-- identity_provider_service...

-- user_registry...

-- database_user_registry...

-- account...

-- validated_ip_address...

-- security_event...

-- handled_error...

-- pg_base_exception...

-- pg_error_class...

-- pg_exception...

-- remote_procedure...



-- (e) Create table functions

-- application...

drop function if exists "application.insert__internal";
create function "application.insert__internal" (
	is_live bool,
	unlock_code_validity_period short_validity_period,
	unlock_key_validity_period validity_period,
	base_url url,
	name internet_name,
	templates_source location default null,
	default_schema object_name default null,
	default_s_et object_name default null,
	default_a_et object_name default null,
	default_r_et object_name default null,
	default_u_et object_name default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "application.insert__internal".name is null then
				"application.insert__internal".name = '';
			end if;
			if "application.insert__internal".base_url is null then
				"application.insert__internal".base_url = '';
			end if;
		-- (A) Check that required values are present
			if "application.insert__internal".base_url = '' then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er moet een waarde ingevuld worden voor Base Url',
						'base_url'
					)::_error_record;
			end if;
			if "application.insert__internal".unlock_key_validity_period is null then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er moet een waarde ingevuld worden voor Unlock Key Validity Period',
						'unlock_key_validity_period'
					)::_error_record;
			end if;
			if "application.insert__internal".unlock_code_validity_period is null then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er moet een waarde ingevuld worden voor Unlock Code Validity Period',
						'unlock_code_validity_period'
					)::_error_record;
			end if;
			if "application.insert__internal".is_live is null then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er moet een waarde ingevuld worden voor Is Live',
						'is_live'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM application A
			WHERE
				A.name = "application.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er is al een Application geregistreed met '
						'Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "application.insert__internal"._check_only then
				INSERT INTO application (
					name,
					base_url,
					templates_source,
					default_schema,
					default_s_et,
					default_a_et,
					default_r_et,
					default_u_et,
					unlock_key_validity_period,
					unlock_code_validity_period,
					is_live
				) VALUES (
					"application.insert__internal"."name",
					"application.insert__internal"."base_url",
					"application.insert__internal"."templates_source",
					"application.insert__internal"."default_schema",
					"application.insert__internal"."default_s_et",
					"application.insert__internal"."default_a_et",
					"application.insert__internal"."default_r_et",
					"application.insert__internal"."default_u_et",
					"application.insert__internal"."unlock_key_validity_period",
					"application.insert__internal"."unlock_code_validity_period",
					"application.insert__internal"."is_live" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"application.insert__internal"('
		'bool,'
		'short_validity_period,'
		'validity_period,'
		'url,'
		'internet_name,'
		'location,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'integer,'
		'boolean)'
);

drop function if exists "application.insert";
	create function "application.insert" (
		is_live bool,
		unlock_code_validity_period short_validity_period,
		unlock_key_validity_period validity_period,
		base_url url,
		name internet_name,
		templates_source location default null,
		default_schema object_name default null,
		default_s_et object_name default null,
		default_a_et object_name default null,
		default_r_et object_name default null,
		default_u_et object_name default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "application.insert__internal"(
				name => "application.insert".name,
				base_url => "application.insert".base_url,
				templates_source => "application.insert".templates_source,
				default_schema => "application.insert".default_schema,
				default_s_et => "application.insert".default_s_et,
				default_a_et => "application.insert".default_a_et,
				default_r_et => "application.insert".default_r_et,
				default_u_et => "application.insert".default_u_et,
				unlock_key_validity_period => "application.insert".unlock_key_validity_period,
				unlock_code_validity_period => "application.insert".unlock_code_validity_period,
				is_live => "application.insert".is_live);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "application.update__internal";
	create function "application.update__internal" (
		name internet_name,
		base_url url default null,
		templates_source location default null,
		default_schema object_name default null,
		default_s_et object_name default null,
		default_a_et object_name default null,
		default_r_et object_name default null,
		default_u_et object_name default null,
		unlock_key_validity_period validity_period default null,
		unlock_code_validity_period short_validity_period default null,
		is_live bool default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM application A
			WHERE
				A.name = "application.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er is geen Application gevonden met '
						'Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE application A
			SET
				base_url = coalesce("application.update__internal".base_url, A.base_url),
				templates_source = coalesce("application.update__internal".templates_source, A.templates_source),
				default_schema = coalesce("application.update__internal".default_schema, A.default_schema),
				default_s_et = coalesce("application.update__internal".default_s_et, A.default_s_et),
				default_a_et = coalesce("application.update__internal".default_a_et, A.default_a_et),
				default_r_et = coalesce("application.update__internal".default_r_et, A.default_r_et),
				default_u_et = coalesce("application.update__internal".default_u_et, A.default_u_et),
				unlock_key_validity_period = coalesce("application.update__internal".unlock_key_validity_period, A.unlock_key_validity_period),
				unlock_code_validity_period = coalesce("application.update__internal".unlock_code_validity_period, A.unlock_code_validity_period),
				is_live = coalesce("application.update__internal".is_live, A.is_live)
			WHERE 
				A.name = "application.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"application.update__internal"('
			'internet_name,'
			'url,'
			'location,'
			'object_name,'
			'object_name,'
			'object_name,'
			'object_name,'
			'object_name,'
			'validity_period,'
			'short_validity_period,'
			'bool,'
			'integer,'
			'boolean)'
	);

drop function if exists "application.update";
	create function "application.update" (
		name internet_name,
		base_url url default null,
		templates_source location default null,
		default_schema object_name default null,
		default_s_et object_name default null,
		default_a_et object_name default null,
		default_r_et object_name default null,
		default_u_et object_name default null,
		unlock_key_validity_period validity_period default null,
		unlock_code_validity_period short_validity_period default null,
		is_live bool default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "application.update__internal"(
				name => "application.update".name,
				base_url => "application.update".base_url,
				templates_source => "application.update".templates_source,
				default_schema => "application.update".default_schema,
				default_s_et => "application.update".default_s_et,
				default_a_et => "application.update".default_a_et,
				default_r_et => "application.update".default_r_et,
				default_u_et => "application.update".default_u_et,
				unlock_key_validity_period => "application.update".unlock_key_validity_period,
				unlock_code_validity_period => "application.update".unlock_code_validity_period,
				is_live => "application.update".is_live);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "application.delete__internal";
	create function "application.delete__internal" (
		name internet_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM application A
			WHERE
				A.name = "application.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('application', _index,
						'Er is geen Application gevonden met '
						'Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM application A
			WHERE 
				A.name = "application.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"application.delete__internal"('
			'internet_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "application.delete";
	create function "application.delete" (
		name internet_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "application.delete__internal"(
				name => "application.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- application_schema...

drop function if exists "application_schema.insert__internal";
create function "application_schema.insert__internal" (
	database object_name,
	name object_name,
	application internet_name,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "application_schema.insert__internal".application is null then
				"application_schema.insert__internal".application = '';
			end if;
			if "application_schema.insert__internal".name is null then
				"application_schema.insert__internal".name = '';
			end if;
			if "application_schema.insert__internal".database is null then
				"application_schema.insert__internal".database = '';
			end if;
		-- (A) Check that required values are present
			if "application_schema.insert__internal".database = '' then
				_status.errors = _status.errors ||
					ROW('application_schema', _index,
						'Er moet een waarde ingevuld worden voor Database',
						'database'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM application_schema A
			WHERE
				A.application = "application_schema.insert__internal".application AND
				A.name = "application_schema.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('application_schema', _index,
						'Er is al een Application Schema geregistreed met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "application_schema.insert__internal"._check_only then
				INSERT INTO application_schema (
					application,
					name,
					database
				) VALUES (
					"application_schema.insert__internal"."application",
					"application_schema.insert__internal"."name",
					"application_schema.insert__internal"."database" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"application_schema.insert__internal"('
		'object_name,'
		'object_name,'
		'internet_name,'
		'integer,'
		'boolean)'
);

drop function if exists "application_schema.insert";
	create function "application_schema.insert" (
		database object_name,
		name object_name,
		application internet_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "application_schema.insert__internal"(
				application => "application_schema.insert".application,
				name => "application_schema.insert".name,
				database => "application_schema.insert".database);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "application_schema.update__internal";
	create function "application_schema.update__internal" (
		application internet_name,
		name object_name,
		database object_name default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM application_schema A
			WHERE
				A.application = "application_schema.update__internal".application AND
				A.name = "application_schema.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('application_schema', _index,
						'Er is geen Application Schema gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE application_schema A
			SET
				database = coalesce("application_schema.update__internal".database, A.database)
			WHERE 
				A.application = "application_schema.update__internal".application AND
				A.name = "application_schema.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"application_schema.update__internal"('
			'internet_name,'
			'object_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "application_schema.update";
	create function "application_schema.update" (
		application internet_name,
		name object_name,
		database object_name default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "application_schema.update__internal"(
				application => "application_schema.update".application,
				name => "application_schema.update".name,
				database => "application_schema.update".database);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "application_schema.delete__internal";
	create function "application_schema.delete__internal" (
		application internet_name,
		name object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM application_schema A
			WHERE
				A.application = "application_schema.delete__internal".application AND
				A.name = "application_schema.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('application_schema', _index,
						'Er is geen Application Schema gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM application_schema A
			WHERE 
				A.application = "application_schema.delete__internal".application AND
				A.name = "application_schema.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"application_schema.delete__internal"('
			'internet_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "application_schema.delete";
	create function "application_schema.delete" (
		application internet_name,
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "application_schema.delete__internal"(
				application => "application_schema.delete".application,
				name => "application_schema.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- email_dispatcher...

drop function if exists "email_dispatcher.insert__internal";
create function "email_dispatcher.insert__internal" (
	display_name person_name,
	name object_name,
	application internet_name,
	protocol email_dispatch_protocol default null,
	url url default null,
	port internet_port default null,
	username email_server_username default null,
	password encrypted__email_server_password default null,
	whitelist text default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "email_dispatcher.insert__internal".application is null then
				"email_dispatcher.insert__internal".application = '';
			end if;
			if "email_dispatcher.insert__internal".name is null then
				"email_dispatcher.insert__internal".name = '';
			end if;
			if "email_dispatcher.insert__internal".display_name is null then
				"email_dispatcher.insert__internal".display_name = '';
			end if;
		-- (A) Check that required values are present
			if "email_dispatcher.insert__internal".display_name = '' then
				_status.errors = _status.errors ||
					ROW('email_dispatcher', _index,
						'Er moet een waarde ingevuld worden voor Display Name',
						'display_name'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM email_dispatcher E
			WHERE
				E.application = "email_dispatcher.insert__internal".application AND
				E.name = "email_dispatcher.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('email_dispatcher', _index,
						'Er is al een Email Dispatcher geregistreed met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "email_dispatcher.insert__internal"._check_only then
				INSERT INTO email_dispatcher (
					application,
					name,
					display_name,
					protocol,
					url,
					port,
					username,
					password,
					whitelist
				) VALUES (
					"email_dispatcher.insert__internal"."application",
					"email_dispatcher.insert__internal"."name",
					"email_dispatcher.insert__internal"."display_name",
					"email_dispatcher.insert__internal"."protocol",
					"email_dispatcher.insert__internal"."url",
					"email_dispatcher.insert__internal"."port",
					"email_dispatcher.insert__internal"."username",
					"email_dispatcher.insert__internal"."password",
					"email_dispatcher.insert__internal"."whitelist" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"email_dispatcher.insert__internal"('
		'person_name,'
		'object_name,'
		'internet_name,'
		'email_dispatch_protocol,'
		'url,'
		'internet_port,'
		'email_server_username,'
		'encrypted__email_server_password,'
		'text,'
		'integer,'
		'boolean)'
);

drop function if exists "email_dispatcher.insert";
	create function "email_dispatcher.insert" (
		display_name person_name,
		name object_name,
		application internet_name,
		protocol email_dispatch_protocol default null,
		url url default null,
		port internet_port default null,
		username email_server_username default null,
		password encrypted__email_server_password default null,
		whitelist text default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "email_dispatcher.insert__internal"(
				application => "email_dispatcher.insert".application,
				name => "email_dispatcher.insert".name,
				display_name => "email_dispatcher.insert".display_name,
				protocol => "email_dispatcher.insert".protocol,
				url => "email_dispatcher.insert".url,
				port => "email_dispatcher.insert".port,
				username => "email_dispatcher.insert".username,
				password => "email_dispatcher.insert".password,
				whitelist => "email_dispatcher.insert".whitelist);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "email_dispatcher.update__internal";
	create function "email_dispatcher.update__internal" (
		application internet_name,
		name object_name,
		display_name person_name default null,
		protocol email_dispatch_protocol default null,
		url url default null,
		port internet_port default null,
		username email_server_username default null,
		password encrypted__email_server_password default null,
		whitelist text default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM email_dispatcher E
			WHERE
				E.application = "email_dispatcher.update__internal".application AND
				E.name = "email_dispatcher.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('email_dispatcher', _index,
						'Er is geen Email Dispatcher gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE email_dispatcher E
			SET
				display_name = coalesce("email_dispatcher.update__internal".display_name, E.display_name),
				protocol = coalesce("email_dispatcher.update__internal".protocol, E.protocol),
				url = coalesce("email_dispatcher.update__internal".url, E.url),
				port = coalesce("email_dispatcher.update__internal".port, E.port),
				username = coalesce("email_dispatcher.update__internal".username, E.username),
				password = coalesce("email_dispatcher.update__internal".password, E.password),
				whitelist = coalesce("email_dispatcher.update__internal".whitelist, E.whitelist)
			WHERE 
				E.application = "email_dispatcher.update__internal".application AND
				E.name = "email_dispatcher.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"email_dispatcher.update__internal"('
			'internet_name,'
			'object_name,'
			'person_name,'
			'email_dispatch_protocol,'
			'url,'
			'internet_port,'
			'email_server_username,'
			'encrypted__email_server_password,'
			'text,'
			'integer,'
			'boolean)'
	);

drop function if exists "email_dispatcher.update";
	create function "email_dispatcher.update" (
		application internet_name,
		name object_name,
		display_name person_name default null,
		protocol email_dispatch_protocol default null,
		url url default null,
		port internet_port default null,
		username email_server_username default null,
		password encrypted__email_server_password default null,
		whitelist text default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "email_dispatcher.update__internal"(
				application => "email_dispatcher.update".application,
				name => "email_dispatcher.update".name,
				display_name => "email_dispatcher.update".display_name,
				protocol => "email_dispatcher.update".protocol,
				url => "email_dispatcher.update".url,
				port => "email_dispatcher.update".port,
				username => "email_dispatcher.update".username,
				password => "email_dispatcher.update".password,
				whitelist => "email_dispatcher.update".whitelist);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "email_dispatcher.delete__internal";
	create function "email_dispatcher.delete__internal" (
		application internet_name,
		name object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM email_dispatcher E
			WHERE
				E.application = "email_dispatcher.delete__internal".application AND
				E.name = "email_dispatcher.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('email_dispatcher', _index,
						'Er is geen Email Dispatcher gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM email_dispatcher E
			WHERE 
				E.application = "email_dispatcher.delete__internal".application AND
				E.name = "email_dispatcher.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"email_dispatcher.delete__internal"('
			'internet_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "email_dispatcher.delete";
	create function "email_dispatcher.delete" (
		application internet_name,
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "email_dispatcher.delete__internal"(
				application => "email_dispatcher.delete".application,
				name => "email_dispatcher.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- jaaql...

-- email_template...

drop function if exists "email_template.insert__internal";
create function "email_template.insert__internal" (
	content_url safe_path,
	type email_template_type,
	name object_name,
	dispatcher object_name,
	application internet_name,
	validation_schema object_name default null,
	base_relation object_name default null,
	dbms_user_column_name object_name default null,
	permissions_view object_name default null,
	data_view object_name default null,
	dispatcher_domain_recipient email_account_username default null,
	requires_confirmation bool default null,
	can_be_sent_anonymously bool default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "email_template.insert__internal".application is null then
				"email_template.insert__internal".application = '';
			end if;
			if "email_template.insert__internal".dispatcher is null then
				"email_template.insert__internal".dispatcher = '';
			end if;
			if "email_template.insert__internal".name is null then
				"email_template.insert__internal".name = '';
			end if;
			if "email_template.insert__internal".type is null then
				"email_template.insert__internal".type = '';
			end if;
			if "email_template.insert__internal".content_url is null then
				"email_template.insert__internal".content_url = '';
			end if;
		-- (A) Check that required values are present
			if "email_template.insert__internal".dispatcher = '' then
				_status.errors = _status.errors ||
					ROW('email_template', _index,
						'Er moet een waarde ingevuld worden voor Dispatcher',
						'dispatcher'
					)::_error_record;
			end if;
			if "email_template.insert__internal".type = '' then
				_status.errors = _status.errors ||
					ROW('email_template', _index,
						'Er moet een waarde ingevuld worden voor Type',
						'type'
					)::_error_record;
			end if;
			if "email_template.insert__internal".content_url = '' then
				_status.errors = _status.errors ||
					ROW('email_template', _index,
						'Er moet een waarde ingevuld worden voor Content Url',
						'content_url'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM email_template E
			WHERE
				E.application = "email_template.insert__internal".application AND
				E.name = "email_template.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('email_template', _index,
						'Er is al een Email Template geregistreed met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "email_template.insert__internal"._check_only then
				INSERT INTO email_template (
					application,
					dispatcher,
					name,
					type,
					content_url,
					validation_schema,
					base_relation,
					dbms_user_column_name,
					permissions_view,
					data_view,
					dispatcher_domain_recipient,
					requires_confirmation,
					can_be_sent_anonymously
				) VALUES (
					"email_template.insert__internal"."application",
					"email_template.insert__internal"."dispatcher",
					"email_template.insert__internal"."name",
					"email_template.insert__internal"."type",
					"email_template.insert__internal"."content_url",
					"email_template.insert__internal"."validation_schema",
					"email_template.insert__internal"."base_relation",
					"email_template.insert__internal"."dbms_user_column_name",
					"email_template.insert__internal"."permissions_view",
					"email_template.insert__internal"."data_view",
					"email_template.insert__internal"."dispatcher_domain_recipient",
					"email_template.insert__internal"."requires_confirmation",
					"email_template.insert__internal"."can_be_sent_anonymously" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"email_template.insert__internal"('
		'safe_path,'
		'email_template_type,'
		'object_name,'
		'object_name,'
		'internet_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'object_name,'
		'email_account_username,'
		'bool,'
		'bool,'
		'integer,'
		'boolean)'
);

drop function if exists "email_template.insert";
	create function "email_template.insert" (
		content_url safe_path,
		type email_template_type,
		name object_name,
		dispatcher object_name,
		application internet_name,
		validation_schema object_name default null,
		base_relation object_name default null,
		dbms_user_column_name object_name default null,
		permissions_view object_name default null,
		data_view object_name default null,
		dispatcher_domain_recipient email_account_username default null,
		requires_confirmation bool default null,
		can_be_sent_anonymously bool default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "email_template.insert__internal"(
				application => "email_template.insert".application,
				dispatcher => "email_template.insert".dispatcher,
				name => "email_template.insert".name,
				type => "email_template.insert".type,
				content_url => "email_template.insert".content_url,
				validation_schema => "email_template.insert".validation_schema,
				base_relation => "email_template.insert".base_relation,
				dbms_user_column_name => "email_template.insert".dbms_user_column_name,
				permissions_view => "email_template.insert".permissions_view,
				data_view => "email_template.insert".data_view,
				dispatcher_domain_recipient => "email_template.insert".dispatcher_domain_recipient,
				requires_confirmation => "email_template.insert".requires_confirmation,
				can_be_sent_anonymously => "email_template.insert".can_be_sent_anonymously);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "email_template.update__internal";
	create function "email_template.update__internal" (
		application internet_name,
		name object_name,
		dispatcher object_name default null,
		type email_template_type default null,
		content_url safe_path default null,
		validation_schema object_name default null,
		base_relation object_name default null,
		dbms_user_column_name object_name default null,
		permissions_view object_name default null,
		data_view object_name default null,
		dispatcher_domain_recipient email_account_username default null,
		requires_confirmation bool default null,
		can_be_sent_anonymously bool default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM email_template E
			WHERE
				E.application = "email_template.update__internal".application AND
				E.name = "email_template.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('email_template', _index,
						'Er is geen Email Template gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE email_template E
			SET
				dispatcher = coalesce("email_template.update__internal".dispatcher, E.dispatcher),
				type = coalesce("email_template.update__internal".type, E.type),
				content_url = coalesce("email_template.update__internal".content_url, E.content_url),
				validation_schema = coalesce("email_template.update__internal".validation_schema, E.validation_schema),
				base_relation = coalesce("email_template.update__internal".base_relation, E.base_relation),
				dbms_user_column_name = coalesce("email_template.update__internal".dbms_user_column_name, E.dbms_user_column_name),
				permissions_view = coalesce("email_template.update__internal".permissions_view, E.permissions_view),
				data_view = coalesce("email_template.update__internal".data_view, E.data_view),
				dispatcher_domain_recipient = coalesce("email_template.update__internal".dispatcher_domain_recipient, E.dispatcher_domain_recipient),
				requires_confirmation = coalesce("email_template.update__internal".requires_confirmation, E.requires_confirmation),
				can_be_sent_anonymously = coalesce("email_template.update__internal".can_be_sent_anonymously, E.can_be_sent_anonymously)
			WHERE 
				E.application = "email_template.update__internal".application AND
				E.name = "email_template.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"email_template.update__internal"('
			'internet_name,'
			'object_name,'
			'object_name,'
			'email_template_type,'
			'safe_path,'
			'object_name,'
			'object_name,'
			'object_name,'
			'object_name,'
			'object_name,'
			'email_account_username,'
			'bool,'
			'bool,'
			'integer,'
			'boolean)'
	);

drop function if exists "email_template.update";
	create function "email_template.update" (
		application internet_name,
		name object_name,
		dispatcher object_name default null,
		type email_template_type default null,
		content_url safe_path default null,
		validation_schema object_name default null,
		base_relation object_name default null,
		dbms_user_column_name object_name default null,
		permissions_view object_name default null,
		data_view object_name default null,
		dispatcher_domain_recipient email_account_username default null,
		requires_confirmation bool default null,
		can_be_sent_anonymously bool default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "email_template.update__internal"(
				application => "email_template.update".application,
				dispatcher => "email_template.update".dispatcher,
				name => "email_template.update".name,
				type => "email_template.update".type,
				content_url => "email_template.update".content_url,
				validation_schema => "email_template.update".validation_schema,
				base_relation => "email_template.update".base_relation,
				dbms_user_column_name => "email_template.update".dbms_user_column_name,
				permissions_view => "email_template.update".permissions_view,
				data_view => "email_template.update".data_view,
				dispatcher_domain_recipient => "email_template.update".dispatcher_domain_recipient,
				requires_confirmation => "email_template.update".requires_confirmation,
				can_be_sent_anonymously => "email_template.update".can_be_sent_anonymously);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "email_template.delete__internal";
	create function "email_template.delete__internal" (
		application internet_name,
		name object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM email_template E
			WHERE
				E.application = "email_template.delete__internal".application AND
				E.name = "email_template.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('email_template', _index,
						'Er is geen Email Template gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM email_template E
			WHERE 
				E.application = "email_template.delete__internal".application AND
				E.name = "email_template.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"email_template.delete__internal"('
			'internet_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "email_template.delete";
	create function "email_template.delete" (
		application internet_name,
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "email_template.delete__internal"(
				application => "email_template.delete".application,
				name => "email_template.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- document_template...

drop function if exists "document_template.insert__internal";
create function "document_template.insert__internal" (
	content_path safe_path,
	name object_name,
	application internet_name,
	email_template object_name default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "document_template.insert__internal".application is null then
				"document_template.insert__internal".application = '';
			end if;
			if "document_template.insert__internal".name is null then
				"document_template.insert__internal".name = '';
			end if;
			if "document_template.insert__internal".content_path is null then
				"document_template.insert__internal".content_path = '';
			end if;
		-- (A) Check that required values are present
			if "document_template.insert__internal".content_path = '' then
				_status.errors = _status.errors ||
					ROW('document_template', _index,
						'Er moet een waarde ingevuld worden voor Content Path',
						'content_path'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM document_template D
			WHERE
				D.application = "document_template.insert__internal".application AND
				D.name = "document_template.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('document_template', _index,
						'Er is al een Document Template geregistreed met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "document_template.insert__internal"._check_only then
				INSERT INTO document_template (
					application,
					name,
					content_path,
					email_template
				) VALUES (
					"document_template.insert__internal"."application",
					"document_template.insert__internal"."name",
					"document_template.insert__internal"."content_path",
					"document_template.insert__internal"."email_template" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"document_template.insert__internal"('
		'safe_path,'
		'object_name,'
		'internet_name,'
		'object_name,'
		'integer,'
		'boolean)'
);

drop function if exists "document_template.insert";
	create function "document_template.insert" (
		content_path safe_path,
		name object_name,
		application internet_name,
		email_template object_name default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "document_template.insert__internal"(
				application => "document_template.insert".application,
				name => "document_template.insert".name,
				content_path => "document_template.insert".content_path,
				email_template => "document_template.insert".email_template);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "document_template.update__internal";
	create function "document_template.update__internal" (
		application internet_name,
		name object_name,
		content_path safe_path default null,
		email_template object_name default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM document_template D
			WHERE
				D.application = "document_template.update__internal".application AND
				D.name = "document_template.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('document_template', _index,
						'Er is geen Document Template gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE document_template D
			SET
				content_path = coalesce("document_template.update__internal".content_path, D.content_path),
				email_template = coalesce("document_template.update__internal".email_template, D.email_template)
			WHERE 
				D.application = "document_template.update__internal".application AND
				D.name = "document_template.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"document_template.update__internal"('
			'internet_name,'
			'object_name,'
			'safe_path,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "document_template.update";
	create function "document_template.update" (
		application internet_name,
		name object_name,
		content_path safe_path default null,
		email_template object_name default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "document_template.update__internal"(
				application => "document_template.update".application,
				name => "document_template.update".name,
				content_path => "document_template.update".content_path,
				email_template => "document_template.update".email_template);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "document_template.delete__internal";
	create function "document_template.delete__internal" (
		application internet_name,
		name object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM document_template D
			WHERE
				D.application = "document_template.delete__internal".application AND
				D.name = "document_template.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('document_template', _index,
						'Er is geen Document Template gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM document_template D
			WHERE 
				D.application = "document_template.delete__internal".application AND
				D.name = "document_template.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"document_template.delete__internal"('
			'internet_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "document_template.delete";
	create function "document_template.delete" (
		application internet_name,
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "document_template.delete__internal"(
				application => "document_template.delete".application,
				name => "document_template.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- document_request...

drop function if exists "document_request.insert__internal";
create function "document_request.insert__internal" (
	encrypted_access_token encrypted__access_token,
	request_timestamp timestamptz,
	uuid uuid,
	template object_name,
	application internet_name,
	encrypted_parameters text default null,
	render_timestamp timestamptz default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "document_request.insert__internal".application is null then
				"document_request.insert__internal".application = '';
			end if;
			if "document_request.insert__internal".template is null then
				"document_request.insert__internal".template = '';
			end if;
			if "document_request.insert__internal".encrypted_access_token is null then
				"document_request.insert__internal".encrypted_access_token = '';
			end if;
		-- (A) Check that required values are present
			if "document_request.insert__internal".application = '' then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er moet een waarde ingevuld worden voor Application',
						'application'
					)::_error_record;
			end if;
			if "document_request.insert__internal".template = '' then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er moet een waarde ingevuld worden voor Template',
						'template'
					)::_error_record;
			end if;
			if "document_request.insert__internal".request_timestamp is null then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er moet een waarde ingevuld worden voor Request Timestamp',
						'request_timestamp'
					)::_error_record;
			end if;
			if "document_request.insert__internal".encrypted_access_token = '' then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er moet een waarde ingevuld worden voor Encrypted Access Token',
						'encrypted_access_token'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM document_request D
			WHERE
				D.uuid = "document_request.insert__internal".uuid;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er is al een Document Request geregistreed met '
						'Uuid',
						'uuid'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "document_request.insert__internal"._check_only then
				INSERT INTO document_request (
					application,
					template,
					uuid,
					request_timestamp,
					encrypted_access_token,
					encrypted_parameters,
					render_timestamp
				) VALUES (
					"document_request.insert__internal"."application",
					"document_request.insert__internal"."template",
					"document_request.insert__internal"."uuid",
					"document_request.insert__internal"."request_timestamp",
					"document_request.insert__internal"."encrypted_access_token",
					"document_request.insert__internal"."encrypted_parameters",
					"document_request.insert__internal"."render_timestamp" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"document_request.insert__internal"('
		'encrypted__access_token,'
		'timestamptz,'
		'uuid,'
		'object_name,'
		'internet_name,'
		'text,'
		'timestamptz,'
		'integer,'
		'boolean)'
);

drop function if exists "document_request.insert";
	create function "document_request.insert" (
		encrypted_access_token encrypted__access_token,
		request_timestamp timestamptz,
		uuid uuid,
		template object_name,
		application internet_name,
		encrypted_parameters text default null,
		render_timestamp timestamptz default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "document_request.insert__internal"(
				application => "document_request.insert".application,
				template => "document_request.insert".template,
				uuid => "document_request.insert".uuid,
				request_timestamp => "document_request.insert".request_timestamp,
				encrypted_access_token => "document_request.insert".encrypted_access_token,
				encrypted_parameters => "document_request.insert".encrypted_parameters,
				render_timestamp => "document_request.insert".render_timestamp);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "document_request.update__internal";
	create function "document_request.update__internal" (
		uuid uuid,
		application internet_name default null,
		template object_name default null,
		request_timestamp timestamptz default null,
		encrypted_access_token encrypted__access_token default null,
		encrypted_parameters text default null,
		render_timestamp timestamptz default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM document_request D
			WHERE
				D.uuid = "document_request.update__internal".uuid;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er is geen Document Request gevonden met '
						'Uuid',
						'uuid'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE document_request D
			SET
				application = coalesce("document_request.update__internal".application, D.application),
				template = coalesce("document_request.update__internal".template, D.template),
				request_timestamp = coalesce("document_request.update__internal".request_timestamp, D.request_timestamp),
				encrypted_access_token = coalesce("document_request.update__internal".encrypted_access_token, D.encrypted_access_token),
				encrypted_parameters = coalesce("document_request.update__internal".encrypted_parameters, D.encrypted_parameters),
				render_timestamp = coalesce("document_request.update__internal".render_timestamp, D.render_timestamp)
			WHERE 
				D.uuid = "document_request.update__internal".uuid;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"document_request.update__internal"('
			'uuid,'
			'internet_name,'
			'object_name,'
			'timestamptz,'
			'encrypted__access_token,'
			'text,'
			'timestamptz,'
			'integer,'
			'boolean)'
	);

drop function if exists "document_request.update";
	create function "document_request.update" (
		uuid uuid,
		application internet_name default null,
		template object_name default null,
		request_timestamp timestamptz default null,
		encrypted_access_token encrypted__access_token default null,
		encrypted_parameters text default null,
		render_timestamp timestamptz default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "document_request.update__internal"(
				application => "document_request.update".application,
				template => "document_request.update".template,
				uuid => "document_request.update".uuid,
				request_timestamp => "document_request.update".request_timestamp,
				encrypted_access_token => "document_request.update".encrypted_access_token,
				encrypted_parameters => "document_request.update".encrypted_parameters,
				render_timestamp => "document_request.update".render_timestamp);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "document_request.delete__internal";
	create function "document_request.delete__internal" (
		uuid uuid,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM document_request D
			WHERE
				D.uuid = "document_request.delete__internal".uuid;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('document_request', _index,
						'Er is geen Document Request gevonden met '
						'Uuid',
						'uuid'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM document_request D
			WHERE 
				D.uuid = "document_request.delete__internal".uuid;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"document_request.delete__internal"('
			'uuid,'
			'integer,'
			'boolean)'
	);

drop function if exists "document_request.delete";
	create function "document_request.delete" (
		uuid uuid) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "document_request.delete__internal"(
				uuid => "document_request.delete".uuid);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- federation_procedure...

drop function if exists "federation_procedure.insert__internal";
create function "federation_procedure.insert__internal" (
	name object_name,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "federation_procedure.insert__internal".name is null then
				"federation_procedure.insert__internal".name = '';
			end if;
		-- (A) Check that required values are present
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM federation_procedure F
			WHERE
				F.name = "federation_procedure.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('federation_procedure', _index,
						'Er is al een Federation Procedure geregistreed met '
						'Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "federation_procedure.insert__internal"._check_only then
				INSERT INTO federation_procedure (
					name
				) VALUES (
					"federation_procedure.insert__internal"."name" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"federation_procedure.insert__internal"('
		'object_name,'
		'integer,'
		'boolean)'
);

drop function if exists "federation_procedure.insert";
	create function "federation_procedure.insert" (
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "federation_procedure.insert__internal"(
				name => "federation_procedure.insert".name);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "federation_procedure.delete__internal";
	create function "federation_procedure.delete__internal" (
		name object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM federation_procedure F
			WHERE
				F.name = "federation_procedure.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('federation_procedure', _index,
						'Er is geen Federation Procedure gevonden met '
						'Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM federation_procedure F
			WHERE 
				F.name = "federation_procedure.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"federation_procedure.delete__internal"('
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "federation_procedure.delete";
	create function "federation_procedure.delete" (
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "federation_procedure.delete__internal"(
				name => "federation_procedure.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- federation_procedure_parameter...

drop function if exists "federation_procedure_parameter.insert__internal";
create function "federation_procedure_parameter.insert__internal" (
	name scope_name,
	procedure object_name,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "federation_procedure_parameter.insert__internal".procedure is null then
				"federation_procedure_parameter.insert__internal".procedure = '';
			end if;
			if "federation_procedure_parameter.insert__internal".name is null then
				"federation_procedure_parameter.insert__internal".name = '';
			end if;
		-- (A) Check that required values are present
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM federation_procedure_parameter F
			WHERE
				F.procedure = "federation_procedure_parameter.insert__internal".procedure AND
				F.name = "federation_procedure_parameter.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('federation_procedure_parameter', _index,
						'Er is al een Federation Procedure Parameter geregistreed met '
						'Procedure, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "federation_procedure_parameter.insert__internal"._check_only then
				INSERT INTO federation_procedure_parameter (
					procedure,
					name
				) VALUES (
					"federation_procedure_parameter.insert__internal"."procedure",
					"federation_procedure_parameter.insert__internal"."name" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"federation_procedure_parameter.insert__internal"('
		'scope_name,'
		'object_name,'
		'integer,'
		'boolean)'
);

drop function if exists "federation_procedure_parameter.insert";
	create function "federation_procedure_parameter.insert" (
		name scope_name,
		procedure object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "federation_procedure_parameter.insert__internal"(
				procedure => "federation_procedure_parameter.insert".procedure,
				name => "federation_procedure_parameter.insert".name);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "federation_procedure_parameter.delete__internal";
	create function "federation_procedure_parameter.delete__internal" (
		procedure object_name,
		name scope_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM federation_procedure_parameter F
			WHERE
				F.procedure = "federation_procedure_parameter.delete__internal".procedure AND
				F.name = "federation_procedure_parameter.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('federation_procedure_parameter', _index,
						'Er is geen Federation Procedure Parameter gevonden met '
						'Procedure, Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM federation_procedure_parameter F
			WHERE 
				F.procedure = "federation_procedure_parameter.delete__internal".procedure AND
				F.name = "federation_procedure_parameter.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"federation_procedure_parameter.delete__internal"('
			'object_name,'
			'scope_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "federation_procedure_parameter.delete";
	create function "federation_procedure_parameter.delete" (
		procedure object_name,
		name scope_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "federation_procedure_parameter.delete__internal"(
				procedure => "federation_procedure_parameter.delete".procedure,
				name => "federation_procedure_parameter.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- identity_provider_service...

drop function if exists "identity_provider_service.insert__internal";
create function "identity_provider_service.insert__internal" (
	requires_email_verification bool,
	logo_url url,
	name provider_name,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "identity_provider_service.insert__internal".name is null then
				"identity_provider_service.insert__internal".name = '';
			end if;
			if "identity_provider_service.insert__internal".logo_url is null then
				"identity_provider_service.insert__internal".logo_url = '';
			end if;
		-- (A) Check that required values are present
			if "identity_provider_service.insert__internal".logo_url = '' then
				_status.errors = _status.errors ||
					ROW('identity_provider_service', _index,
						'Er moet een waarde ingevuld worden voor Logo Url',
						'logo_url'
					)::_error_record;
			end if;
			if "identity_provider_service.insert__internal".requires_email_verification is null then
				_status.errors = _status.errors ||
					ROW('identity_provider_service', _index,
						'Er moet een waarde ingevuld worden voor Requires Email Verification',
						'requires_email_verification'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM identity_provider_service I
			WHERE
				I.name = "identity_provider_service.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('identity_provider_service', _index,
						'Er is al een Identity Provider Service geregistreed met '
						'Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "identity_provider_service.insert__internal"._check_only then
				INSERT INTO identity_provider_service (
					name,
					logo_url,
					requires_email_verification
				) VALUES (
					"identity_provider_service.insert__internal"."name",
					"identity_provider_service.insert__internal"."logo_url",
					"identity_provider_service.insert__internal"."requires_email_verification" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"identity_provider_service.insert__internal"('
		'bool,'
		'url,'
		'provider_name,'
		'integer,'
		'boolean)'
);

drop function if exists "identity_provider_service.insert";
	create function "identity_provider_service.insert" (
		requires_email_verification bool,
		logo_url url,
		name provider_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "identity_provider_service.insert__internal"(
				name => "identity_provider_service.insert".name,
				logo_url => "identity_provider_service.insert".logo_url,
				requires_email_verification => "identity_provider_service.insert".requires_email_verification);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "identity_provider_service.update__internal";
	create function "identity_provider_service.update__internal" (
		name provider_name,
		logo_url url default null,
		requires_email_verification bool default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM identity_provider_service I
			WHERE
				I.name = "identity_provider_service.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('identity_provider_service', _index,
						'Er is geen Identity Provider Service gevonden met '
						'Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE identity_provider_service I
			SET
				logo_url = coalesce("identity_provider_service.update__internal".logo_url, I.logo_url),
				requires_email_verification = coalesce("identity_provider_service.update__internal".requires_email_verification, I.requires_email_verification)
			WHERE 
				I.name = "identity_provider_service.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"identity_provider_service.update__internal"('
			'provider_name,'
			'url,'
			'bool,'
			'integer,'
			'boolean)'
	);

drop function if exists "identity_provider_service.update";
	create function "identity_provider_service.update" (
		name provider_name,
		logo_url url default null,
		requires_email_verification bool default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "identity_provider_service.update__internal"(
				name => "identity_provider_service.update".name,
				logo_url => "identity_provider_service.update".logo_url,
				requires_email_verification => "identity_provider_service.update".requires_email_verification);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "identity_provider_service.delete__internal";
	create function "identity_provider_service.delete__internal" (
		name provider_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM identity_provider_service I
			WHERE
				I.name = "identity_provider_service.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('identity_provider_service', _index,
						'Er is geen Identity Provider Service gevonden met '
						'Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM identity_provider_service I
			WHERE 
				I.name = "identity_provider_service.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"identity_provider_service.delete__internal"('
			'provider_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "identity_provider_service.delete";
	create function "identity_provider_service.delete" (
		name provider_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "identity_provider_service.delete__internal"(
				name => "identity_provider_service.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- user_registry...

drop function if exists "user_registry.insert__internal";
create function "user_registry.insert__internal" (
	discovery_url url,
	tenant tenant_name,
	provider provider_name,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "user_registry.insert__internal".provider is null then
				"user_registry.insert__internal".provider = '';
			end if;
			if "user_registry.insert__internal".tenant is null then
				"user_registry.insert__internal".tenant = '';
			end if;
			if "user_registry.insert__internal".discovery_url is null then
				"user_registry.insert__internal".discovery_url = '';
			end if;
		-- (A) Check that required values are present
			if "user_registry.insert__internal".discovery_url = '' then
				_status.errors = _status.errors ||
					ROW('user_registry', _index,
						'Er moet een waarde ingevuld worden voor Discovery Url',
						'discovery_url'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM user_registry U
			WHERE
				U.provider = "user_registry.insert__internal".provider AND
				U.tenant = "user_registry.insert__internal".tenant;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('user_registry', _index,
						'Er is al een User Registry geregistreed met '
						'Provider, Tenant',
						'tenant'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "user_registry.insert__internal"._check_only then
				INSERT INTO user_registry (
					provider,
					tenant,
					discovery_url
				) VALUES (
					"user_registry.insert__internal"."provider",
					"user_registry.insert__internal"."tenant",
					"user_registry.insert__internal"."discovery_url" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"user_registry.insert__internal"('
		'url,'
		'tenant_name,'
		'provider_name,'
		'integer,'
		'boolean)'
);

drop function if exists "user_registry.insert";
	create function "user_registry.insert" (
		discovery_url url,
		tenant tenant_name,
		provider provider_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "user_registry.insert__internal"(
				provider => "user_registry.insert".provider,
				tenant => "user_registry.insert".tenant,
				discovery_url => "user_registry.insert".discovery_url);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "user_registry.update__internal";
	create function "user_registry.update__internal" (
		provider provider_name,
		tenant tenant_name,
		discovery_url url default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM user_registry U
			WHERE
				U.provider = "user_registry.update__internal".provider AND
				U.tenant = "user_registry.update__internal".tenant;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('user_registry', _index,
						'Er is geen User Registry gevonden met '
						'Provider, Tenant',
						'tenant'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE user_registry U
			SET
				discovery_url = coalesce("user_registry.update__internal".discovery_url, U.discovery_url)
			WHERE 
				U.provider = "user_registry.update__internal".provider AND
				U.tenant = "user_registry.update__internal".tenant;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"user_registry.update__internal"('
			'provider_name,'
			'tenant_name,'
			'url,'
			'integer,'
			'boolean)'
	);

drop function if exists "user_registry.update";
	create function "user_registry.update" (
		provider provider_name,
		tenant tenant_name,
		discovery_url url default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "user_registry.update__internal"(
				provider => "user_registry.update".provider,
				tenant => "user_registry.update".tenant,
				discovery_url => "user_registry.update".discovery_url);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "user_registry.delete__internal";
	create function "user_registry.delete__internal" (
		provider provider_name,
		tenant tenant_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM user_registry U
			WHERE
				U.provider = "user_registry.delete__internal".provider AND
				U.tenant = "user_registry.delete__internal".tenant;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('user_registry', _index,
						'Er is geen User Registry gevonden met '
						'Provider, Tenant',
						'tenant'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM user_registry U
			WHERE 
				U.provider = "user_registry.delete__internal".provider AND
				U.tenant = "user_registry.delete__internal".tenant;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"user_registry.delete__internal"('
			'provider_name,'
			'tenant_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "user_registry.delete";
	create function "user_registry.delete" (
		provider provider_name,
		tenant tenant_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "user_registry.delete__internal"(
				provider => "user_registry.delete".provider,
				tenant => "user_registry.delete".tenant);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- database_user_registry...

drop function if exists "database_user_registry.insert__internal";
create function "database_user_registry.insert__internal" (
	client_id encrypted__oidc_client_id,
	federation_procedure object_name,
	database object_name,
	tenant tenant_name,
	provider provider_name,
	client_secret encrypted__oidc_client_secret default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "database_user_registry.insert__internal".provider is null then
				"database_user_registry.insert__internal".provider = '';
			end if;
			if "database_user_registry.insert__internal".tenant is null then
				"database_user_registry.insert__internal".tenant = '';
			end if;
			if "database_user_registry.insert__internal".database is null then
				"database_user_registry.insert__internal".database = '';
			end if;
			if "database_user_registry.insert__internal".federation_procedure is null then
				"database_user_registry.insert__internal".federation_procedure = '';
			end if;
			if "database_user_registry.insert__internal".client_id is null then
				"database_user_registry.insert__internal".client_id = '';
			end if;
		-- (A) Check that required values are present
			if "database_user_registry.insert__internal".federation_procedure = '' then
				_status.errors = _status.errors ||
					ROW('database_user_registry', _index,
						'Er moet een waarde ingevuld worden voor Federation Procedure',
						'federation_procedure'
					)::_error_record;
			end if;
			if "database_user_registry.insert__internal".client_id = '' then
				_status.errors = _status.errors ||
					ROW('database_user_registry', _index,
						'Er moet een waarde ingevuld worden voor Client Id',
						'client_id'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM database_user_registry D
			WHERE
				D.provider = "database_user_registry.insert__internal".provider AND
				D.tenant = "database_user_registry.insert__internal".tenant AND
				D.database = "database_user_registry.insert__internal".database;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('database_user_registry', _index,
						'Er is al een Database User Registry geregistreed met '
						'Provider, Tenant, Database',
						'database'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "database_user_registry.insert__internal"._check_only then
				INSERT INTO database_user_registry (
					provider,
					tenant,
					database,
					federation_procedure,
					client_id,
					client_secret
				) VALUES (
					"database_user_registry.insert__internal"."provider",
					"database_user_registry.insert__internal"."tenant",
					"database_user_registry.insert__internal"."database",
					"database_user_registry.insert__internal"."federation_procedure",
					"database_user_registry.insert__internal"."client_id",
					"database_user_registry.insert__internal"."client_secret" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"database_user_registry.insert__internal"('
		'encrypted__oidc_client_id,'
		'object_name,'
		'object_name,'
		'tenant_name,'
		'provider_name,'
		'encrypted__oidc_client_secret,'
		'integer,'
		'boolean)'
);

drop function if exists "database_user_registry.insert";
	create function "database_user_registry.insert" (
		client_id encrypted__oidc_client_id,
		federation_procedure object_name,
		database object_name,
		tenant tenant_name,
		provider provider_name,
		client_secret encrypted__oidc_client_secret default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "database_user_registry.insert__internal"(
				provider => "database_user_registry.insert".provider,
				tenant => "database_user_registry.insert".tenant,
				database => "database_user_registry.insert".database,
				federation_procedure => "database_user_registry.insert".federation_procedure,
				client_id => "database_user_registry.insert".client_id,
				client_secret => "database_user_registry.insert".client_secret);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "database_user_registry.update__internal";
	create function "database_user_registry.update__internal" (
		provider provider_name,
		tenant tenant_name,
		database object_name,
		federation_procedure object_name default null,
		client_id encrypted__oidc_client_id default null,
		client_secret encrypted__oidc_client_secret default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM database_user_registry D
			WHERE
				D.provider = "database_user_registry.update__internal".provider AND
				D.tenant = "database_user_registry.update__internal".tenant AND
				D.database = "database_user_registry.update__internal".database;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('database_user_registry', _index,
						'Er is geen Database User Registry gevonden met '
						'Provider, Tenant, Database',
						'database'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE database_user_registry D
			SET
				federation_procedure = coalesce("database_user_registry.update__internal".federation_procedure, D.federation_procedure),
				client_id = coalesce("database_user_registry.update__internal".client_id, D.client_id),
				client_secret = coalesce("database_user_registry.update__internal".client_secret, D.client_secret)
			WHERE 
				D.provider = "database_user_registry.update__internal".provider AND
				D.tenant = "database_user_registry.update__internal".tenant AND
				D.database = "database_user_registry.update__internal".database;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"database_user_registry.update__internal"('
			'provider_name,'
			'tenant_name,'
			'object_name,'
			'object_name,'
			'encrypted__oidc_client_id,'
			'encrypted__oidc_client_secret,'
			'integer,'
			'boolean)'
	);

drop function if exists "database_user_registry.update";
	create function "database_user_registry.update" (
		provider provider_name,
		tenant tenant_name,
		database object_name,
		federation_procedure object_name default null,
		client_id encrypted__oidc_client_id default null,
		client_secret encrypted__oidc_client_secret default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "database_user_registry.update__internal"(
				provider => "database_user_registry.update".provider,
				tenant => "database_user_registry.update".tenant,
				database => "database_user_registry.update".database,
				federation_procedure => "database_user_registry.update".federation_procedure,
				client_id => "database_user_registry.update".client_id,
				client_secret => "database_user_registry.update".client_secret);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "database_user_registry.delete__internal";
	create function "database_user_registry.delete__internal" (
		provider provider_name,
		tenant tenant_name,
		database object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM database_user_registry D
			WHERE
				D.provider = "database_user_registry.delete__internal".provider AND
				D.tenant = "database_user_registry.delete__internal".tenant AND
				D.database = "database_user_registry.delete__internal".database;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('database_user_registry', _index,
						'Er is geen Database User Registry gevonden met '
						'Provider, Tenant, Database',
						'database'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM database_user_registry D
			WHERE 
				D.provider = "database_user_registry.delete__internal".provider AND
				D.tenant = "database_user_registry.delete__internal".tenant AND
				D.database = "database_user_registry.delete__internal".database;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"database_user_registry.delete__internal"('
			'provider_name,'
			'tenant_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "database_user_registry.delete";
	create function "database_user_registry.delete" (
		provider provider_name,
		tenant tenant_name,
		database object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "database_user_registry.delete__internal"(
				provider => "database_user_registry.delete".provider,
				tenant => "database_user_registry.delete".tenant,
				database => "database_user_registry.delete".database);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- account...

drop function if exists "account.insert__internal";
create function "account.insert__internal" (
	email_verified bool,
	sub encrypted__oidc_sub,
	id postgres_role,
	username username default null,
	email encrypted__email default null,
	deletion_timestamp timestamptz default null,
	provider provider_name default null,
	tenant tenant_name default null,
	api_key api_key default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "account.insert__internal".id is null then
				"account.insert__internal".id = '';
			end if;
			if "account.insert__internal".sub is null then
				"account.insert__internal".sub = '';
			end if;
		-- (A) Check that required values are present
			if "account.insert__internal".sub = '' then
				_status.errors = _status.errors ||
					ROW('account', _index,
						'Er moet een waarde ingevuld worden voor Sub',
						'sub'
					)::_error_record;
			end if;
			if "account.insert__internal".email_verified is null then
				_status.errors = _status.errors ||
					ROW('account', _index,
						'Er moet een waarde ingevuld worden voor Email Verified',
						'email_verified'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM account A
			WHERE
				A.id = "account.insert__internal".id;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('account', _index,
						'Er is al een Account geregistreed met '
						'Id',
						'id'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "account.insert__internal"._check_only then
				INSERT INTO account (
					id,
					sub,
					username,
					email,
					email_verified,
					deletion_timestamp,
					provider,
					tenant,
					api_key
				) VALUES (
					"account.insert__internal"."id",
					"account.insert__internal"."sub",
					"account.insert__internal"."username",
					"account.insert__internal"."email",
					"account.insert__internal"."email_verified",
					"account.insert__internal"."deletion_timestamp",
					"account.insert__internal"."provider",
					"account.insert__internal"."tenant",
					"account.insert__internal"."api_key" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"account.insert__internal"('
		'bool,'
		'encrypted__oidc_sub,'
		'postgres_role,'
		'username,'
		'encrypted__email,'
		'timestamptz,'
		'provider_name,'
		'tenant_name,'
		'api_key,'
		'integer,'
		'boolean)'
);

drop function if exists "account.insert";
	create function "account.insert" (
		email_verified bool,
		sub encrypted__oidc_sub,
		id postgres_role,
		username username default null,
		email encrypted__email default null,
		deletion_timestamp timestamptz default null,
		provider provider_name default null,
		tenant tenant_name default null,
		api_key api_key default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "account.insert__internal"(
				id => "account.insert".id,
				sub => "account.insert".sub,
				username => "account.insert".username,
				email => "account.insert".email,
				email_verified => "account.insert".email_verified,
				deletion_timestamp => "account.insert".deletion_timestamp,
				provider => "account.insert".provider,
				tenant => "account.insert".tenant,
				api_key => "account.insert".api_key);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "account.update__internal";
	create function "account.update__internal" (
		id postgres_role,
		sub encrypted__oidc_sub default null,
		username username default null,
		email encrypted__email default null,
		email_verified bool default null,
		deletion_timestamp timestamptz default null,
		provider provider_name default null,
		tenant tenant_name default null,
		api_key api_key default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM account A
			WHERE
				A.id = "account.update__internal".id;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('account', _index,
						'Er is geen Account gevonden met '
						'Id',
						'id'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE account A
			SET
				sub = coalesce("account.update__internal".sub, A.sub),
				username = coalesce("account.update__internal".username, A.username),
				email = coalesce("account.update__internal".email, A.email),
				email_verified = coalesce("account.update__internal".email_verified, A.email_verified),
				deletion_timestamp = coalesce("account.update__internal".deletion_timestamp, A.deletion_timestamp),
				provider = coalesce("account.update__internal".provider, A.provider),
				tenant = coalesce("account.update__internal".tenant, A.tenant),
				api_key = coalesce("account.update__internal".api_key, A.api_key)
			WHERE 
				A.id = "account.update__internal".id;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"account.update__internal"('
			'postgres_role,'
			'encrypted__oidc_sub,'
			'username,'
			'encrypted__email,'
			'bool,'
			'timestamptz,'
			'provider_name,'
			'tenant_name,'
			'api_key,'
			'integer,'
			'boolean)'
	);

drop function if exists "account.update";
	create function "account.update" (
		id postgres_role,
		sub encrypted__oidc_sub default null,
		username username default null,
		email encrypted__email default null,
		email_verified bool default null,
		deletion_timestamp timestamptz default null,
		provider provider_name default null,
		tenant tenant_name default null,
		api_key api_key default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "account.update__internal"(
				id => "account.update".id,
				sub => "account.update".sub,
				username => "account.update".username,
				email => "account.update".email,
				email_verified => "account.update".email_verified,
				deletion_timestamp => "account.update".deletion_timestamp,
				provider => "account.update".provider,
				tenant => "account.update".tenant,
				api_key => "account.update".api_key);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "account.delete__internal";
	create function "account.delete__internal" (
		id postgres_role,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM account A
			WHERE
				A.id = "account.delete__internal".id;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('account', _index,
						'Er is geen Account gevonden met '
						'Id',
						'id'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM account A
			WHERE 
				A.id = "account.delete__internal".id;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"account.delete__internal"('
			'postgres_role,'
			'integer,'
			'boolean)'
	);

drop function if exists "account.delete";
	create function "account.delete" (
		id postgres_role) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "account.delete__internal"(
				id => "account.delete".id);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- validated_ip_address...

drop function if exists "validated_ip_address.insert__internal";
create function "validated_ip_address.insert__internal" (
	last_authentication_timestamp timestamptz,
	first_authentication_timestamp timestamptz,
	encrypted_salted_ip_address encrypted__salted_ip,
	uuid uuid,
	account postgres_role,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "validated_ip_address.insert__internal".account is null then
				"validated_ip_address.insert__internal".account = '';
			end if;
			if "validated_ip_address.insert__internal".encrypted_salted_ip_address is null then
				"validated_ip_address.insert__internal".encrypted_salted_ip_address = '';
			end if;
		-- (A) Check that required values are present
			if "validated_ip_address.insert__internal".account = '' then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er moet een waarde ingevuld worden voor Account',
						'account'
					)::_error_record;
			end if;
			if "validated_ip_address.insert__internal".encrypted_salted_ip_address = '' then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er moet een waarde ingevuld worden voor Encrypted Salted Ip Address',
						'encrypted_salted_ip_address'
					)::_error_record;
			end if;
			if "validated_ip_address.insert__internal".first_authentication_timestamp is null then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er moet een waarde ingevuld worden voor First Authentication Timestamp',
						'first_authentication_timestamp'
					)::_error_record;
			end if;
			if "validated_ip_address.insert__internal".last_authentication_timestamp is null then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er moet een waarde ingevuld worden voor Last Authentication Timestamp',
						'last_authentication_timestamp'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM validated_ip_address V
			WHERE
				V.uuid = "validated_ip_address.insert__internal".uuid;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er is al een Validated Ip Address geregistreed met '
						'Uuid',
						'uuid'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "validated_ip_address.insert__internal"._check_only then
				INSERT INTO validated_ip_address (
					account,
					uuid,
					encrypted_salted_ip_address,
					first_authentication_timestamp,
					last_authentication_timestamp
				) VALUES (
					"validated_ip_address.insert__internal"."account",
					"validated_ip_address.insert__internal"."uuid",
					"validated_ip_address.insert__internal"."encrypted_salted_ip_address",
					"validated_ip_address.insert__internal"."first_authentication_timestamp",
					"validated_ip_address.insert__internal"."last_authentication_timestamp" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"validated_ip_address.insert__internal"('
		'timestamptz,'
		'timestamptz,'
		'encrypted__salted_ip,'
		'uuid,'
		'postgres_role,'
		'integer,'
		'boolean)'
);

drop function if exists "validated_ip_address.insert";
	create function "validated_ip_address.insert" (
		last_authentication_timestamp timestamptz,
		first_authentication_timestamp timestamptz,
		encrypted_salted_ip_address encrypted__salted_ip,
		uuid uuid,
		account postgres_role) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "validated_ip_address.insert__internal"(
				account => "validated_ip_address.insert".account,
				uuid => "validated_ip_address.insert".uuid,
				encrypted_salted_ip_address => "validated_ip_address.insert".encrypted_salted_ip_address,
				first_authentication_timestamp => "validated_ip_address.insert".first_authentication_timestamp,
				last_authentication_timestamp => "validated_ip_address.insert".last_authentication_timestamp);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "validated_ip_address.update__internal";
	create function "validated_ip_address.update__internal" (
		uuid uuid,
		account postgres_role default null,
		encrypted_salted_ip_address encrypted__salted_ip default null,
		first_authentication_timestamp timestamptz default null,
		last_authentication_timestamp timestamptz default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM validated_ip_address V
			WHERE
				V.uuid = "validated_ip_address.update__internal".uuid;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er is geen Validated Ip Address gevonden met '
						'Uuid',
						'uuid'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE validated_ip_address V
			SET
				account = coalesce("validated_ip_address.update__internal".account, V.account),
				encrypted_salted_ip_address = coalesce("validated_ip_address.update__internal".encrypted_salted_ip_address, V.encrypted_salted_ip_address),
				first_authentication_timestamp = coalesce("validated_ip_address.update__internal".first_authentication_timestamp, V.first_authentication_timestamp),
				last_authentication_timestamp = coalesce("validated_ip_address.update__internal".last_authentication_timestamp, V.last_authentication_timestamp)
			WHERE 
				V.uuid = "validated_ip_address.update__internal".uuid;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"validated_ip_address.update__internal"('
			'uuid,'
			'postgres_role,'
			'encrypted__salted_ip,'
			'timestamptz,'
			'timestamptz,'
			'integer,'
			'boolean)'
	);

drop function if exists "validated_ip_address.update";
	create function "validated_ip_address.update" (
		uuid uuid,
		account postgres_role default null,
		encrypted_salted_ip_address encrypted__salted_ip default null,
		first_authentication_timestamp timestamptz default null,
		last_authentication_timestamp timestamptz default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "validated_ip_address.update__internal"(
				account => "validated_ip_address.update".account,
				uuid => "validated_ip_address.update".uuid,
				encrypted_salted_ip_address => "validated_ip_address.update".encrypted_salted_ip_address,
				first_authentication_timestamp => "validated_ip_address.update".first_authentication_timestamp,
				last_authentication_timestamp => "validated_ip_address.update".last_authentication_timestamp);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "validated_ip_address.delete__internal";
	create function "validated_ip_address.delete__internal" (
		uuid uuid,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM validated_ip_address V
			WHERE
				V.uuid = "validated_ip_address.delete__internal".uuid;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('validated_ip_address', _index,
						'Er is geen Validated Ip Address gevonden met '
						'Uuid',
						'uuid'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM validated_ip_address V
			WHERE 
				V.uuid = "validated_ip_address.delete__internal".uuid;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"validated_ip_address.delete__internal"('
			'uuid,'
			'integer,'
			'boolean)'
	);

drop function if exists "validated_ip_address.delete";
	create function "validated_ip_address.delete" (
		uuid uuid) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "validated_ip_address.delete__internal"(
				uuid => "validated_ip_address.delete".uuid);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- security_event...

drop function if exists "security_event.insert__internal";
create function "security_event.insert__internal" (
	unlock_code unlock_code,
	unlock_key uuid,
	email_template object_name,
	wrong_key_attempt_count current_attempt_count,
	creation_timestamp timestamptz,
	event_lock uuid,
	application internet_name,
	account postgres_role default null,
	fake_account encrypted__jaaql_username default null,
	unlock_timestamp timestamptz default null,
	finish_timestamp timestamptz default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "security_event.insert__internal".application is null then
				"security_event.insert__internal".application = '';
			end if;
			if "security_event.insert__internal".email_template is null then
				"security_event.insert__internal".email_template = '';
			end if;
			if "security_event.insert__internal".unlock_code is null then
				"security_event.insert__internal".unlock_code = '';
			end if;
		-- (A) Check that required values are present
			if "security_event.insert__internal".creation_timestamp is null then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er moet een waarde ingevuld worden voor Creation Timestamp',
						'creation_timestamp'
					)::_error_record;
			end if;
			if "security_event.insert__internal".wrong_key_attempt_count is null then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er moet een waarde ingevuld worden voor Wrong Key Attempt Count',
						'wrong_key_attempt_count'
					)::_error_record;
			end if;
			if "security_event.insert__internal".email_template = '' then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er moet een waarde ingevuld worden voor Email Template',
						'email_template'
					)::_error_record;
			end if;
			if "security_event.insert__internal".unlock_key is null then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er moet een waarde ingevuld worden voor Unlock Key',
						'unlock_key'
					)::_error_record;
			end if;
			if "security_event.insert__internal".unlock_code = '' then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er moet een waarde ingevuld worden voor Unlock Code',
						'unlock_code'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM security_event S
			WHERE
				S.application = "security_event.insert__internal".application AND
				S.event_lock = "security_event.insert__internal".event_lock;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er is al een Security Event geregistreed met '
						'Application, Event Lock',
						'event_lock'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "security_event.insert__internal"._check_only then
				INSERT INTO security_event (
					application,
					event_lock,
					creation_timestamp,
					wrong_key_attempt_count,
					email_template,
					account,
					fake_account,
					unlock_key,
					unlock_code,
					unlock_timestamp,
					finish_timestamp
				) VALUES (
					"security_event.insert__internal"."application",
					"security_event.insert__internal"."event_lock",
					"security_event.insert__internal"."creation_timestamp",
					"security_event.insert__internal"."wrong_key_attempt_count",
					"security_event.insert__internal"."email_template",
					"security_event.insert__internal"."account",
					"security_event.insert__internal"."fake_account",
					"security_event.insert__internal"."unlock_key",
					"security_event.insert__internal"."unlock_code",
					"security_event.insert__internal"."unlock_timestamp",
					"security_event.insert__internal"."finish_timestamp" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"security_event.insert__internal"('
		'unlock_code,'
		'uuid,'
		'object_name,'
		'current_attempt_count,'
		'timestamptz,'
		'uuid,'
		'internet_name,'
		'postgres_role,'
		'encrypted__jaaql_username,'
		'timestamptz,'
		'timestamptz,'
		'integer,'
		'boolean)'
);

drop function if exists "security_event.insert";
	create function "security_event.insert" (
		unlock_code unlock_code,
		unlock_key uuid,
		email_template object_name,
		wrong_key_attempt_count current_attempt_count,
		creation_timestamp timestamptz,
		event_lock uuid,
		application internet_name,
		account postgres_role default null,
		fake_account encrypted__jaaql_username default null,
		unlock_timestamp timestamptz default null,
		finish_timestamp timestamptz default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "security_event.insert__internal"(
				application => "security_event.insert".application,
				event_lock => "security_event.insert".event_lock,
				creation_timestamp => "security_event.insert".creation_timestamp,
				wrong_key_attempt_count => "security_event.insert".wrong_key_attempt_count,
				email_template => "security_event.insert".email_template,
				account => "security_event.insert".account,
				fake_account => "security_event.insert".fake_account,
				unlock_key => "security_event.insert".unlock_key,
				unlock_code => "security_event.insert".unlock_code,
				unlock_timestamp => "security_event.insert".unlock_timestamp,
				finish_timestamp => "security_event.insert".finish_timestamp);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "security_event.update__internal";
	create function "security_event.update__internal" (
		application internet_name,
		event_lock uuid,
		creation_timestamp timestamptz default null,
		wrong_key_attempt_count current_attempt_count default null,
		email_template object_name default null,
		account postgres_role default null,
		fake_account encrypted__jaaql_username default null,
		unlock_key uuid default null,
		unlock_code unlock_code default null,
		unlock_timestamp timestamptz default null,
		finish_timestamp timestamptz default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM security_event S
			WHERE
				S.application = "security_event.update__internal".application AND
				S.event_lock = "security_event.update__internal".event_lock;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er is geen Security Event gevonden met '
						'Application, Event Lock',
						'event_lock'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE security_event S
			SET
				creation_timestamp = coalesce("security_event.update__internal".creation_timestamp, S.creation_timestamp),
				wrong_key_attempt_count = coalesce("security_event.update__internal".wrong_key_attempt_count, S.wrong_key_attempt_count),
				email_template = coalesce("security_event.update__internal".email_template, S.email_template),
				account = coalesce("security_event.update__internal".account, S.account),
				fake_account = coalesce("security_event.update__internal".fake_account, S.fake_account),
				unlock_key = coalesce("security_event.update__internal".unlock_key, S.unlock_key),
				unlock_code = coalesce("security_event.update__internal".unlock_code, S.unlock_code),
				unlock_timestamp = coalesce("security_event.update__internal".unlock_timestamp, S.unlock_timestamp),
				finish_timestamp = coalesce("security_event.update__internal".finish_timestamp, S.finish_timestamp)
			WHERE 
				S.application = "security_event.update__internal".application AND
				S.event_lock = "security_event.update__internal".event_lock;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"security_event.update__internal"('
			'internet_name,'
			'uuid,'
			'timestamptz,'
			'current_attempt_count,'
			'object_name,'
			'postgres_role,'
			'encrypted__jaaql_username,'
			'uuid,'
			'unlock_code,'
			'timestamptz,'
			'timestamptz,'
			'integer,'
			'boolean)'
	);

drop function if exists "security_event.update";
	create function "security_event.update" (
		application internet_name,
		event_lock uuid,
		creation_timestamp timestamptz default null,
		wrong_key_attempt_count current_attempt_count default null,
		email_template object_name default null,
		account postgres_role default null,
		fake_account encrypted__jaaql_username default null,
		unlock_key uuid default null,
		unlock_code unlock_code default null,
		unlock_timestamp timestamptz default null,
		finish_timestamp timestamptz default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "security_event.update__internal"(
				application => "security_event.update".application,
				event_lock => "security_event.update".event_lock,
				creation_timestamp => "security_event.update".creation_timestamp,
				wrong_key_attempt_count => "security_event.update".wrong_key_attempt_count,
				email_template => "security_event.update".email_template,
				account => "security_event.update".account,
				fake_account => "security_event.update".fake_account,
				unlock_key => "security_event.update".unlock_key,
				unlock_code => "security_event.update".unlock_code,
				unlock_timestamp => "security_event.update".unlock_timestamp,
				finish_timestamp => "security_event.update".finish_timestamp);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "security_event.delete__internal";
	create function "security_event.delete__internal" (
		application internet_name,
		event_lock uuid,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM security_event S
			WHERE
				S.application = "security_event.delete__internal".application AND
				S.event_lock = "security_event.delete__internal".event_lock;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('security_event', _index,
						'Er is geen Security Event gevonden met '
						'Application, Event Lock',
						'event_lock'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM security_event S
			WHERE 
				S.application = "security_event.delete__internal".application AND
				S.event_lock = "security_event.delete__internal".event_lock;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"security_event.delete__internal"('
			'internet_name,'
			'uuid,'
			'integer,'
			'boolean)'
	);

drop function if exists "security_event.delete";
	create function "security_event.delete" (
		application internet_name,
		event_lock uuid) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "security_event.delete__internal"(
				application => "security_event.delete".application,
				event_lock => "security_event.delete".event_lock);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- handled_error...

drop function if exists "handled_error.insert__internal";
create function "handled_error.insert__internal" (
	description text,
	is_arrayed bool,
	code error_code,
	error_name error_name default null,
	table_name object_name default null,
	table_name_required bool default null,
	table_possible bool default null,
	column_possible bool default null,
	has_associated_set bool default null,
	column_name object_name default null,
	http_response_code http_response_code default null,
	message text default null,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
		-- (A) Check that required values are present
			if "handled_error.insert__internal".is_arrayed is null then
				_status.errors = _status.errors ||
					ROW('handled_error', _index,
						'Er moet een waarde ingevuld worden voor Is Arrayed',
						'is_arrayed'
					)::_error_record;
			end if;
			if "handled_error.insert__internal".description is null then
				_status.errors = _status.errors ||
					ROW('handled_error', _index,
						'Er moet een waarde ingevuld worden voor Description',
						'description'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM handled_error H
			WHERE
				H.code = "handled_error.insert__internal".code;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('handled_error', _index,
						'Er is al een Handled Error geregistreed met '
						'Code',
						'code'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "handled_error.insert__internal"._check_only then
				INSERT INTO handled_error (
					code,
					error_name,
					is_arrayed,
					table_name,
					table_name_required,
					table_possible,
					column_possible,
					has_associated_set,
					column_name,
					http_response_code,
					message,
					description
				) VALUES (
					"handled_error.insert__internal"."code",
					"handled_error.insert__internal"."error_name",
					"handled_error.insert__internal"."is_arrayed",
					"handled_error.insert__internal"."table_name",
					"handled_error.insert__internal"."table_name_required",
					"handled_error.insert__internal"."table_possible",
					"handled_error.insert__internal"."column_possible",
					"handled_error.insert__internal"."has_associated_set",
					"handled_error.insert__internal"."column_name",
					"handled_error.insert__internal"."http_response_code",
					"handled_error.insert__internal"."message",
					"handled_error.insert__internal"."description" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"handled_error.insert__internal"('
		'text,'
		'bool,'
		'error_code,'
		'error_name,'
		'object_name,'
		'bool,'
		'bool,'
		'bool,'
		'bool,'
		'object_name,'
		'http_response_code,'
		'text,'
		'integer,'
		'boolean)'
);

drop function if exists "handled_error.insert";
	create function "handled_error.insert" (
		description text,
		is_arrayed bool,
		code error_code,
		error_name error_name default null,
		table_name object_name default null,
		table_name_required bool default null,
		table_possible bool default null,
		column_possible bool default null,
		has_associated_set bool default null,
		column_name object_name default null,
		http_response_code http_response_code default null,
		message text default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "handled_error.insert__internal"(
				code => "handled_error.insert".code,
				error_name => "handled_error.insert".error_name,
				is_arrayed => "handled_error.insert".is_arrayed,
				table_name => "handled_error.insert".table_name,
				table_name_required => "handled_error.insert".table_name_required,
				table_possible => "handled_error.insert".table_possible,
				column_possible => "handled_error.insert".column_possible,
				has_associated_set => "handled_error.insert".has_associated_set,
				column_name => "handled_error.insert".column_name,
				http_response_code => "handled_error.insert".http_response_code,
				message => "handled_error.insert".message,
				description => "handled_error.insert".description);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "handled_error.update__internal";
	create function "handled_error.update__internal" (
		code error_code,
		error_name error_name default null,
		is_arrayed bool default null,
		table_name object_name default null,
		table_name_required bool default null,
		table_possible bool default null,
		column_possible bool default null,
		has_associated_set bool default null,
		column_name object_name default null,
		http_response_code http_response_code default null,
		message text default null,
		description text default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM handled_error H
			WHERE
				H.code = "handled_error.update__internal".code;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('handled_error', _index,
						'Er is geen Handled Error gevonden met '
						'Code',
						'code'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE handled_error H
			SET
				error_name = coalesce("handled_error.update__internal".error_name, H.error_name),
				is_arrayed = coalesce("handled_error.update__internal".is_arrayed, H.is_arrayed),
				table_name = coalesce("handled_error.update__internal".table_name, H.table_name),
				table_name_required = coalesce("handled_error.update__internal".table_name_required, H.table_name_required),
				table_possible = coalesce("handled_error.update__internal".table_possible, H.table_possible),
				column_possible = coalesce("handled_error.update__internal".column_possible, H.column_possible),
				has_associated_set = coalesce("handled_error.update__internal".has_associated_set, H.has_associated_set),
				column_name = coalesce("handled_error.update__internal".column_name, H.column_name),
				http_response_code = coalesce("handled_error.update__internal".http_response_code, H.http_response_code),
				message = coalesce("handled_error.update__internal".message, H.message),
				description = coalesce("handled_error.update__internal".description, H.description)
			WHERE 
				H.code = "handled_error.update__internal".code;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"handled_error.update__internal"('
			'error_code,'
			'error_name,'
			'bool,'
			'object_name,'
			'bool,'
			'bool,'
			'bool,'
			'bool,'
			'object_name,'
			'http_response_code,'
			'text,'
			'text,'
			'integer,'
			'boolean)'
	);

drop function if exists "handled_error.update";
	create function "handled_error.update" (
		code error_code,
		error_name error_name default null,
		is_arrayed bool default null,
		table_name object_name default null,
		table_name_required bool default null,
		table_possible bool default null,
		column_possible bool default null,
		has_associated_set bool default null,
		column_name object_name default null,
		http_response_code http_response_code default null,
		message text default null,
		description text default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "handled_error.update__internal"(
				code => "handled_error.update".code,
				error_name => "handled_error.update".error_name,
				is_arrayed => "handled_error.update".is_arrayed,
				table_name => "handled_error.update".table_name,
				table_name_required => "handled_error.update".table_name_required,
				table_possible => "handled_error.update".table_possible,
				column_possible => "handled_error.update".column_possible,
				has_associated_set => "handled_error.update".has_associated_set,
				column_name => "handled_error.update".column_name,
				http_response_code => "handled_error.update".http_response_code,
				message => "handled_error.update".message,
				description => "handled_error.update".description);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "handled_error.delete__internal";
	create function "handled_error.delete__internal" (
		code error_code,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM handled_error H
			WHERE
				H.code = "handled_error.delete__internal".code;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('handled_error', _index,
						'Er is geen Handled Error gevonden met '
						'Code',
						'code'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM handled_error H
			WHERE 
				H.code = "handled_error.delete__internal".code;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"handled_error.delete__internal"('
			'error_code,'
			'integer,'
			'boolean)'
	);

drop function if exists "handled_error.delete";
	create function "handled_error.delete" (
		code error_code) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "handled_error.delete__internal"(
				code => "handled_error.delete".code);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
-- pg_base_exception...

-- pg_error_class...

-- pg_exception...

-- remote_procedure...

drop function if exists "remote_procedure.insert__internal";
create function "remote_procedure.insert__internal" (
	access procedure_access_level,
	command text,
	name object_name,
	application internet_name,
	_index integer default null,
	_check_only boolean default false ) returns _status_record as
$$
DECLARE
	_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
	_count integer not null = 0;
BEGIN
		-- (1) Coercion
			if "remote_procedure.insert__internal".application is null then
				"remote_procedure.insert__internal".application = '';
			end if;
			if "remote_procedure.insert__internal".name is null then
				"remote_procedure.insert__internal".name = '';
			end if;
			if "remote_procedure.insert__internal".access is null then
				"remote_procedure.insert__internal".access = '';
			end if;
		-- (A) Check that required values are present
			if "remote_procedure.insert__internal".command is null then
				_status.errors = _status.errors ||
					ROW('remote_procedure', _index,
						'Er moet een waarde ingevuld worden voor Command',
						'command'
					)::_error_record;
			end if;
			if "remote_procedure.insert__internal".access = '' then
				_status.errors = _status.errors ||
					ROW('remote_procedure', _index,
						'Er moet een waarde ingevuld worden voor Access',
						'access'
					)::_error_record;
			end if;
		-- (D) Check that there is no record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM remote_procedure R
			WHERE
				R.application = "remote_procedure.insert__internal".application AND
				R.name = "remote_procedure.insert__internal".name;
			if _count <> 0 then
				_status.errors = _status.errors ||
					ROW('remote_procedure', _index,
						'Er is al een Remote Procedure geregistreed met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			-- Now do the work
			if not "remote_procedure.insert__internal"._check_only then
				INSERT INTO remote_procedure (
					application,
					name,
					command,
					access
				) VALUES (
					"remote_procedure.insert__internal"."application",
					"remote_procedure.insert__internal"."name",
					"remote_procedure.insert__internal"."command",
					"remote_procedure.insert__internal"."access" );
				_status.result = 1;
			end if;
	return _status;
END;
$$ language plpgsql security definer;
select * from plpgsql_check_function(
	'"remote_procedure.insert__internal"('
		'procedure_access_level,'
		'text,'
		'object_name,'
		'internet_name,'
		'integer,'
		'boolean)'
);

drop function if exists "remote_procedure.insert";
	create function "remote_procedure.insert" (
		access procedure_access_level,
		command text,
		name object_name,
		application internet_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "remote_procedure.insert__internal"(
				application => "remote_procedure.insert".application,
				name => "remote_procedure.insert".name,
				command => "remote_procedure.insert".command,
				access => "remote_procedure.insert".access);

		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "remote_procedure.update__internal";
	create function "remote_procedure.update__internal" (
		application internet_name,
		name object_name,
		command text default null,
		access procedure_access_level default null,
		_index integer default null,
		_check_only boolean default false) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM remote_procedure R
			WHERE
				R.application = "remote_procedure.update__internal".application AND
				R.name = "remote_procedure.update__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('remote_procedure', _index,
						'Er is geen Remote Procedure gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;
			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			UPDATE remote_procedure R
			SET
				command = coalesce("remote_procedure.update__internal".command, R.command),
				access = coalesce("remote_procedure.update__internal".access, R.access)
			WHERE 
				R.application = "remote_procedure.update__internal".application AND
				R.name = "remote_procedure.update__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"remote_procedure.update__internal"('
			'internet_name,'
			'object_name,'
			'text,'
			'procedure_access_level,'
			'integer,'
			'boolean)'
	);

drop function if exists "remote_procedure.update";
	create function "remote_procedure.update" (
		application internet_name,
		name object_name,
		command text default null,
		access procedure_access_level default null) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "remote_procedure.update__internal"(
				application => "remote_procedure.update".application,
				name => "remote_procedure.update".name,
				command => "remote_procedure.update".command,
				access => "remote_procedure.update".access);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;
drop function if exists "remote_procedure.delete__internal";
	create function "remote_procedure.delete__internal" (
		application internet_name,
		name object_name,
		_index integer default null,
		_check_only boolean default false ) returns _status_record as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
			_count integer not null = 0;
		BEGIN
		-- (D) Check that there is a record in the table with the same prime key
			SELECT COUNT(*) into _count
			FROM remote_procedure R
			WHERE
				R.application = "remote_procedure.delete__internal".application AND
				R.name = "remote_procedure.delete__internal".name;
			if _count <> 1 then
				_status.errors = _status.errors ||
					ROW('remote_procedure', _index,
						'Er is geen Remote Procedure gevonden met '
						'Application, Name',
						'name'
					)::_error_record;
			end if;			-- Get out quick if there are errors
			if cardinality(_status.errors) <> 0 then
				return _status;
			end if;
			if _check_only then
				return _status;
			end if;

			DELETE FROM remote_procedure R
			WHERE 
				R.application = "remote_procedure.delete__internal".application AND
				R.name = "remote_procedure.delete__internal".name;
			return _status;
		END;
	$$ language plpgsql security definer;

	select * from plpgsql_check_function(
		'"remote_procedure.delete__internal"('
			'internet_name,'
			'object_name,'
			'integer,'
			'boolean)'
	);

drop function if exists "remote_procedure.delete";
	create function "remote_procedure.delete" (
		application internet_name,
		name object_name) returns _jaaql_procedure_result as
	$$
		DECLARE
			_status _status_record = ROW(0, ARRAY[]::_error_record[])::_status_record;
		BEGIN
			SELECT * INTO strict _status FROM "remote_procedure.delete__internal"(
				application => "remote_procedure.delete".application,
				name => "remote_procedure.delete".name);
		-- Throw exception, which triggers a rollback if errors
		if cardinality(_status.errors) <> 0 then
			SELECT raise_jaaql_handled_query_exception(_status);
		end if;
		return _status.result::_jaaql_procedure_result;
		END;
	$$ language plpgsql security definer;


-- (e) Grant access to functions

	grant execute on function "application.insert" to registered;
	grant execute on function "application.delete" to registered;
	grant execute on function "application.update" to registered;
	grant execute on function "application_schema.insert" to registered;
	grant execute on function "application_schema.delete" to registered;
	grant execute on function "application_schema.update" to registered;
	grant execute on function "email_dispatcher.insert" to registered;
	grant execute on function "email_dispatcher.delete" to registered;
	grant execute on function "email_dispatcher.update" to registered;
	grant execute on function "email_template.insert" to registered;
	grant execute on function "email_template.delete" to registered;
	grant execute on function "email_template.update" to registered;
	grant execute on function "document_template.insert" to registered;
	grant execute on function "document_template.delete" to registered;
	grant execute on function "document_template.update" to registered;
	grant execute on function "document_request.insert" to registered;
	grant execute on function "document_request.delete" to registered;
	grant execute on function "document_request.update" to registered;
	grant execute on function "identity_provider_service.insert" to registered;
	grant execute on function "identity_provider_service.delete" to registered;
	grant execute on function "identity_provider_service.update" to registered;
	grant execute on function "user_registry.insert" to registered;
	grant execute on function "user_registry.delete" to registered;
	grant execute on function "user_registry.update" to registered;
	grant execute on function "database_user_registry.insert" to registered;
	grant execute on function "database_user_registry.delete" to registered;
	grant execute on function "database_user_registry.update" to registered;
	grant execute on function "account.insert" to registered;
	grant execute on function "account.delete" to registered;
	grant execute on function "account.update" to registered;
	grant execute on function "validated_ip_address.insert" to registered;
	grant execute on function "validated_ip_address.delete" to registered;
	grant execute on function "validated_ip_address.update" to registered;
	grant execute on function "security_event.insert" to registered;
	grant execute on function "security_event.delete" to registered;
	grant execute on function "security_event.update" to registered;
	grant execute on function "handled_error.insert" to registered;
	grant execute on function "handled_error.delete" to registered;
	grant execute on function "handled_error.update" to registered;
	grant execute on function "remote_procedure.insert" to registered;
	grant execute on function "remote_procedure.delete" to registered;
	grant execute on function "remote_procedure.update" to registered;


-- (f) Grant access to tables

	grant select, insert, update, delete on application to registered;
	grant select, insert, update, delete on application_schema to registered;
	grant select, insert, update, delete on email_dispatcher to registered;
	grant select, insert, update, delete on jaaql to registered;
	grant select, insert, update, delete on email_template to registered;
	grant select, insert, update, delete on document_template to registered;
	grant select, insert, update, delete on document_request to registered;
	grant select, insert, update, delete on federation_procedure to registered;
	grant select, insert, update, delete on federation_procedure_parameter to registered;
	grant select, insert, update, delete on identity_provider_service to registered;
	grant select, insert, update, delete on user_registry to registered;
	grant select, insert, update, delete on database_user_registry to registered;
	grant select, insert, update, delete on account to registered;
	grant select, insert, update, delete on validated_ip_address to registered;
	grant select, insert, update, delete on security_event to registered;
	grant select, insert, update, delete on handled_error to registered;
	grant select, insert, update, delete on pg_base_exception to registered;
	grant select, insert, update, delete on pg_error_class to registered;
	grant select, insert, update, delete on pg_exception to registered;
	grant select, insert, update, delete on remote_procedure to registered;
