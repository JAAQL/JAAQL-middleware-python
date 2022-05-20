from jaaql.constants import DB__jaaql, NODE__host_node

QUERY__fetch_table_columns = "SELECT column_name, is_primary FROM table_cols_marked_primary WHERE table_name = :table_name"
QUERY__fetch_email_template = "SELECT * FROM jaaql__email_template WHERE id = :id AND deleted is NULL"
QUERY__fetch_email_template_by_name = "SELECT * FROM jaaql__email_template WHERE name = :email_template AND deleted is NULL"
QUERY__make_user_public = "UPDATE jaaql__user SET public_credentials = concat(:username, ':', :new_password), application = :application, is_public = TRUE WHERE deleted is null AND id = :user_id"
QUERY__fetch_url_from_application_name = "SELECT url FROM jaaql__application WHERE name = :application"
QUERY__fetch_application_public_user_credentials = "SELECT split_part(public_credentials, ':', 1) as username, split_part(public_credentials, ':', 2) as password FROM jaaql__user WHERE application = :application"
QUERY__my_roles = "SELECT rolname FROM pg_roles WHERE pg_has_role(oid, 'member');"
QUERY__grant_role = "GRANT %s TO %s"
QUERY__default_roles_sel = "SELECT * FROM jaaql__default_role"
QUERY__default_roles_ins = "INSERT INTO jaaql__default_role (the_role) VALUES (:role)"
QUERY__default_roles_del = "DELETE FROM jaaql__default_role WHERE the_role = :role"
QUERY__fetch_my_applications = "SELECT * FROM jaaql__my_applications"
QUERY__application_set_url = "UPDATE jaaql__application SET url = :url WHERE name = :name"
QUERY__application_ins = "INSERT INTO jaaql__application (name, description, url) VALUES (:name, :description, :url)"
QUERY__application_setup_host = "INSERT INTO jaaql__assigned_database (application, configuration, database, node, dataset) VALUES (:application, 'host', '%s', '%s', 'node')" % (DB__jaaql, NODE__host_node)
QUERY__application_del = "DELETE FROM jaaql__application WHERE name = :name"
QUERY__application_sel = "SELECT * FROM jaaql__application"
QUERY__application_count = "SELECT COUNT(*) FROM jaaql__application"
QUERY__application_upd = "UPDATE jaaql__application SET name = coalesce(:new_name, name), description = coalesce(:new_description, description), url = coalesce(:new_url, url) WHERE name = :name"
QUERY__database_ins = "INSERT INTO jaaql__database (node, name) VALUES (:node, :name)"
QUERY__email_template_ins = "INSERT INTO jaaql__email_template (name, subject, account, description, app_relative_path, data_validation_table, recipient_validation_view, allow_signup, allow_confirm_signup_attempt) VALUES (:name, :subject, :account, :description, :app_relative_path, :data_validation_table, :recipient_validation_view, :allow_signup, :allow_confirm_signup_attempt)"
QUERY__email_account_ins = "INSERT INTO jaaql__email_account (name, send_name, protocol, host, port, username, encrypted_password) VALUES (:name, :send_name, :protocol, :host, :port, :username, :password)"
QUERY__email_account_del = "DELETE FROM jaaql__email_account WHERE id = :id RETURNING id"
QUERY__email_account_sel = "SELECT id FROM jaaql__email_account WHERE name = :name and deleted is null"
QUERY__email_template_del = "DELETE FROM jaaql__email_template WHERE id = :id RETURNING id"
QUERY__email_template_sel = "SELECT id FROM jaaql__email_template WHERE name = :name and deleted is null"
QUERY__email_history_sel = "SELECT * FROM jaaql__my_email_history"
QUERY__email_history_count = "SELECT count(*) FROM jaaql__my_email_history"
QUERY__email_history_singular_sel = "SELECT jet.name as template, jeh.sent, jeh.encrypted_subject as subject, jeh.encrypted_recipients_keys as recipient, jeh.encrypted_body as body, jeh.encrypted_attachments as attachments FROM jaaql__email_history jeh INNER JOIN jaaql__email_template jet ON jet.id = jeh.template WHERE jeh.sender = :user_id"
QUERY__node_create = "SELECT jaaql__create_node(:name, :address, :port, :description);"
QUERY__database_sel = "SELECT * FROM jaaql__database"
QUERY__email_accounts_sel = "SELECT name, send_name, protocol, host, port, username FROM jaaql__email_account"
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
QUERY__node_credentials_ins = "INSERT INTO jaaql__credentials_node (node, role, db_encrypted_username, db_encrypted_password, precedence) VALUES (:node, :role, :username, :password, coalesce(:precedence, 0))"
QUERY__node_credentials_del = "UPDATE jaaql__credentials_node SET deleted = current_timestamp WHERE role = :role AND node = :node AND deleted is null"
QUERY__node_credentials_sel = "SELECT id, node, role, deleted FROM jaaql__credentials_node"
QUERY__role_connection_sel = "SELECT ad.id as id, ad.db_encrypted_username as username, ad.db_encrypted_password as password, nod.address, nod.port FROM jaaql__credentials_node ad INNER JOIN jaaql__node nod ON nod.name = ad.node WHERE role = (SELECT coalesce(alias, email) FROM jaaql__user WHERE email = :role) AND node = :node AND ad.deleted is null AND nod.deleted is null;"
QUERY__node_credentials_count = "SELECT COUNT(*) FROM jaaql__credentials_node"
QUERY__user_ins = "INSERT INTO jaaql__user (email, mobile, alias, is_public, application, public_credentials) VALUES (lower(:email), :mobile, :alias, :is_public, :application, :public_credentials) RETURNING id"
QUERY__revoke_user = "UPDATE jaaql__user SET deleted = current_timestamp WHERE email = lower(:username) AND email not in ('jaaql', 'superjaaql') AND deleted is NULL"
QUERY__disable_mfa = "UPDATE jaaql__user SET enc_totp_iv = null WHERE id = :user_id"
QUERY__set_mfa = "UPDATE jaaql__user SET enc_totp_iv = :totp_iv WHERE id = :user_id"
QUERY__user_id_from_username = "SELECT id FROM jaaql__user WHERE email = lower(:username) AND deleted is null"
QUERY__user_totp_upd = "UPDATE jaaql__user SET last_totp = :last_totp WHERE id = :user_id"
QUERY__user_ip_sel = "SELECT encrypted_address as address, first_use, most_recent_use FROM jaaql__my_ips"
QUERY__user_ip_count = "SELECT COUNT(*) FROM jaaql__my_ips"
QUERY__user_ip_ins = "INSERT INTO jaaql__user_ip (the_user, address_hash, encrypted_address) VALUES (:id, :address_hash, :ip_address) ON CONFLICT ON CONSTRAINT jaaql__user_ip_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_ua_ins = "INSERT INTO jaaql__user_ua (the_user, ua_hash, encrypted_ua) VALUES (:id, :ua_hash, :ua) ON CONFLICT ON CONSTRAINT jaaql__user_ua_unq DO UPDATE SET most_recent_use = current_timestamp RETURNING most_recent_use <> first_use as existed, id"
QUERY__user_password_ins = "INSERT INTO jaaql__user_password (the_user, password_hash) VALUES (:the_user, :password_hash)"
QUERY__fetch_user_latest_password = "SELECT id, email, password_hash, enc_totp_iv as totp_iv, last_totp, is_public FROM jaaql__user_latest_password WHERE email = lower(:username)"
QUERY__user_create_role = "SELECT jaaql__create_role(lower(:username), :password)"
QUERY__log_ins = "INSERT INTO jaaql__log (the_user, occurred, duration_ms, encrypted_exception, encrypted_input, ip, ua, status, endpoint) VALUES (:user_id, :occurred, :duration_ms, :exception, :input, :ip, :ua, :status, :endpoint)"
QUERY__user_log_sel = "SELECT occurred, encrypted_address as address, encrypted_ua as user_agent, status, endpoint, duration_ms, encrypted_exception as exception FROM jaaql__my_logs"
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