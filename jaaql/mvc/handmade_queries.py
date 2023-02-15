from .exception_queries import *  # Do not remove as others refer to this import

QUERY__setup_jaaql_role = "SELECT setup_jaaql_role();"
QUERY__setup_jaaql_role_with_password = "SELECT setup_jaaql_role_with_password(%(password)s);"
