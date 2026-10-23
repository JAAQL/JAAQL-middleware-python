"""
set_web_config puts the application's nginx config into /etc/nginx/conf.d/jaaql.conf and HTTP/3 (http3 on, quic_retry on,
http3_max_concurrent_streams 64, the two QUIC listens and Alt-Svc) on lines of their own before Certbot's `listen 443 ssl`, exactly once
however often it runs, unless JAAQL_HTTP3 is FALSE. Earlier versions wrote those lines without line ends, glued onto the front of
`listen 443 ssl`, so every later run dropped that line and aborted; such a file is repaired.

Whatever JAAQL_HTTP3 says, the server with Certbot's `listen 443 ssl` keeps exactly one IPv6 TLS listen, on the line after it: Certbot's
`listen [::]:443 ssl ipv6only=on`, which it writes before or after `listen 443 ssl` and which earlier versions lost when it came before,
or `listen [::]:443 ssl` where a file had lost it.

    python -m unittest jaaql.test.test_web_config

The tests need only the package's requirements. With JAAQL_TEST_NGINX set to an nginx binary (as root, since nginx -t binds the ports;
the JAAQL image has both), every merged config is also checked with nginx -t, with a self-signed certificate made by cryptography
"""
import datetime
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel, _merge_web_config

INSTALL_PATH = "/JAAQL-middleware-python"

# The shape of /etc/nginx/conf.d/jaaql.conf after docker/entrypoint.sh wrote it for an HTTPS box and Certbot 5.8.0's nginx installer
# added the certificate and the redirect (certbot install --nginx --redirect), with fewer security headers
CERTBOT_CONF = """limit_req_zone $binary_remote_addr zone=jaaqllimit:10m rate=3r/s;
limit_req_zone $binary_remote_addr zone=httplimit:10m rate=5r/s;
server {
    server_name example.com www.example.com;
    charset UTF-8;
    add_header "X-Frame-Options" "DENY";
    add_header "X-Content-Type-Options" "nosniff";

    root /JAAQL-middleware-python/www;
    index index.html;
    location / {
        limit_req zone=httplimit burst=24 delay=16;
        limit_req_status 429;
    }
    location /api/ {
        limit_req zone=jaaqllimit burst=10 delay=7;
        limit_req_status 429;
        proxy_pass http://unix:/JAAQL-middleware-python/jaaql.sock:/;
        proxy_set_header Host              $http_host;
    }

    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot


}

server {
    listen 80;
    listen [::]:80;
    server_name 127.0.0.1 localhost;
    charset UTF-8;
    add_header "X-Frame-Options" "DENY";
    add_header "X-Content-Type-Options" "nosniff";

    root /JAAQL-middleware-python/www;
    location /api/ {
        proxy_pass http://unix:/JAAQL-middleware-python/jaaql.sock:/;
        proxy_set_header Host              $http_host;
    }
    index index.html;
    location / {
    }
}

server {
    if ($host = www.example.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = example.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;
    return 404; # managed by Certbot




}
"""

# An application's nginx.config as BATON's nginx pattern writes it (fewer headers), with the Alt-Svc of its own that older patterns put on
# the static files, which is not set_web_config's to remove
APP_CONFIG = """    charset UTF-8;
    expires 0;

    http2 on;

    add_header "Content-Security-Policy" "default-src 'self'; frame-ancestors 'self'";
    add_header "X-Frame-Options" "DENY";

    root /{{JAAQL_INSTALL_LOCATION}}/www;
    index index.html;
    location / {
        limit_req zone=httplimit burst=120 delay=80;
        limit_req_status 429;
    }

    location /api/ {
        limit_req zone=jaaqllimit burst=40 delay=30;
        limit_req_status 429;
        proxy_pass http://unix:/{{JAAQL_INSTALL_LOCATION}}/jaaql.sock:/;
        proxy_set_header Host              $http_host;
    }

    location ~* \\.(css|js|map)$ {
        expires max;
        add_header Alt-Svc 'h3=":443"; ma=86400' always;
        add_header Cache-Control "public";
    }"""
NEW_DATA = APP_CONFIG.replace("{{JAAQL_INSTALL_LOCATION}}", INSTALL_PATH)

