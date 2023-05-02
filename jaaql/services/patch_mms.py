from jaaql.patch import monkey_patch

monkey_patch()

from jaaql.services.migrations_manager_service import bootup
import os
from jaaql.constants import ENVIRON__vault_key, ENVIRON__local_install

bootup(os.environ.get(ENVIRON__vault_key), True, os.environ.get(ENVIRON__local_install) == "TRUE")
