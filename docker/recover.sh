#!/bin/sh
set -e

DATA_DIR=/var/lib/postgresql/data
ARCHIVE_DIR=/var/lib/postgresql/archives

rm -rf $DATA_DIR/*

cp -r $ARCHIVE_DIR/basebackup/* /var/lib/postgresql/data
rm -rf $DATA_DIR/postgresql.conf

touch $DATA_DIR/recovery.signal
cp -r $ARCHIVE_DIR/recovery.conf $DATA_DIR/postgresql.conf

echo "" >> $DATA_DIR/postgresql.conf

recovery_target_action="promote"
if [ -z "${RECOVERY_TARGET_ACTION}" ]; then
  recovery_target_action="promote"
else
  recovery_target_action=$RECOVERY_TARGET_ACTION
fi

echo "Using recovery_target_action $recovery_target_action"

if [ $RESTORE_FROM_BOTH = "true" ]; then
  echo "restore_command = 'cp /var/lib/postgresql/archives/archived_wal_branch/%f %p || cp /var/lib/postgresql/archives/pg_restore_wal/%f %p'" >> $DATA_DIR/postgresql.conf
else
  echo "restore_command = 'cp /var/lib/postgresql/archives/archived_wal_branch/%f %p'" >> $DATA_DIR/postgresql.conf
fi

echo "recovery_target_action = '$recovery_target_action'" >> $DATA_DIR/postgresql.conf

rm -rf /docker-entrypoint-initdb.d/*

docker-entrypoint.sh postgres &

while [ -e $DATA_DIR/recovery.signal ]; do
  sleep 1
done

su - postgres -c "/usr/lib/postgresql/16/bin/pg_ctl stop -D $DATA_DIR"

echo "Recovery complete"

rm -rf $DATA_DIR/postgresql.conf
cp $ARCHIVE_DIR/basebackup/postgresql.conf $DATA_DIR/postgresql.conf