# What set_web_config of 5.3.24 wrote over CERTBOT_CONF with APP_CONFIG, as on the boxes in October 2026: the HTTP/3 directives glued
# onto the front of `listen 443 ssl`, which made every later run abort
LEGACY_CONF = """limit_req_zone $binary_remote_addr zone=jaaqllimit:10m rate=3r/s;
limit_req_zone $binary_remote_addr zone=httplimit:10m rate=5r/s;
server {
    server_name example.com www.example.com;
    charset UTF-8;
    expires 0;

    http2 on;

    add_header "Content-Security-Policy" "default-src 'self'; frame-ancestors 'self'";
    add_header "X-Frame-Options" "DENY";

    root //JAAQL-middleware-python/www;
    index index.html;
    location / {
        limit_req zone=httplimit burst=120 delay=80;
        limit_req_status 429;
    }

    location /api/ {
        limit_req zone=jaaqllimit burst=40 delay=30;
        limit_req_status 429;
        proxy_pass http://unix://JAAQL-middleware-python/jaaql.sock:/;
        proxy_set_header Host              $http_host;
    }

    location ~* \\.(css|js|map)$ {
        expires max;
        add_header Alt-Svc 'h3=":443"; ma=86400' always;
        add_header Cache-Control "public";
    }
    http3 on;    listen 443 quic reuseport;    listen [::]:443 quic reuseport ipv6only=on;    add_header Alt-Svc 'h3=":443"; ma=86400';    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot


}

server {
    listen 80;
    listen [::]:80;
    server_name 127.0.0.1 localhost;
    charset UTF-8;
    expires 0;

    http2 on;

    add_header "Content-Security-Policy" "default-src 'self'; frame-ancestors 'self'";
    add_header "X-Frame-Options" "DENY";

    root //JAAQL-middleware-python/www;
    index index.html;
    location / {
        limit_req zone=httplimit burst=120 delay=80;
        limit_req_status 429;
    }

    location /api/ {
        limit_req zone=jaaqllimit burst=40 delay=30;
        limit_req_status 429;
        proxy_pass http://unix://JAAQL-middleware-python/jaaql.sock:/;
        proxy_set_header Host              $http_host;
    }

    location ~* \\.(css|js|map)$ {
        expires max;
        add_header Alt-Svc 'h3=":443"; ma=86400' always;
        add_header Cache-Control "public";
    }
}

server {
    if ($host = www.example.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = example.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;
    return 404; # managed by Certbot




}
"""

HTTP3_LINES = [
    "    http3 on;\n",
    "    quic_retry on;\n",
    "    http3_max_concurrent_streams 64;\n",
    "    listen 443 quic reuseport;\n",
    "    listen [::]:443 quic reuseport ipv6only=on;\n",
    "    add_header Alt-Svc 'h3=\":443\"; ma=86400';\n",
]
HTTP3_TEXT = ["http3 on", "quic_retry", "http3_max_concurrent_streams", "443 quic", "add_header Alt-Svc 'h3=\":443\"; ma=86400';"]
LISTEN_SSL = "    listen 443 ssl; # managed by Certbot\n"
LISTEN_SSL_IPV6 = "    listen [::]:443 ssl ipv6only=on; # managed by Certbot\n"
LISTEN_SSL_IPV6_RESTORED = "    listen [::]:443 ssl;\n"
APP_ALT_SVC = "        add_header Alt-Svc 'h3=\":443\"; ma=86400' always;\n"

# The same with Certbot's two listens the other way round, as it also writes them
CERTBOT_CONF_IPV4_FIRST = CERTBOT_CONF.replace(LISTEN_SSL_IPV6 + LISTEN_SSL, LISTEN_SSL + LISTEN_SSL_IPV6)
# Certbot's installer on a server with no IPv6 listen of its own writes no IPv6 TLS listen
CERTBOT_CONF_NO_IPV6 = CERTBOT_CONF.replace(LISTEN_SSL_IPV6, "")

# The server docker/entrypoint.sh writes for a wildcard or the user's own certificate, with its own two listens
OWN_CERTIFICATE_CONF = """server {
    server_name example.com *.example.com;
    charset UTF-8;
    root /JAAQL-middleware-python/www;
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
}
"""

IPV6_TLS_LISTEN = re.compile(r"\s*listen\s+\[::\]:443\s[^;]*\bssl\b")


