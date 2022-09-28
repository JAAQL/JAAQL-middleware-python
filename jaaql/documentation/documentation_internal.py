from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.documentation.documentation_shared import rename_arg, ARG_RES__tenant, ARG_RES__password

TITLE = "JAAQL Internal API"
DESCRIPTION = "Collection of methods in the JAAQL internal API"
FILENAME = "jaaql_internal_api"

ARG_RES__install_key = SwaggerArgumentResponse(
    name=KEY__install_key,
    description="Single use/purpose key. Find in the logs, line starting with 'INSTALL KEY:' at startup",
    arg_type=str,
    example=["aefc1b08-a573-466f-bdd0-706ae281cc99", "ec63aa9a-b189-419f-8e0b-7fcc4ff8c857"],
    required=True
)

ARG_RES__uninstall_key = rename_arg(ARG_RES__install_key, KEY__uninstall_key, ARG_RES__install_key.description.replace("INSTALL", "UNINSTALL"))

DOCUMENTATION__install = SwaggerDocumentation(
    tags="Installation",
    security=False,  # This method is not secured as the system is not setup yet. It uses a OTP token system via logs
    methods=SwaggerMethod(
        name="Install JAAQL",
        description="Installs JAAQL to the configured database. Please allow a minute after running for the server to "
                    "refresh and reload. A connection string is required for local installation and is not allowed when running "
                    "inside a docker container as the docker container comes with a postgres database and JAAQL will use that",
        method=REST__POST,
        body=[
            SwaggerArgumentResponse(
                name="db_connection_string",
                description="Database connection string",
                arg_type=str,
                example=["postgresql://postgres:123456@localhost:5432/",
                         "postgresql://postgres:pa55word@localhost:5432/"],
                required=True,
                local_only=True
            ),
            ARG_RES__install_key,
            SwaggerArgumentResponse(
                name=KEY__default_tenant_password,
                description="As well as the jaaql tenant, the default tenant is also created. The super user for this tenant has a username "
                            "'tenantsuper'",
                example=["pa55word"],
                strip=True,
                arg_type=str
            ),
            SwaggerArgumentResponse(
                name=KEY__superjaaql_password,
                description="At the postgres level, the postgres user is used to set up the jaaql user. If you want "
                            "access to the postgres user through JAAQL, please provide a password and this user will be setup for "
                            "you. This is a JAAQL login for superjaaql so it is entirely independent of the postgres password at "
                            "the database level. If you do not supply this password, you will not be able to login to jaaql "
                            "authenticating as postgres with the local database node. You can currently not set this up later but it is possible ",
                example=["passw0rd"],
                required=False,
                strip=True,
                condition="Does the superjaaql user have a password",
                arg_type=str
            ),
            SwaggerArgumentResponse(
                name=KEY__allow_uninstall,
                description="Allows uninstall. DO NOT USE ON PROD, used to aid with testing. Defaults to false if not supplied",
                example=[False, True],
                required=False,
                condition="If you want to specify if uninstallation allowed",
                arg_type=bool
            )
        ],
        response=[
            SwaggerFlatResponse(),
            SwaggerFlatResponse(
                description=ERR__already_installed,
                code=HTTPStatus.UNPROCESSABLE_ENTITY,
                body=ERR__already_installed
            )
        ]
    )
)

DOCUMENTATION__uninstall = SwaggerDocumentation(
    tags="Installation",
    security=False,  # Would not matter which user uses it, needs root db credentials
    methods=SwaggerMethod(
        name="Uninstall JAAQL",
        description="Uninstalls the JAAQL system",
        method=REST__POST,
        body=[
            SwaggerArgumentResponse(
                name=KEY__db_super_user_password,
                description="The password for the database super user account",
                example=["123456"],
                arg_type=str
            ),
            ARG_RES__uninstall_key
        ]
    )
)

DOCUMENTATION__is_installed = SwaggerDocumentation(
    tags="Installation",
    security=False,
    methods=SwaggerMethod(
        name="Is installed",
        description="Returns 200 OK if the service has installed otherwise a 422",
        method=REST__GET,
        response=[
            SwaggerFlatResponse(),
            SwaggerFlatResponse(
                description=ERR__not_yet_installed,
                code=HTTPStatus.UNPROCESSABLE_ENTITY,
                body=ERR__not_yet_installed
            )
        ]
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh

DOCUMENTATION__is_alive = SwaggerDocumentation(
    security=False,
    tags="Is Alive",
    methods=SwaggerMethod(
        name="Check is alive",
        description="An endpoint that can be called by any service to see if the service is alive",
        method=REST__GET
    )
)

DOCUMENTATION__add_tenant = SwaggerDocumentation(
    tags="Tenants",
    methods=SwaggerMethod(
        name="Add Tenant",
        method=REST__POST,
        description="Adds a new tenant",
        arguments=[
            rename_arg(ARG_RES__tenant, KEY__tenant_name),
            rename_arg(ARG_RES__password, new_description="The password for the tenant super user")
        ]
    )
)

DOCUMENTATION__deploy = SwaggerDocumentation(
    tags="Deployment",
    methods=[
        SwaggerMethod(
            name="Redeploys the JAAQL service",
            description="Will redeploy the JAAQL service, loading the latest version from git. In the future will "
                        "support loading a specific tagged version",
            method=REST__POST
        )
    ]
)
