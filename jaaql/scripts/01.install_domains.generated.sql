/*
**  This installation module was generated from ..\..\Packages/DBMS/Postgres/15/domains.install for Postgres/15
*/

CREATE DOMAIN encrypted__email_server_password AS character varying(256);
CREATE DOMAIN encrypted__access_token AS character varying(64);
CREATE DOMAIN encrypted__jaaql_username AS character varying(255);
CREATE DOMAIN encrypted__hash AS character varying(512);
CREATE DOMAIN encrypted__salted_ip AS character varying(256);
CREATE DOMAIN internet_name AS character varying(63) CHECK (VALUE ~* '^[a-z0-9\-\$]*$');
CREATE DOMAIN url AS character varying(256);
CREATE DOMAIN location AS character varying(256);
CREATE DOMAIN object_name AS character varying(63) CHECK (VALUE ~* '^[a-zA-Z_][a-zA-Z_0-9\$]*$');
CREATE DOMAIN validity_period AS integer CHECK (VALUE between 15 and 9999999);
CREATE DOMAIN short_validity_period AS integer CHECK (VALUE between 15 and 86400);
CREATE DOMAIN person_name AS character varying(64);
CREATE DOMAIN email_dispatch_protocol AS character varying(8);
CREATE DOMAIN internet_port AS integer CHECK (VALUE between 1 and 65536);
CREATE DOMAIN email_server_username AS character varying(255);
CREATE DOMAIN postgres_role AS character varying(63);
CREATE DOMAIN attempt_count AS smallint CHECK (VALUE between 1 and 3);
CREATE DOMAIN email_template_type AS character varying(1);
CREATE DOMAIN safe_path AS character varying(255) CHECK (VALUE ~* '^[a-z$0-9_\-\/]+(\.[a-zA-Z0-9_\-]+)?$');
CREATE DOMAIN email_account_username AS character varying(64) CHECK (VALUE ~* '^[a-zA-Z0-9_\-\.]+$');
CREATE DOMAIN current_attempt_count AS smallint CHECK (VALUE between 0 and 3);
CREATE DOMAIN unlock_code AS character varying(10);
CREATE DOMAIN error_code AS numeric CHECK (VALUE between 1001 and 1999);
CREATE DOMAIN error_name AS character varying(45);
CREATE DOMAIN http_response_code AS numeric CHECK (VALUE between 100 and 599);
CREATE DOMAIN pg_base_exception_name AS character varying(20);
CREATE DOMAIN pg_error_class_code AS character varying(2);
CREATE DOMAIN pg_error_class_name AS character varying(50);
CREATE DOMAIN pg_error_class_description AS character varying(200);
CREATE DOMAIN pg_sqlstate AS character varying(5);
CREATE DOMAIN pg_exception_name AS character varying(50);
CREATE DOMAIN procedure_access_level AS character varying(1);