def merge(text, http3=None):
    environ = {k: v for k, v in os.environ.items() if k != "JAAQL_HTTP3"}
    if http3 is not None:
        environ["JAAQL_HTTP3"] = http3
    with mock.patch.dict(os.environ, environ, clear=True):
        merged = _merge_web_config(text.splitlines(keepends=True), NEW_DATA)
    return None if merged is None else "".join(merged)


class TestMergeWebConfig(unittest.TestCase):
    def assert_http3_once_before_listen_ssl(self, text):
        lines = text.splitlines(keepends=True)
        at = lines.index(LISTEN_SSL)
        self.assertEqual(lines[at - len(HTTP3_LINES):at], HTTP3_LINES)
        for line in HTTP3_LINES:
            self.assertEqual(lines.count(line), 1, line)

    def assert_no_http3(self, text):
        self.assertIn(LISTEN_SSL, text.splitlines(keepends=True))
        for line in text.splitlines():
            if line != APP_ALT_SVC.rstrip("\n"):
                self.assertFalse(any(directive in line for directive in HTTP3_TEXT), line)

    def assert_tls_listens_once(self, text, ipv6_listen=LISTEN_SSL_IPV6, listen_ssl=LISTEN_SSL):
        # `listen 443 ssl` once, and the one IPv6 TLS listen on the line after it
        lines = text.splitlines(keepends=True)
        self.assertEqual(lines.count(listen_ssl), 1)
        self.assertEqual([line for line in lines if IPV6_TLS_LISTEN.match(line)], [ipv6_listen])
        self.assertEqual(lines[lines.index(listen_ssl) + 1], ipv6_listen)

    def test_a_certbot_config_gets_http3_once_and_a_second_run_changes_nothing(self):
        first = merge(CERTBOT_CONF)
        second = merge(first)

        self.assertEqual(second, first)
        self.assert_http3_once_before_listen_ssl(first)
        self.assert_tls_listens_once(first)
        self.assertNotIn("http3 on;    ", first)
        # The application's config replaced the entrypoint's in both servers, with its own Alt-Svc
        self.assertEqual(first.splitlines(keepends=True).count("    http2 on;\n"), 2)
        self.assertEqual(first.splitlines(keepends=True).count(APP_ALT_SVC), 2)
        self.assertNotIn("add_header \"X-Content-Type-Options\"", first)

    def test_the_http3_lines_are_exactly_those_of_the_hardened_config(self):
        self.assertEqual(model.WEB_CONFIG__http3_lines, HTTP3_LINES)

    def test_certbot_s_ipv6_tls_listen_is_kept_on_whichever_side_of_listen_ssl_it_came(self):
        # Earlier versions replaced everything from `charset` to `listen 443 ssl`, Certbot's IPv6 listen included when it came first
        self.assertEqual(merge(CERTBOT_CONF_IPV4_FIRST), merge(CERTBOT_CONF))
        for http3 in [None, "FALSE"]:
            for conf in [CERTBOT_CONF, CERTBOT_CONF_IPV4_FIRST]:
                self.assert_tls_listens_once(merge(conf, http3=http3))

    def test_a_server_without_an_ipv6_tls_listen_gets_one(self):
        merged = merge(CERTBOT_CONF_NO_IPV6)

        self.assert_tls_listens_once(merged, LISTEN_SSL_IPV6_RESTORED)
        self.assertEqual(merged, merge(CERTBOT_CONF).replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))
        self.assertEqual(model.WEB_CONFIG__ipv6_tls_listen_line, LISTEN_SSL_IPV6_RESTORED)

    def test_several_ipv6_tls_listens_become_the_first_one(self):
        doubled = CERTBOT_CONF.replace(LISTEN_SSL, LISTEN_SSL + LISTEN_SSL_IPV6_RESTORED + "    listen [::]:443 ssl http2;\n")

        self.assertEqual(merge(doubled), merge(CERTBOT_CONF))

    def test_runs_two_and_three_write_what_run_one_wrote(self):
        for http3 in [None, "FALSE"]:
            for conf in [CERTBOT_CONF, CERTBOT_CONF_IPV4_FIRST, CERTBOT_CONF_NO_IPV6, LEGACY_CONF, OWN_CERTIFICATE_CONF]:
                first = merge(conf, http3=http3)
                second = merge(first, http3=http3)
                self.assertEqual(second, first)
                self.assertEqual(merge(second, http3=http3), first)

    def test_a_config_with_the_lines_glued_onto_listen_ssl_is_repaired(self):
        repaired = merge(LEGACY_CONF)

        # As on the boxes, the IPv6 TLS listen Certbot had put before `listen 443 ssl` is gone from it, and comes back
        self.assertFalse(any(IPV6_TLS_LISTEN.match(line) for line in LEGACY_CONF.splitlines()))
        self.assertEqual(repaired, merge(CERTBOT_CONF).replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))
        self.assert_http3_once_before_listen_ssl(repaired)
        self.assert_tls_listens_once(repaired, LISTEN_SSL_IPV6_RESTORED)
        self.assertEqual(merge(repaired), repaired)

    def test_http3_switched_off_strips_it_and_adds_none(self):
        expected = merge(CERTBOT_CONF, http3="FALSE")
        self.assert_no_http3(expected)
        self.assert_tls_listens_once(expected)

        for http3 in ["FALSE", "false", "False"]:
            self.assertEqual(merge(merge(CERTBOT_CONF), http3=http3), expected)
            self.assertEqual(merge(LEGACY_CONF, http3=http3), expected.replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))
        self.assertEqual(merge(expected, http3="FALSE"), expected)

    def test_the_entrypoint_s_listens_for_its_own_certificates_stay_as_they_are(self):
        merged = merge(OWN_CERTIFICATE_CONF)

        self.assert_tls_listens_once(merged, "    listen [::]:443 ssl http2;\n", "    listen 443 ssl http2;\n")
        lines = merged.splitlines(keepends=True)
        self.assertEqual(lines[lines.index("    listen 443 ssl http2;\n") - len(HTTP3_LINES):lines.index("    listen 443 ssl http2;\n")],
                         HTTP3_LINES)
        self.assertEqual(merge(OWN_CERTIFICATE_CONF, http3="FALSE"), merged.replace("".join(HTTP3_LINES), ""))

    def test_http3_is_on_unless_switched_off(self):
        on = merge(CERTBOT_CONF)
        for http3 in ["TRUE", "true", "", "0", "no"]:
            self.assertEqual(merge(CERTBOT_CONF, http3=http3), on)
        self.assertEqual(merge(merge(CERTBOT_CONF, http3="FALSE")), on)

    def test_a_config_without_certbot_gets_no_http3(self):
        no_tls = "server {\n    listen 80;\n    server_name example.com;\n    charset UTF-8;\n    root /x/www;\n}\n"
        merged = merge(no_tls)

        self.assertEqual(merged, "server {\n    listen 80;\n    server_name example.com;\n" + NEW_DATA + "\n}\n")
        self.assertEqual(merge(merged), merged)
        self.assertFalse(any(IPV6_TLS_LISTEN.match(line) for line in merged.splitlines()))

    def test_the_localhost_server_keeps_the_application_s_limit_req(self):
        # In Certbot's layout the TLS server has no listen 80, so the entrypoint's localhost server is nginx's default server on port
        # 80: plain HTTP to the box's address, or with a Host it does not serve, lands there, and must be as throttled as the TLS server
        limits = ["limit_req zone=httplimit burst=120 delay=80;", "limit_req_status 429;",
                  "limit_req zone=jaaqllimit burst=40 delay=30;", "limit_req_status 429;"]
        for label, conf in {"certbot": CERTBOT_CONF, "legacy": LEGACY_CONF}.items():
            for http3 in [None, "FALSE"]:
                with self.subTest(conf=label, http3=http3):
                    merged = merge(conf, http3=http3)
                    servers = [server for server in re.split(r"(?m)^(?=server \{)", merged) if "\n    charset UTF-8;\n" in server]
                    self.assertEqual(len(servers), 2)
                    self.assertEqual(sum("\n    server_name 127.0.0.1 localhost;\n" in server for server in servers), 1)
                    for server in servers:
                        self.assertEqual([line.strip() for line in server.splitlines() if line.strip().startswith("limit_req")], limits)

    def test_losing_listen_ssl_aborts(self):
        self.assertIsNone(merge("server {\n    charset UTF-8;\n    index index.html;    listen 443 ssl;\n}\n"))

    def test_losing_an_ipv6_tls_listen_aborts(self):
        # A server with only an IPv6 TLS listen, inside the section the application's config replaces
        self.assertIsNone(merge("server {\n    charset UTF-8;\n    listen [::]:443 ssl;\n}\n"))


