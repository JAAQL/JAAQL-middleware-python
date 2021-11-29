#!/bin/bash
set -e


if [ -f "/JAAQL-middleware-python/redeploy" ] ; then
    git clone https://github.com/JAAQL/JAAQL-middleware-python.git /JAAQL-middleware-python/JAAQL-middleware-python
    rm -rf /JAAQL-middleware-python/JAAQL-middleware-python/.git
    cp -rpf /JAAQL-middleware-python/JAAQL-middleware-python/* /JAAQL-middleware-python
    rm -rf /JAAQL-middleware-python/JAAQL-middleware-python
    rm -rf /JAAQL-middleware-python/redeploy
fi
