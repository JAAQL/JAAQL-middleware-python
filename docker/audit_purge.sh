#!/bin/sh
# Nightly purge of the audit trail of record changes (jaaql/scripts/audit_trail.sql), run by cron as root inside the container
# (/etc/cron.d/jaaql_cron, written by entrypoint.sh). For every database that has the audit schema it calls audit.purge_expired(),
# which deletes the records older than audit.setting.keep_changes (24 months) and the rows of the retention rules older than their
# period (as an erasure, so their history goes too), each rule on its own; a failing rule is reported here and in
# audit.setting.last_purge_errors. It runs as dba, the owner of the application tables, so that the retention deletes and any
# trigger they fire never run as a superuser. Its lines go to stdout, which cron appends to $INSTALL_PATH/log/audit_purge.log
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

stamp() {
  date -u +%FT%TZ
}

if ! dbs="$(psql -U postgres -d postgres -X -A -t -c "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate AND NOT pg_is_in_recovery() ORDER BY datname")"; then
  echo "$(stamp) could not list the databases; nothing purged" >&2
  exit 1
fi

status=0
printf '%s\n' "$dbs" | {
  while IFS= read -r db; do
    if [ -z "$db" ]; then
      continue
    fi
    if [ "$(PGDATABASE="$db" psql -U postgres -X -A -t -c "SELECT to_regnamespace('audit') IS NOT NULL")" != "t" ]; then
      continue
    fi
    if [ "$(PGDATABASE="$db" psql -U postgres -X -A -t -c "SELECT count(*) FROM pg_roles WHERE rolname = 'dba'")" = "1" ]; then
      as_role="SET SESSION AUTHORIZATION dba"
    else
      as_role="SET client_min_messages = warning"
    fi
    if out="$(PGDATABASE="$db" psql -U postgres -X -q -A -t -v ON_ERROR_STOP=1 -c "$as_role" -c "SELECT 'rows purged: ' || audit.purge_expired()" 2>&1)"; then
      printf '%s\n' "$out" | while IFS= read -r line; do
        echo "$(stamp) audit trail of database \"$db\": $line"
      done
    else
      printf '%s\n' "$out" | while IFS= read -r line; do
        echo "$(stamp) audit trail of database \"$db\": $line" >&2
      done
      echo "$(stamp) audit trail of database \"$db\": the purge failed; the next night tries again" >&2
      status=1
    fi
  done
  exit $status
}
