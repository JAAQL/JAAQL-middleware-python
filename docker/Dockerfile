FROM postgres:15.2
LABEL maintainer="jaaql.io"

EXPOSE 80
EXPOSE 443

ENV PY_PATH /usr/local/bin/python3
ENV PIP_PATH /usr/local/bin/pip3
ENV GUNICORN_PATH /usr/local/bin/gunicorn
ENV CERTBOT_PATH /usr/local/bin/certbot
ENV INSTALL_PATH /JAAQL-middleware-python
ENV JAAQL_CONFIG_LOC /JAAQL-config
ENV JAAQL_DEPLOYED true
ENV PIGGYBACK_LETSENCRYPT FALSE

ENV LANG en_GB.UTF-8
ENV LANGUAGE en_GB:en
ENV LC_ALL en_GB.UTF-8

ARG CHROME_VERSION="109.0.5414.74-1"
ARG PYTHON_MAJOR_VERSION="3.11"
ARG PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.3"

VOLUME /etc/letsencrypt
VOLUME $INSTALL_PATH/vault
COPY docker/jaaql.service /lib/systemd/system/jaaql.service
VOLUME /etc/nginx/sites-available/
COPY ./pgextension /pgextension

RUN apt-get update && apt-get install -y build-essential && apt update && \
    apt install -y libpq-dev && \
    apt-get install -y git && \
    apt-get install -y cron && \
    mkdir -p /etc/letsencrypt/live && \
    apt -y install nginx && \
    apt-get -y install libzbar0 && \
    apt-get -y install libbz2-dev && \
    apt-get install dos2unix && \
    apt -y install bzip2 && \
    apt -y install wget && \
    wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz && \
    tar xf Python-${PYTHON_VERSION}.tar.xz && \
    apt install build-essential zlib1g-dev -y \
    libncurses5-dev libgdbm-dev libnss3-dev -y \
    libssl-dev libreadline-dev libffi-dev libbz2-dev curl -y && \
    cd /Python-${PYTHON_VERSION} && \
    ./configure --enable-optimizations --disable-test-modules --without-doc-strings --prefix=/usr/local --with-ensurepip=install && \
    make install && \
    cd ../ && \
    $PY_PATH -m ensurepip --default-pip && \
    $PY_PATH -mpip install -U pip wheel && \
    $PY_PATH -mpip install certbot-nginx==1.2.0 && \
    apt-get purge --auto-remove build-essential -y && \
    wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb && \
    apt install -y /tmp/chrome.deb && \
    rm /tmp/chrome.deb && \
    apt-get install unzip && \
    wget -N https://chromedriver.storage.googleapis.com/109.0.5414.74/chromedriver_linux64.zip -P ~/ && \
    unzip ~/chromedriver_linux64.zip -d ~/ && \
    rm ~/chromedriver_linux64.zip && \
    mv -f ~/chromedriver /usr/local/bin/chromedriver && \
    chown root:root /usr/local/bin/chromedriver && \
    chmod 0755 /usr/local/bin/chromedriver && \
    apt-get install -y gstreamer1.0-libav libnss3-tools libatk-bridge2.0-0 libcups2-dev libxkbcommon-x11-0 libxcomposite-dev libxrandr2 libgbm-dev libgtk-3-0 && \
    apt-get install -y xvfb && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf && \
    apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable && \
    apt-get -y install imagemagick x11-apps && \
    /bin/mkdir -p '/usr/share/postgresql/15/extension' && \
    /bin/mkdir -p '/usr/lib/postgresql/15/lib' && \
    /usr/bin/install -c -m 644 /pgextension/jaaql.control '/usr/share/postgresql/15/extension/' && \
    /usr/bin/install -c -m 644 /pgextension/jaaql--1.0.0.sql  '/usr/share/postgresql/15/extension/' && \
    /usr/bin/install -c -m 755 /pgextension/bin/jaaql.so '/usr/lib/postgresql/15/lib/' && \
    /bin/mkdir -p '/usr/lib/postgresql/15/lib/bitcode/jaaql' && \
    /bin/mkdir -p '/usr/lib/postgresql/15/lib/bitcode'/jaaql/ && \
    /usr/bin/install -c -m 644 /pgextension/bin/jaaql.bc '/usr/lib/postgresql/15/lib/bitcode'/jaaql/./ && \
    mv /pgextension/bin/jaaql.index.bc '/usr/lib/postgresql/15/lib/bitcode' && \
    rm -rf /usr/local/lib/python${PYTHON_MAJOR_VERSION}/test && \
    rm -rf /Python-${PYTHON_VERSION} && \
    rm -rf /Python-${PYTHON_VERSION}.tar.xz && \
    apt-get -y install locales && \
    sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    apt-get autoremove --purge -y

COPY requirements.txt $INSTALL_PATH/requirements.txt
RUN $PY_PATH -mpip install -r $INSTALL_PATH/requirements.txt
COPY . $INSTALL_PATH

RUN git clone https://github.com/JAAQL/JEQL.git && \
    cd JEQL && \
    git checkout tags/v2.2.20 && \
    cd ../ && \
    rm -rf $INSTALL_PATH/jaaql/config/config.ini && \
    mv $INSTALL_PATH/jaaql/config/config-docker.ini $INSTALL_PATH/jaaql/config/config.ini && \
    mkdir -p $INSTALL_PATH/www && \
    mkdir -p $INSTALL_PATH/log && \
    chown -R "$USER":www-data $INSTALL_PATH/www && \
    mv $INSTALL_PATH/docker/jaaql.sql /docker-entrypoint-initdb.d/01-jaaql.sql && \
    mv $INSTALL_PATH/docker/entrypoint.sh entrypoint.sh && \
    dos2unix entrypoint.sh && \
    mv $INSTALL_PATH/docker/pg_reboot.sh pg_reboot.sh && \
    dos2unix pg_reboot.sh && \
    dos2unix $INSTALL_PATH/base_reboot.sh && \
    cd $INSTALL_PATH && \
    $PY_PATH setup.py sdist bdist_wheel && \
    VERSION=$(grep '^VERSION = ' /JAAQL-middleware-python/jaaql/constants.py | cut -d'=' -f2 | cut -d'"' -f2) && $PIP_PATH install --no-deps /JAAQL-middleware-python/dist/jaaql_middleware_python-"$VERSION"-py3-none-any.whl && \
    cd / && \
    mkdir -p $INSTALL_PATH/log

ENTRYPOINT ["sh", "entrypoint.sh"]
