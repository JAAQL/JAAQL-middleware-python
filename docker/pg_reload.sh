sed -i 's/trust/md5/g' /var/lib/postgresql/data/pg_hba.conf
./usr/lib/postgresql/14/bin/pg_ctl reload -D /var/lib/postgresql/data