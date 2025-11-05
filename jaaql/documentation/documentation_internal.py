from jaaql.documentation.documentation_public import ARG_RES__query
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
                description="Not yet installed",
                code=HTTPStatus.UNPROCESSABLE_ENTITY,
                body="Not yet installed"
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

DOCUMENTATION__freeze = SwaggerDocumentation(
    tags="Freeze",
    methods=[
        SwaggerMethod(
            name="Freeze JAAQL",
            description="Allows only requests from local IP addresses or super user",
            method=REST__POST
        )
    ]
)

DOCUMENTATION__defrost = SwaggerDocumentation(
    tags="Freeze",
    methods=SwaggerMethod(
        name="Defrost JAAQL",
        description="Allows all requests again",
        method=REST__POST
    )
)

DOCUMENTATION__check_frozen = SwaggerDocumentation(
    tags="Freeze",
    security=False,
    methods=SwaggerMethod(
        name="Check Frozen",
        description="Allows only requests from local IP addresses or super user",
        method=REST__GET
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh, ARG_RES__tenant, ARG_RES__provider

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

DOCUMENTATION__domains = SwaggerDocumentation(
    tags="Prepare",
    methods=SwaggerMethod(
        name="Fetches domains",
        description="Fetches database level domains",
        method=REST__POST,
        body=SwaggerArgumentResponse(
            name=KEY__database,
            description="The database against which to fetch the domains",
            arg_type=str,
            example=["database"]
        ),
        response=RES__allow_all
    )
)

DOCUMENTATION__set_web_config = SwaggerDocumentation(
    tags="Web Config",
    methods=SwaggerMethod(
        name="Sets web config",
        description="Updates the nginx configuration, including security headers",
        method=REST__POST
    )
)

DOCUMENTATION__last_successful_build_timestamp = SwaggerDocumentation(
    tags="Build Information",
    security=False,
    methods=[
        SwaggerMethod(
            name="Sets build time",
            description="Updates the nginx configuration, including security headers",
            method=REST__POST,
            body=[
                SwaggerArgumentResponse(
                    name=KG__jaaql__last_successful_build_time,
                    description="The build time",
                    arg_type=int,
                    example=[1735462031]
                )
            ]
        ),
        SwaggerMethod(
            name="Gets build time",
            description="Sets the time at which the last successful build happened",
            method=REST__GET,
            response=SwaggerFlatResponse(
                description="The time that this build occurred, or 0 if unset"
            )
        )
    ]
)

DOCUMENTATION__flush_cache = SwaggerDocumentation(
    tags="Cache",
    security=False,
    methods=SwaggerMethod(
        name="Flush JAAQL Cache",
        description="Triggers a cache flush",
        method=REST__GET,
    )
)

DOCUMENTATION__cron = SwaggerDocumentation(
    tags="Cron",
    security=False,
    methods=SwaggerMethod(
        name="Trigger cron jobs",
        description="Internal only method that will trigger cron jobs",
        method=REST__GET
    )
)

ARG_RES__application = SwaggerArgumentResponse(
    name=KG__application_schema__application,
    description="The name of the application",
    arg_type=str,
    example=["out-and-about"]
)
ARG_RES__schema = SwaggerArgumentResponse(
    name=KEY__schema,
    description="The schema of the application",
    arg_type=str,
    required=False,
    condition="Whether to use the default schema",
    example=["default"]
)
KEY__redirect_uri = "redirect_uri"
ARG_RES__redirect_uri = SwaggerArgumentResponse(
    name=KEY__redirect_uri,
    description="The redirect uri that shall be used",
    arg_type=str,
    required=True,
    example=["index.html"]
)

DOCUMENTATION__oidc_user_registries = SwaggerDocumentation(
    tags="oidc",
    security=False,
    methods=SwaggerMethod(
        name="Fetch OIDC registries",
        description="Fetches OIDC registries for specified database and tenant",
        method=REST__GET,
        arguments=[
            ARG_RES__tenant,
            ARG_RES__application,
            ARG_RES__schema
        ],
        response=SwaggerResponse(
            description="Providers response",
            response=SwaggerArgumentResponse(
                name="providers",
                description="A list of the providers",
                arg_type=SwaggerList(
                    ARG_RES__provider,
                    SwaggerArgumentResponse(
                        name=KG__identity_provider_service__logo_url,
                        description="The logo url for the provider",
                        arg_type=str,
                        example=["/identity-logos/azure.png"]
                    )
                )
            )
        )
    )
)

DOCUMENTATION__oidc_redirect_url = SwaggerDocumentation(
    tags="oidc",
    security=False,
    methods=SwaggerMethod(
        name="Fetch OIDC base redirect",
        description="Fetches OIDC base redirect URL",
        method=REST__GET,
        arguments=[
            ARG_RES__tenant,
            ARG_RES__provider,
            ARG_RES__application,
            ARG_RES__schema,
            ARG_RES__redirect_uri
        ],
        response=SwaggerFlatResponse(
            description="URL",
            code=HTTPStatus.FOUND,
            body="You are being redirected to the identity server..."
        )
    )
)

KEY__code = "code"
KEY__state = "state"

DOCUMENTATION__oidc_exchange_code = SwaggerDocumentation(
    tags="oidc",
    security=False,
    methods=SwaggerMethod(
        name="Fetch OIDC code",
        description="Exchanges OIDC auth code for auth token, returns the token",
        method=REST__GET,
        arguments=SwaggerArgumentResponse(
            name="response",
            description="The OIDC response JWT object",
            arg_type=str,
            example=["eyJ..."]
        ),
        response=SwaggerFlatResponse(
            description="URL",
            code=HTTPStatus.FOUND,
            body="You are being redirected back to your place in the app..."
        )
    )
)

DOCUMENTATION__jwks = SwaggerDocumentation(
    tags="jwks",
    security=False,
    methods=SwaggerMethod(
        name="Fetch JWKS",
        description="Fetches the JWKS so that mTLS can be used with JAAQL",
        method=REST__GET,
        response=SwaggerResponse(
            description="The Keys",
            response=SwaggerArgumentResponse(
                name="keys",
                description="A list of keys",
                arg_type=SwaggerList(
                    SwaggerArgumentResponse(
                        name="e",
                        description="JWKS e",
                        arg_type=str,
                        example=["AQAB"]
                    ),
                    SwaggerArgumentResponse(
                        name="kty",
                        description="JWKS kty",
                        arg_type=str,
                        example=["RSA"]
                    ),
                    SwaggerArgumentResponse(
                        name="n",
                        description="The public key",
                        arg_type=str,
                        example=["tKiq..."]
                    ),
                    SwaggerArgumentResponse(
                        name="kid",
                        description="The unique id",
                        arg_type=str,
                        example=["tKiq..."]
                    ),
                    SwaggerArgumentResponse(
                        name="alg",
                        description="The algorithm",
                        arg_type=str,
                        example=["RS256"]
                    ),
                    SwaggerArgumentResponse(
                        name="use",
                        description="The use",
                        arg_type=str,
                        example=["SIG"]
                    )
                )
            )
        )
    )
)


DOCUMENTATION__procedures = SwaggerDocumentation(
    tags="procedures",
    methods=SwaggerMethod(
        name="Set Procedures",
        description="Sets the procedures",
        method=REST__POST,
        body=[
            ARG_RES__application,
            SwaggerArgumentResponse(
                name="procs",
                description="A list of procs",
                arg_type=SwaggerList(
                    SwaggerArgumentResponse(
                        name=KG__remote_procedure__name,
                        description="The name of the procedure",
                        arg_type=str,
                        example=["webhook$receive"]
                    ),
                    SwaggerArgumentResponse(
                        name=KG__remote_procedure__command,
                        description="The command used to execute the procedure",
                        arg_type=str,
                        example=["cd /procs && node 'some/file.js'"]
                    ),
                    SwaggerArgumentResponse(
                        name=KG__remote_procedure__access,
                        description="The access level of the procedure",
                        arg_type=str,
                        example=["P"]
                    ),
                    SwaggerArgumentResponse(
                        name="cron",
                        description="The cron expression",
                        arg_type=str,
                        required=False,
                        condition="Only for system procedures",
                        example=["16 17 * * WED"]
                    )
                )
            )
        ]
    )
)

ARG_RES__id_token_hint = SwaggerArgumentResponse(
	name="id_token_hint",
	description="Optional ID Token previously issued to the user; recommended for OIDC RP-initiated logout.",
	arg_type=str,
	required=False,
    condition="Recommended",
	example=["eyJ..."]
)

DOCUMENTATION__oidc_begin_logout = SwaggerDocumentation(
	tags="oidc",
	security=False,
	methods=SwaggerMethod(
		name="Begin OIDC logout",
		description="Clears the app session, sets a logout state cookie, and redirects the browser to the OP end-session endpoint. After logout, the OP redirects to /api/oidc/post-logout.",
		method=REST__GET,
		arguments=[
			ARG_RES__tenant,
			ARG_RES__provider,
			ARG_RES__application,
			ARG_RES__schema,
			ARG_RES__redirect_uri,
			ARG_RES__id_token_hint
		],
		response=SwaggerFlatResponse(
			description="Redirect",
			code=HTTPStatus.FOUND,
			body="You are being redirected to the identity server for logout..."
		)
	)
)

DOCUMENTATION__oidc_post_logout = SwaggerDocumentation(
	tags="oidc",
	security=False,
	methods=SwaggerMethod(
		name="OIDC post-logout redirect",
		description="Receives the OP redirect after logout, validates state, clears the cookie, and redirects to the final app URL.",
		method=REST__GET,
		arguments=SwaggerArgumentResponse(
			name="state",
			description="Opaque state returned by the OP; must match the value set at logout start.",
			arg_type=str,
			example=["y3nvJ..."]
		),
		response=SwaggerFlatResponse(
			description="Redirect",
			code=HTTPStatus.FOUND,
			body="You are being redirected back to your place in the app..."
		)
	)
)

DOCUMENTATION__security_event = SwaggerDocumentation(
    tags="security",
    methods=SwaggerMethod(
        name="Action security event",
        description="Executes a security event",
        method=REST__POST,
        body=[
            ARG_RES__application,
            SwaggerArgumentResponse(
                name=KG__security_event__name,
                description="The name of the security event",
                arg_type=str,
                example=["add-user"]
            ),
            SwaggerArgumentResponse(
                name=KG__security_event__type,
                description="The name of the security event",
                arg_type=str,
                example=["add-user"]
            ),
            SwaggerArgumentResponse(
                name=KEY__parameters,
                description="Any parameters to pass to the underlying function",
                arg_type=ARG_RESP__allow_all
            ),
            SwaggerArgumentResponse(
                name="explicit_types",
                description="Explicit types for parameters",
                arg_type=ARG_RESP__allow_all
            )
        ],
        response=RES__allow_all
    )
)