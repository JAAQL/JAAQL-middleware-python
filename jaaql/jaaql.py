from logging import StreamHandler
from jaaql.constants import ENVIRON__vault_key, ENVIRON__jaaql_profiling
import re
import logging
import pkgutil
from jaaql.openapi.swagger_documentation import produce_all_documentation
from jaaql.email.email_manager_service import create_flask_app as create_email_service_app
from jaaql.services.migrations_manager_service import bootup
from jaaql.services.shared_var_service import bootup as shared_var_bootup
from typing import List
from jaaql.utilities.options import parse_options, Option, OPT_KEY__profiling
import sys
import threading
import os
import jaaql.documentation as documentation
from jaaql.utilities.utils import load_config, get_base_url
from jaaql.mvc.controller import JAAQLController
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.controller_interface import JAAQLControllerInterface
from jaaql.mvc.model_interface import JAAQLModelInterface
from jaaql.config_constants import *
import inspect
from os.path import join, dirname, basename


DEFAULT__mfa_label = "test"
DEFAULT_VAULT_KEY = "default_vault_key"

WARNING__audit_off = "Audit trail is off. Logs will still be kept by the internal postgres instance"


class SensitiveHandler(StreamHandler):

    PATTERN = r"(?:\?|&|;)([^=]+)=([^\s&|;]+)"

    def emit(self, record):
        msg = self.format(record)
        msg = re.sub(self.PATTERN, lambda x: x[0][0:len(x[0]) - len(x[2])] + min(len(x[2]), 5) * '*', msg)
        if "GET /internal/is_installed HTTP/1.1" not in msg:
            print(msg)


def dir_non_builtins(folder):
    if isinstance(folder, str):
        pkgpath = folder
    else:
        pkgpath = os.path.dirname(folder.__file__)
    pre_dirs = [(loader, name) for loader, name, _ in pkgutil.walk_packages([pkgpath])]
    dirs = []
    for sub_dir in pre_dirs:
        if sub_dir[1] in dir(folder):
            dirs.append(getattr(folder, sub_dir[1]))
        else:
            dirs.append(sub_dir[0].find_module(sub_dir[1]).load_module(sub_dir[1]))
    return [doc for doc in dirs if doc.__name__ != "builtins"]


def create_app(override_config_path: str = None, controllers: [JAAQLControllerInterface] = None, models: [JAAQLModelInterface] = None,
               additional_options: List[Option] = None, supplied_documentation = None, **kwargs):
    is_gunicorn = os.environ.get("JAAQL_DEPLOYED") == "true"

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

    if not is_gunicorn:
        options = parse_options(sys.argv, False, additional_options=additional_options)
    else:
        options = {}

    if not is_gunicorn:
        threading.Thread(target=create_email_service_app, args=[DEFAULT_VAULT_KEY], daemon=True).start()
        threading.Thread(target=bootup, args=[DEFAULT_VAULT_KEY, False], daemon=True).start()
        threading.Thread(target=shared_var_bootup, daemon=True).start()

    if is_gunicorn:
        vault_key = os.environ.get(ENVIRON__vault_key)
        if not vault_key:
            print("Could not find vault key. Set with environment variable: '" + ENVIRON__vault_key + "'")
            exit(1)
    else:
        vault_key = DEFAULT_VAULT_KEY

    logging.getLogger("werkzeug").handlers.append(SensitiveHandler())

    config = load_config(is_gunicorn, override_config_path)

    mfa_name = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__mfa_label]
    if mfa_name == DEFAULT__mfa_label:
        print("MFA label is set to default. This isn't a security issue but adds a nice name when added to "
              "authenticator apps via QR codes. You can change in the config")

    force_mfa = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__force_mfa] in ("true", "True", True, "TRUE")
    do_audit = config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__do_audit] in ("true", "True", True, "TRUE")

    # The following code sets it "properly" in case it is accessed incorrectly from elsewhere
    config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__force_mfa] = force_mfa
    config[CONFIG_KEY__security][CONFIG_KEY_SECURITY__do_audit] = do_audit

    if not do_audit:
        print(WARNING__audit_off, file=sys.stderr)

    url = config[CONFIG_KEY__swagger][CONFIG_KEY_SWAGGER__url]

    migration_folder = join(dirname(inspect.stack()[1].filename), "migrations")
    migration_project_name = basename(dirname(inspect.stack()[1].filename))
    if not os.path.exists(migration_folder):
        migration_folder = None
        migration_project_name = None

    model = JAAQLModel(config, vault_key, options, migration_project_name, migration_folder, is_container=is_gunicorn, url=url)
    controller = JAAQLController(model, is_gunicorn, get_base_url(config, is_gunicorn),
                                 OPT_KEY__profiling in options or os.environ.get(ENVIRON__jaaql_profiling))
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
        controller.app.run(port=int(config[CONFIG_KEY__server][CONFIG_KEY_SERVER__port]), host="0.0.0.0", threaded=True)
