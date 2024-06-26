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

disallow_all_new() {
  DATABASES=$(psql -U postgres -d postgres -t -c "SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1');")

  for DB in $DATABASES; do
      echo "Disabling connections to database: $DB"
      psql -U postgres -d postgres -c "ALTER DATABASE $DB WITH ALLOW_CONNECTIONS false;"
  done
}

disallow_all_new
# Terminate all connections to the target databases
psql -U postgres -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname IN (SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template1', 'template0'))
  AND pid <> pg_backend_pid();"

# Wait until all connections are closed
timeout=3
start_time=$(date +%s)
# Function to get current time
current_time() {
  echo $(date +%s)
}

while : ; do
  # Get the number of active connections excluding system databases
  active_connections=$(psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname NOT IN ('postgres', 'template1', 'template0');")

  # Check if there are no active connections
  if [ "$active_connections" -eq 0 ]; then
    echo "All connections closed."
    break
  fi

  # Check if the timeout has been reached
  if [ $(($(current_time) - $start_time)) -ge $timeout ]; then
    echo "Timeout reached: connections have not closed."
    break
  fi

  # Wait a bit before checking again
  sleep 0.05
done

echo "Proceeding with database and role cleanup."

# Execute the functions
drop_databases
drop_roles

psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/01-jaaql.sql