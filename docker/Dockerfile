FROM postgres:16.2
LABEL maintainer="jaaql.io"

ARG POSTGRES_VERSION="16"

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
ENV JAAQL_CONVERT_DATES true

ENV LANG en_GB.UTF-8
ENV LANGUAGE en_GB:en
ENV LC_ALL en_GB.UTF-8

ARG CHROME_VERSION="137.0.7151.70"
ARG PYTHON_MAJOR_VERSION="3.12"
ARG PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.2"

VOLUME /etc/letsencrypt
VOLUME $INSTALL_PATH/vault
COPY docker/jaaql.service /lib/systemd/system/jaaql.service
VOLUME /etc/nginx/sites-available/
COPY ./pgextension /pgextension
COPY ./plpgsql_check /plpgsql_check

RUN apt-get update && apt-get install -y build-essential && apt update && \
    apt install -y libpq-dev && \
    apt-get install -y cron && \
    mkdir -p /etc/letsencrypt/live && \
    apt-get install -y --no-install-recommends \
        curl gnupg2 ca-certificates lsb-release && \

    ## import the signing key
    curl -fsSL https://nginx.org/keys/nginx_signing.key \
      | gpg --dearmor -o /usr/share/keyrings/nginx-archive-keyring.gpg && \

    ## add the *mainline* repo for Debian 12 (“bookworm”)
    echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
      http://nginx.org/packages/mainline/debian $(lsb_release -cs) nginx" \
      > /etc/apt/sources.list.d/nginx.list && \

    ## pin nginx.org above Debian’s copy so upgrades stay on the newer track
    printf 'Package: *\nPin: origin nginx.org\nPin-Priority: 900\n' \
      > /etc/apt/preferences.d/99nginx && \

    ## refresh metadata
    apt-get update && \

    ## install *exactly* 1.29.0 (pattern allows the “‑1~bookworm” suffix)
    apt-get install -y --no-install-recommends nginx=1.29.0* && \

    ## show the version in the build log for sanity
    nginx -v && \

    apt-get -y install libzbar0 && \
    apt-get -y install libbz2-dev && \
    apt-get install dos2unix && \
    apt -y install bzip2 && \
    apt -y install wget && \
    wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz && \
    tar xf Python-${PYTHON_VERSION}.tar.xz && \
    rm -rf Python-${PYTHON_VERSION}.tar.xz && \
    apt install build-essential zlib1g-dev -y \
    libncurses5-dev libgdbm-dev libnss3-dev -y \
    libssl-dev libreadline-dev libffi-dev libbz2-dev curl -y && \
    cd /Python-${PYTHON_VERSION} && \
    ./configure --enable-optimizations --with-lto --disable-test-modules --without-doc-strings --prefix=/usr/local --with-ensurepip=install && \
    make install && \
    cd ../ && \
    rm -rf /Python-${PYTHON_VERSION} && \
    $PY_PATH -m ensurepip --default-pip && \
    $PY_PATH -mpip install -U pip wheel && \
    $PY_PATH -mpip install certbot-nginx==4.1.1 && \
    apt-get install unzip && \
    wget --no-verbose -O /tmp/chrome.zip https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip && \
    unzip /tmp/chrome.zip -d /opt/ && \
    ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
    rm /tmp/chrome.zip && \
    wget -N https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip -P ~/ && \
    unzip ~/chromedriver-linux64.zip -d ~/ && \
    rm ~/chromedriver-linux64.zip && \
    mv -f ~/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf ~/chromedriver-linux64 && \
    chown root:root /usr/local/bin/chromedriver && \
    chmod 0755 /usr/local/bin/chromedriver && \
    apt-get install -y gstreamer1.0-libav libnss3-tools libatk-bridge2.0-0 libcups2-dev libxkbcommon-x11-0 libxcomposite-dev libxrandr2 libgbm-dev libgtk-3-0 && \
    apt-get install -y xvfb && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf && \
    apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-scalable && \
    apt-get -y install imagemagick x11-apps && \
    /bin/mkdir -p '/usr/share/postgresql/'${POSTGRES_VERSION}'/extension' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib' && \
    /usr/bin/install -c -m 644 /pgextension/jaaql.control '/usr/share/postgresql/'${POSTGRES_VERSION}'/extension/' && \
    /usr/bin/install -c -m 644 /pgextension/jaaql--1.0.0.sql  '/usr/share/postgresql/'${POSTGRES_VERSION}'/extension/' && \
    /usr/bin/install -c -m 755 /pgextension/bin/jaaql.so '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode/jaaql' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/jaaql/ && \
    /usr/bin/install -c -m 644 /pgextension/bin/jaaql.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/jaaql/./ && \
    mv /pgextension/bin/jaaql.index.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode' && \
    cd /plpgsql_check && \
    /usr/bin/install -c -m 755  plpgsql_check.so '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/plpgsql_check.so' && \
    /usr/bin/install -c -m 644 .//plpgsql_check.control '/usr/share/postgresql/'${POSTGRES_VERSION}'/extension/' && \
    /usr/bin/install -c -m 644 .//plpgsql_check--2.5.sql  '/usr/share/postgresql/'${POSTGRES_VERSION}'/extension/' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode/plpgsql_check' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/assign.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/catalog.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/check_expr.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/check_function.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/expr_walk.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/format.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/parser.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/pldbgapi2.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/plpgsql_check.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/pragma.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/profiler.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/report.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/stmtwalk.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/tablefunc.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/tracer.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/typdesc.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 plpgsql_check.index.bc '/usr/lib/postgresql/'${POSTGRES_VERSION}'/lib/bitcode' && \
    cd ../ && \
    rm -rf /usr/local/lib/python${PYTHON_MAJOR_VERSION}/test && \
    rm -rf /Python-${PYTHON_VERSION} && \
    rm -rf /Python-${PYTHON_VERSION}.tar.xz && \
    apt-get -y install locales && \
    sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    curl -fsSL https://nodejs.org/dist/v20.12.0/node-v20.12.0-linux-x64.tar.xz | tar -xJf - -C /usr/local --strip-components=1

