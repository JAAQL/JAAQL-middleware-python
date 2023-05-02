docker rm jaaql-middleware-python-rebuild
docker rmi jaaql/jaaql-middleware-python-rebuild
docker build -t jaaql/jaaql-middleware-python-rebuild -f docker/Dockerfile-rebuild .
rmdir %TEMP%\baton-generated /s /q
mkdir "%TEMP%"/baton-generated/
docker run -p 80:80 -e LOG_TO_OUTPUT=TRUE --mount type=bind,source="%TEMP%"/baton-generated/,target=/JAAQL-middleware-python/www --mount type=bind,source="%TEMP%"/baton-generated/artifacts,target=/JAAQL-middleware-python/www/artifacts --name jaaql-middleware-python-rebuild -e GUNICORN_WORKERS=15 -e POSTGRES_PASSWORD=123456 -e JAAQL_VAULT_PASSWORD=pa55word jaaql/jaaql-middleware-python-rebuild
docker rm jaaql-middleware-python-rebuild
docker rmi jaaql/jaaql-middleware-python-rebuild
