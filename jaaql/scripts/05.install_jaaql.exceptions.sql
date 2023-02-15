ALTER TABLE account ALTER COLUMN id SET DEFAULT gen_random_uuid()::postgres_role;ALTER TABLE validated_ip_address ALTER COLUMN last_authentication_timestamp SET DEFAULT current_timestamp;
