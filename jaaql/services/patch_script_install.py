from jaaql.patch import monkey_patch

monkey_patch()

from jaaql.services.script_install import bootup
import os
from jaaql.constants import ENVIRON__vault_key

bootup(os.environ.get(ENVIRON__vault_key), True)
