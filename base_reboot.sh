#!/bin/bash
set -e

echo "Running base reboot script"

if [ -f "/JAAQL-middleware-python/redeploy" ] ; then
    echo "Redeploying"
    git clone https://github.com/JAAQL/JAAQL-middleware-python.git /JAAQL-middleware-python/JAAQL-middleware-python
    echo "Finished clone"
    rm -rf /JAAQL-middleware-python/JAAQL-middleware-python/.git
    echo "Removed git folder"
    cp -rpf /JAAQL-middleware-python/JAAQL-middleware-python/* /JAAQL-middleware-python
    echo "Overwrote files"
    rm -rf /JAAQL-middleware-python/JAAQL-middleware-python
    echo "Deleted copy"
    rm -rf /JAAQL-middleware-python/redeploy
    echo "Finished redeploy"
fi
echo "Exiting base reboot script"
