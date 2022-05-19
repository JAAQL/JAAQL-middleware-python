from logging import StreamHandler
from jaaql.constants import ENVIRON__vault_key
import re
import logging
import pkgutil
from os.path import exists
import configparser
from jaaql.openapi.swagger_documentation import produce_all_documentation
from jaaql.utilities.options import *
import sys
import os
import jaaql.documentation as documentation
from jaaql.utilities.utils import load_config
from jaaql.mvc.controller import JAAQLController
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.controller_interface import JAAQLControllerInterface
from jaaql.mvc.model_interface import JAAQLModelInterface
from jaaql.config_constants import *


DEFAULT__mfa_label = "test"

CONFIG_KEY__security = "SECURITY"
CONFIG_KEY_SECURITY__mfa_label = "mfa_label"
CONFIG_KEY_SECURITY__do_audit = "do_audit"
CONFIG_KEY__swagger = "SWAGGER"
CONFIG_KEY_SWAGGER__url = "url"

WARNING__vault_key_stdin = "MAJOR SECURITY ISSUE! Passing vault key via program arguments is insecure as other progra" \
                           "ms can see the arguments. Please provide via stdin instead!"

WARNING__audit_off = "Audit trail is off. Logs will still be kept by the internal postgres instance"


class SensitiveHandler(StreamHandler):

    PATTERN = r"(?:\?|&|;)([^=]+)=([^\s&|;]+)"

    def emit(self, record):
        msg = self.format(record)
        msg = re.sub(self.PATTERN, lambda x: x[0][0:len(x[0]) - len(x[2])] + min(len(x[2]), 5) * '*', msg)
        if "GET /internal/is_installed HTTP/1.1" not in msg:
            print(msg)


def dir_non_builtins(folder):
    pkgpath = os.path.dirname(folder.__file__)
    pre_dirs = [(loader, name) for loader, name, _ in pkgutil.walk_packages([pkgpath])]
    dirs = []
    for sub_dir in pre_dirs:
        if sub_dir[1] in dir(folder):
            dirs.append(getattr(folder, sub_dir[1]))
        else:
            dirs.append(sub_dir[0].find_module(sub_dir[1]).load_module(sub_dir[1]))
    return [doc for doc in dirs if doc.__name__ != "builtins"]


def create_app(is_gunicorn: bool = False, override_config_path: str = None, migration_db_interface=None,
               migration_project_name: str = None, migration_folder: str = None, supplied_documentation = None,
               controllers: [JAAQLControllerInterface] = None, models: [JAAQLModelInterface] = None, **options):
    if controllers is None:
        controllers = []
    if models is None:
        models = []
    if not isinstance(controllers, list):
        controllers = [controllers]
    if not isinstance(models, list):
        models = [models]

    if supplied_documentation is None:
        supplied_documentation = []
    if not isinstance(supplied_documentation, list):
        supplied_documentation = [supplied_documentation]

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

    config = load_config(is_gunicorn)

    if override_config_path is not None:
        override_config = configparser.ConfigParser()
        override_config.sections()
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
            else:
                config[each] = override_config[each]

    mfa_name = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__mfa_label]
    if mfa_name == DEFAULT__mfa_label:
        print("MFA label is set to default. This isn't a security issue but adds a nice name when added to "
              "authenticator apps via QR codes. You can change in the config")

    force_mfa = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__force_mfa] in ("true", "True", True)
    do_audit = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__do_audit] in ("true", "True", True)
    invite_only = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__invite_only] in ("true", "True", True)

    # The following code sets it "properly" in case it is accessed incorrectly from elsewhere
    config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__force_mfa] = force_mfa
    config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__do_audit] = do_audit
    config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__invite_only] = invite_only

    if not do_audit:
        print(WARNING__audit_off, file=sys.stderr)

    url = config[CONFIG_KEY__swagger][CONFIG_KEY_SWAGGER__url]

    model = JAAQLModel(config, vault_key, migration_db_interface, migration_project_name, migration_folder,
                       is_container=is_gunicorn, url=url)
    controller = JAAQLController(model, is_gunicorn)
    controller.create_app()

    for sub_controller in controllers:
        sub_controller.route(controller)

    for sub_model in models:
        sub_model.set_model(model)

    doc_modules = dir_non_builtins(documentation)
    all_docs = []
    for doc in supplied_documentation:
        all_docs.extend(dir_non_builtins(doc))

    base_path = None
    if is_gunicorn:
        base_path = "www"
        url += "/api/"

    produce_all_documentation(doc_modules + all_docs, url, is_prod=is_gunicorn, base_path=base_path)

    if is_gunicorn:
        return controller.app
    else:
        return int(config[CONFIG_KEY__server][CONFIG_KEY_SERVER__port]), controller.app
