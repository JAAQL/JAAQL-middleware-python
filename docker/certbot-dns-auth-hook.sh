#!/bin/bash

echo "${CERTBOT_VALIDATION}" > /dns/txt.out

echo "Waiting for DNS propagation..."
sleep 300