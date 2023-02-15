#!/bin/bash
set -e

su -c "pg_ctl stop" postgres
rm -rf /var/lib/postgresql/data/*
docker-entrypoint.sh postgres &

until psql -U "postgres" -d "jaaql" -c "select 1" > /dev/null 2>&1; do
  echo "Waiting for postgres server"
  sleep 1
done
