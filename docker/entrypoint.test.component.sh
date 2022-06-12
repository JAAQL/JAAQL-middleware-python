cd $INSTALL_PATH
export PYTHONUNBUFFERED=TRUE
export PYTHONPATH=.
$PYPY_PATH/bin/pypy $INSTALL_PATH/component.py &
cd /
./entrypoint.sh

coverage combine
coverage html
