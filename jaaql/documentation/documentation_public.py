from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.documentation.documentation_shared import RES__totp_mfa_nullable, ARG_RES__jaaql_password, JWT__invite,\
    gen_arg_res_sort_pageable, gen_filtered_records, ARG_RES__mfa_key, RES__oauth_token, RES__deletion_key,\
    ARG_RES__deletion_key, set_nullable, ARG_RES__application_body, ARG_RES__email, rename_arg,\
    ARG_RES__reference_dataset, ARG_RES__dataset_description

TITLE = "JAAQL API"
DESCRIPTION = "Collection of methods in the JAAQL API"
FILENAME = "jaaql_api"

ARG_RES__application = SwaggerArgumentResponse(
    name=KEY__application,
    description="The name of the application",
    arg_type=str,
    example=["Library Browser", "Meeting Room"],
    required=True
)

ARG_RES__configuration = SwaggerArgumentResponse(
    name=KEY__configuration,
    description="The name of the configuration",
    arg_type=str,
    example=["Library QA", "Meeting DEV"],
    required=True
)

DOCUMENTATION__sign_up = SwaggerDocumentation(
    tags="Signup",
    # The security is in the invite key. User has not signed up yet so cannot get an oauth token
    security=False,
    methods=SwaggerMethod(
        name="Signup",
        description="Signs up to JAAQL using either the key provided in the email or the email address itself if the "
        "user has not been invited to the platform",
        method=REST__POST,
        body=[
            SwaggerArgumentResponse(
                name=KEY__invite_key,
                description="A JWT that functions as an invite for a specific email address",
                arg_type=str,
                example=[JWT__invite],
                required=False,
                condition="Is an invite key required"
            ),
            ARG_RES__jaaql_password
        ],
        response=[
            RES__totp_mfa_nullable,
            SwaggerFlatResponse(
                description=ERR__already_signed_up,
                code=HTTPStatus.CONFLICT,
                body=ERR__already_signed_up
            )
        ]
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh

DOCUMENTATION__my_applications = SwaggerDocumentation(
    tags="Applications",
    methods=SwaggerMethod(
        name="Fetch my applications",
        description="Fetches a list of applications for which this user is authorised for",
        method=REST__GET,
        response=SwaggerResponse(
            description="List of applications the user has access to",
            response=SwaggerList(*ARG_RES__application_body)
        )
    )
)

DOCUMENTATION__my_configs = SwaggerDocumentation(
    tags="Configuration",
    methods=SwaggerMethod(
        name="Fetch authorised applications with configurations",
        description="Fetches the applications with configurations for which this user is authorised for",
        arguments=set_nullable(ARG_RES__application, "Do you want to search on application name"),
        method=REST__GET,
        response=SwaggerResponse(
            description="List of configurations and applications",
            response=SwaggerList(
                ARG_RES__application,
                SwaggerArgumentResponse(
                    name=KEY__application_description,
                    description="Application description",
                    arg_type=str,
                    example=["Browses books in the library", "Helps book meetings"],
                    required=True
                ),
                ARG_RES__configuration,
                SwaggerArgumentResponse(
                    name=KEY__configuration_description,
                    description="The configuration description",
                    arg_type=str,
                    example=["Library configuration for QA", "Meeting room PROD configuration for client A"],
                    required=True
                )
            )
        )
    )
)

JWT__connection = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IiQwTUcxYzNZVVkwR0NMd0J5UWFwbVNlIn0.-lzAl33gMBiAMtMq4" \
                  "s_xzKk0QzL_bpX6pnAOhGZsyM0"

ARG_RES__connection = SwaggerArgumentResponse(
    name=KEY__connection,
    description="A JWT representing the authenticated connection between user and database/node",
    arg_type=str,
    example=[JWT__connection],
    required=True
)

DOCUMENTATION__config_assigned_databases = SwaggerDocumentation(
    tags="Configuration",
    methods=SwaggerMethod(
        name="Fetch assigned databases for configuration",
        description="Fetches the assigned databases for a configuration and a JWT token describing each of them",
        method=REST__GET,
        arguments=[
            ARG_RES__application,
            ARG_RES__configuration
        ],
        response=SwaggerResponse(
            description="List of datasets and their assigned databases for the configuration",
            response=SwaggerList(
                ARG_RES__reference_dataset,
                rename_arg(ARG_RES__dataset_description, KEY__dataset_description),
                ARG_RES__connection
            )
        )
    )
)

DOCUMENTATION__assigned_database_roles = SwaggerDocumentation(
    tags="Configuration",
    methods=SwaggerMethod(
        name="Fetch roles for assigned database",
        description="Fetches my database level roles for the assigned database",
        arguments=ARG_RES__connection,
        method=REST__GET,
        response=SwaggerResponse(
            description="List of database roles for the current connection",
            response=SwaggerSimpleList(
                arg_type=str,
                description="A list of database roles for the current connection",
                example=["pg_read_all_stats", "pg_monitor", "pg_read_all_settings"],
                required=True
            )
        )
    )
)

KEY__address = "address"
EXAMPLE__address = "127.0.0.1"
KEY__first_use = "first_use"
EXAMPLE__first_use = "2021-08-07 19:05:07.763189+01:00"
KEY__most_recent_use = "most_recent_use"
EXAMPLE__most_recent_use = "2021-08-07 19:05:07.763189+01:00"


ARG_RES__address = SwaggerArgumentResponse(
    name=KEY__address,
    description="The ip address",
    arg_type=str,
    example=[EXAMPLE__address, "::1/128"],
    required=True
)

ARG_RES__mfa_enabled = SwaggerArgumentResponse(
    name=KEY__mfa_enabled,
    description="Is MFA enabled",
    arg_type=bool,
    example=[True, False],
    required=True
)

DOCUMENTATION__my_account_info = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="My account info",
        description="Fetch information for my account",
        method=REST__GET,
        response=SwaggerResponse(
            description="Account information",
            response=[ARG_RES__email, ARG_RES__mfa_enabled]
        )
    )
)

