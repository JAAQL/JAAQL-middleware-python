import coverage
# cov = coverage.coverage()
# cov.start()

from os.path import exists
import os
from jaaql.jaaql import create_app
from jaaql.utilities.utils import load_email_templates
from mvc.controller import CTPController
from mvc.model import CTPModel
import documentation as documentation

import atexit

from os.path import join, dirname
migration_folder = join(dirname(__file__), "migrations")
migration_project_name = "ctp"

was_not_install = exists("has_restarted")


def save_coverage():
    # TODO combine coverage reports
    # TODO coverage reports for library too (so it covers JAAQL)

    print("Saving Coverage")
    # cov.stop()
    # cov.save()
    # cov.html_report(directory="main_coverage" if was_not_install else "install_coverage")

    if was_not_install:
        open("DO_EXIT", "w").close()
    os._exit(0)


atexit.register(save_coverage)

models = CTPModel(load_email_templates())
controllers = CTPController(models)

if __name__ == '__main__':
    port, flask_app = create_app(supplied_documentation=documentation, models=models,
                                 controllers=controllers,
                                 migration_folder=migration_folder,
                                 migration_project_name=migration_project_name)
    flask_app.run(port=port, host="0.0.0.0", threaded=True,)
else:
    def build_app(*args, **kwargs):
        return create_app(is_gunicorn=True, supplied_documentation=documentation,
                          migration_folder=migration_folder,
                          migration_project_name=migration_project_name,
                          models=models, controllers=controllers, **kwargs)
