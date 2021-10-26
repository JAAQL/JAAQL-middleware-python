from psycopg2cffi import compat
from logging import StreamHandler
from jaaql.mvc.controller import JAAQLController
from jaaql.mvc.model import JAAQLModel
import re
import logging
import types
from os.path import exists, join
import configparser
from jaaql.openapi.swagger_documentation import produce_all_documentation
from jaaql.utilities.options import *
import sys
import os
import jaaql.documentation as documentation
from gevent import monkey
from psycogreen import gevent
from jaaql.utilities.utils import get_jaaql_root

DIR__config = "config"
FILE__config = "config.ini"

ENVIRON__vault_key = "JAAQL_VAULT_PASSWORD"

DEFAULT__mfa_label = "test"
CONFIG_KEY__security = "SECURITY"
CONFIG_KEY_SECURITY__mfa_label = "mfa_label"
CONFIG_KEY_SECURITY__use_mfa = "use_mfa"
CONFIG_KEY__swagger = "SWAGGER"
CONFIG_KEY_SWAGGER__url = "url"
CONFIG_KEY__server = "SERVER"
CONFIG_KEY_SERVER__port = "port"

WARNING__vault_key_stdin = "MAJOR SECURITY ISSUE! Passing vault key via program arguments is insecure as other progra" \
                           "ms can see the arguments. Please provide via stdin instead!"

WARNING__mfa_off = "MAJOR SECURITY ISSUE! config SECURITY->use_mfa is set to false. Please enable it for PROD (it wil" \
                   "l be enabled using the default docker configuration"


class SensitiveHandler(StreamHandler):

    PATTERN = r"(?:\?|&|;)([^=]+)=([^\s&|;]+)"

    def emit(self, record):
        msg = self.format(record)
        msg = re.sub(self.PATTERN, lambda x: x[0][0:len(x[0]) - len(x[2])] + min(len(x[2]), 5) * '*', msg)
        print(msg)


def dir_non_builtins(folder):
    dirs = [getattr(documentation, sub) for sub in dir(folder) if isinstance(getattr(documentation, sub),
                                                                             types.ModuleType)]
    return [doc for doc in dirs if doc.__name__ != "builtins"]


def create_app(is_gunicorn: bool = False, override_config_path: str = None, **options):
    if is_gunicorn:
        compat.register()
        monkey.patch_all()
        gevent.patch_psycopg()

    if len(options) == 0 and not is_gunicorn:
        options = parse_options(sys.argv, False)

    if OPT_KEY__vault_key in options:
        print(WARNING__vault_key_stdin, file=sys.stderr)
        vault_key = options[OPT_KEY__vault_key]
    elif is_gunicorn:
        vault_key = os.environ.get(ENVIRON__vault_key)
    else:
        vault_key = input("Input vault key: ")

    logging.getLogger("werkzeug").handlers.append(SensitiveHandler())

    config = configparser.ConfigParser()
    config.sections()
    config_path = join(get_jaaql_root(), DIR__config, FILE__config)
    if not exists(config_path):
        raise Exception("Could not find config. Please check working directory has access to '" + config_path + "'")
    config.read(config_path)
    config = {s: dict(config.items(s)) for s in config.sections()}

    if override_config_path is not None:
        override_config = configparser.ConfigParser()
        override_config.sections()
        override_config_path = join(get_jaaql_root(), DIR__config, FILE__config)
        if not exists(override_config_path):
            raise Exception("Could not find override config. Please check working directory has access to '"
                            + override_config_path + "'")
        override_config.read(override_config_path)
        override_config = {s: dict(override_config.items(s)) for s in override_config.sections()}
        for each, _ in override_config.items():
            if each in config:
                for sub_each, val in override_config[each].items():
                    if sub_each in config[each]:
                        config[each][sub_each] = val

    mfa_name = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__mfa_label]
    if mfa_name == DEFAULT__mfa_label:
        print("MFA label is set to default. This isn't a security issue but adds a nice name when added to "
              "authenticator apps via QR codes. You can change in the config")

    use_mfa = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__use_mfa] in ("true", "True", True)
    config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__use_mfa] = use_mfa
    if not use_mfa:
        print(WARNING__mfa_off, file=sys.stderr)

    model = JAAQLModel(config, vault_key)
    controller = JAAQLController(model)
    controller.create_app()

    doc_modules = dir_non_builtins(documentation)

    base_path = None
    url = config[CONFIG_KEY__swagger][CONFIG_KEY_SWAGGER__url]
    if is_gunicorn:
        base_path = "www"
        url += "/api/"

    produce_all_documentation(doc_modules, url, is_prod=is_gunicorn, base_path=base_path)

    if is_gunicorn:
        return controller.app
    else:
        return int(config[CONFIG_KEY__server][CONFIG_KEY_SERVER__port]), controller.app
