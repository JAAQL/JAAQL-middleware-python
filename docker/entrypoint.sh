#!/bin/bash
set -e

Xvfb -ac :99 -screen 0 1920x1080x16 &
export DISPLAY=:99

service cron start

if [ -z "${JEQL_VERSION}" ]; then
  echo "Using default JEQL version"
else
  echo "Switching to JEQL version $JEQL_VERSION"
  cd JEQL
  git checkout -
  git pull
  git checkout tags/v$JEQL_VERSION
  cd ../
fi
if [ -z "${SERVER_ADDRESS}" ]; then
  SERVER_ADDRESS="127.0.0.1"
fi
if [ -z "${SERVER_ADDRESS}" ]; then
  MFA_LABEL="JAAQL"
fi

mkdir -p $INSTALL_PATH/log/nginx
mkdir -p $INSTALL_PATH/www
cp -r JEQL /JAAQL-middleware-python/jaaql/apps/JEQL

JEQL_REPLACE="import * as JEQL from '../../JEQL/JEQL.js'"
sed -ri '1s@^.*$@'"$JEQL_REPLACE"'@' /JAAQL-middleware-python/jaaql/apps/console/scripts/site.js
sed -ri '1s@^.*$@'"$JEQL_REPLACE"'@' /JAAQL-middleware-python/jaaql/apps/manager/scripts/site.js
sed -ri '1s@^.*$@'"$JEQL_REPLACE"'@' /JAAQL-middleware-python/jaaql/apps/playground/scripts/site.js

cp -r /JAAQL-middleware-python/jaaql/apps $INSTALL_PATH/www

LOG_FILE=$INSTALL_PATH/log/gunicorn.log
LOG_FILE_EMAILS=$INSTALL_PATH/log/mail_service.log
LOG_FILE_SCRIPT_INSTALL=$INSTALL_PATH/log/script_install.log
ACCESS_LOG_FILE=$INSTALL_PATH/log/gunicorn_access.log

if [ "$LOG_TO_OUTPUT" = "TRUE" ] ; then
  LOG_FILE='-'
  LOG_FILE_EMAILS=/dev/stdout
  LOG_FILE_SCRIPT_INSTALL=/dev/stdout
  ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /dev/stderr /var/log/nginx/error.log
fi

DO_OVERWRITE=TRUE
SITE_FILE=/etc/nginx/sites-available/jaaql

if [ -f "$SITE_FILE" ] ; then
  WAS_HTTPS=FALSE
  if grep -lq "listen 443 ssl;" "$SITE_FILE"; then
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
  echo "limit_req_zone \$binary_remote_addr zone=jaaqllimit:10m rate=5r/s;" >> /etc/nginx/sites-available/jaaql
  echo "limit_req_zone \$binary_remote_addr zone=httplimit:10m rate=10r/s;" >> /etc/nginx/sites-available/jaaql
  if [ "$IS_HTTPS" = "TRUE" ] ; then
    echo "server {" >> /etc/nginx/sites-available/jaaql
    echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
    echo "    server_name $SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    echo "    return 301 http://www.$SERVER_ADDRESS\$request_uri;" >> /etc/nginx/sites-available/jaaql
    echo "}" >> /etc/nginx/sites-available/jaaql
    echo "" >> /etc/nginx/sites-available/jaaql
  fi
  echo "server {" >> /etc/nginx/sites-available/jaaql
  echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
  if [ "$IS_HTTPS" = "TRUE" ] ; then
    echo "    server_name www.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
  else
    echo "    server_name $SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
  fi
  echo "    root $INSTALL_PATH/www;" >> /etc/nginx/sites-available/jaaql
  echo "    index index.html;" >> /etc/nginx/sites-available/jaaql
  echo "    location / {" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req zone=httplimit burst=24 delay=16;" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req_status 429;" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "    location /api {" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req zone=jaaqllimit burst=24 delay=16;" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req_status 429;" >> /etc/nginx/sites-available/jaaql
  echo "        include proxy_params;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_pass http://unix:$INSTALL_PATH/jaaql.sock:/;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_set_header X-Real-IP \$remote_addr;" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "}" >> /etc/nginx/sites-available/jaaql
  echo "" >> /etc/nginx/sites-available/jaaql
  echo "server {" >> /etc/nginx/sites-available/jaaql
  echo "    server_name 127.0.0.1;" >> /etc/nginx/sites-available/jaaql
  echo "    location /api {" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req zone=jaaqllimit burst=24 delay=16;" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req_status 429;" >> /etc/nginx/sites-available/jaaql
  echo "        include proxy_params;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_pass http://unix:$INSTALL_PATH/jaaql.sock:/;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_set_header X-Real-IP \$remote_addr;" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "    root /JAAQL-sentinel-middleware/www;" >> /etc/nginx/sites-available/jaaql
  echo "    index index.html;" >> /etc/nginx/sites-available/jaaql
  echo "    location / {" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req zone=httplimit burst=24 delay=16;" >> /etc/nginx/sites-available/jaaql
  echo "        limit_req_status 429;" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "}" >> /etc/nginx/sites-available/jaaql
