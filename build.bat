@echo off
ECHO This script will build jaaql and push to pypi and docker
REM python setup.py sdist bdist_wheel
python version.py>version.txt
set /p VERSION=<version.txt
del version.txt
REM py -m twine upload dist/*
rmdir build /s /q
rmdir dist /s /q
rmdir jaaql_middleware_python.egg-info /s /q
docker build -t jaaql/jaaql-middleware-python -f docker/Dockerfile .
docker tag jaaql/jaaql-middleware-python jaaql/jaaql-middleware-python:%VERSION%
docker push jaaql/jaaql-middleware-python
docker push jaaql/jaaql-middleware-python:%VERSION%
