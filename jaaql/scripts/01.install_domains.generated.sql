/*
**  This installation module was generated from ../../../Packages/DBMS/Postgres/15/domains.install for Postgres/15
*/

CREATE DOMAIN encrypted__email_server_password AS character varying(256);
CREATE DOMAIN encrypted__access_token AS character varying(64);
CREATE DOMAIN encrypted__jaaql_username AS character varying(255);
CREATE DOMAIN encrypted__hash AS character varying(512);
CREATE DOMAIN encrypted__salted_ip AS character varying(256);
CREATE DOMAIN internet_name AS character varying(63) CHECK (VALUE ~* '^[a-z0-9\-]*$');
CREATE DOMAIN url AS character varying(256);
CREATE DOMAIN location AS character varying(256);
CREATE DOMAIN object_name AS character varying(63) CHECK (VALUE ~* '^[a-z0-9_]*$');
CREATE DOMAIN validity_period AS integer;
CREATE DOMAIN short_validity_period AS integer;
CREATE DOMAIN person_name AS character varying(64);
CREATE DOMAIN email_dispatch_protocol AS character varying(8);
CREATE DOMAIN internet_port AS integer;
CREATE DOMAIN email_server_username AS character varying(255);
CREATE DOMAIN postgres_role AS character varying(63);
CREATE DOMAIN attempt_count AS smallint;
CREATE DOMAIN email_template_type AS character varying(1);
CREATE DOMAIN safe_path AS character varying(255) CHECK (VALUE ~* '^[a-z0-9_\-\/]+(\.[a-zA-Z0-9]+)?$');
CREATE DOMAIN current_attempt_count AS smallint;
CREATE DOMAIN unlock_code AS character varying(10);
