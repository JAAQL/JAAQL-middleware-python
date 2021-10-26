#!/bin/bash
set -e

DO_OVERWRITE=TRUE
SITE_FILE=/etc/nginx/sites-available/jaaql

if [ -f "$SITE_FILE" ] ; then
  WAS_HTTPS=FALSE
  if [ grep -q "listen 443 ssl;" "$SITE_FILE" ] ; then
    WAS_HTTPS=TRUE
  fi
  if [ "$WAS_HTTPS" = "$IS_HTTPS" ] ; then
    DO_OVERWRITE=FALSE
  fi
fi
if [ "$DO_OVERWRITE" = "TRUE" ] ; then
  echo "Writing nginx config file"
  if [ "$IS_HTTPS" = "TRUE" ] ; then
    echo "server {" >> /etc/nginx/sites-available/jaaql
    echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
    echo "    server_name $SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
    echo "    return 301 http://www.$SERVER_ADDRESS\$request_uri;" >> /etc/nginx/sites-available/jaaql
    echo "}" >> /etc/nginx/sites-available/jaaql
    echo "" >> /etc/nginx/sites-available/jaaql
  fi
  echo "server {" > /etc/nginx/sites-available/jaaql
  echo "    listen 80;" >> /etc/nginx/sites-available/jaaql
  if [ "$IS_HTTPS" = "TRUE" ] ; then
    echo "    server_name www.$SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
  else
    echo "    server_name $SERVER_ADDRESS;" >> /etc/nginx/sites-available/jaaql
  fi
  echo "    root /JAAQL-middleware-python/www;" >> /etc/nginx/sites-available/jaaql
  echo "    index index.html;" >> /etc/nginx/sites-available/jaaql
  echo "    location /api {" >> /etc/nginx/sites-available/jaaql
  echo "        include proxy_params;" >> /etc/nginx/sites-available/jaaql
  echo "        proxy_pass http://unix:/JAAQL-middleware-python/jaaql.sock:/;" >> /etc/nginx/sites-available/jaaql
  echo "    }" >> /etc/nginx/sites-available/jaaql
  echo "}" >> /etc/nginx/sites-available/jaaql
fi

if [ "$IS_HTTPS" = "TRUE" ] ; then
  sed -i 's/^    server_name www\..*/    server_name www.'$SERVER_ADDRESS';/g' $SITE_FILE
  sed -i '/^    server_name www\./!  s/^    server_name .*/    server_name '$SERVER_ADDRESS';/g' $SITE_FILE
else
  sed -i 's/^    server_name .*/    server_name '$SERVER_ADDRESS';/g' $SITE_FILE
fi

ln -s $SITE_FILE /etc/nginx/sites-enabled

SERVER_PROTOCOL="http"
if [ "$IS_HTTPS" = "TRUE" ] ; then
  SERVER_PROTOCOL="https"
fi

sed -i 's/{{SERVER_ADDRESS}}/'$SERVER_PROTOCOL':\/\/'$SERVER_ADDRESS'/g' /JAAQL-middleware-python/config/config.ini

CERT_DIR=/etc/letsencrypt/live/$SERVER_ADDRESS
if [[ "$IS_HTTPS" = "TRUE" && ! -d "$CERT_DIR" ]] ; then
  echo "Initialising certbot"
  /pypy3.7-v7.3.5-linux64/bin/certbot --nginx -d $SERVER_ADDRESS -d www.$SERVER_ADDRESS --redirect --noninteractive --no-eff-email --email $HTTPS_EMAIL --agree-tos --webroot /JAAQL-middleware-python/www
fi

service nginx restart
docker-entrypoint.sh postgres &

if [ "$IS_HTTPS" = "TRUE" ] ; then
  certbot renew --dry-run
fi

cd /JAAQL-middleware-python
export PYTHONUNBUFFERED=TRUE
/pypy3.7-v7.3.5-linux64/bin/gunicorn --bind unix:jaaql.sock -m 777 --config docker/gunicorn_config.py --log-file /JAAQL-middleware-python/log/gunicorn.log --capture-output --log-level info 'wsgi:build_app()'
