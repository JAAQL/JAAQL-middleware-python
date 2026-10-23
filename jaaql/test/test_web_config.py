"""
set_web_config puts the application's nginx config into /etc/nginx/conf.d/jaaql.conf and HTTP/3 (http3 on, quic_retry on,
http3_max_concurrent_streams 64, the two QUIC listens and Alt-Svc) on lines of their own before Certbot's `listen 443 ssl`, exactly once
however often it runs, unless JAAQL_HTTP3 is FALSE. Earlier versions wrote those lines without line ends, glued onto the front of
`listen 443 ssl`, so every later run dropped that line and aborted; such a file is repaired.

    python -m unittest jaaql.test.test_web_config

The tests need only the package's requirements
"""
import os
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
APP_ALT_SVC = "        add_header Alt-Svc 'h3=\":443\"; ma=86400' always;\n"


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

    def test_a_certbot_config_gets_http3_once_and_a_second_run_changes_nothing(self):
        first = merge(CERTBOT_CONF)
        second = merge(first)

        self.assertEqual(second, first)
        self.assert_http3_once_before_listen_ssl(first)
        self.assertNotIn("http3 on;    ", first)
        # The application's config replaced the entrypoint's in both servers, with its own Alt-Svc
        self.assertEqual(first.splitlines(keepends=True).count("    http2 on;\n"), 2)
        self.assertEqual(first.splitlines(keepends=True).count(APP_ALT_SVC), 2)
        self.assertNotIn("add_header \"X-Content-Type-Options\"", first)

    def test_the_http3_lines_are_exactly_those_of_the_hardened_config(self):
        self.assertEqual(model.WEB_CONFIG__http3_lines, HTTP3_LINES)

    def test_a_config_with_the_lines_glued_onto_listen_ssl_is_repaired(self):
        repaired = merge(LEGACY_CONF)

        self.assertEqual(repaired, merge(CERTBOT_CONF))
        self.assertEqual(merge(repaired), repaired)

    def test_http3_switched_off_strips_it_and_adds_none(self):
        expected = merge(CERTBOT_CONF, http3="FALSE")
        self.assert_no_http3(expected)

        for http3 in ["FALSE", "false", "False"]:
            self.assertEqual(merge(merge(CERTBOT_CONF), http3=http3), expected)
            self.assertEqual(merge(LEGACY_CONF, http3=http3), expected)
        self.assertEqual(merge(expected, http3="FALSE"), expected)

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

    def test_losing_listen_ssl_aborts(self):
        self.assertIsNone(merge("server {\n    charset UTF-8;\n    index index.html;    listen 443 ssl;\n}\n"))


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
        self.assertEqual(self.run_set_web_config(LEGACY_CONF)[0], merge(CERTBOT_CONF))
        self.assertEqual(self.run_set_web_config(LEGACY_CONF, http3="FALSE")[0], merge(CERTBOT_CONF, http3="FALSE"))

    def test_an_abort_leaves_the_file_alone(self):
        broken = "server {\n    charset UTF-8;\n    index index.html;    listen 443 ssl;\n}\n"
        text, calls = self.run_set_web_config(broken)

        self.assertEqual(text, broken)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
