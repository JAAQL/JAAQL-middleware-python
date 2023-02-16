ALTER TABLE account ALTER COLUMN id SET DEFAULT gen_random_uuid()::postgres_role;
ALTER TABLE validated_ip_address ALTER COLUMN last_authentication_timestamp SET DEFAULT current_timestamp;
ALTER TABLE application ADD constraint application__is_live_has_default_schema check (is_live is false or default_schema is not null);
