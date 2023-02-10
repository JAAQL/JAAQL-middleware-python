QUERY__setup_system = "SELECT setup();"
QUERY__fetch_internal_admin = "SELECT * FROM check_admin"
QUERY__fetch_recent_passwords_with_ips = "SELECT * FROM fetch_recent_passwords_with_ips WHERE username = :enc_username AND encrypted_address = :encrypted_address;"
QUERY__fetch_recent_passwords = "SELECT * FROM fetch_recent_passwords WHERE username = :enc_username;"
QUERY__fetch_recent_passwords_with_account = "SELECT * FROM fetch_recent_passwords WHERE user_id = :user_id;"
QUERY__create_account = "SELECT create_account(:username, :is_public, :attach_as)"
QUERY__fetch_matching_recent_passwords_with_account = "SELECT * FROM fetch_recent_passwords WHERE user_id = :user_id AND password_id = :password;"
QUERY__add_password = "INSERT INTO account_password (account, password_hash) VALUES (:account, :password_hash) RETURNING id;"
QUERY__add_password_cache = "UPDATE account SET password = :password WHERE user_id = :account"
QUERY__add_or_update_ip = "INSERT INTO account_ip (account, encrypted_address) VALUES (:account, :encrypted_address) ON CONFLICT ON CONSTRAINT user_ip_unq DO UPDATE SET most_recent_login = current_timestamp RETURNING id as address"
QUERY__setup_jaaql_role = "SELECT setup_jaaql_role();"
QUERY__attach_account = "SELECT attach_account(:user_id, :enc_username);"
QUERY__fetch_user_from_username = "SELECT user_id FROM account WHERE username = :username"
QUERY__fetch_user_record_from_username = "SELECT * FROM account WHERE username = :username"
QUERY__fetch_application = "SELECT * FROM application WHERE name = :application"
QUERY__postgres_version = "SELECT version() as version;"
QUERY__drop_email_account = "SELECT drop_email_account(:name)"
QUERY__drop_database = "SELECT drop_database(:name)"
QUERY__fetch_email_template_with_app_url = "SELECT et.*, a.artifact_base_url, a.url, et.account, et.override_send_name FROM email_template et INNER JOIN application a ON a.name = et.application WHERE et.name = :name AND et.application = :application"
QUERY__fetch_table_columns = "SELECT column_name, is_primary FROM jaaql__table_cols_marked_primary WHERE table_name = :table_name"
QUERY__sign_up_count = "SELECT COUNT(*) as count FROM sign_up WHERE account = :user_id AND (created + interval '24 hour') > current_timestamp"
QUERY__sign_up_insert = "INSERT INTO sign_up (account, email_template, data_lookup_json, invite_code, application) VALUES (:the_user, :template, :data_lookup_json, :invite_code, :application) RETURNING key_a as invite_key, key_b as invite_poll_key, invite_code as invite_code"
QUERY__sign_up_poll = "SELECT key_a as invite_key, invite_code, activated, su.created, su.account, su.closed, us.username as email, su.code_expiry_ms, su.used_key_a, su.code_attempts FROM sign_up su INNER JOIN account us ON us.user_id = su.account WHERE (key_a = :invite_or_poll_key or key_b = :invite_or_poll_key) AND extract(epoch FROM (current_timestamp - su.created)) * 1000 < expiry_ms"
QUERY__sign_up_upd = "UPDATE sign_up SET activated = TRUE WHERE key_a = :invite_key"
QUERY__sign_up_upd_used = "UPDATE sign_up SET used_key_a = TRUE WHERE key_a = :invite_key"
QUERY__sign_up_increment_attempts = "UPDATE sign_up SET code_attempts = code_attempts + 1 WHERE key_a = :invite_key"
QUERY__sign_up_fetch = "SELECT su.key_a as invite_key, su.activated, su.account, su.closed, su.data_lookup_json, us.username as email, su.email_template as template, su.data_lookup_json, su.application FROM sign_up su INNER JOIN account us on us.user_id = su.account WHERE ((su.key_a = :invite_or_poll_key) or (su.activated and su.key_b = :invite_or_poll_key)) AND extract(epoch FROM (current_timestamp - su.created)) * 1000 < su.expiry_ms AND su.closed is null"
QUERY__sign_up_close = "UPDATE sign_up SET closed = current_timestamp WHERE key_a = :invite_key"
QUERY__reset_count = "SELECT COUNT(*) as count FROM reset_password WHERE the_user = :the_user AND (created + interval '24 hour') > current_timestamp"
QUERY__fake_reset_count = "SELECT COUNT(*) as count FROM fake_reset_password WHERE email = :email AND (created + interval '24 hour') > current_timestamp"
QUERY__reset_insert = "INSERT INTO reset_password (the_user, email_template, data_lookup_json, reset_code, application) VALUES (:the_user, :template, :data_lookup_json, :reset_code, :application) RETURNING key_a as reset_key, key_b as reset_poll_key, reset_code as reset_code"
QUERY__fake_reset_insert = "INSERT INTO fake_reset_password (email) VALUES (:email) RETURNING key_b as reset_poll_key"
QUERY__reset_poll = "SELECT key_a as reset_key, reset_code, activated, rp.created, rp.the_user, rp.closed, us.username as email, rp.code_expiry_ms, rp.used_key_a, rp.code_attempts FROM reset_password rp INNER JOIN account us ON us.user_id = rp.the_user WHERE (key_a = :reset_or_poll_key or key_b = :reset_or_poll_key) AND extract(epoch FROM (current_timestamp - rp.created)) * 1000 < expiry_ms"
QUERY__fake_reset_poll = "SELECT gen_random_uuid() as reset_key, rp.created, rp.email, rp.code_attempts, FALSE as activated, rp.code_expiry_ms, gen_random_uuid() as reset_code FROM fake_reset_password rp WHERE key_b = :reset_or_poll_key AND extract(epoch FROM (current_timestamp - rp.created)) * 1000 < expiry_ms"
QUERY__reset_upd = "UPDATE reset_password SET activated = TRUE WHERE key_a = :reset_key"
QUERY__reset_upd_used = "UPDATE reset_password SET used_key_a = TRUE WHERE key_a = :reset_key"
QUERY__fake_reset_increment_attempts = "UPDATE fake_reset_password SET code_attempts = code_attempts + 1 WHERE key_b = :reset_key"
QUERY__reset_increment_attempts = "UPDATE reset_password SET code_attempts = code_attempts + 1 WHERE key_a = :reset_key"
QUERY__reset_fetch = "SELECT rp.key_a as reset_key, rp.activated, rp.the_user, rp.closed, us.username as email, rp.email_template as template, rp.data_lookup_json, rp.application FROM reset_password rp INNER JOIN account us on us.user_id = rp.the_user WHERE ((rp.key_a = :reset_or_poll_key) or (rp.activated and rp.key_b = :reset_or_poll_key)) AND extract(epoch FROM (current_timestamp - rp.created)) * 1000 < rp.expiry_ms AND rp.closed is null"
QUERY__reset_close = "UPDATE reset_password SET closed = current_timestamp WHERE key_a = :reset_key or key_b = :reset_key"
QUERY__ins_rendered_document = "INSERT INTO rendered_document (encrypted_parameters, encrypted_access_token, document, create_file, application) VALUES (:parameters, :oauth_token, :name, :create_file, :application) RETURNING document_id"
QUERY__purge_rendered_document = "DELETE FROM rendered_document WHERE completed is not null and document_id = :document_id RETURNING content"
QUERY__fetch_rendered_document = "SELECT rd.document_id, able.render_as, rd.filename, rd.create_file, rd.completed, rd.encrypted_access_token as oauth_token FROM rendered_document rd INNER JOIN renderable_document able ON rd.document = able.name WHERE rd.document_id = :document_id"
QUERY__log_ins = "INSERT INTO log (the_user, occurred, duration_ms, encrypted_exception, encrypted_input, ip, status, endpoint) VALUES (:user_id, :occurred, :duration_ms, :exception, :input, :ip, :status, :endpoint)"
