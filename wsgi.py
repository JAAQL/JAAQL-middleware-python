from jaaql.jaaql import create_app
import jaaql.documentation as documentation
from jaaql.utilities.options import *
import sys
import threading
import time
from jaaql.utilities.vault import Vault, DIR__vault
from jaaql.email.email_manager_service import create_flask_app as create_email_service_app

if __name__ == '__main__':
    options = parse_options(sys.argv, False)
    Vault(options.get(OPT_KEY__vault_key), DIR__vault)  # Initialise the Vault, creating the salt
    threading.Thread(target=create_email_service_app,
                     args=[options.get(OPT_KEY__vault_key), options.get(OPT_KEY__email_credentials)],
                     daemon=True).start()
    time.sleep(5)
    port, flask_app = create_app(supplied_documentation=documentation)
    flask_app.run(port=port, host="0.0.0.0", threaded=True)
else:
    def build_app(*args, **kwargs):
        return create_app(is_gunicorn=True, **kwargs)
