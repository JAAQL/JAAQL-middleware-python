"""
set_web_config puts the application's nginx config into /etc/nginx/conf.d/jaaql.conf and HTTP/3 (http3 on, quic_retry on,
http3_max_concurrent_streams 64, the two QUIC listens and Alt-Svc) on lines of their own before Certbot's `listen 443 ssl`, exactly once
however often it runs, unless JAAQL_HTTP3 is FALSE. Earlier versions wrote those lines without line ends, glued onto the front of
`listen 443 ssl`, so every later run dropped that line and aborted; such a file is repaired.

Whatever JAAQL_HTTP3 says, the server with Certbot's `listen 443 ssl` keeps exactly one IPv6 TLS listen, on the line after it: Certbot's
`listen [::]:443 ssl ipv6only=on`, which it writes before or after `listen 443 ssl` and which earlier versions lost when it came before,
or `listen [::]:443 ssl` where a file had lost it.

nginx -t then checks the whole configuration: a merged config it refuses is replaced by the file as it was, byte for byte, nginx is not
reloaded and the request fails with nginx's error; a failed nginx -s reload fails it too.

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

from jaaql.exceptions.http_status_exception import HttpStatusException
from jaaql.mvc import model
from jaaql.mvc.model import JAAQLModel, _merge_web_config

INSTALL_PATH = "/JAAQL-middleware-python"
# subprocess.run itself, which run_set_web_config patches (model.subprocess is this module's subprocess)
SUBPROCESS_RUN = subprocess.run

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


NGINX_TEST_OK = ("nginx: the configuration file /etc/nginx/nginx.conf syntax is ok\n"
                 "nginx: configuration file /etc/nginx/nginx.conf test is successful\n")
NGINX_TEST = ["nginx", "-t"]
NGINX_RELOAD = ["nginx", "-s", "reload"]
# An application config nginx refuses
APP_CONFIG_REFUSED = APP_CONFIG + "\n    jaaql_test_unknown_directive on;"


class NginxStandIn:
    # Stands in for subprocess.run under set_web_config: records each command and answers nginx -t and nginx -s reload with the exit code
    # and stderr given for each
    def __init__(self, test=(0, NGINX_TEST_OK), reload=(0, "")):
        self.calls = []
        self.answers = {tuple(NGINX_TEST): test, tuple(NGINX_RELOAD): reload}

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        returncode, stderr = self.answers[tuple(command)]
        return subprocess.CompletedProcess(command, returncode, stdout="", stderr=stderr)


def run_set_web_config(site, run, app_config=APP_CONFIG, http3=None, directory=None):
    # set_web_config with /etc/nginx/conf.d/jaaql.conf (holding site, text or bytes) and /nginx-mount/nginx.config (holding app_config)
    # redirected to files in directory, a temporary one when None, and subprocess.run to run. Returns the bytes the site file holds
    # afterwards and the HttpStatusException set_web_config raised, or None
    real_open, real_exists = open, os.path.exists
    with tempfile.TemporaryDirectory() as temporary:
        directory = directory or temporary
        paths = {"/etc/nginx/conf.d/jaaql.conf": os.path.join(directory, "jaaql.conf"),
                 "/nginx-mount/nginx.config": os.path.join(directory, "nginx.config")}
        with real_open(paths["/etc/nginx/conf.d/jaaql.conf"], "wb") as f:
            f.write(site if isinstance(site, bytes) else site.encode("utf-8"))
        with real_open(paths["/nginx-mount/nginx.config"], "w") as f:
            f.write(app_config)

        environ = {k: v for k, v in os.environ.items() if k not in ("JAAQL_HTTP3", "SET_WEB_CONFIG_OVERRIDE")}
        environ["INSTALL_PATH"] = INSTALL_PATH
        if http3 is not None:
            environ["JAAQL_HTTP3"] = http3
        stub = mock.Mock(is_container=True)
        raised = None
        with mock.patch.dict(os.environ, environ, clear=True), \
                mock.patch("builtins.open", lambda path, *args, **kwargs: real_open(paths.get(path, path), *args, **kwargs)), \
                mock.patch("os.path.exists", lambda path: real_exists(paths.get(path, path))), \
                mock.patch.object(model.subprocess, "run", side_effect=run), \
                mock.patch.object(model.subprocess, "call") as call:
            try:
                JAAQLModel.set_web_config(stub, connection=None)
            except HttpStatusException as ex:
                raised = ex

        stub.is_super_admin.assert_called_once_with(None)
        call.assert_not_called()
        with real_open(paths["/etc/nginx/conf.d/jaaql.conf"], "rb") as f:
            return f.read(), raised


class TestSetWebConfig(unittest.TestCase):
    """
    set_web_config itself, with /etc/nginx/conf.d/jaaql.conf and /nginx-mount/nginx.config redirected to temporary files and nginx stood in
    for
    """

    def test_twice_on_a_certbot_config(self):
        nginx = NginxStandIn()
        first, raised = run_set_web_config(CERTBOT_CONF, nginx)
        self.assertIsNone(raised)
        second, raised = run_set_web_config(first, nginx)
        self.assertIsNone(raised)

        self.assertEqual(first.decode("utf-8"), merge(CERTBOT_CONF))
        self.assertEqual(second, first)
        self.assertEqual(nginx.calls, [NGINX_TEST, NGINX_RELOAD, NGINX_TEST, NGINX_RELOAD])

    def test_a_legacy_config_is_repaired_and_switched_off(self):
        self.assertEqual(run_set_web_config(LEGACY_CONF, NginxStandIn())[0].decode("utf-8"),
                         merge(CERTBOT_CONF).replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))
        self.assertEqual(run_set_web_config(LEGACY_CONF, NginxStandIn(), http3="FALSE")[0].decode("utf-8"),
                         merge(CERTBOT_CONF, http3="FALSE").replace(LISTEN_SSL_IPV6, LISTEN_SSL_IPV6_RESTORED))

    def test_an_abort_leaves_the_file_alone(self):
        broken = "server {\n    charset UTF-8;\n    index index.html;    listen 443 ssl;\n}\n"
        nginx = NginxStandIn()
        text, raised = run_set_web_config(broken, nginx)

        self.assertEqual(text.decode("utf-8"), broken)
        self.assertIsNone(raised)
        self.assertEqual(nginx.calls, [])

    def test_a_config_nginx_refuses_is_put_back_byte_for_byte_and_not_reloaded(self):
        # Line ends of CR LF and a last line without one, which a file read and written as text would not keep
        error = "nginx: [emerg] unknown directive \"jaaql_test_unknown_directive\" in /etc/nginx/conf.d/jaaql.conf:30\n" \
                "nginx: configuration file /etc/nginx/nginx.conf test failed\n"
        for label, site in {"certbot": CERTBOT_CONF.encode("utf-8"), "legacy": LEGACY_CONF.encode("utf-8"),
                            "CR LF, no last line end": CERTBOT_CONF.replace("\n", "\r\n").encode("utf-8")[:-2]}.items():
            with self.subTest(site=label):
                nginx = NginxStandIn(test=(1, error))
                text, raised = run_set_web_config(site, nginx)

                self.assertEqual(text, site)
                self.assertEqual(nginx.calls, [NGINX_TEST])
                self.assertEqual(raised.response_code, 500)
                self.assertIn(error.strip(), raised.message)
                self.assertIn("/etc/nginx/conf.d/jaaql.conf was put back as it was and nginx was not reloaded", raised.message)

    def test_a_failed_reload_fails_the_request_and_keeps_the_config_nginx_accepted(self):
        error = "nginx: [error] invalid PID number \"\" in \"/run/nginx.pid\"\n"
        nginx = NginxStandIn(reload=(1, error))
        text, raised = run_set_web_config(CERTBOT_CONF, nginx)

        self.assertEqual(text.decode("utf-8"), merge(CERTBOT_CONF))
        self.assertEqual(nginx.calls, [NGINX_TEST, NGINX_RELOAD])
        self.assertEqual(raised.response_code, 500)
        self.assertIn("nginx -s reload failed:\n" + error.strip(), raised.message)


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

    def localise(self, text):
        # Certbot's /etc/letsencrypt paths pointed at this class's, without DH parameters where Certbot is not installed
        text = text.replace("/etc/letsencrypt/", self.directory + "/letsencrypt/")
        if not self.has_dhparams:
            text = "".join(line for line in text.splitlines(keepends=True) if "ssl_dhparam" not in line)
        return text

    def run_nginx(self, command, **kwargs):
        # nginx -t or nginx -s reload as set_web_config runs it, by the nginx under test with this class's nginx.conf, whose
        # conf.d/jaaql.conf is the file set_web_config writes. No nginx runs with its pid file, so a reload fails as on a box whose nginx
        # is not running
        self.commands.append(command)
        return SUBPROCESS_RUN([os.environ["JAAQL_TEST_NGINX"], *command[1:], "-e", self.directory + "/error.log", "-p", self.directory,
                               "-c", self.directory + "/nginx.conf"], **kwargs)

    def setUp(self):
        self.commands = []

    def assert_nginx_accepts(self, text, allowed_warning=None):
        with open(os.path.join(self.directory, "jaaql.conf"), "w") as f:
            f.write(self.localise(text))
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

    def test_set_web_config_reloads_a_config_nginx_accepts(self):
        # The reload stood in for, as no nginx runs here to take it
        site = self.localise(CERTBOT_CONF)
        reload = NginxStandIn()
        text, raised = run_set_web_config(site, lambda command, **kwargs: self.run_nginx(command, **kwargs) if command == NGINX_TEST
                                          else reload(command, **kwargs), directory=self.directory)

        self.assertIsNone(raised)
        self.assertEqual(text.decode("utf-8"), merge(site))
        self.assertEqual(self.commands, [NGINX_TEST])
        self.assertEqual(reload.calls, [NGINX_RELOAD])

    def test_set_web_config_puts_back_a_config_nginx_refuses_byte_for_byte_and_does_not_reload(self):
        # Line ends of CR LF and a last line without one, which a file read and written as text would not keep
        for label, conf in {"certbot": CERTBOT_CONF, "legacy": LEGACY_CONF,
                            "CR LF, no last line end": CERTBOT_CONF.replace("\n", "\r\n")[:-2]}.items():
            with self.subTest(site=label):
                self.commands = []
                site = self.localise(conf).encode("utf-8")
                text, raised = run_set_web_config(site, self.run_nginx, app_config=APP_CONFIG_REFUSED, directory=self.directory)

                self.assertEqual(text, site)
                self.assertEqual(self.commands, [NGINX_TEST])
                self.assertEqual(raised.response_code, 500)
                self.assertIn('[emerg] unknown directive "jaaql_test_unknown_directive" in ' + self.directory + '/jaaql.conf:', raised.message)
                self.assertIn("test failed", raised.message)
                self.assert_nginx_accepts(site.decode("utf-8"))

    def test_a_failed_reload_fails_set_web_config_and_keeps_the_config_nginx_accepted(self):
        site = self.localise(CERTBOT_CONF)
        text, raised = run_set_web_config(site, self.run_nginx, directory=self.directory)

        self.assertEqual(text.decode("utf-8"), merge(site))
        self.assertEqual(self.commands, [NGINX_TEST, NGINX_RELOAD])
        self.assertEqual(raised.response_code, 500)
        self.assertIn("nginx -s reload failed:\n", raised.message)
        self.assertIn(self.directory + "/nginx.pid", raised.message)


if __name__ == "__main__":
    unittest.main()
