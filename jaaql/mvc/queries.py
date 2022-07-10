from jaaql.constants import DB__jaaql, NODE__host_node

QUERY__fetch_table_columns = "SELECT column_name, is_primary FROM table_cols_marked_primary WHERE table_name = :table_name"
QUERY__fetch_email_template = "SELECT * FROM jaaql__email_template WHERE id = :id AND deleted is NULL"
QUERY__fetch_email_template_by_name = "SELECT * FROM jaaql__email_template WHERE name = :template AND deleted is NULL"
QUERY__make_user_public = "UPDATE jaaql__user SET public_credentials = concat(:username::text, ':', :new_password::text), application = :application, is_public = TRUE WHERE deleted is null AND id = :user_id"
QUERY__fetch_url_from_application_name = "SELECT url FROM jaaql__application WHERE name = :application"
QUERY__fetch_application_public_user_credentials = "SELECT split_part(public_credentials, ':', 1) as username, split_part(public_credentials, ':', 2) as password FROM jaaql__user WHERE application = :application"
QUERY__fetch_application_default_templates = "SELECT jet.name as template, jet2.name as existing_user_template, jet3.name as default_reset_password_template FROM jaaql__application ja LEFT JOIN jaaql__email_template jet ON jet.id = ja.default_email_signup_template AND jet.deleted is NULL LEFT JOIN jaaql__email_template jet2 ON jet2.id = ja.default_email_already_signed_up_template AND jet2.deleted is NULL LEFT JOIN jaaql__email_template jet3 ON jet3.id = ja.default_reset_password_template AND jet3.deleted is NULL WHERE ja.name = :application"
QUERY__my_roles = "SELECT rolname FROM pg_roles WHERE pg_has_role(oid, 'member');"
QUERY__grant_role = "GRANT \"%s\" TO \"%s\""
QUERY__default_roles_sel = "SELECT * FROM jaaql__default_role"
QUERY__default_roles_ins = "INSERT INTO jaaql__default_role (the_role) VALUES (:role)"
QUERY__default_roles_del = "DELETE FROM jaaql__default_role WHERE the_role = :role"
QUERY__fetch_my_applications = "SELECT * FROM jaaql__my_applications"
QUERY__application_set_url = "UPDATE jaaql__application SET url = :url WHERE name = :name"
QUERY__application_ins = "INSERT INTO jaaql__application (name, description, url, default_email_signup_template, default_email_already_signed_up_template, default_reset_password_template) VALUES (:name, :description, :url, :default_email_signup_template, :default_email_already_signed_up_template, :default_reset_password_template)"
QUERY__application_setup_host = "INSERT INTO jaaql__assigned_database (application, configuration, database, node, dataset) VALUES (:application, 'host', '%s', '%s', 'node')" % (DB__jaaql, NODE__host_node)
QUERY__application_del = "DELETE FROM jaaql__application WHERE name = :name"
QUERY__application_sel = "SELECT ja.name, ja.description, ja.url, ja.created, jet.name as default_email_signup_template, jet2.name as default_email_already_signed_up_template, jet3.name as default_reset_password_template FROM jaaql__application ja LEFT JOIN jaaql__email_template jet ON jet.id = ja.default_email_signup_template AND jet.deleted is NULL LEFT JOIN jaaql__email_template jet2 ON jet2.id = ja.default_email_already_signed_up_template AND jet2.deleted is NULL LEFT JOIN jaaql__email_template jet3 ON jet3.id = ja.default_reset_password_template AND jet3.deleted is NULL"
QUERY__application_count = "SELECT COUNT(*) FROM jaaql__application"
QUERY__application_upd = "UPDATE jaaql__application SET name = coalesce(:new_name, name), description = coalesce(:new_description, description), url = coalesce(:new_url, url) WHERE name = :name"
QUERY__database_ins = "INSERT INTO jaaql__database (node, name) VALUES (:node, :name)"
QUERY__setup_jaaql_role = "SELECT setup_jaaql_role()"
QUERY__email_template_ins = "INSERT INTO jaaql__email_template (name, subject, account, description, app_relative_path, data_validation_table, data_validation_view, recipient_validation_view, allow_signup, allow_confirm_signup_attempt, allow_reset_password) VALUES (:name, :subject, :account, :description, :app_relative_path, :data_validation_table, :data_validation_view, :recipient_validation_view, :allow_signup, :allow_confirm_signup_attempt, :allow_reset_password)"
QUERY__email_account_ins = "INSERT INTO jaaql__email_account (name, send_name, protocol, host, port, username, encrypted_password) VALUES (:name, :send_name, :protocol, :host, :port, :username, :password)"
QUERY__email_account_del = "UPDATE jaaql__email_account SET deleted = current_timestamp WHERE name = :name AND deleted is null"
QUERY__email_account_sel = "SELECT id FROM jaaql__email_account WHERE name = :name and deleted is null"
QUERY__email_template_del = "UPDATE jaaql__email_template SET deleted = current_timestamp WHERE name = :name and deleted is null"
QUERY__email_template_sel = "SELECT id FROM jaaql__email_template WHERE name = :name and deleted is null"
QUERY__email_history_sel = "SELECT * FROM jaaql__my_email_history"
QUERY__email_history_count = "SELECT count(*) FROM jaaql__my_email_history"
QUERY__email_history_singular_sel = "SELECT jet.name as template, jeh.sent, jeh.encrypted_subject as subject, jeh.encrypted_recipients_keys as recipient, jeh.encrypted_body as body, jeh.encrypted_attachments as attachments FROM jaaql__email_history jeh INNER JOIN jaaql__email_template jet ON jet.id = jeh.template WHERE jeh.sender = :user_id"
QUERY__node_create = "SELECT jaaql__create_node(:name, :address, :port, :description);"
QUERY__database_sel = "SELECT * FROM jaaql__database"
QUERY__email_accounts_sel = "SELECT id, name, send_name, protocol, host, port, username FROM jaaql__email_account"
QUERY__email_accounts_count = "SELECT count(*) FROM jaaql__email_account"
QUERY__email_templates_sel = "SELECT * FROM jaaql__email_templates"
QUERY__email_templates_count = "SELECT count(*) FROM jaaql__email_templates"
QUERY__node_sel = "SELECT * FROM jaaql__node"
QUERY__database_del = "DELETE FROM jaaql__database WHERE name = :name AND node = :node"
QUERY__node_del = "SELECT jaaql__delete_node(:name);"
QUERY__database_count = "SELECT COUNT(*) FROM jaaql__database"
QUERY__node_count = "SELECT COUNT(*) FROM jaaql__node"
QUERY__application_dataset_ins = "INSERT INTO jaaql__application_dataset (application, name, description) VALUES (:application, :name, :description)"
QUERY__application_dataset_del = "DELETE FROM jaaql__application_dataset WHERE name = :name AND application = :application"
QUERY__application_dataset_sel = "SELECT * FROM jaaql__application_dataset"
QUERY__application_dataset_count = "SELECT COUNT(*) FROM jaaql__application_dataset"
QUERY__application_configuration_ins = "INSERT INTO jaaql__application_configuration (application, name, description) VALUES (:application, :name, :description)"
QUERY__application_configuration_del = "DELETE FROM jaaql__application_configuration WHERE name = :name AND application = :application"
QUERY__application_configuration_sel = "SELECT * FROM jaaql__application_configuration"
QUERY__application_configuration_count = "SELECT COUNT(*) FROM jaaql__application_configuration"
QUERY__assigned_database_ins = "INSERT INTO jaaql__assigned_database (application, configuration, database, node, dataset) VALUES (:application, :configuration, :database, :node, :dataset)"
QUERY__assigned_database_del = "DELETE FROM jaaql__assigned_database WHERE application = :application AND configuration = :configuration AND dataset = :dataset"
QUERY__assigned_database_sel = "SELECT * FROM jaaql__assigned_database"
QUERY__assigned_database_count = "SELECT COUNT(*) FROM jaaql__assigned_database"
QUERY__configuration_authorization_ins = "INSERT INTO jaaql__authorization_configuration (application, configuration, role) VALUES (:application, :configuration, :role)"
QUERY__configuration_authorization_del = "DELETE FROM jaaql__authorization_configuration WHERE application = :application AND role = :role AND configuration = :configuration"
QUERY__configuration_authorization_sel = "SELECT * FROM jaaql__authorization_configuration"
QUERY__configuration_authorization_count = "SELECT COUNT(*) FROM jaaql__authorization_configuration"
QUERY__node_credentials_set_public_user = "UPDATE jaaql__credentials_node SET precedence = -1 WHERE role = :username AND node = :node"
QUERY__node_credentials_ins = "INSERT INTO jaaql__credentials_node (node, role, db_encrypted_username, db_encrypted_password, precedence) VALUES (:node, :role, :username, :password, coalesce(:precedence, 0))"
QUERY__node_credentials_del = "UPDATE jaaql__credentials_node SET deleted = current_timestamp WHERE role = :role AND node = :node AND deleted is null"
QUERY__node_credentials_sel = "SELECT id, node, role, deleted FROM jaaql__credentials_node"
QUERY__role_connection_sel = "SELECT ad.id as id, ad.db_encrypted_username as username, ad.db_encrypted_password as password, nod.address, nod.port FROM jaaql__credentials_node ad INNER JOIN jaaql__node nod ON nod.name = ad.node WHERE role = jaaql__fetch_alias_from_id(:user_id) AND node = :node AND ad.deleted is null AND nod.deleted is null;"
QUERY__node_credentials_count = "SELECT COUNT(*) FROM jaaql__credentials_node"
QUERY__ins_rendered_document = "INSERT INTO jaaql__rendered_document (encrypted_parameters, encrypted_access_token, document, create_file) VALUES (:parameters, :oauth_token, :name, :create_file) RETURNING document_id"
QUERY__fetch_rendered_document = "SELECT rd.document_id, able.render_as, rd.filename, rd.create_file, rd.completed, rd.encrypted_access_token as oauth_token FROM jaaql__rendered_document rd INNER JOIN jaaql__renderable_document able ON rd.document = able.name WHERE rd.document_id = :document_id"
QUERY__purge_rendered_document = "DELETE FROM jaaql__rendered_document WHERE completed is not null and document_id = :document_id RETURNING content"
QUERY__user_ins = "INSERT INTO jaaql__user (email, mobile, alias, is_public, application, public_credentials) VALUES (:email, :mobile, :alias, :is_public, :application, :public_credentials) RETURNING id"
QUERY__postgres_version = "SELECT version() as version;"
QUERY__revoke_user = "UPDATE jaaql__user SET deleted = current_timestamp WHERE id = :id AND deleted is NULL"
QUERY__disable_mfa = "UPDATE jaaql__user SET enc_totp_iv = null WHERE id = :user_id"
QUERY__set_mfa = "UPDATE jaaql__user SET enc_totp_iv = :totp_iv WHERE id = :user_id"
QUERY__user_id_from_username = "SELECT id FROM jaaql__user WHERE email = :username AND deleted is null"
QUERY__user_totp_upd = "UPDATE jaaql__user SET last_totp = :last_totp WHERE id = :user_id"
QUERY__user_ip_sel = "SELECT encrypted_address as address, first_use, most_recent_use FROM jaaql__my_ips"
QUERY__user_ip_count = "SELECT COUNT(*) FROM jaaql__my_ips"
QUERY__user_ip_ins = "INSERT INTO jaaql__user_ip (the_user, encrypted_address) VALUES (:id, :ip_address) ON CONFLICT ON CONSTRAINT jaaql__user_ip_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_password_ins = "INSERT INTO jaaql__user_password (the_user, password_hash) VALUES (:the_user, :password_hash)"
QUERY__fetch_user_latest_password = "SELECT id, email, password_created, password_hash, enc_totp_iv as totp_iv, last_totp, is_public FROM jaaql__user_latest_password WHERE email = :username"
QUERY__fetch_user_latest_credentials = "SELECT id, email, password_created, password_hash, enc_totp_iv as totp_iv, last_totp, is_public, encrypted_address, ip_id FROM jaaql__user_latest_credentials WHERE email = :username AND encrypted_address = :ip_address"
QUERY__sign_up_insert = "INSERT INTO jaaql__sign_up (the_user, email_template, data_lookup_json, invite_code) VALUES (:the_user, :template, :data_lookup_json, :invite_code) RETURNING key_a as invite_key, key_b as invite_poll_key, invite_code as invite_code"
QUERY__sign_up_count = "SELECT COUNT(*) as count FROM jaaql__sign_up WHERE the_user = :the_user AND (created + interval '24 hour') > current_timestamp"
QUERY__reset_count = "SELECT COUNT(*) as count FROM jaaql__reset_password WHERE the_user = :the_user AND (created + interval '24 hour') > current_timestamp"
QUERY__fake_reset_count = "SELECT COUNT(*) as count FROM jaaql__fake_reset_password WHERE email = :email AND (created + interval '24 hour') > current_timestamp"
QUERY__fake_reset_insert = "INSERT INTO jaaql__fake_reset_password (email) VALUES (:email) RETURNING key_b as reset_poll_key"
QUERY__reset_insert = "INSERT INTO jaaql__reset_password (the_user, email_template, data_lookup_json, reset_code) VALUES (:the_user, :template, :data_lookup_json, :reset_code) RETURNING key_a as reset_key, key_b as reset_poll_key, reset_code as reset_code"
QUERY__sign_up_increment_attempts = "UPDATE jaaql__sign_up SET code_attempts = code_attempts + 1 WHERE key_a = :invite_key"
QUERY__reset_increment_attempts = "UPDATE jaaql__reset_password SET code_attempts = code_attempts + 1 WHERE key_a = :reset_key"
QUERY__fake_reset_increment_attempts = "UPDATE jaaql__fake_reset_password SET code_attempts = code_attempts + 1 WHERE key_b = :reset_key"
QUERY__sign_up_poll = "SELECT key_a as invite_key, invite_code, activated, su.created, su.the_user, su.closed, us.email, su.code_expiry_ms, su.used_key_a, su.code_attempts FROM jaaql__sign_up su INNER JOIN jaaql__user us ON us.id = su.the_user WHERE (key_a = :invite_or_poll_key or key_b = :invite_or_poll_key) AND extract(epoch FROM (current_timestamp - su.created)) * 1000 < expiry_ms"
QUERY__reset_poll = "SELECT key_a as reset_key, reset_code, activated, rp.created, rp.the_user, rp.closed, us.email, rp.code_expiry_ms, rp.used_key_a, rp.code_attempts FROM jaaql__reset_password rp INNER JOIN jaaql__user us ON us.id = rp.the_user WHERE (key_a = :reset_or_poll_key or key_b = :reset_or_poll_key) AND extract(epoch FROM (current_timestamp - rp.created)) * 1000 < expiry_ms"
QUERY__fake_reset_poll = "SELECT gen_random_uuid() as reset_key, rp.created, rp.email, rp.code_attempts, FALSE as activated, rp.code_expiry_ms, gen_random_uuid() as reset_code FROM jaaql__fake_reset_password rp WHERE key_b = :reset_or_poll_key AND extract(epoch FROM (current_timestamp - rp.created)) * 1000 < expiry_ms"
QUERY__sign_up_fetch = "SELECT su.key_a as invite_key, su.activated, su.the_user, su.closed, su.data_lookup_json, us.email, su.email_template as template, su.data_lookup_json FROM jaaql__sign_up su INNER JOIN jaaql__user us on us.id = su.the_user WHERE ((su.key_a = :invite_or_poll_key) or (su.activated and su.key_b = :invite_or_poll_key)) AND extract(epoch FROM (current_timestamp - su.created)) * 1000 < su.expiry_ms AND su.closed is null"
QUERY__reset_fetch = "SELECT rp.key_a as reset_key, rp.activated, rp.the_user, rp.closed, us.email, rp.email_template as template, rp.data_lookup_json FROM jaaql__reset_password rp INNER JOIN jaaql__user us on us.id = rp.the_user WHERE ((rp.key_a = :reset_or_poll_key) or (rp.activated and rp.key_b = :reset_or_poll_key)) AND extract(epoch FROM (current_timestamp - rp.created)) * 1000 < rp.expiry_ms AND rp.closed is null"
QUERY__sign_up_upd = "UPDATE jaaql__sign_up SET activated = TRUE WHERE key_a = :invite_key"
QUERY__reset_upd = "UPDATE jaaql__reset_password SET activated = TRUE WHERE key_a = :reset_key"
QUERY__reset_upd_used = "UPDATE jaaql__reset_password SET used_key_a = TRUE WHERE key_a = :reset_key"
QUERY__sign_up_upd_used = "UPDATE jaaql__sign_up SET used_key_a = TRUE WHERE key_a = :invite_key"
QUERY__sign_up_close = "UPDATE jaaql__sign_up SET closed = current_timestamp WHERE key_a = :invite_key"
QUERY__reset_close = "UPDATE jaaql__reset_password SET closed = current_timestamp WHERE key_a = :reset_key or key_b = :reset_key"
QUERY__user_create_role = "SELECT jaaql__create_role(lower(:username::text), :password)"
QUERY__log_ins = "INSERT INTO jaaql__log (the_user, occurred, duration_ms, encrypted_exception, encrypted_input, ip, status, endpoint) VALUES (:user_id, :occurred, :duration_ms, :exception, :input, :ip, :status, :endpoint)"
QUERY__user_log_sel = "SELECT occurred, encrypted_address as address, status, endpoint, duration_ms, encrypted_exception as exception FROM jaaql__my_logs"
QUERY__user_log_count = "SELECT COUNT(*) FROM jaaql__my_logs"
QUERY__my_configs = "SELECT * FROM jaaql__my_configurations WHERE application = :application or :application is null"
QUERY__my_configs_where = "SELECT * FROM jaaql__my_configurations WHERE application = :application AND configuration = :configuration"
QUERY__create_database = "create database \"%s\""
QUERY__drop_database = "drop database \"%s\""
QUERY__node_single_credential_sel = """
SELECT
    *
FROM
    jaaql__their_single_authorized_wildcard_node wn
WHERE (wn.node, wn.precedence) in 
    (SELECT
        wnsub.node,
        max(wnsub.precedence) as max_precedence
    FROM jaaql__their_single_authorized_wildcard_node wnsub
    WHERE (wnsub.role = '' or pg_has_role(jaaql__fetch_alias_from_id(:user_id), wnsub.role, 'MEMBER'))
    GROUP BY wnsub.node) AND
    (wn.role = '' or pg_has_role(jaaql__fetch_alias_from_id(:user_id), wn.role, 'MEMBER')) AND wn.node = :node;
"""
QUERY__authorized_configuration = """
SELECT
    jtac.*
FROM jaaql__their_authorized_configurations jtac
INNER JOIN (
    SELECT DISTINCT application, configuration FROM jaaql__their_authorized_app_only_configurations WHERE pg_has_role(jaaql__fetch_alias_from_id(:user_id), conf_role, 'MEMBER') AND application = :application AND configuration = :configuration
) sub ON sub.application = jtac.application AND sub.configuration = jtac.configuration
WHERE pg_has_role(jaaql__fetch_alias_from_id(:user_id), node_role, 'MEMBER') AND jtac.application = :application AND jtac.configuration = :configuration AND jtac.precedence IN (
    SELECT
        MAX(precedence)
    FROM jaaql__their_authorized_configurations
    WHERE pg_has_role(jaaql__fetch_alias_from_id(:user_id), node_role, 'MEMBER') AND application = :application AND configuration = :configuration
);
"""

QUERY__uninstall_jaaql_0 = "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'jaaql' AND pid <> pg_backend_pid();"
QUERY__uninstall_jaaql_1 = "drop database if exists jaaql"
QUERY__uninstall_jaaql_2 = "drop role if exists jaaql"
QUERY__uninstall_jaaql_3 = "create database jaaql"