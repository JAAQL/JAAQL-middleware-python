cd $INSTALL_PATH
export PYTHONPATH=.
$PY_PATH $INSTALL_PATH/component.py &
cd /
./entrypoint.sh

coverage combine
coverage html
