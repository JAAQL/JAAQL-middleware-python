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
    rm -rf /JAAQL-middleware-python/jaaql/config/config.ini
    mv /JAAQL-middleware-python/jaaql/config/config-docker.ini /JAAQL-middleware-python/jaaql/config/config.ini
    echo "Moved config"
    rm -rf /JAAQL-middleware-python/redeploy
    echo "Removed deployment code"
    cd / && $PYPY_PATH/bin/pip uninstall --verbose jaaql-middleware-python -y
    cd /JAAQL-middleware-python
    rm -rf dist
    $PYPY_PATH/bin/python setup.py sdist bdist_wheel
    VERSION=$(grep '^VERSION = ' /JAAQL-middleware-python/jaaql/constants.py | cut -d'=' -f2 | cut -d'"' -f2) && $PYPY_PATH/bin/pip install --force-reinstall --no-deps /JAAQL-middleware-python/dist/jaaql_middleware_python-"$VERSION"-py3-none-any.whl
    echo "Removed deployment code"
fi
echo "Exiting base reboot script"
