#!/bin/sh
set -e

DATA_DIR=/var/lib/postgresql/data
ARCHIVE_DIR=/var/lib/postgresql/archives
PG_BIN=/usr/lib/postgresql/$PG_MAJOR/bin

# How long PostgreSQL may take to finish the promotion once it has removed recovery.signal: it still writes the
# timeline history file and the end-of-recovery checkpoint, which writes out every page the recovery replayed
PROMOTION_TIMEOUT_SECONDS="${RECOVERY_PROMOTION_TIMEOUT_SECONDS:-900}"

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
if [ "$recovery_target_action" = "pause" ]; then
  echo "At the recovery target PostgreSQL pauses: recover.sh waits until pg_wal_replay_resume() or pg_promote() is run over the socket, then for the promotion"
fi

if [ "$RESTORE_FROM_BOTH" = "true" ]; then
  echo "restore_command = 'cp /var/lib/postgresql/archives/archived_wal_branch/%f %p || cp /var/lib/postgresql/archives/pg_restore_wal/%f %p'" >> $DATA_DIR/postgresql.conf
else
  echo "restore_command = 'cp /var/lib/postgresql/archives/archived_wal_branch/%f %p'" >> $DATA_DIR/postgresql.conf
fi

echo "recovery_target_action = '$recovery_target_action'" >> $DATA_DIR/postgresql.conf

rm -rf /docker-entrypoint-initdb.d/*

# The state pg_control records: "in archive recovery" until the promotion has finished, then "in production", and
# "shut down" after a clean stop. A stop before "in production" leaves "shut down in recovery", from which the next
# start runs crash recovery on the old timeline through every WAL file in pg_wal, past the recovery target
cluster_state() {
  LC_ALL=C LANGUAGE=C "$PG_BIN/pg_controldata" -D "$DATA_DIR" 2>/dev/null | sed -n 's/^Database cluster state:[[:space:]]*//p'
}

cluster_timeline() {
  LC_ALL=C LANGUAGE=C "$PG_BIN/pg_controldata" -D "$DATA_DIR" 2>/dev/null | sed -n "s/^Latest checkpoint's TimeLineID:[[:space:]]*//p"
}

# docker-entrypoint.sh execs into the postmaster, so its pid is the server's. A server that has exited stays in the
# process table as a zombie until this shell reaps it
server_running() {
  kill -0 "$SERVER_PID" 2>/dev/null || return 1
  case "$(sed -n 's/^State:[[:space:]]*\(.\).*/\1/p' "/proc/$SERVER_PID/status" 2>/dev/null)" in
    Z|X|"") return 1 ;;
  esac
  return 0
}

recovery_failed() {
  echo "RECOVERY FAILED: $1" >&2
  echo "pg_control says: Database cluster state: $(cluster_state)" >&2
  echo "The data directory does not hold a finished recovery: do not start JAAQL on it. Run the restore again, which starts over from the base backup" >&2
  exit 1
}

docker-entrypoint.sh postgres &
SERVER_PID=$!

while [ -e $DATA_DIR/recovery.signal ]; do
  if ! server_running; then
    if [ "$recovery_target_action" = "shutdown" ]; then
      recovery_failed "PostgreSQL shut down at the recovery target without promoting, as recovery_target_action = 'shutdown' asks"
    fi
    recovery_failed "PostgreSQL stopped before the recovery reached its end (its log is above)"
  fi
  sleep 1
done

echo "PostgreSQL removed recovery.signal: waiting up to $PROMOTION_TIMEOUT_SECONDS s for the promotion to finish"
waited=0
while [ "$(cluster_state)" != "in production" ]; do
  if ! server_running; then
    recovery_failed "PostgreSQL stopped before the promotion finished (its log is above)"
  fi
  if [ "$waited" -ge "$PROMOTION_TIMEOUT_SECONDS" ]; then
    recovery_failed "PostgreSQL had not finished the promotion $PROMOTION_TIMEOUT_SECONDS s after it removed recovery.signal (RECOVERY_PROMOTION_TIMEOUT_SECONDS sets this wait, passed to the restore container with docker run -e). recover.sh exits without stopping it, as a stop before the promotion has finished leaves the cluster shut down in recovery, and when recover.sh is the container's first process its exit kills PostgreSQL mid-promotion"
  fi
  sleep 1
  waited=$((waited + 1))
done

echo "Promotion finished: the cluster is in production"

if ! su - postgres -c "$PG_BIN/pg_ctl stop -D $DATA_DIR -m fast -t 600"; then
  recovery_failed "pg_ctl could not stop PostgreSQL after the promotion"
fi
wait "$SERVER_PID" || true

if [ "$(cluster_state)" != "shut down" ]; then
  recovery_failed "PostgreSQL did not shut down cleanly after the promotion"
fi

# Read from the shutdown checkpoint, which is on the new timeline: a fast promotion (pg_promote) reaches "in production"
# with only an end-of-recovery record, so the latest checkpoint is still the old timeline's until the stop. "Recovery
# complete" stays a line of its own, which the backup tests and the run sheets look for
echo "PostgreSQL shut down cleanly on timeline $(cluster_timeline)"
echo "Recovery complete"

rm -rf $DATA_DIR/postgresql.conf
cp $ARCHIVE_DIR/basebackup/postgresql.conf $DATA_DIR/postgresql.conf