COPY requirements.txt $INSTALL_PATH/requirements.txt

RUN sed -i 's/\[binary\]/[c]/g' $INSTALL_PATH/requirements.txt && \
    $PY_PATH -mpip install -r $INSTALL_PATH/requirements.txt && \
    apt-get purge -y --auto-remove build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libbz2-dev unzip bzip2 wget && \
    apt-get autoremove --purge -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*

COPY . $INSTALL_PATH

RUN rm -rf $INSTALL_PATH/jaaql/config/config.ini && \
    mv $INSTALL_PATH/jaaql/config/config-docker.ini $INSTALL_PATH/jaaql/config/config.ini && \
    mkdir -p $INSTALL_PATH/www && \
    mkdir -p $INSTALL_PATH/log && \
    chown -R "$USER":www-data $INSTALL_PATH/www && \
    mv $INSTALL_PATH/docker/jaaql.sql /docker-entrypoint-initdb.d/01-jaaql.sql && \
    mv $INSTALL_PATH/docker/entrypoint.sh entrypoint.sh && \
    mv $INSTALL_PATH/docker/certbot-dns-cleanup-hook.sh certbot-dns-cleanup-hook.sh && \
    chmod +x certbot-dns-cleanup-hook.sh && \
    mv $INSTALL_PATH/docker/certbot-dns-auth-hook.sh certbot-dns-auth-hook.sh && \
    chmod +x certbot-dns-auth-hook.sh && \
    dos2unix entrypoint.sh && \
    mv $INSTALL_PATH/docker/reboot.sh reboot.sh && \
    dos2unix reboot.sh && \
    chmod +x reboot.sh && \
    mv $INSTALL_PATH/docker/recover.sh recover.sh && \
    dos2unix recover.sh && \
    mv $INSTALL_PATH/docker/pg_reboot.sh pg_reboot.sh && \
    dos2unix pg_reboot.sh && \
    dos2unix $INSTALL_PATH/base_reboot.sh && \
    cd $INSTALL_PATH && \
    $PY_PATH setup.py sdist bdist_wheel && \
    VERSION=$(grep '^VERSION = ' /JAAQL-middleware-python/jaaql/constants.py | cut -d'=' -f2 | cut -d'"' -f2) && $PIP_PATH install --no-deps /JAAQL-middleware-python/dist/jaaql_middleware_python-"$VERSION"-py3-none-any.whl && \
    cd / && \
    mkdir -p $INSTALL_PATH/log

ENTRYPOINT ["sh", "entrypoint.sh"]
