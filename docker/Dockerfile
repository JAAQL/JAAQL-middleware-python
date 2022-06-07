FROM postgres:14.3
LABEL maintainer="jaaql.io"

EXPOSE 80
EXPOSE 443

RUN apt-get update && apt-get install -y build-essential
RUN apt install -y libpq-dev
RUN apt-get install -y git

ENV INSTALL_PATH /JAAQL-middleware-python
ENV JAAQL_DEPLOYED true
COPY . $INSTALL_PATH

RUN git clone https://github.com/JAAQL/JEQL.git
WORKDIR JEQL
RUN git checkout Release-2.1.1
WORKDIR /

RUN rm -rf $INSTALL_PATH/jaaql/config/config.ini
RUN mv $INSTALL_PATH/jaaql/config/config-docker.ini $INSTALL_PATH/jaaql/config/config.ini

RUN mkdir -p $INSTALL_PATH/www
RUN mkdir -p $INSTALL_PATH/log
RUN chown -R "$USER":www-data $INSTALL_PATH/www

RUN mkdir -p /etc/letsencrypt/live

VOLUME /etc/letsencrypt
VOLUME /etc/cron.d
VOLUME $INSTALL_PATH/vault

COPY docker/jaaql.service /lib/systemd/system/jaaql.service

RUN apt update
RUN apt -y install nginx

VOLUME /etc/nginx/sites-available/

RUN apt-get -y install libzbar0
RUN apt-get install dos2unix
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
RUN dos2unix entrypoint.sh
RUN dos2unix $INSTALL_PATH/base_reboot.sh

WORKDIR $INSTALL_PATH
RUN /pypy3.7-v7.3.5-linux64/bin/python setup.py sdist bdist_wheel

RUN VERSION=$(grep '^VERSION = ' /JAAQL-middleware-python/jaaql/constants.py | cut -d'=' -f2 | cut -d'"' -f2) && /pypy3.7-v7.3.5-linux64/bin/pip install --no-deps /JAAQL-middleware-python/dist/jaaql_middleware_python-"$VERSION"-py3-none-any.whl
WORKDIR /

ENTRYPOINT ["sh", "entrypoint.sh"]