fi

rm -rf /etc/nginx/sites-enabled/jaaql  # Not strictly necessary but helps stuck containers
ln -s $SITE_FILE /etc/nginx/sites-enabled

SERVER_PROTOCOL="http:\/\/"
if [ "$IS_HTTPS" = "TRUE" ] ; then
  SERVER_PROTOCOL="https:\/\/www."
fi

replace_config() {
  sed -i 's/{{SERVER_ADDRESS}}/'$SERVER_PROTOCOL$SERVER_ADDRESS'/g' /JAAQL-middleware-python/jaaql/config/config.ini
  sed -i 's/{{MFA_LABEL}}/$MFA_LABEL/g' /JAAQL-middleware-python/jaaql/config/config.ini

  if [ "$FORCE_MFA" = "TRUE" ] ; then
    sed -i 's/{{FORCE_MFA}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{FORCE_MFA}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi

  if [ "$INVITE_ONLY" = "FALSE" ] ; then
    sed -i 's/{{INVITE_ONLY}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{INVITE_ONLY}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
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

  if [ -z "$MFA_ISSUER" ] ; then
    sed -i 's/{{MFA_ISSUER}}/'$MFA_ISSUER'/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{MFA_ISSUER}}/None/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi
}

replace_config

rm -rf /etc/nginx/sites-enabled/default
service nginx restart

CERT_DIR=/etc/letsencrypt/live/$SERVER_ADDRESS
if [ "$IS_HTTPS" = "TRUE" ] && [ ! -d "$CERT_DIR" ] ; then
  echo "Initialising certbot"
  $CERTBOT_PATH --nginx -d $SERVER_ADDRESS -d www.$SERVER_ADDRESS --redirect --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos -w $INSTALL_PATH/www
  service nginx restart
elif [ "$IS_HTTPS" = "TRUE" ] && [ -d "$CERT_DIR" ] ; then
  echo "Found existing certificates. Installing"
  printf "1,2\n1\n" | $CERTBOT_PATH --nginx
  service nginx restart
fi

docker-entrypoint.sh postgres &

if [ "$IS_HTTPS" = "TRUE" ] ; then
  if [ "$PIGGYBACK_LETSENCRYPT" = "TRUE" ] ; then
    echo "Skipping certbot renewal as piggybacking implementation"
  else
    $CERTBOT_PATH renew --dry-run &
    echo "0 0,12 * * * root $PY_PATH -c 'import random; import time; time.sleep(random.random() * 3600)' && $CERTBOT_PATH renew -q" | tee -a /etc/crontab > /dev/null
  fi
fi

cd $INSTALL_PATH
export PYTHONPATH=.
export PYTHONUNBUFFERED=TRUE

# $PY_PATH /JAAQL-middleware-python/jaaql/email/patch_ems.py &> $LOG_FILE_EMAILS &
$PY_PATH /JAAQL-middleware-python/jaaql/services/patch_script_install.py &> $LOG_FILE_SCRIPT_INSTALL &

echo "from jaaql.patch import monkey_patch" >> wsgi_patch.py
echo "monkey_patch()" >> wsgi_patch.py
echo "from wsgi import build_app" >> wsgi_patch.py

until psql -U "postgres" -d "jaaql" -c "select 1" > /dev/null 2>&1; do
  echo "Waiting for postgres server"
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
