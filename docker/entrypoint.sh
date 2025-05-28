#!/bin/sh
set -e

Xvfb -ac :99 -screen 0 1920x1080x16 &
export DISPLAY=:99

ARCHIVE_DIR=/var/lib/postgresql/archives
mkdir -p $ARCHIVE_DIR
WAS_EMPTY="false"
if [ -z "$(ls -A /var/lib/postgresql/data)" ]; then
    WAS_EMPTY="true"
    su postgres -c "echo \"$POSTGRES_PASSWORD\" | TZ=\"$TZ\" /usr/lib/postgresql/16/bin/initdb -A scram-sha-256 --pwfile=/dev/stdin $POSTGRES_INITDB_ARGS /var/lib/postgresql/data"
    rm -f $ARCHIVE_DIR/basebackup
    cp -r /var/lib/postgresql/data $ARCHIVE_DIR/basebackup
    echo "local   all             all                                     trust" > /var/lib/postgresql/data/pg_hba.conf
    echo "host    all             all             127.0.0.1/32            trust" >> /var/lib/postgresql/data/pg_hba.conf
    echo "host    all             all             ::1/128                 trust" >> /var/lib/postgresql/data/pg_hba.conf
    echo "local   replication     all                                     trust" >> /var/lib/postgresql/data/pg_hba.conf
    echo "host    replication     all             127.0.0.1/32            trust" >> /var/lib/postgresql/data/pg_hba.conf
    echo "host    replication     all             ::1/128                 trust" >> /var/lib/postgresql/data/pg_hba.conf
    echo "host all all all scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
fi

if [ -z "${TZ}" ]; then
  echo "Using default timezone"
else
  echo "Using timezone $TZ"
  ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
fi

service cron start

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
SITE_FILE=/etc/nginx/sites-available/jaaql

if [ -f "$SITE_FILE" ] ; then
  WAS_HTTPS=FALSE
  if grep -lq "listen 443 ssl" "$SITE_FILE"; then
    WAS_HTTPS=TRUE
  fi
  if [ "$WAS_HTTPS" = "$IS_HTTPS" ] ; then
    DO_OVERWRITE=FALSE
  else
    rm -rf /etc/nginx/sites-available/jaaql
  fi
