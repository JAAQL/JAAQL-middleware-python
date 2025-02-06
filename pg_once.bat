rmdir /s /q swagger
rmdir /s /q vault
call pg_teardown.bat
rd /s /q %TEMP%/jaaql-debug-slurp-in
mkdir %TEMP%/jaaql-debug-slurp-in
docker run --name jaaql_pg -it -p 5434:5432 --mount type=bind,source=%TEMP%/jaaql-debug-slurp-in,target=/slurp-in jaaql/jaaql_pg
