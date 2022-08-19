docker build -t jaaql/jaaql_pg -f docker/Postgreslocal .
docker run --name jaaql_pg -it -p 5434:5432 jaaql/jaaql_pg
