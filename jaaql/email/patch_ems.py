from jaaql.patch import monkey_patch

monkey_patch()

from jaaql.email.email_manager_service import create_flask_app
import os
from jaaql.constants import ENVIRON__vault_key

create_flask_app(os.environ.get(ENVIRON__vault_key), True)
