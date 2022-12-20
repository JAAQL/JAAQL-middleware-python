FROM postgres:15.0
LABEL maintainer="jaaql.io"

EXPOSE 80
EXPOSE 443

RUN apt-get update && apt-get install -y build-essential
RUN apt install -y libpq-dev
RUN apt-get install -y git
RUN apt-get install -y cron

ENV INSTALL_PATH /JAAQL-middleware-python
ENV JAAQL_DEPLOYED true
ENV PIGGYBACK_LETSENCRYPT FALSE
COPY . $INSTALL_PATH

RUN git clone https://github.com/JAAQL/JEQL.git
WORKDIR JEQL
RUN git checkout tags/v3.0.4
WORKDIR /

RUN rm -rf $INSTALL_PATH/jaaql/config/config.ini
RUN mv $INSTALL_PATH/jaaql/config/config-docker.ini $INSTALL_PATH/jaaql/config/config.ini

RUN mkdir -p $INSTALL_PATH/www
RUN mkdir -p $INSTALL_PATH/log
RUN chown -R "$USER":www-data $INSTALL_PATH/www

RUN mkdir -p /etc/letsencrypt/live

VOLUME /etc/letsencrypt
VOLUME $INSTALL_PATH/vault

COPY docker/jaaql.service /lib/systemd/system/jaaql.service

RUN apt update
RUN apt -y install nginx

VOLUME /etc/nginx/sites-available/

RUN mkdir -p /user_files
VOLUME /user_files

RUN apt-get -y install libzbar0
RUN apt-get install dos2unix
RUN apt -y install bzip2
RUN apt -y install wget
RUN wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tar.xz
RUN tar xf Python-3.11.0.tar.xz
RUN apt install build-essential zlib1g-dev \
    libncurses5-dev libgdbm-dev libnss3-dev \
    libssl-dev libreadline-dev libffi-dev curl -y
WORKDIR /Python-3.11.0
RUN ./configure --enable-optimizations --prefix=/usr/local --with-ensurepip=install
RUN make install
ENV PY_PATH /usr/local/bin/python3
ENV PIP_PATH /usr/local/bin/pip3
ENV GUNICORN_PATH /usr/local/bin/gunicorn
ENV CERTBOT_PATH /usr/local/bin/certbot
WORKDIR /
RUN $PY_PATH -m ensurepip --default-pip
RUN $PY_PATH -mpip install -U pip wheel
RUN $PY_PATH -mpip install certbot-nginx==1.2.0
RUN $PY_PATH -mpip install -r $INSTALL_PATH/requirements.txt

RUN mv $INSTALL_PATH/docker/jaaql.sql /docker-entrypoint-initdb.d/01-jaaql.sql
RUN dos2unix $INSTALL_PATH/docker/pg_reload.sh
RUN mv $INSTALL_PATH/docker/pg_reload.sh /docker-entrypoint-initdb.d/02-pg_reload.sh
RUN mv $INSTALL_PATH/docker/entrypoint.sh entrypoint.sh
RUN dos2unix entrypoint.sh
RUN dos2unix $INSTALL_PATH/base_reboot.sh

WORKDIR $INSTALL_PATH
RUN $PY_PATH setup.py sdist bdist_wheel

RUN VERSION=$(grep '^VERSION = ' /JAAQL-middleware-python/jaaql/constants.py | cut -d'=' -f2 | cut -d'"' -f2) && $PIP_PATH install --no-deps /JAAQL-middleware-python/dist/jaaql_middleware_python-"$VERSION"-py3-none-any.whl
WORKDIR /

ARG CHROME_VERSION="95.0.4638.69-1"
RUN wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb \
  && apt install -y /tmp/chrome.deb \
  && rm /tmp/chrome.deb

RUN mkdir -p $INSTALL_PATH/log

RUN apt-get install unzip
RUN wget -N https://chromedriver.storage.googleapis.com/95.0.4638.69/chromedriver_linux64.zip -P ~/
RUN unzip ~/chromedriver_linux64.zip -d ~/
RUN rm ~/chromedriver_linux64.zip
RUN mv -f ~/chromedriver /usr/local/bin/chromedriver
RUN chown root:root /usr/local/bin/chromedriver
RUN chmod 0755 /usr/local/bin/chromedriver
RUN apt-get install -y gstreamer1.0-libav libnss3-tools libatk-bridge2.0-0 libcups2-dev libxkbcommon-x11-0 libxcomposite-dev libxrandr2 libgbm-dev libgtk-3-0
RUN apt-get install -y xvfb
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf
RUN apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable
RUN apt-get -y install imagemagick x11-apps

COPY ./pgextension /pgextension
RUN /bin/mkdir -p '/usr/share/postgresql/15/extension'
RUN /bin/mkdir -p '/usr/lib/postgresql/15/lib'
RUN /usr/bin/install -c -m 644 /pgextension/jaaql.control '/usr/share/postgresql/15/extension/'
RUN /usr/bin/install -c -m 644 /pgextension/jaaql--1.0.0.sql  '/usr/share/postgresql/15/extension/'
RUN /usr/bin/install -c -m 755 /pgextension/bin/jaaql.so '/usr/lib/postgresql/15/lib/'
RUN /bin/mkdir -p '/usr/lib/postgresql/15/lib/bitcode/jaaql'
RUN /bin/mkdir -p '/usr/lib/postgresql/15/lib/bitcode'/jaaql/
RUN /usr/bin/install -c -m 644 /pgextension/bin/jaaql.bc '/usr/lib/postgresql/15/lib/bitcode'/jaaql/./
RUN mv /pgextension/bin/jaaql.index.bc '/usr/lib/postgresql/15/lib/bitcode'

ENTRYPOINT ["sh", "entrypoint.sh"]