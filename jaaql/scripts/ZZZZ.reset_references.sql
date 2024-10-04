

-- (4) References

-- application...
ALTER TABLE application DROP CONSTRAINT IF EXISTS application__default_schema;
alter table application add constraint application__default_schema
    foreign key (name, default_schema)
        references application_schema (application, name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE application DROP CONSTRAINT IF EXISTS application__default_sign_up_email_template;
alter table application add constraint application__default_sign_up_email_template
    foreign key (name, default_s_et)
        references email_template (application, name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE application DROP CONSTRAINT IF EXISTS application__default_already_signed_up_email_template;
alter table application add constraint application__default_already_signed_up_email_template
    foreign key (name, default_a_et)
        references email_template (application, name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE application DROP CONSTRAINT IF EXISTS application__default_reset_password_email_template;
alter table application add constraint application__default_reset_password_email_template
    foreign key (name, default_r_et)
        references email_template (application, name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE application DROP CONSTRAINT IF EXISTS application__default_unregistered_password_reset_email_template;
alter table application add constraint application__default_unregistered_password_reset_email_template
    foreign key (name, default_u_et)
        references email_template (application, name) ON DELETE cascade ON UPDATE cascade; 
-- application_schema...
ALTER TABLE application_schema DROP CONSTRAINT IF EXISTS application_schema__application;
alter table application_schema add constraint application_schema__application
    foreign key (application)
        references application (name) ON DELETE cascade ON UPDATE cascade; 
-- email_dispatcher...
ALTER TABLE email_dispatcher DROP CONSTRAINT IF EXISTS email_dispatcher__application;
alter table email_dispatcher add constraint email_dispatcher__application
    foreign key (application)
        references application (name) ON DELETE cascade ON UPDATE cascade; 
-- jaaql...
ALTER TABLE _jaaql DROP CONSTRAINT IF EXISTS jaaql__the_anonymous_user;
alter table _jaaql add constraint jaaql__the_anonymous_user
    foreign key (the_anonymous_user)
        references account (id) ON DELETE cascade ON UPDATE cascade; 
-- email_template...
ALTER TABLE email_template DROP CONSTRAINT IF EXISTS email_template__dispatcher;
alter table email_template add constraint email_template__dispatcher
    foreign key (application, dispatcher)
        references email_dispatcher (application, name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE email_template DROP CONSTRAINT IF EXISTS email_template__validation_schema;
alter table email_template add constraint email_template__validation_schema
    foreign key (application, validation_schema)
        references application_schema (application, name) ON DELETE cascade ON UPDATE cascade; 
-- document_template...
ALTER TABLE document_template DROP CONSTRAINT IF EXISTS document_template__application;
alter table document_template add constraint document_template__application
    foreign key (application)
        references application (name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE document_template DROP CONSTRAINT IF EXISTS document_template__email_template;
alter table document_template add constraint document_template__email_template
    foreign key (application, email_template)
        references email_template (application, name) ON DELETE cascade ON UPDATE cascade; 
-- document_request...
ALTER TABLE document_request DROP CONSTRAINT IF EXISTS document_request__template;
alter table document_request add constraint document_request__template
    foreign key (application, template)
        references document_template (application, name) ON DELETE cascade ON UPDATE cascade; 
-- account...
ALTER TABLE account DROP CONSTRAINT IF EXISTS account__most_recent_password;
alter table account add constraint account__most_recent_password
    foreign key (most_recent_password)
        references account_password (uuid) ON DELETE cascade ON UPDATE cascade; 
-- account_password...
ALTER TABLE account_password DROP CONSTRAINT IF EXISTS account_password__account;
alter table account_password add constraint account_password__account
    foreign key (account)
        references account (id) ON DELETE cascade ON UPDATE cascade; 
-- validated_ip_address...
ALTER TABLE validated_ip_address DROP CONSTRAINT IF EXISTS validated_ip_address__account;
alter table validated_ip_address add constraint validated_ip_address__account
    foreign key (account)
        references account (id) ON DELETE cascade ON UPDATE cascade; 
-- security_event...
ALTER TABLE security_event DROP CONSTRAINT IF EXISTS security_event__application;
alter table security_event add constraint security_event__application
    foreign key (application)
        references application (name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE security_event DROP CONSTRAINT IF EXISTS security_event__email_template;
alter table security_event add constraint security_event__email_template
    foreign key (application, email_template)
        references email_template (application, name) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE security_event DROP CONSTRAINT IF EXISTS security_event__account;
alter table security_event add constraint security_event__account
    foreign key (account)
        references account (id) ON DELETE cascade ON UPDATE cascade; 



-- pg_exception...
ALTER TABLE pg_exception DROP CONSTRAINT IF EXISTS pg_exception__pg_error_class;
alter table pg_exception add constraint pg_exception__pg_error_class
    foreign key (pg_class)
        references pg_error_class (code) ON DELETE cascade ON UPDATE cascade; 
ALTER TABLE pg_exception DROP CONSTRAINT IF EXISTS pg_exception__pg_base_exception;
alter table pg_exception add constraint pg_exception__pg_base_exception
    foreign key (base_exception)
        references pg_base_exception (name) ON DELETE cascade ON UPDATE cascade; 
-- remote_procedure...
ALTER TABLE remote_procedure DROP CONSTRAINT IF EXISTS remote_procedure__application;
alter table remote_procedure add constraint remote_procedure__application
    foreign key (application)
        references application (name) ON DELETE cascade ON UPDATE cascade; 