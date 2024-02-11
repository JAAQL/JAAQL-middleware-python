@echo off
ECHO This script will build jaaql and not push to pypi and docker
python setup.py sdist bdist_wheel
python version.py>version.txt
set /p VERSION=<version.txt
del version.txt
rmdir build /s /q
rmdir dist /s /q
rmdir jaaql_middleware_python.egg-info /s /q
docker build -t jaaql/jaaql-middleware-python -f docker/Dockerfile .
docker tag jaaql/jaaql-middleware-python jaaql/jaaql-middleware-python:%VERSION%
