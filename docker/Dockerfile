FROM postgres:14.0
LABEL maintainer="jaaql.io"

EXPOSE 80
EXPOSE 443

RUN apt-get update && apt-get install -y build-essential
RUN apt install -y libpq-dev

ENV INSTALL_PATH /JAAQL-middleware-python
COPY . $INSTALL_PATH

RUN rm -rf $INSTALL_PATH/jaaql/config/config.ini
RUN mv $INSTALL_PATH/jaaql/config/config-docker.ini $INSTALL_PATH/config/config.ini

RUN mkdir -p $INSTALL_PATH/www
RUN mkdir -p $INSTALL_PATH/log
RUN chcon -R -h -t httpd_sys_content_t $INSTALL_PATH/www

RUN mkdir -p /etc/letsencrypt

VOLUME /etc/letsencrypt
VOLUME /etc/cron.d
VOLUME $INSTALL_PATH/vault

COPY docker/jaaql.service /lib/systemd/system/jaaql.service

RUN apt update
RUN apt -y install nginx

VOLUME /etc/nginx/sites-available/

RUN apt -y install bzip2
RUN apt -y install wget
RUN wget https://downloads.python.org/pypy/pypy3.7-v7.3.5-linux64.tar.bz2
RUN tar xf pypy3.7-v7.3.5-linux64.tar.bz2
RUN ./pypy3.7-v7.3.5-linux64/bin/pypy -m ensurepip --default-pip
RUN ./pypy3.7-v7.3.5-linux64/bin/pypy -mpip install -U pip wheel
RUN ./pypy3.7-v7.3.5-linux64/bin/pypy -mpip install certbot-nginx==1.2.0
RUN ./pypy3.7-v7.3.5-linux64/bin/pypy -mpip install -r $INSTALL_PATH/requirements.txt

RUN mv $INSTALL_PATH/docker/jaaql.sql /docker-entrypoint-initdb.d/jaaql.sql
RUN mv $INSTALL_PATH/docker/entrypoint.sh entrypoint.sh

ENTRYPOINT ["sh", "entrypoint.sh"]
