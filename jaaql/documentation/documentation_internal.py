from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.mvc.generated_queries import *

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
                description="Database connection string for the superuser",
                arg_type=str,
                example=["postgresql://postgres:123456@localhost:5432/",
                         "postgresql://postgres:pa55word@localhost:5432/"],
                required=True,
                local_only=True
            ),
            ARG_RES__install_key,
            SwaggerArgumentResponse(
                name=KEY__jaaql_password,
                description="The password for the jaaql user, can create applications, configurations",
                example=["pa55word"],
                strip=True,
                arg_type=str
            ),
            SwaggerArgumentResponse(
                name=KEY__super_db_password,
                description="Gives access to the database super user",
                example=["passw0rd"],
                required=True,
                strip=True,
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

DOCUMENTATION__migrations = SwaggerDocumentation(
    tags="Migrations",
    security=True,
    methods=SwaggerMethod(
        name="Execute migrations",
        description="Executes the migrations. Can only be done by the super user",
        method=REST__POST
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

DOCUMENTATION__is_alive = SwaggerDocumentation(
    security=False,
    tags="Is Alive",
    methods=SwaggerMethod(
        name="Check is alive",
        description="An endpoint that can be called by any service to see if the service is alive",
        method=REST__GET
    )
)

DOCUMENTATION__clean = SwaggerDocumentation(
    tags="Installation",
    methods=SwaggerMethod(
        name="Clean database",
        description="Will clear the database and leave jaaql installed",
        method=REST__POST
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh

DOCUMENTATION__dispatchers = SwaggerDocumentation(
    tags="Dispatchers",
    methods=SwaggerMethod(
        name="Attach credentials to dispatcher",
        description="Given a prime key for a dispatcher, will encrypt credentials and attach at the database level",
        method=REST__POST,
        body=[
            SwaggerArgumentResponse(
                name=KG__email_dispatcher__application,
                description="The application of the dispatcher",
                arg_type=str,
                example=["out-and-about"]
            ),
            SwaggerArgumentResponse(
                name=KG__email_dispatcher__name,
                description="The name of the email dispatcher",
                arg_type=str,
                example="default"
            ),
            SwaggerArgumentResponse(
                name=KG__email_dispatcher__url,
                description="The url of the mail server against which the dispatcher will authenticate",
                arg_type=str,
                example="mail-server.nl"
            ),
            SwaggerArgumentResponse(
                name=KG__email_dispatcher__port,
                description="The port of the email server which you can connect to using SMTP STARTTLS",
                arg_type=int,
                example=587
            ),
            SwaggerArgumentResponse(
                name=KG__email_dispatcher__username,
                description="The username with which the dispatcher will authenticate",
                arg_type=str,
                example="address@domain.com"
            ),
            SwaggerArgumentResponse(
                name=KG__email_dispatcher__password,
                description="The password with which the dispatcher will authenticate",
                arg_type=str,
                example="pa55word"
            )
        ]
    )
)

DOCUMENTATION__prepare = SwaggerDocumentation(
    tags="Prepare",
    methods=SwaggerMethod(
        name="Prepares queries",
        description="Prepares a set of queries for an application",
        method=REST__POST,
        arguments=ARG_RESP__allow_all,
        response=RES__allow_all
    )
)