fi
if [ "$DO_OVERWRITE" = "TRUE" ] ; then
  echo "Writing nginx config file"
  if [ "$ALLOW_UNLIMITED_REQUESTS" = "TRUE" ]; then
    echo "Allowing unlimited requests"
  else
    echo "limit_req_zone \$binary_remote_addr zone=jaaqllimit:10m rate=3r/s;" >> /etc/nginx/sites-available/jaaql
    echo "limit_req_zone \$binary_remote_addr zone=httplimit:10m rate=5r/s;" >> /etc/nginx/sites-available/jaaql
  fi
  if [ "$IS_HTTPS" = "TRUE" ] ; then
    if [ "$HTTPS_WWW" = "TRUE" ] ; then
      echo "server {" >> /etc/nginx/sites-available/jaaql
      echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
      echo "    listen [::]:80;" >> /etc/nginx/sites-available/jaaql
      if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
        echo "    server_name $SERVER_ADDRESS *.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
      else
        echo "    server_name $SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
      fi
      echo "    return 301 http://www.\$host\$request_uri;" >> /etc/nginx/sites-available/jaaql
      echo "}" >> /etc/nginx/sites-available/jaaql
      echo "" >> /etc/nginx/sites-available/jaaql
    else
      echo "server {" >> /etc/nginx/sites-available/jaaql
      echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
      echo "    listen [::]:80;" >> /etc/nginx/sites-available/jaaql
      if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
        echo "    server_name www.$SERVER_ADDRESS www.*.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
      else
        echo "    server_name www.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
      fi
      echo "    return 301 http://\$host\$request_uri;" >> /etc/nginx/sites-available/jaaql
      echo "}" >> /etc/nginx/sites-available/jaaql
      echo "" >> /etc/nginx/sites-available/jaaql
    fi
  fi
  echo "server {" >> /etc/nginx/sites-available/jaaql
  if [ "$IS_HTTPS_WILDCARD" != "TRUE" ]; then
    echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
    echo "    listen [::]:80;" >> /etc/nginx/sites-available/jaaql
  fi
  if [ "$IS_HTTPS" = "TRUE" ] && [ "$HTTPS_WWW" = "TRUE" ] ; then
    if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
      echo "    server_name www.$SERVER_ADDRESS www.*.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    else
      echo "    server_name www.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    fi
  else
    if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
      echo "    server_name $SERVER_ADDRESS *.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    else
      echo "    server_name $SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    fi
  fi
  echo "$SECURITY_HEADERS$HSTS_HEADER" >> /etc/nginx/sites-available/jaaql
  echo "    root $INSTALL_PATH/www;" >> /etc/nginx/sites-available/jaaql
  echo "    index index.html;" >> /etc/nginx/sites-available/jaaql
  echo "    location / {" >> /etc/nginx/sites-available/jaaql
  if [ "$ALLOW_UNLIMITED_REQUESTS" = "TRUE" ]; then
    echo "Skipping httplimit as unlimited requests allowed"
  else
    echo "        limit_req zone=httplimit burst=24 delay=16;" >> /etc/nginx/sites-available/jaaql
    echo "        limit_req_status 429;" >> /etc/nginx/sites-available/jaaql
  fi
  if [ "$IS_FROZEN" = "TRUE" ] ; then
    echo "        return 503;"
  fi
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "    location /api {" >> /etc/nginx/sites-available/jaaql
  if [ "$ALLOW_UNLIMITED_REQUESTS" = "TRUE" ]; then
    echo "Skipping jaaqllimit as unlimited requests allowed"
  else
    echo "        limit_req zone=jaaqllimit burst=10 delay=7;" >> /etc/nginx/sites-available/jaaql
    echo "        limit_req_status 429;" >> /etc/nginx/sites-available/jaaql
  fi
  echo "        include proxy_params;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_pass http://unix:$INSTALL_PATH/jaaql.sock:/;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_set_header X-Real-IP \$remote_addr;" >> /etc/nginx/sites-available/jaaql
  if [ "$IS_FROZEN" = "TRUE" ] ; then
    echo "        return 503;"
  fi
  echo "    }" >> /etc/nginx/sites-available/jaaql
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    echo "    # listen 443 ssl http2;" >> /etc/nginx/sites-available/jaaql
  fi
  echo "}" >> /etc/nginx/sites-available/jaaql
  echo "" >> /etc/nginx/sites-available/jaaql
  # The following is needed to allow https-less access via 127.0.0.1 address
  echo "server {" >> /etc/nginx/sites-available/jaaql
  echo "    server_name localhost;" >> /etc/nginx/sites-available/jaaql
  echo "$SECURITY_HEADERS" >> /etc/nginx/sites-available/jaaql
  echo "    root $INSTALL_PATH/www;" >> /etc/nginx/sites-available/jaaql
  echo "    location /api {" >> /etc/nginx/sites-available/jaaql
  echo "        include proxy_params;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_pass http://unix:$INSTALL_PATH/jaaql.sock:/;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_set_header X-Real-IP \$remote_addr;" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "    index index.html;" >> /etc/nginx/sites-available/jaaql
  echo "    location / {" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "}" >> /etc/nginx/sites-available/jaaql

  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    echo "server {" >> /etc/nginx/sites-available/jaaql
    echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
    echo "    listen [::]:80;" >> /etc/nginx/sites-available/jaaql
    echo "    server_name $SERVER_ADDRESS *.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    echo "    return 301 https://\$host\$request_uri;" >> /etc/nginx/sites-available/jaaql
    echo "}" >> /etc/nginx/sites-available/jaaql
  fi
fi

rm -rf /etc/nginx/sites-enabled/jaaql  # Not strictly necessary but helps stuck containers
ln -s $SITE_FILE /etc/nginx/sites-enabled

