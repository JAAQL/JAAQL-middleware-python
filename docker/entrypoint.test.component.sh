cd $INSTALL_PATH
export PYTHONPATH=.
/pypy3.7-v7.3.5-linux64/bin/pypy $INSTALL_PATH/component.py &
cd /
./entrypoint.sh

coverage combine
coverage html
