docker rm jaaql-middleware-python-rebuild
docker rmi jaaql/jaaql-middleware-python-rebuild
docker build -t jaaql/jaaql-middleware-python-rebuild -f docker/Dockerfile-rebuild .
rmdir %TEMP%\baton-generated /s /q
mkdir "%TEMP%"/baton-generated/
docker run -p 80:80 --name jaaql-middleware-python-rebuild -e JAAQL_DEBUGGING=TRUE -e GUNICORN_WORKERS=3 -e LOG_TO_OUTPUT=TRUE -e POSTGRES_PASSWORD=123456 -e JAAQL_LOCAL_INSTALL=TRUE -e JAAQL_VAULT_PASSWORD=pa55word -e GUNICORN_TIMEOUT=300 -e TZ=Europe/Amsterdam -e ALLOW_UNSAFE_INLINE_SCRIPTS=TRUE jaaql/jaaql-middleware-python-rebuild
docker rm jaaql-middleware-python-rebuild
docker rmi jaaql/jaaql-middleware-python-rebuild