class TestSetWebConfig(unittest.TestCase):
    """
    set_web_config itself, with /etc/nginx/conf.d/jaaql.conf and /nginx-mount/nginx.config redirected to temporary files
    """

    def run_set_web_config(self, site_text, http3=None):
        real_open, real_exists = open, os.path.exists
        with tempfile.TemporaryDirectory() as directory:
            paths = {"/etc/nginx/conf.d/jaaql.conf": os.path.join(directory, "jaaql.conf"),
                     "/nginx-mount/nginx.config": os.path.join(directory, "nginx.config")}
            with real_open(paths["/etc/nginx/conf.d/jaaql.conf"], "w") as f:
                f.write(site_text)
            with real_open(paths["/nginx-mount/nginx.config"], "w") as f:
                f.write(APP_CONFIG)

            environ = {k: v for k, v in os.environ.items() if k not in ("JAAQL_HTTP3", "SET_WEB_CONFIG_OVERRIDE")}
            environ["INSTALL_PATH"] = INSTALL_PATH
            if http3 is not None:
                environ["JAAQL_HTTP3"] = http3
            stub = mock.Mock(is_container=True)
            with mock.patch.dict(os.environ, environ, clear=True), \
                    mock.patch("builtins.open", lambda path, *args, **kwargs: real_open(paths.get(path, path), *args, **kwargs)), \
                    mock.patch("os.path.exists", lambda path: real_exists(paths.get(path, path))), \
                    mock.patch.object(model.subprocess, "call") as call:
                JAAQLModel.set_web_config(stub, connection=None)

            stub.is_super_admin.assert_called_once_with(None)
            with real_open(paths["/etc/nginx/conf.d/jaaql.conf"]) as f:
                return f.read(), call.call_args_list

    def test_twice_on_a_certbot_config(self):
        first, calls = self.run_set_web_config(CERTBOT_CONF)
        second, _ = self.run_set_web_config(first)

        self.assertEqual(first, merge(CERTBOT_CONF))
        self.assertEqual(second, first)
        self.assertEqual(calls, [mock.call(["nginx", "-s", "reload"])])

    def test_a_legacy_config_is_repaired_and_switched_off(self):
        self.assertEqual(self.run_set_web_config(LEGACY_CONF)[0], merge(CERTBOT_CONF).replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))
        self.assertEqual(self.run_set_web_config(LEGACY_CONF, http3="FALSE")[0],
                         merge(CERTBOT_CONF, http3="FALSE").replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))

    def test_an_abort_leaves_the_file_alone(self):
        broken = "server {\n    charset UTF-8;\n    index index.html;    listen 443 ssl;\n}\n"
        text, calls = self.run_set_web_config(broken)

        self.assertEqual(text, broken)
        self.assertEqual(calls, [])


