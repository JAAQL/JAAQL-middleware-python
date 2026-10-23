FROM postgres:18.6-trixie
LABEL maintainer="jaaql.io"

ARG POSTGRES_VERSION="18"
# Old volumes hold clusters of this version; its binaries are kept in the image so the
# entrypoint can pg_upgrade them in place
ARG OLD_POSTGRES_VERSION="16"

# The postgres 18 image moved its default data directory to /var/lib/postgresql/18/docker;
# pin the pre-18 path so existing volume mounts keep working
ENV PGDATA /var/lib/postgresql/data

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

ARG CHROME_VERSION="156.0.8078.47"
ARG CHROME_SHA256="e6c94490f0b6b337225aeb2d2a5034858516b7017356980ba94f5176d8774a50"
ARG CHROMEDRIVER_SHA256="2a5024610c53f340a1aaa5d9a3e2a4fa448be7d71cca5238bd8c3c7f16181df4"
ARG PYTHON_MAJOR_VERSION="3.14"
ARG PYTHON_VERSION="${PYTHON_MAJOR_VERSION}.9"
ARG PYTHON_SHA256="e02d9ac21cebda6e46435369744a92c65cc7cd8669697694122cf97ffacd1e53"
ARG NGINX_VERSION="1.31.8"
ARG NODE_VERSION="24.22.1"
ARG NODE_SHA256="6c172a9ab6718f7b801fb5a7bd486af2ee5e32758086a04b84fcce2aa77095e6"

VOLUME /etc/letsencrypt
VOLUME $INSTALL_PATH/vault
COPY docker/jaaql.service /lib/systemd/system/jaaql.service
VOLUME /etc/nginx/sites-available/
COPY ./pgextension /pgextension
COPY ./plpgsql_check /plpgsql_check

COPY docker/75-emoji.conf /etc/fonts/conf.d/75-emoji.conf

# Chrome for Testing ships its own root store and, headless, neither fetches CRLSets nor enforces
# certificate transparency, so it still trusted the eMudhra root and TLS intermediates whose private
# keys became public in October 2026. It reads managed policies from this directory only
COPY docker/chrome-policies/distrust-emudhra.json /etc/opt/chrome_for_testing/policies/managed/distrust-emudhra.json

RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y build-essential && \
    apt install -y libpq-dev && \
    apt-get install -y --no-install-recommends cron && \
    mkdir -p /etc/letsencrypt/live && \
    apt-get install -y --no-install-recommends \
        curl gnupg2 ca-certificates lsb-release && \

    ## import the signing key
    curl -fsSL https://nginx.org/keys/nginx_signing.key \
      | gpg --dearmor -o /usr/share/keyrings/nginx-archive-keyring.gpg && \

    ## add the nginx.org *mainline* repo for this Debian release
    echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
      http://nginx.org/packages/mainline/debian $(lsb_release -cs) nginx" \
      > /etc/apt/sources.list.d/nginx.list && \

    ## pin nginx.org above Debian’s copy so upgrades stay on the newer track
    printf 'Package: *\nPin: origin nginx.org\nPin-Priority: 900\n' \
      > /etc/apt/preferences.d/99nginx && \

    ## refresh metadata
    apt-get update && \

    apt-get install -y --no-install-recommends \
        fontconfig \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-core \
        fonts-noto-cjk \
        fonts-noto-color-emoji && \

    mkdir -p /etc/fonts/conf.d && \
    fc-cache -f && \

    ## install exactly NGINX_VERSION for this Debian release, fail the build if apt resolved anything
    ## else or the build lacks HTTP/3, and show the full build (OpenSSL, modules) in the build log
    apt-get install -y --no-install-recommends nginx=${NGINX_VERSION}-1~$(lsb_release -cs) && \
    nginx -v 2>&1 | grep -qx "nginx version: nginx/${NGINX_VERSION}" && \
    nginx -V 2>&1 | grep -q -- "--with-http_v3_module" && \
    nginx -V && \

    ## clang 19 + llvm tooling (PGO/LTO) for the CPython build, from Debian main; purged after use.
    ## libclang-rt-19-dev supplies libclang_rt.profile.a, required by PGO instrumentation
    apt-get install -y --no-install-recommends clang-19 llvm-19 libclang-rt-19-dev && \
    ln -s /usr/bin/llvm-profdata-19 /usr/local/bin/llvm-profdata && \
    ln -s /usr/bin/llvm-ar-19 /usr/local/bin/llvm-ar && \
    ln -s /usr/bin/llvm-ranlib-19 /usr/local/bin/llvm-ranlib && \
    ln -s /usr/bin/llvm-nm-19 /usr/local/bin/llvm-nm && \

    ## old postgres binaries so the entrypoint can pg_upgrade old data volumes, new dev headers
    ## to build the jaaql extension, and plpgsql_check for the new major from PGDG
    mkdir -p /etc/postgresql-common/createcluster.d && \
    echo "create_main_cluster = false" > /etc/postgresql-common/createcluster.d/jaaql-no-main.conf && \
    apt-get install -y --no-install-recommends postgresql-${OLD_POSTGRES_VERSION} \
      postgresql-server-dev-${POSTGRES_VERSION} postgresql-${POSTGRES_VERSION}-plpgsql-check && \

    apt-get -y install libbz2-dev && \
    apt-get install dos2unix && \
    apt -y install bzip2 && \
    apt -y install wget && \
    wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz && \
    echo "${PYTHON_SHA256}  Python-${PYTHON_VERSION}.tar.xz" | sha256sum -c - && \
    tar xf Python-${PYTHON_VERSION}.tar.xz && \
    rm -rf Python-${PYTHON_VERSION}.tar.xz && \
    apt install build-essential zlib1g-dev -y \
    libncurses-dev libgdbm-dev libnss3-dev -y \
    libssl-dev libreadline-dev libffi-dev libbz2-dev curl -y && \
    cd /Python-${PYTHON_VERSION} && \
    CC=clang-19 CXX=clang++-19 ./configure --enable-optimizations --with-lto --with-tail-call-interp --disable-test-modules --without-doc-strings --prefix=/usr/local --with-ensurepip=install && \
    make install && \
    cd ../ && \
    rm -rf /Python-${PYTHON_VERSION} && \
    $PY_PATH -m ensurepip --default-pip && \
    $PY_PATH -mpip install -U pip wheel && \
    $PY_PATH -mpip install certbot==5.8.0 certbot-nginx==5.8.0 acme==5.8.0 cryptography==50.0.2 pyOpenSSL==26.4.0 && \
    apt-get install unzip && \
    wget --no-verbose -O /tmp/chrome.zip https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip && \
    echo "${CHROME_SHA256}  /tmp/chrome.zip" | sha256sum -c - && \
    unzip /tmp/chrome.zip -d /opt/ && \
    ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
    rm /tmp/chrome.zip && \
    wget -N https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip -P ~/ && \
    echo "${CHROMEDRIVER_SHA256}  $HOME/chromedriver-linux64.zip" | sha256sum -c - && \
    unzip ~/chromedriver-linux64.zip -d ~/ && \
    rm ~/chromedriver-linux64.zip && \
    mv -f ~/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf ~/chromedriver-linux64 && \
    chown root:root /usr/local/bin/chromedriver && \
    chmod 0755 /usr/local/bin/chromedriver && \
    apt-get install -y gstreamer1.0-libav libnss3-tools libatk-bridge2.0-0t64 libcups2-dev libxkbcommon-x11-0 libxcomposite-dev libxrandr2 libgbm-dev libgtk-3-0t64 && \
    apt-get install -y xvfb && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install xorg xvfb gtk2-engines-pixbuf && \
    apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-scalable && \
    apt-get -y install imagemagick x11-apps && \
    /bin/mkdir -p '/usr/share/postgresql/'${OLD_POSTGRES_VERSION}'/extension' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib' && \
    /usr/bin/install -c -m 644 /pgextension/jaaql.control '/usr/share/postgresql/'${OLD_POSTGRES_VERSION}'/extension/' && \
    /usr/bin/install -c -m 644 /pgextension/jaaql--1.0.0.sql  '/usr/share/postgresql/'${OLD_POSTGRES_VERSION}'/extension/' && \
    /usr/bin/install -c -m 755 /pgextension/bin/jaaql.so '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode/jaaql' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/jaaql/ && \
    /usr/bin/install -c -m 644 /pgextension/bin/jaaql.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/jaaql/./ && \
    mv /pgextension/bin/jaaql.index.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode' && \
    cd /plpgsql_check && \
    /usr/bin/install -c -m 755  plpgsql_check.so '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/plpgsql_check.so' && \
    /usr/bin/install -c -m 644 .//plpgsql_check.control '/usr/share/postgresql/'${OLD_POSTGRES_VERSION}'/extension/' && \
    /usr/bin/install -c -m 644 .//plpgsql_check--2.5.sql  '/usr/share/postgresql/'${OLD_POSTGRES_VERSION}'/extension/' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode/plpgsql_check' && \
    /bin/mkdir -p '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/assign.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/catalog.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/check_expr.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/check_function.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/expr_walk.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/format.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/parser.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/pldbgapi2.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/plpgsql_check.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/pragma.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/profiler.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/report.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/stmtwalk.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/tablefunc.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/tracer.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 src/typdesc.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode'/plpgsql_check/src/ && \
    /usr/bin/install -c -m 644 plpgsql_check.index.bc '/usr/lib/postgresql/'${OLD_POSTGRES_VERSION}'/lib/bitcode' && \
    cd ../ && \
    ## build the jaaql extension from source against the new postgres major (the vendored .so
    ## above is a postgres 16 binary and only loads into the old cluster during pg_upgrade)
    cd /pgextension && \
    make PG_CONFIG=/usr/lib/postgresql/${POSTGRES_VERSION}/bin/pg_config with_llvm=no && \
    make PG_CONFIG=/usr/lib/postgresql/${POSTGRES_VERSION}/bin/pg_config with_llvm=no install && \
    ## pg_upgrade's binary-mode dump recreates extensions at their old version, so the 2.5
    ## install script must exist alongside the newer PGDG plpgsql_check
    /usr/bin/install -c -m 644 /plpgsql_check/plpgsql_check--2.5.sql '/usr/share/postgresql/'${POSTGRES_VERSION}'/extension/' && \
    cd / && \
    rm -rf /usr/local/lib/python${PYTHON_MAJOR_VERSION}/test && \
    rm -rf /Python-${PYTHON_VERSION} && \
    rm -rf /Python-${PYTHON_VERSION}.tar.xz && \
    apt-get -y install locales && \
    sed -i '/en_GB.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    curl -fsSLo /tmp/node.tar.xz https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz && \
    echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum -c - && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.xz

