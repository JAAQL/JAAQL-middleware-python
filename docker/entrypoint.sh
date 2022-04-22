#!/bin/bash
set -e

LOG_FILE=$INSTALL_PATH/log/gunicorn.log

if [ "$LOG_TO_OUTPUT" = "TRUE" ] ; then
  LOG_FILE='-'
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
fi

if [ "$IS_HTTPS" = "TRUE" ] ; then
  sed -i 's/^    server_name www\..*/    server_name www.'$SERVER_ADDRESS';/g' $SITE_FILE
  sed -i '/^    server_name www\./!  s/^    server_name .*/    server_name '$SERVER_ADDRESS';/g' $SITE_FILE
else
  sed -i 's/^    server_name .*/    server_name '$SERVER_ADDRESS';/g' $SITE_FILE
fi

rm -rf /etc/nginx/sites-enabled/jaaql  # Not strictly necessary but helps stuck containers
ln -s $SITE_FILE /etc/nginx/sites-enabled

SERVER_PROTOCOL="http:\/\/"
if [ "$IS_HTTPS" = "TRUE" ] ; then
  SERVER_PROTOCOL="https:\/\/www."
fi

replace_config() {
  sed -i 's/{{SERVER_ADDRESS}}/'$SERVER_PROTOCOL$SERVER_ADDRESS'/g' /JAAQL-middleware-python/jaaql/config/config.ini
  sed -i 's/{{MFA_LABEL}}/'$MFA_LABEL'/g' /JAAQL-middleware-python/jaaql/config/config.ini

  if [ "$FORCE_MFA" = "FALSE" ] ; then
    sed -i 's/{{FORCE_MFA}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{FORCE_MFA}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
  fi

  if [ "$INVITE_ONLY" = "FALSE" ] ; then
    sed -i 's/{{INVITE_ONLY}}/false/g' /JAAQL-middleware-python/jaaql/config/config.ini
  else
    sed -i 's/{{INVITE_ONLY}}/true/g' /JAAQL-middleware-python/jaaql/config/config.ini
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
  /pypy3.7-v7.3.5-linux64/bin/certbot --nginx -d $SERVER_ADDRESS -d www.$SERVER_ADDRESS --redirect --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos -w $INSTALL_PATH/www
  service nginx restart
elif [ "$IS_HTTPS" = "TRUE" ] && [ -d "$CERT_DIR" ] ; then
  echo "Found existing certificates. Installing"
  printf "1,2\n1\n" | /pypy3.7-v7.3.5-linux64/bin/certbot --nginx
  service nginx restart
fi

docker-entrypoint.sh postgres &

if [ "$IS_HTTPS" = "TRUE" ] ; then
  /pypy3.7-v7.3.5-linux64/bin/certbot renew --dry-run &
fi

cd $INSTALL_PATH
export PYTHONUNBUFFERED=TRUE

echo "from jaaql.patch import monkey_patch" >> wsgi_patch.py
echo "monkey_patch()" >> wsgi_patch.py
echo "from wsgi import build_app" >> wsgi_patch.py

while :
do
  /pypy3.7-v7.3.5-linux64/bin/gunicorn --bind unix:jaaql.sock -m 777 --config /JAAQL-middleware-python/docker/gunicorn_config.py --log-file $LOG_FILE --capture-output --log-level info 'wsgi_patch:build_app()'
  chmod +777 /JAAQL-middleware-python/base_reboot.sh
  /JAAQL-middleware-python/base_reboot.sh
  replace_config
  if [ -f "reboot.sh" ] ; then
    chmod +777 reboot.sh
    ./reboot.sh
  fi
done