@unittest.skipUnless(os.environ.get("JAAQL_TEST_NGINX"), "JAAQL_TEST_NGINX is not set to an nginx binary")
class TestMergedConfigsWithNginx(unittest.TestCase):
    """
    nginx -t on each merged config as conf.d/jaaql.conf of an http block, with Certbot's /etc/letsencrypt paths pointed at a self-signed
    certificate and Certbot's own TLS options and DH parameters where Certbot is installed (else a stub of the options, without DH)
    """

    @classmethod
    def setUpClass(cls):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID

        cls.directory = tempfile.mkdtemp(prefix="jaaql-nginx-")
        live = os.path.join(cls.directory, "letsencrypt", "live", "example.com")
        os.makedirs(live)
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "example.com")])
        now = datetime.datetime.now(datetime.timezone.utc)
        certificate = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()) \
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1)) \
            .not_valid_after(now + datetime.timedelta(days=2)).sign(key, hashes.SHA256())
        with open(os.path.join(live, "fullchain.pem"), "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))
        with open(os.path.join(live, "privkey.pem"), "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

        cls.has_dhparams = False
        try:
            import certbot
            certbot_dir = os.path.dirname(certbot.__file__)
            options = [os.path.join(root, "options-ssl-nginx.conf") for root, _, files in os.walk(certbot_dir) if "options-ssl-nginx.conf" in files]
            shutil.copy(options[0], os.path.join(cls.directory, "letsencrypt", "options-ssl-nginx.conf"))
            shutil.copy(os.path.join(certbot_dir, "ssl-dhparams.pem"), os.path.join(cls.directory, "letsencrypt", "ssl-dhparams.pem"))
            cls.has_dhparams = True
        except (ImportError, IndexError, OSError):
            with open(os.path.join(cls.directory, "letsencrypt", "options-ssl-nginx.conf"), "w") as f:
                f.write("ssl_session_cache shared:le_nginx_SSL:10m;\nssl_session_timeout 1440m;\nssl_session_tickets off;\n"
                        "ssl_protocols TLSv1.2 TLSv1.3;\nssl_prefer_server_ciphers off;\n")

        with open(os.path.join(cls.directory, "nginx.conf"), "w") as f:
            f.write(f"pid {cls.directory}/nginx.pid;\nerror_log {cls.directory}/error.log;\nevents {{}}\nhttp {{\n    access_log off;\n"
                    + "".join(f"    {kind}_temp_path {cls.directory}/{kind};\n" for kind in ["client_body", "proxy", "fastcgi", "uwsgi", "scgi"])
                    + f"    include {cls.directory}/jaaql.conf;\n}}\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def assert_nginx_accepts(self, text, allowed_warning=None):
        text = text.replace("/etc/letsencrypt/", self.directory + "/letsencrypt/")
        if not self.has_dhparams:
            text = "".join(line for line in text.splitlines(keepends=True) if "ssl_dhparam" not in line)
        with open(os.path.join(self.directory, "jaaql.conf"), "w") as f:
            f.write(text)
        result = subprocess.run([os.environ["JAAQL_TEST_NGINX"], "-t", "-e", self.directory + "/error.log", "-p", self.directory,
                                 "-c", self.directory + "/nginx.conf"], capture_output=True, text=True)
        messages = [line for line in result.stderr.splitlines() if "[" in line and (allowed_warning is None or allowed_warning not in line)]
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("test is successful", result.stderr)
        self.assertEqual(messages, [])

    def test_every_merged_config_passes_nginx_t(self):
        configs = {"certbot": CERTBOT_CONF, "certbot, IPv4 listen first": CERTBOT_CONF_IPV4_FIRST, "certbot without IPv6": CERTBOT_CONF_NO_IPV6,
                   "legacy": LEGACY_CONF}
        for http3 in [None, "FALSE"]:
            for label, conf in configs.items():
                with self.subTest(conf=label, http3=http3):
                    first = merge(conf, http3=http3)
                    self.assert_nginx_accepts(first)
                    self.assert_nginx_accepts(merge(first, http3=http3))

    def test_the_entrypoint_s_own_certificate_server_passes_nginx_t(self):
        for http3 in [None, "FALSE"]:
            with self.subTest(http3=http3):
                self.assert_nginx_accepts("limit_req_zone $binary_remote_addr zone=jaaqllimit:10m rate=3r/s;\n"
                                          "limit_req_zone $binary_remote_addr zone=httplimit:10m rate=5r/s;\n" + merge(OWN_CERTIFICATE_CONF, http3=http3),
                                          allowed_warning='the "listen ... http2" directive is deprecated')

    def test_a_second_ipv6_tls_listen_with_options_would_fail(self):
        # Why the restored line carries no options: nginx takes options for an address and port once, and refuses a second set
        doubled = merge(CERTBOT_CONF).replace("server {\n    listen 80;\n    listen [::]:80;\n    server_name 127.0.0.1 localhost;\n",
                                              "server {\n    listen 80;\n    listen [::]:80;\n    listen [::]:443 ssl ipv6only=on;\n"
                                              "    server_name 127.0.0.1 localhost;\n", 1)
        self.assertNotEqual(doubled, merge(CERTBOT_CONF))
        with self.assertRaises(AssertionError) as raised:
            self.assert_nginx_accepts(doubled)
        self.assertIn("duplicate listen options for [::]:443", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
