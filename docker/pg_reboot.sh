#!/bin/bash
set -e

# Function to drop all databases except the essential ones
drop_databases() {
    PSQL="psql -U postgres -d postgres -t -c"
    $PSQL "SELECT 'DROP DATABASE \"' || datname || '\";' FROM pg_database WHERE datname NOT IN ('postgres', 'template1', 'template0');" | psql -U postgres -d postgres
}

# Function to drop all user-created roles
drop_roles() {
    PSQL="psql -U postgres -d postgres -t -c"
    $PSQL "SELECT 'DROP ROLE IF EXISTS \"' || rolname || '\";' FROM pg_roles WHERE rolname NOT IN ('postgres', 'pg_database_owner', 'pg_read_all_data', 'pg_write_all_data', 'pg_monitor', 'pg_read_all_settings', 'pg_read_all_stats', 'pg_stat_scan_tables', 'pg_read_server_files', 'pg_write_server_files', 'pg_execute_server_program', 'pg_signal_backend', 'pg_checkpoint', 'pg_use_reserved_connections', 'pg_create_subscription');" | psql -U postgres -d postgres
}

# Terminate all connections to the target databases
psql -U postgres -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname IN (SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template1', 'template0'))
  AND pid <> pg_backend_pid();"

# Wait until all connections are closed
until [ $(psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname NOT IN ('postgres', 'template1', 'template0');") -eq 0 ]; do
  echo "Waiting for connections to close..."
  sleep 0.05 # Adjust this value as needed to balance efficiency and CPU usage
done

echo "All connections closed. Proceeding with database and role cleanup."

# Execute the functions
drop_databases
drop_roles

psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/01-jaaql.sql