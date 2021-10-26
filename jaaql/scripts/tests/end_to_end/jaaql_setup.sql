INSERT INTO public.jaaql__database (id, name, description, port, address, jaaql_name, interface_class, deleted) VALUES ('d79ba54a-9f82-4689-98a0-f9c2645a13dc', 'library', 'The library database on PROD', 5432, '127.0.0.1', 'Library database PROD', 'DBPGInterface', null);
INSERT INTO public.jaaql__database (id, name, description, port, address, jaaql_name, interface_class, deleted) VALUES ('073ef083-9846-43e6-9863-577848b7c8ec', 'delete_test', 'The test delete database', 5432, '127.0.0.1', 'Test delete db', 'DBPGInterface', '2021-08-24 22:31:02.099071');
INSERT INTO public.jaaql__database (id, name, description, port, address, jaaql_name, interface_class, deleted) VALUES ('1b981a86-4655-4580-b531-1575d4cefd8b', 'meeting', 'The meeting room database on PROD', 5432, '127.0.0.1', 'Meeting DB PROD', 'DBPGInterface', null);
INSERT INTO public.jaaql__database (id, name, description, port, address, jaaql_name, interface_class, deleted) VALUES ('55d29def-c5d9-4ac1-b4ad-bcf27090c9f7', 'meeting_stg', 'The meeting room database on STG', 5432, '127.0.0.1', 'Meeting DB STG', 'DBPGInterface', null);

INSERT INTO public.jaaql__application (name, description, url, created) VALUES ('Meeting Room Scheduling Assistant', 'Helps book meetings', 'https://jaaql.com/demos/meeting-application', '2021-08-08 17:17:59.425508');
INSERT INTO public.jaaql__application (name, description, url, created) VALUES ('Library Browser', 'Browses books in the library', 'https://jaaql.com/demos/library-application', '2021-08-08 18:23:30.878474');
INSERT INTO public.jaaql__application (name, description, url, created) VALUES ('Multi DB Application', 'Browses books in the library & books meetings', 'https://jaaql.com/demos/multi-db-application', '2021-08-24 21:52:32.780066');

INSERT INTO public.jaaql__application_database_configuration (application, name, description) VALUES ('Meeting Room Scheduling Assistant', 'Meeting Room PROD', 'Meeting configuration for PROD');
INSERT INTO public.jaaql__application_database_configuration (application, name, description) VALUES ('Meeting Room Scheduling Assistant', 'Meeting Room STG', 'Meeting configuration for STG');
INSERT INTO public.jaaql__application_database_configuration (application, name, description) VALUES ('Multi DB Application', 'Multi DB PROD', 'Multi DB Application for PROD');
INSERT INTO public.jaaql__application_database_configuration (application, name, description) VALUES ('Library Browser', 'Library Browser PROD', 'Library Browser PROD Config');
INSERT INTO public.jaaql__application_database_configuration (application, name, description) VALUES ('Library Browser', 'Library Browser QA', 'Library Browser QA Config');

INSERT INTO public.jaaql__application_database_parameter (application, name, description) VALUES ('Library Browser', 'library_db', 'The library book database');
INSERT INTO public.jaaql__application_database_parameter (application, name, description) VALUES ('Meeting Room Scheduling Assistant', 'meeting_db', 'The meeting room database');
INSERT INTO public.jaaql__application_database_parameter (application, name, description) VALUES ('Multi DB Application', 'meeting_db', 'The meeting room database');
INSERT INTO public.jaaql__application_database_parameter (application, name, description) VALUES ('Multi DB Application', 'library_db', 'The library book database');

INSERT INTO public.jaaql__application_database_argument (application, configuration, database, parameter) VALUES ('Library Browser', 'Library Browser PROD', 'd79ba54a-9f82-4689-98a0-f9c2645a13dc', 'library_db');
INSERT INTO public.jaaql__application_database_argument (application, configuration, database, parameter) VALUES ('Multi DB Application', 'Multi DB PROD', 'd79ba54a-9f82-4689-98a0-f9c2645a13dc', 'library_db');
INSERT INTO public.jaaql__application_database_argument (application, configuration, database, parameter) VALUES ('Multi DB Application', 'Multi DB PROD', '1b981a86-4655-4580-b531-1575d4cefd8b', 'meeting_db');
INSERT INTO public.jaaql__application_database_argument (application, configuration, database, parameter) VALUES ('Meeting Room Scheduling Assistant', 'Meeting Room PROD', '1b981a86-4655-4580-b531-1575d4cefd8b', 'meeting_db');
INSERT INTO public.jaaql__application_database_argument (application, configuration, database, parameter) VALUES ('Meeting Room Scheduling Assistant', 'Meeting Room STG', '55d29def-c5d9-4ac1-b4ad-bcf27090c9f7', 'meeting_db');

INSERT INTO public.jaaql__authorization_application (application, role) VALUES ('Library Browser', 'aaron@jaaql.com');