SERVER_PROTOCOL="http:\/\/"
if [ "$IS_HTTPS" = "TRUE" ] ; then
  if [ "$HTTPS_WWW" = "TRUE" ] ; then
    SERVER_PROTOCOL="https:\/\/www."
  else
    SERVER_PROTOCOL="https:\/\/"
  fi
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

rm -rf /etc/nginx/sites-enabled/default
sed 's/\\n/\
/g' -i /etc/nginx/sites-available/jaaql
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
  if [ "$HTTPS_WWW" = "TRUE" ] ; then
    APPLY_URL="$APPLY_URL -d www.$SERVER_ADDRESS"
    if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
      APPLY_URL="$APPLY_URL -d www.*.$SERVER_ADDRESS"
    fi
  fi
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    $CERTBOT_PATH certonly --manual --manual-auth-hook /certbot-dns-auth-hook.sh --manual-cleanup-hook /certbot-dns-cleanup-hook.sh --preferred-challenges dns $APPLY_URL --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos
    sed -i '/^[ \t]*# listen 443 ssl http2;/c\
    listen 443 ssl http2;\
    listen [::]:443 ssl http2;\
    ssl_certificate /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/fullchain.pem;\
    ssl_certificate_key /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/privkey.pem;\
    include /etc/letsencrypt/options-ssl-nginx.conf;\
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;' /etc/nginx/sites-available/jaaql
  else
    $CERTBOT_PATH --nginx $APPLY_URL --redirect --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos -w $INSTALL_PATH/www
  fi
  service nginx restart || { echo "Failed to restart nginx. Reason: $(nginx -t 2>&1)"; exit 1; }
elif [ "$IS_HTTPS" = "TRUE" ] && [ -d "$CERT_DIR" ] ; then
  echo "Found existing certificates. Installing"
  if [ "$IS_HTTPS_WILDCARD" = "TRUE" ]; then
    sed -i '/^[ \t]*# listen 443 ssl http2;/c\
    listen 443 ssl http2;\
    listen [::]:443 ssl http2;\
    ssl_certificate /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/fullchain.pem;\
    ssl_certificate_key /etc/letsencrypt/live/'"$SERVER_ADDRESS"'/privkey.pem;\
    include /etc/letsencrypt/options-ssl-nginx.conf;\
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;' /etc/nginx/sites-available/jaaql
  else
    if [ "$HTTPS_WWW" = "TRUE" ] ; then
      printf "1,2\n1\n" | $CERTBOT_PATH --nginx
    else
      printf "1\n1\n" | $CERTBOT_PATH --nginx
    fi
  fi
  service nginx restart || { echo "Failed to restart nginx. Reason: $(nginx -t 2>&1)"; exit 1; }
fi

docker-entrypoint.sh postgres &

(echo "TZ=$TZ") | /usr/bin/crontab -

if [ "$IS_HTTPS" = "TRUE" ] ; then
  if [ "$PIGGYBACK_LETSENCRYPT" = "TRUE" ] ; then
    echo "Skipping certbot renewal as piggybacking implementation"
  else
    $CERTBOT_PATH renew --dry-run &
    (/usr/bin/crontab -l 2>/dev/null; echo "0 0,12 * * * $PY_PATH -c 'import random; import time; time.sleep(random.random() * 3600)' && $CERTBOT_PATH renew -q") | /usr/bin/crontab -
  fi
fi

cd $INSTALL_PATH
export PYTHONPATH=.

if [ "$JAAQL_DEBUGGING" = "TRUE" ] ; then
  export PYTHONUNBUFFERED=TRUE
fi

$PY_PATH /JAAQL-middleware-python/jaaql/email/patch_ems.py &> $LOG_FILE_EMAILS &
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

mv /JAAQL-middleware-python/docker/generate_jwks.py generate_jwks.py
$PY_PATH generate_jwks.py

openssl req -new -x509 -key /tmp/client_key.pem -out /tmp/client_cert.pem -days 3650 -subj "/CN=jaaql-key-$SERVER_ADDRESS"

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