DOCUMENTATION__my_ips = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="Fetch ip information",
        description="Fetch ip addresses that have interacted with my account",
        method=REST__GET,
        arguments=gen_arg_res_sort_pageable(KEY__most_recent_use, KEY__first_use, EXAMPLE__most_recent_use,
                                            EXAMPLE__first_use),
        response=SwaggerResponse(
            description="List of ip addresses",
            response=gen_filtered_records(
                "ip address",
                [
                    ARG_RES__address,
                    SwaggerArgumentResponse(
                        name=KEY__first_use,
                        description="First use of this IP address",
                        arg_type=str,
                        example=[EXAMPLE__first_use, "2021-08-07 18:04:41.156935+01:00"],
                        required=True
                    ),
                    SwaggerArgumentResponse(
                        name=KEY__most_recent_use,
                        description="Most recent use of this IP address",
                        arg_type=str,
                        example=[EXAMPLE__most_recent_use, "2021-08-07 18:04:41.156935+01:00"],
                        required=True
                    )
                ]
            )
        )
    )
)

DOCUMENTATION__password = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="Change password",
        description="Changes your password",
        method=REST__POST,
        body=[
            ARG_RES__jaaql_password,
            SwaggerArgumentResponse(
                name=KEY__new_password,
                description="New login password",
                arg_type=str,
                example=["p@55word", "p@ssw0rd"],
                required=True
            ),
            SwaggerArgumentResponse(
                name=KEY__new_password_confirm,
                description="Confirm new login password",
                arg_type=str,
                example=["p@55word", "p@ssw0rd"],
                required=True
            ),
            ARG_RES__mfa_key
        ],
        response=[
            RES__oauth_token,
            SwaggerFlatResponse(
                description=ERR__passwords_do_not_match,
                code=HTTPStatus.UNPROCESSABLE_ENTITY,
                body=ERR__passwords_do_not_match
            )
        ]
    )
)

