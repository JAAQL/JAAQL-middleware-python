@echo off
ECHO This script will build jaaql and push to pypi and docker
python setup.py sdist bdist_wheel
python version.py>version.txt
set /p VERSION=<version.txt
del version.txt
py -m twine upload dist/*
rmdir build /s /q
rmdir dist /s /q
rmdir jaaql_middleware_python.egg-info /s /q
docker build -t jaaql/jaaql-middleware-python:%VERSION% -f docker/Dockerfile .
docker push jaaql/jaaql-middleware-python:%VERSION%
