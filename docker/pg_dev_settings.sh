#!/bin/sh
# Emits extra postgres server arguments for a throwaway development database.
# Honoured only when the local development launcher set both variables; the database
# these settings stop protecting is dropped and rebuilt by the next build anyway.

if [ "$JAAQL_DEV_UNSAFE_POSTGRES" != "TRUE" ]; then
  exit 0
fi

if [ "$JAAQL_LOCAL_INSTALL" != "TRUE" ]; then
  echo "Ignoring JAAQL_DEV_UNSAFE_POSTGRES because JAAQL_LOCAL_INSTALL is not TRUE" >&2
  exit 0
fi

echo "Starting postgres without durability (JAAQL_DEV_UNSAFE_POSTGRES=TRUE)" >&2
echo "-c fsync=off -c synchronous_commit=off -c full_page_writes=off"
