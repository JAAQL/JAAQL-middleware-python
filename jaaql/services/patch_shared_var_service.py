from jaaql.patch import monkey_patch

monkey_patch()

from jaaql.services.shared_var_service import bootup

bootup()
