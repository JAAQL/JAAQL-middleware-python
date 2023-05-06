To build you need to do the following only once to setup

    sudo apt install postgresql-common
    sudo sh /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
    sudo apt-get install postgresql-server-dev-15

Make a folder called pgextension and place everything but the bin folder in there and run
    
    make
    sudo make install

Then copy generated files to the /bin directory
    
    jaaql.so
    jaaql.bc
    jaaql.o
    /usr/lib/postgresql/15/lib/bitcode/jaaql.index.bc

Some commands to copy stuff off the box

    pscp -r ubuntu@JAAQL:/home/ubuntu/package/* compiled_package/
    pscp -r ubuntu@JAAQL:/usr/lib/postgresql/15/lib/bitcode/* compiled_package/

Building and pushing to hub
    
    sudo docker build -t jaaql/jaaql_pg -f Docker/Postgres .
    sudo docker tag jaaql/jaaql_pg jaaql/jaaql_pg:THE_VERSION
    sudo docker push jaaql/jaaql_pg
    sudo docker push jaaql/jaaql_pg:THE_VERSION