COPY requirements.txt $INSTALL_PATH/requirements.txt

RUN sed -i 's/\[binary\]/[c]/g' $INSTALL_PATH/requirements.txt && \
    $PY_PATH -mpip install -r $INSTALL_PATH/requirements.txt && \
    apt-get purge -y --auto-remove build-essential zlib1g-dev libncurses-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libbz2-dev unzip bzip2 wget clang-19 llvm-19 libclang-rt-19-dev postgresql-server-dev-${POSTGRES_VERSION} && \
    rm -f /usr/local/bin/llvm-profdata /usr/local/bin/llvm-ar /usr/local/bin/llvm-ranlib /usr/local/bin/llvm-nm && \
    apt-get autoremove --purge -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/* && \
    ## fail the build while any trust store in the image still accepts the compromised eMudhra root
    ## "emSign ECC Root CA - G3" (SHA-256 86A1ECBA...6BBE6B): the system store (OpenSSL, curl, libpq,
    ## Python's ssl), certifi (requests, certbot) and Node's bundled roots (BATON cloud procedures).
    ## EMSIGN_G3 is the first base64 line of its PEM; ISRG_X1 is that of ISRG Root X1, which must be
    ## found, so a store that could not be read cannot pass for a clean one
    EMSIGN_G3=MIICTjCCAdOgAwIBAgIKPPYHqWhwDtqLhDAKBggqhkjOPQQDAzBrMQswCQYDVQQG && \
    ISRG_X1=MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw && \
    dpkg --compare-versions "$(dpkg-query -W -f='${Version}' ca-certificates)" ge 20250419+deb13u1 && \
    grep -q "$ISRG_X1" /etc/ssl/certs/ca-certificates.crt && \
    ! grep -q "$EMSIGN_G3" /etc/ssl/certs/ca-certificates.crt && \
    $PY_PATH -I -c "import certifi, sys; pem = open(certifi.where()).read(); sys.exit(0 if '$ISRG_X1' in pem and '$EMSIGN_G3' not in pem else 1)" && \
    node -e "const roots = require('tls').rootCertificates; process.exit(roots.some(c => c.includes('$ISRG_X1')) && !roots.some(c => c.includes('$EMSIGN_G3')) ? 0 : 1)" && \
    grep -q "$EMSIGN_G3" /etc/opt/chrome_for_testing/policies/managed/distrust-emudhra.json

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
    mv $INSTALL_PATH/docker/pg_dev_settings.sh pg_dev_settings.sh && \
    dos2unix pg_dev_settings.sh && \
    dos2unix $INSTALL_PATH/base_reboot.sh && \
    cd $INSTALL_PATH && \
    $PIP_PATH install -U setuptools wheel && \
    $PY_PATH setup.py sdist bdist_wheel && \
    VERSION=$(grep '^VERSION = ' /JAAQL-middleware-python/jaaql/constants.py | cut -d'=' -f2 | cut -d'"' -f2) && $PIP_PATH install --no-deps /JAAQL-middleware-python/dist/jaaql_middleware_python-"$VERSION"-py3-none-any.whl && \
    cd / && \
    mkdir -p $INSTALL_PATH/log

STOPSIGNAL SIGTERM

ENTRYPOINT ["sh", "entrypoint.sh"]
