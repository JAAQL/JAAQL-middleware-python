#!/bin/sh
set -e

DATA_DIR=/var/lib/postgresql/data
ARCHIVE_DIR=/var/lib/postgresql/archives

rm -rf $DATA_DIR/*

su - postgres -c "/usr/lib/postgresql/16/bin/initdb $DATA_DIR"

rm -rf $DATA_DIR/postgresql.conf

touch $DATA_DIR/recovery.signal
cp $ARCHIVE_DIR/recovery.conf $DATA_DIR/postgresql.conf

echo "" >> $DATA_DIR/postgresql.conf
echo "restore_command = 'cp /var/lib/postgresql/archives/archived_wal/%f %p || cp /var/lib/postgresql/archives/pg_restore_wal/%f %p'" >> $DATA_DIR/postgresql.conf
echo "recovery_target_action = 'shutdown'" >> $DATA_DIR/postgresql.conf

docker-entrypoint.sh postgres

echo "Recovery complete"

rm -rf $DATA_DIR/postgresql.conf
cp $ARCHIVE_DIR/postgresql.conf $DATA_DIR/postgresql.conf