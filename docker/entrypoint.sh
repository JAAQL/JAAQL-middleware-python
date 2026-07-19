#!/bin/sh
set -e

ensure_postgres_password() {
  if [ -n "${POSTGRES_PASSWORD}" ] && [ -z "${JAAQL_VAULT_PASSWORD}" ]; then
    return
  fi

  if [ -z "${JAAQL_VAULT_PASSWORD}" ]; then
    echo "POSTGRES_PASSWORD is not set and JAAQL_VAULT_PASSWORD is unavailable to generate one" >&2
    exit 1
  fi

  POSTGRES_PASSWORD="$($PY_PATH - <<'PY'
import os
import sys

install_path = os.environ.get("INSTALL_PATH", "/JAAQL-middleware-python")
sys.path.insert(0, install_path)

from jaaql.constants import VAULT_KEY__postgres_bootstrap_password
from jaaql.utilities.bootstrap_secrets import get_or_seed_vault_secret
from jaaql.utilities.vault import Vault

vault = Vault(os.environ["JAAQL_VAULT_PASSWORD"], os.path.join(install_path, "vault"))
value = get_or_seed_vault_secret(vault, VAULT_KEY__postgres_bootstrap_password, "POSTGRES_PASSWORD", generate_if_missing=True)
print(value or "")
PY
)"

  if [ -z "${POSTGRES_PASSWORD}" ]; then
    echo "Failed to resolve postgres bootstrap password" >&2
    exit 1
  fi

  export POSTGRES_PASSWORD
}

write_pg_hba() {
  echo "local   all             all                                     trust" > $1/pg_hba.conf
  echo "host    all             all             127.0.0.1/32            trust" >> $1/pg_hba.conf
  echo "host    all             all             ::1/128                 trust" >> $1/pg_hba.conf
  echo "local   replication     all                                     trust" >> $1/pg_hba.conf
  echo "host    replication     all             127.0.0.1/32            trust" >> $1/pg_hba.conf
  echo "host    replication     all             ::1/128                 trust" >> $1/pg_hba.conf
  echo "host all all all scram-sha-256" >> $1/pg_hba.conf
}

if [ -f /pki/ca.cert.pem ]; then
	echo "Installing on-prem root CA from /pki/ca.cert.pem"
	mkdir -p /usr/local/share/ca-certificates
	cp /pki/ca.cert.pem /usr/local/share/ca-certificates/onprem-root-ca.crt
	update-ca-certificates
fi

Xvfb -ac :99 -screen 0 1920x1080x16 &
export DISPLAY=:99

