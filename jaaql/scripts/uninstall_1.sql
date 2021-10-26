SELECT username FROM jaaql__user WHERE left(username, 7) = 'jaaql__';
DELETE FROM jaaql__authorization;
DELETE FROM jaaql__application;
DELETE FROM jaaql__user;

DROP VIEW jaaql__authorized_application;
DROP TABLE jaaql__authorization;
DROP TABLE jaaql__application;
DROP TABLE jaaql__user;
DROP SEQUENCE jaaql__user_seq;

DROP FUNCTION jaaql__grant_role;
DROP FUNCTION jaaql__create_role;
