#!/bin/bash

set -e

pid=$(cat JAAQL-middleware-python/app.pid)
echo "a" > JAAQL-middleware-python/vault/was_installed
kill -HUP "$pid"

sleep 1
while true; do
    http_code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/api/internal/is-alive || true)
    if [ "$http_code" -eq 200 ]; then
        break
    fi
    sleep 0.1
done

echo "Rebooted"
