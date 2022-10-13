rmdir /s /q swagger
rmdir /s /q vault
call pg_teardown.bat
docker run --name jaaql_pg -it -p 5434:5432 jaaql/jaaql_pg
call pg_teardown.bat