DOCUMENTATION__account_close = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="Close account",
        description="Closes your account",
        method=REST__DELETE,
        arguments=[
            ARG_RES__jaaql_password,
            ARG_RES__mfa_key
        ],
        response=RES__deletion_key
    )
)

DOCUMENTATION__account_close_confirm = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="Confirm close account",
        description="Confirms account closure",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

DOCUMENTATION__account_mfa = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="Enable/Disable MFA",
        description="Reverses the MFA status on the account. If MFA is required and an attempt to disable it is made, "
        "an error will be returned",
        body=[ARG_RES__jaaql_password, set_nullable(ARG_RES__mfa_key, "Is MFA enabled")],
        method=REST__POST,
        response=RES__totp_mfa_nullable
    )
)

KEY__status = "status"
EXAMPLE__status = "422"
KEY__endpoint = "endpoint"
EXAMPLE__endpoint = "/account/signup"

DOCUMENTATION__my_logs = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        name="Fetch log information",
        description="Fetch system logs pertaining to myself",
        method=REST__GET,
        arguments=gen_arg_res_sort_pageable(KEY__status, KEY__endpoint, EXAMPLE__status, EXAMPLE__endpoint),
        response=SwaggerResponse(
            description="List of system logs",
            response=gen_filtered_records(
                "log",
                [
                    SwaggerArgumentResponse(
                        name="occurred",
                        description="When this event occurred",
                        arg_type=str,
                        example=["2021-08-07 19:05:07.763189+01:00", "2021-08-07 18:04:41.156935+01:00"],
                        required=True
                    ),
                    ARG_RES__address,
                    SwaggerArgumentResponse(
                        name=KEY__user_agent,
                        description="The user agent",
                        arg_type=str,
                        example=["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chro"
                                 "me/77.0.3865.90 Safari/537.36", "Mozilla/5.0 (iPhone; CPU iPhone OS 11_3_1 like Mac O"
                                                                  "S X) AppleWebKit/603.1.30 (KHTML, like Gecko) Versio"
                                                                  "n/10.0 Mobile/14E304 Safari/602.1"],
                        required=False,
                        condition="If a user agent is associated with this"
                    ),
                    SwaggerArgumentResponse(
                        name="status",
                        description="The response status code",
                        arg_type=int,
                        example=[int(EXAMPLE__status), 500],
                        required=True
                    ),
                    SwaggerArgumentResponse(
                        name=KEY__endpoint,
                        description="The associated endpoint",
                        arg_type=str,
                        example=[EXAMPLE__endpoint, "/account/addresses"],
                        required=True
                    ),
                    SwaggerArgumentResponse(
                        name="duration_ms",
                        description="The duration of the event on the server in ms",
                        arg_type=int,
                        example=[134, 862],
                        required=True
                    ),
                    SwaggerArgumentResponse(
                        name=KEY__exception,
                        description="The exception, if one occurred",
                        condition="Whether an exception occurred",
                        arg_type=str,
                        example=["[42P01] ERROR: relation \\\"bar\\\" does not exist Position: 17",
                                 "Deletion key invalid. Either didn't exist or expired"],
                        required=False
                    )
                ]
            )
        )
    )
)

DOCUMENTATION__submit = SwaggerDocumentation(
    tags="JAAQL",
    methods=SwaggerMethod(
        name="Execute JAAQL query",
        description="Executes a JAAQL query which is either a single SQL query or a list of queries. Returns results",
        method=REST__POST,
        arguments=ARG_RESP__allow_all,
        response=RES__allow_all
    )
)

DOCUMENTATION__submit_file = SwaggerDocumentation(
    tags="JAAQL",
    methods=SwaggerMethod(
        name="Submits a file for execution",
        description="Submits a full script file",
        method=REST__POST,
        arguments=ARG_RESP__allow_all,
        response=RES__allow_all
    )
)