# ── EasyAuth ephemeral mode ──────────────────────────────────────────
# Azure App Service preserves the container's writable layer across
# restarts, so Postgres data / vault files can survive when they
# shouldn't.  Wipe on every entrypoint start so the container always
# initialises from scratch.  This is safe because the gunicorn
# "reboot" (to share state across workers) happens inside the while
# loop at the bottom of this script — the entrypoint does not re-run.
if [ "${USE_EASYAUTH}" = "TRUE" ]; then
  echo "EasyAuth: wiping ephemeral data for clean start"
  rm -rf /var/lib/postgresql/data/*
  rm -rf /var/lib/postgresql/archives/*
  rm -rf "${INSTALL_PATH:-/JAAQL-middleware-python}/vault"/* 2>/dev/null || true
fi

ARCHIVE_DIR=/var/lib/postgresql/archives
mkdir -p $ARCHIVE_DIR
WAS_EMPTY="false"
ensure_postgres_password

# ── Automatic postgres major upgrade ─────────────────────────────────────────
# Volumes initialised by older JAAQL images hold a postgres $JAAQL_OLD_PG_MAJOR cluster;
# upgrade it in place (pg_upgrade --link) before the server starts. set -e means any
# pg_upgrade failure aborts the boot loudly while the old cluster is still untouched.
JAAQL_OLD_PG_MAJOR=16
PG_DATA_DIR=/var/lib/postgresql/data
if [ -d "$PG_DATA_DIR/retired_pg_${JAAQL_OLD_PG_MAJOR}_cluster" ] && [ ! -s "$PG_DATA_DIR/PG_VERSION" ]; then
  echo "A previous postgres major-version upgrade was interrupted mid-swap. The old cluster files" >&2
  echo "are in $PG_DATA_DIR/retired_pg_${JAAQL_OLD_PG_MAJOR}_cluster - move them back into" >&2
  echo "$PG_DATA_DIR and restart the container to retry the upgrade" >&2
  exit 1
fi
if [ -s "$PG_DATA_DIR/PG_VERSION" ]; then
  DATA_PG_VERSION="$(cat "$PG_DATA_DIR/PG_VERSION")"
  if [ "$DATA_PG_VERSION" != "$PG_MAJOR" ]; then
    if [ "$DATA_PG_VERSION" != "$JAAQL_OLD_PG_MAJOR" ]; then
      echo "Data directory holds postgres $DATA_PG_VERSION; only $JAAQL_OLD_PG_MAJOR -> $PG_MAJOR upgrades are supported" >&2
      exit 1
    fi
    echo "Upgrading postgres data directory from $DATA_PG_VERSION to $PG_MAJOR"
    UPGRADE_NEW=$PG_DATA_DIR/pg_upgrade_new
    rm -rf $UPGRADE_NEW
    mkdir -p $UPGRADE_NEW
    chown postgres:postgres $UPGRADE_NEW
    chmod 700 $UPGRADE_NEW
    # --no-data-checksums: postgres 18 initdb enables checksums by default but pg_upgrade
    # requires the new cluster to match the old (16 default: off). Trust auth is temporary
    # for the upgrade; the strict pg_hba.conf is written after the swap
    su postgres -c "TZ=\"$TZ\" /usr/lib/postgresql/$PG_MAJOR/bin/initdb -A trust --no-data-checksums $POSTGRES_INITDB_ARGS $UPGRADE_NEW"
    su postgres -c "cd /var/lib/postgresql && /usr/lib/postgresql/$PG_MAJOR/bin/pg_upgrade --old-bindir=/usr/lib/postgresql/$JAAQL_OLD_PG_MAJOR/bin --new-bindir=/usr/lib/postgresql/$PG_MAJOR/bin --old-datadir=$PG_DATA_DIR --new-datadir=$UPGRADE_NEW --link"
    # settings applied via ALTER SYSTEM live in postgresql.auto.conf; carry them over
    if [ -f "$PG_DATA_DIR/postgresql.auto.conf" ]; then
      cp -f $PG_DATA_DIR/postgresql.auto.conf $UPGRADE_NEW/postgresql.auto.conf
      chown postgres:postgres $UPGRADE_NEW/postgresql.auto.conf
    fi
    # swap: retire the old cluster files, promote the new cluster into the volume path.
    # --link means the retired files are hardlinks; removing them frees no table data
    OLD_RETIRED=$PG_DATA_DIR/retired_pg_${JAAQL_OLD_PG_MAJOR}_cluster
    mkdir -p $OLD_RETIRED
    for cluster_entry in "$PG_DATA_DIR"/* "$PG_DATA_DIR"/.[!.]*; do
      cluster_base=$(basename "$cluster_entry")
      if [ -e "$cluster_entry" ] && [ "$cluster_base" != "pg_upgrade_new" ] && [ "$cluster_base" != "retired_pg_${JAAQL_OLD_PG_MAJOR}_cluster" ]; then
        mv "$cluster_entry" $OLD_RETIRED/
      fi
    done
    mv $UPGRADE_NEW/* $PG_DATA_DIR/
    rmdir $UPGRADE_NEW
    rm -rf $OLD_RETIRED
    write_pg_hba $PG_DATA_DIR
    rm -rf $ARCHIVE_DIR/basebackup
    cp -r $PG_DATA_DIR $ARCHIVE_DIR/basebackup
    # pg_upgrade does not transfer all planner statistics; analyze once the server is up
    touch $PG_DATA_DIR/.jaaql_needs_post_upgrade_analyze
    chown postgres:postgres $PG_DATA_DIR/.jaaql_needs_post_upgrade_analyze
    echo "Postgres upgrade to $PG_MAJOR complete"
  fi
fi

if [ -z "$(ls -A /var/lib/postgresql/data)" ] && [ -z "$IS_RESTORING" ]; then
    WAS_EMPTY="true"
    su postgres -c "echo \"$POSTGRES_PASSWORD\" | TZ=\"$TZ\" /usr/lib/postgresql/$PG_MAJOR/bin/initdb -A scram-sha-256 --pwfile=/dev/stdin $POSTGRES_INITDB_ARGS /var/lib/postgresql/data"
    rm -f $ARCHIVE_DIR/basebackup
    cp -r /var/lib/postgresql/data $ARCHIVE_DIR/basebackup
    write_pg_hba /var/lib/postgresql/data
fi

# Postgres bootstrap password is persisted in the JAAQL vault for local install fallback.
# Avoid keeping it in the long-running process environment.
unset POSTGRES_PASSWORD

if [ -z "${TZ}" ]; then
  echo "Using default timezone"
else
  echo "Using timezone $TZ"
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
fi

service cron start

CRON_FILE=/etc/cron.d/jaaql_cron
echo "* * * * * root curl -fsS --retry 3 --max-time 20 http://127.0.0.1/api/cron >/dev/null 2>&1" > "$CRON_FILE"
chmod 0644 "$CRON_FILE"
service cron reload

# We expect a backup here
if [ -z "${IS_RESTORING}" ]; then
  echo "Creating JAAQL from scratch"
else
  echo "Waiting for restore"
  while [ ! -f $INSTALL_PATH/vault/vault ]
  do
    sleep 10
  done
  echo "Detected restore"
fi


CSP_CONNECT_SRC=""
if [ -z "${SENTINEL_URL}" ] || [ "$SENTINEL_URL" = "_" ] ; then
  echo "Setting up CSP to not allow remote sentinel calls from webapp"
else
  CSP_CONNECT_SRC=" connect-src 'self' $SENTINEL_URL;"
fi

SCRIPT_SRC_ATTR=""
if [ "$ALLOW_UNSAFE_INLINE_SCRIPTS" = "TRUE" ] ; then
  SCRIPT_SRC_ATTR=" script-src-attr 'unsafe-inline';"
fi

UPGRADE_INSECURE_REQUESTS=""
if [ "$IS_HTTPS" = "TRUE" ]; then
  UPGRADE_INSECURE_REQUESTS=" upgrade-insecure-requests;"
fi

CSP_HEADER="default-src 'self'; child-src 'none';$SCRIPT_SRC_ATTR$CSP_CONNECT_SRC frame-src 'self'; object-src 'self'; worker-src 'none'; form-action 'self'; frame-ancestors 'self'; style-src-attr 'unsafe-inline';$UPGRADE_INSECURE_REQUESTS"

SECURITY_HEADERS="    charset UTF-8;\n"
if [ "$NO_CACHING" = "TRUE" ]; then
  SECURITY_HEADERS=$SECURITY_HEADERS'    expires 0;\n'
  SECURITY_HEADERS=$SECURITY_HEADERS'    add_header Cache-Control "no-cache, no-store, must-revalidate";\n'
  SECURITY_HEADERS=$SECURITY_HEADERS'    add_header Pragma no-cache;\n'
fi
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "X-Frame-Options" "DENY";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "X-Content-Type-Options" "nosniff";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "Referrer-Policy" "strict-origin-when-cross-origin";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "Cross-Origin-Opener-Policy" "same-origin";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "Cross-Origin-Embedder-Policy" "require-corp";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "Cross-Origin-Resource-Policy" "same-site";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "Permissions-Policy" "camera=(), display-capture=(), fullscreen=(), geolocation=(), interest-cohort=(), microphone=(), web-share=()";\n'
SECURITY_HEADERS=$SECURITY_HEADERS'    add_header "Content-Security-Policy" "'$CSP_HEADER'";\n'
HSTS_HEADER=""
if [ "$HSTS_PRELOAD" = "TRUE" ] && [ "$IS_HTTPS" = "TRUE" ]; then
  HSTS_HEADER='    add_header "Strict-Transport-Security" "max-age=63072000; includeSubDomains; preload";\n'
fi

if [ -z "${SERVER_ADDRESS}" ]; then
  SERVER_ADDRESS="127.0.0.1"
fi
if [ -z "${MFA_LABEL}" ]; then
  MFA_LABEL="JAAQL"
fi

mkdir -p $INSTALL_PATH/log/nginx
mkdir -p $INSTALL_PATH/www

cp -r /JAAQL-middleware-python/jaaql/apps $INSTALL_PATH/www

# ── Serverless mode: generate BATON.config.js and cache-bust assets ────
# APPLICATION_BASE_URL is only set for serverless/cloud deployments where
# reset_app.sh does not run.  Traditional deployments handle config
# generation and cache busting via reset_app.sh instead.
if [ -n "${APPLICATION_BASE_URL:-}" ]; then
  BATON_CONFIG_DIR="$INSTALL_PATH/www/__misc__"
  if [ -d "$BATON_CONFIG_DIR" ]; then
    BATON_DEPLOYED_AT=$(date +%s)
    echo "var BATON_CONFIG = { sentinelUrl: \"${SENTINEL_URL:-}\", jaaqlUrl: \"${APPLICATION_BASE_URL}\", appVersion: \"${APP_VERSION:-1.0.0}\", debug: false, deployedAt: ${BATON_DEPLOYED_AT}, deployed: true, acceptanceTesting: false };" > "$BATON_CONFIG_DIR/BATON.config.js"
    echo "Generated BATON.config.js: jaaqlUrl=${APPLICATION_BASE_URL}"
  fi

  CACHE_BUST_MARKER="$INSTALL_PATH/www/.cache_busted"
  if [ ! -f "$CACHE_BUST_MARKER" ]; then
    CACHE_BUST_ORIG_DIR=$(pwd)
    cd "$INSTALL_PATH/www"
    if ls *.html 1>/dev/null 2>&1; then
      $PY_PATH "$INSTALL_PATH/docker/cache_bust.py"
      touch "$CACHE_BUST_MARKER"
      echo "Cache busting complete"
    fi
    cd "$CACHE_BUST_ORIG_DIR"
  fi
fi

LOG_FILE=$INSTALL_PATH/log/gunicorn.log
LOG_FILE_EMAILS=$INSTALL_PATH/log/mail_service.log
LOG_FILE_MIGRATIONS=$INSTALL_PATH/log/migration_service.log
LOG_FILE_SHARED_VAR_SERVICE=$INSTALL_PATH/log/shared_var_service.log
ACCESS_LOG_FILE=$INSTALL_PATH/log/gunicorn_access.log

if [ "$LOG_TO_OUTPUT" = "TRUE" ] ; then
  LOG_FILE='-'
  LOG_FILE_EMAILS=/dev/stdout
  LOG_FILE_MIGRATIONS=/dev/stdout
  LOG_FILE_SHARED_VAR_SERVICE=/dev/stdout
  ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /dev/stderr /var/log/nginx/error.log
fi

DO_OVERWRITE=TRUE
SITE_FILE=/etc/nginx/conf.d/jaaql.conf

if [ -f "$SITE_FILE" ] ; then
  WAS_HTTPS=FALSE
  if grep -lq "listen 443 ssl" "$SITE_FILE"; then
    WAS_HTTPS=TRUE
  fi
  if [ "$WAS_HTTPS" = "$IS_HTTPS" ] ; then
    DO_OVERWRITE=FALSE
  else
    rm -rf $SITE_FILE
  fi
fi
if [ "$DO_OVERWRITE" = "TRUE" ] ; then
  echo "Writing nginx config file"
  if [ "$ALLOW_UNLIMITED_REQUESTS" = "TRUE" ]; then
    echo "Allowing unlimited requests"
  else
    echo "limit_req_zone \$binary_remote_addr zone=jaaqllimit:10m rate=3r/s;" >> $SITE_FILE
    echo "limit_req_zone \$binary_remote_addr zone=httplimit:10m rate=5r/s;" >> $SITE_FILE
  fi
  echo "server {" >> $SITE_FILE
  if [ "$IS_HTTPS_WILDCARD" != "TRUE" ]; then
    echo "    listen 80;" >> $SITE_FILE
    echo "    listen [::]:80;" >> $SITE_FILE
  fi
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    echo "    server_name $SERVER_ADDRESS *.$SERVER_ADDRESS;" >> $SITE_FILE
  else
    echo "    server_name $SERVER_ADDRESS www.$SERVER_ADDRESS;" >> $SITE_FILE
  fi
  if [ "$IS_HTTPS" = "TRUE" ] ; then
    echo "    if (\$host = www.$SERVER_ADDRESS) { return 301 https://$SERVER_ADDRESS\$request_uri; }"
  fi
  echo "$SECURITY_HEADERS$HSTS_HEADER" >> $SITE_FILE
  echo "    root $INSTALL_PATH/www;" >> $SITE_FILE
  echo "    index index.html;" >> $SITE_FILE
  echo "    location / {" >> $SITE_FILE
  if [ "$ALLOW_UNLIMITED_REQUESTS" = "TRUE" ]; then
    echo "Skipping httplimit as unlimited requests allowed"
  else
    echo "        limit_req zone=httplimit burst=24 delay=16;" >> $SITE_FILE
    echo "        limit_req_status 429;" >> $SITE_FILE
  fi
  if [ "$IS_FROZEN" = "TRUE" ] ; then
    echo "        return 503;"
  fi
  echo "    }" >> $SITE_FILE
  echo "    location /api/ {" >> $SITE_FILE
  if [ "$ALLOW_UNLIMITED_REQUESTS" = "TRUE" ]; then
    echo "Skipping jaaqllimit as unlimited requests allowed"
  else
    echo "        limit_req zone=jaaqllimit burst=10 delay=7;" >> $SITE_FILE
    echo "        limit_req_status 429;" >> $SITE_FILE
  fi
  echo "        proxy_pass http://unix:$INSTALL_PATH/jaaql.sock:/;" >> $SITE_FILE
  echo "        proxy_set_header X-Real-IP         \$remote_addr;" >> $SITE_FILE
  echo "        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;" >> $SITE_FILE
  echo "        proxy_set_header X-Forwarded-Proto \$scheme;" >> $SITE_FILE
  echo "        proxy_set_header Host              \$http_host;" >> $SITE_FILE
  if [ "$IS_FROZEN" = "TRUE" ] ; then
    echo "        return 503;"
  fi
  echo "    }" >> $SITE_FILE
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ] || [ "$SELF_CERTIFICATES" = "TRUE" ]; then
    echo "    # listen 443 ssl http2;" >> $SITE_FILE
  fi
  echo "}" >> $SITE_FILE
  echo "" >> $SITE_FILE
  # The following is needed to allow https-less access via 127.0.0.1 address
  echo "server {" >> $SITE_FILE
  echo "    listen 80;" >> $SITE_FILE
  echo "    listen [::]:80;" >> $SITE_FILE
  echo "    server_name 127.0.0.1 localhost;" >> $SITE_FILE
  echo "$SECURITY_HEADERS" >> $SITE_FILE
  echo "    root $INSTALL_PATH/www;" >> $SITE_FILE
  echo "    location /api/ {" >> $SITE_FILE
  echo "        proxy_pass http://unix:$INSTALL_PATH/jaaql.sock:/;" >> $SITE_FILE
  echo "        proxy_set_header X-Real-IP         \$remote_addr;" >> $SITE_FILE
  echo "        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;" >> $SITE_FILE
  echo "        proxy_set_header X-Forwarded-Proto \$scheme;" >> $SITE_FILE
  echo "        proxy_set_header Host              \$http_host;" >> $SITE_FILE
  echo "    }" >> $SITE_FILE
  echo "    index index.html;" >> $SITE_FILE
  echo "    location / {" >> $SITE_FILE
  echo "    }" >> $SITE_FILE
  echo "}" >> $SITE_FILE

  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    echo "server {" >> $SITE_FILE
    echo "    listen 80;" >> $SITE_FILE
    echo "    listen [::]:80;" >> $SITE_FILE
    echo "    server_name $SERVER_ADDRESS *.$SERVER_ADDRESS;" >> $SITE_FILE
    echo "    return 301 https://\$host\$request_uri;" >> $SITE_FILE
    echo "}" >> $SITE_FILE
  fi
fi

SERVER_PROTOCOL="http:\/\/"
if [ "$IS_HTTPS" = "TRUE" ] ; then
  SERVER_PROTOCOL="https:\/\/"
fi

replace_config() {
  sed -i 's/{{SERVER_ADDRESS}}/'$SERVER_PROTOCOL$SERVER_ADDRESS'/g' /JAAQL-middleware-python/jaaql/config/config.ini
  sed -i 's/{{MFA_LABEL}}/$MFA_LABEL/g' /JAAQL-middleware-python/jaaql/config/config.ini

  if [ "$FORCE_MFA" = "TRUE" ] ; then
    sed -i 's/{{FORCE_MFA}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{FORCE_MFA}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi

  if [ "$OUTPUT_QUERY_EXCEPTIONS" = "TRUE" ] ; then
    sed -i 's/{{OUTPUT_QUERY_EXCEPTIONS}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{OUTPUT_QUERY_EXCEPTIONS}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi

  if [ "$DO_AUDIT" = "FALSE" ] ; then
    sed -i 's/{{DO_AUDIT}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{DO_AUDIT}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi

  if [ -z "${MFA_ISSUER}" ] ; then
    sed -i 's/{{MFA_ISSUER}}/None/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{MFA_ISSUER}}/'$MFA_ISSUER'/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi
}

replace_config

rm -rf /etc/nginx/conf.d/default.conf
sed 's/\\n/\
/g' -i $SITE_FILE
grep -q '^[[:space:]]*server_tokens' /etc/nginx/nginx.conf || sed -i 's/http {/http {\n        server_tokens off;\n        server_names_hash_bucket_size 128;\n/g' /etc/nginx/nginx.conf
sed 's/\\n/\
/g' -i /etc/nginx/nginx.conf
service nginx restart || { echo "Failed to restart nginx. Reason: $(nginx -t 2>&1)"; exit 1; }

CERT_DIR=/etc/letsencrypt/live/$SERVER_ADDRESS
if [ "$IS_HTTPS" = "TRUE" ] && [ ! -d "$CERT_DIR" ] ; then
  echo "Initialising certbot"
  APPLY_URL="-d $SERVER_ADDRESS"
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    APPLY_URL="$APPLY_URL -d *.$SERVER_ADDRESS"
  fi

  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    APPLY_URL="$APPLY_URL -d www.*.$SERVER_ADDRESS"
  else
    APPLY_URL="$APPLY_URL -d www.$SERVER_ADDRESS"
  fi

  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    $CERTBOT_PATH certonly --manual --manual-auth-hook /certbot-dns-auth-hook.sh --manual-cleanup-hook /certbot-dns-cleanup-hook.sh --preferred-challenges dns $APPLY_URL --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos
    sed -i '/^[ \t]*# listen 443 ssl http2;/c\
    listen 443 ssl http2;\
    listen [::]:443 ssl http2;\
    ssl_certificate /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/fullchain.pem;\
    ssl_certificate_key /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/privkey.pem;\
    include /etc/letsencrypt/options-ssl-nginx.conf;\
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;' $SITE_FILE
  else
    $CERTBOT_PATH --nginx $APPLY_URL --redirect --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos -w $INSTALL_PATH/www
  fi
  service nginx restart || { echo "Failed to restart nginx. Reason: $(nginx -t 2>&1)"; exit 1; }
elif [ "$IS_HTTPS" = "TRUE" ] && [ -d "$CERT_DIR" ] ; then
  echo "Found existing certificates. Installing"
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ] || [ "$SELF_CERTIFICATES" = "TRUE" ]; then
    sed -i '/^[ \t]*# listen 443 ssl http2;/c\
    listen 443 ssl http2;\
    listen [::]:443 ssl http2;\
    ssl_certificate /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/fullchain.pem;\
    ssl_certificate_key /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/privkey.pem;\
    include /etc/letsencrypt/options-ssl-nginx.conf;' $SITE_FILE
  else
    printf "1,2\n1\n" | $CERTBOT_PATH --nginx
  fi
  service nginx restart || { echo "Failed to restart nginx. Reason: $(nginx -t 2>&1)"; exit 1; }
fi

docker-entrypoint.sh postgres &

(
	echo "TZ=$TZ"
	echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
) | /usr/bin/crontab -

if [ "$IS_HTTPS" = "TRUE" ] ; then
  if [ "$SELF_CERTIFICATES" = "TRUE" ] ; then
    echo "Skipping certbot renewal as certificates provided by user"
  elif [ "$PIGGYBACK_LETSENCRYPT" = "TRUE" ] ; then
    echo "Skipping certbot renewal as piggybacking implementation"
  else
    # Do NOT run `certbot renew --dry-run` here. Certbot 5.x's nginx plugin
    # writes ACME-challenge blocks into /etc/nginx/conf.d/jaaql.conf during a
    # dry-run and never rolls them back; reset_app.sh's set_web_config then
    # consumes that corrupted input and emits a config without
    # `listen 443 ssl;`, breaking HTTPS until manual recovery.
    (/usr/bin/crontab -l 2>/dev/null; echo "0 0,12 * * * flock -n /var/run/certbot.lock $CERTBOT_PATH renew -q") | /usr/bin/crontab -
  fi
fi

cd $INSTALL_PATH
export PYTHONPATH=.

if [ "$JAAQL_DEBUGGING" = "TRUE" ] ; then
  export PYTHONUNBUFFERED=TRUE
fi

if [ "$SKIP_EMAIL_SERVICE" = "TRUE" ]; then
	echo "Skipping email service (SKIP_EMAIL_SERVICE=TRUE)"
elif [ -f /pki/ca.cert.pem ]; then
	echo "Starting patch_ems.py with IGNORE_CERTS=TRUE"
	IGNORE_CERTS=TRUE $PY_PATH /JAAQL-middleware-python/jaaql/email/patch_ems.py &> $LOG_FILE_EMAILS &
else
	$PY_PATH /JAAQL-middleware-python/jaaql/email/patch_ems.py &> $LOG_FILE_EMAILS &
fi
$PY_PATH /JAAQL-middleware-python/jaaql/services/patch_mms.py &> $LOG_FILE_MIGRATIONS &
$PY_PATH /JAAQL-middleware-python/jaaql/services/patch_shared_var_service.py &> $LOG_FILE_SHARED_VAR_SERVICE &

echo "from jaaql.patch import monkey_patch" >> wsgi_patch.py
echo "monkey_patch()" >> wsgi_patch.py
echo "from wsgi import build_app" >> wsgi_patch.py

if [ -z "${GUNICORN_WORKERS}" ]; then
  GUNICORN_WORKERS="5"
fi

if [ -z "${GUNICORN_TIMEOUT}" ]; then
  GUNICORN_TIMEOUT="10"
fi

echo "workers = ${GUNICORN_WORKERS}" | cat - /JAAQL-middleware-python/docker/gunicorn_config.py > /JAAQL-middleware-python/docker/gunicorn_config.py.tmp
mv /JAAQL-middleware-python/docker/gunicorn_config.py.tmp /JAAQL-middleware-python/docker/gunicorn_config.py
echo "timeout = ${GUNICORN_TIMEOUT}" | cat - /JAAQL-middleware-python/docker/gunicorn_config.py > /JAAQL-middleware-python/docker/gunicorn_config.py.tmp
mv /JAAQL-middleware-python/docker/gunicorn_config.py.tmp /JAAQL-middleware-python/docker/gunicorn_config.py

cp -n /JAAQL-middleware-python/docker/generate_jwks.py generate_jwks.py
$PY_PATH generate_jwks.py

if [ "${USE_EASYAUTH}" != "TRUE" ]; then
  CN_VALUE="jaaql-key-$(echo "$SERVER_ADDRESS" | cut -c1-54)"
  openssl req -new -x509 -key /tmp/client_key.pem -out /tmp/client_cert.pem -days 3650 -subj "/CN=$CN_VALUE"
fi

if [ $WAS_EMPTY = "true" ]; then
  until psql -U "postgres" -d "postgres" -c "select 1" > /dev/null 2>&1; do
    echo "Waiting for postgres server"
    sleep 1
  done

  for sql_file in /docker-entrypoint-initdb.d/*.sql; do
    psql -U postgres -d postgres -f $sql_file
  done
fi

until psql -U "postgres" -d "jaaql" -c "select 1" > /dev/null 2>&1; do
  echo "Waiting for JAAQL db"
  sleep 1
done

if [ -f "$PG_DATA_DIR/.jaaql_needs_post_upgrade_analyze" ]; then
  echo "Rebuilding planner statistics missing after the postgres major upgrade (in background)"
  (su postgres -c "vacuumdb --all --analyze-in-stages --missing-stats-only" && rm -f $PG_DATA_DIR/.jaaql_needs_post_upgrade_analyze) &
fi

while :
do
  $GUNICORN_PATH -p app.pid --bind unix:jaaql.sock -m 777 --config /JAAQL-middleware-python/docker/gunicorn_config.py --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(M)sms"' --access-logfile $ACCESS_LOG_FILE --log-file $LOG_FILE --capture-output --log-level info 'wsgi_patch:build_app()'
  chmod +777 /JAAQL-middleware-python/base_reboot.sh
  /JAAQL-middleware-python/base_reboot.sh
  replace_config
  if [ -f "reboot.sh" ] ; then
    chmod +777 reboot.sh
    ./reboot.sh
  fi
  touch has_restarted
  if [ -f "DO_EXIT" ] ; then
    break
  fi
done
