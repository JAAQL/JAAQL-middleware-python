from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.documentation.documentation_shared import ARG_RES__jaaql_password, ARG_RES__totp_mfa, ARG_RES__email,\
    JWT__invite, gen_arg_res_sort_pageable, gen_filtered_records, ARG_RES__deletion_key, RES__deletion_key

TITLE = "JAAQL Internal API"
DESCRIPTION = "Collection of methods in the JAAQL internal API"
FILENAME = "jaaql_internal_api"


DOCUMENTATION__install = SwaggerDocumentation(
    tags="Installation",
    security=False,  # This method is not secured as the system is not setup yet. It uses a OTP token system via logs
    methods=SwaggerMethod(
        name="Install JAAQL",
        description="Installs JAAQL to the configured database. Please allow a minute after running for the server to "
        "refresh and reload",
        method=REST__POST,
        body=[
            SwaggerArgumentResponse(
                name="db_connection_string",
                description="Database connection string",
                arg_type=str,
                example=["postgresql://postgres:123456@localhost:5432/jaaql",
                         "postgresql://postgres:pa55word@localhost:5432/jaaql"],
                required=True
            ),
            ARG_RES__jaaql_password,
            SwaggerArgumentResponse(
                name=KEY__install_key,
                description="Single use/purpose key. Find in the logs, line starting with 'INSTALL KEY:' at startup",
                arg_type=str,
                example=["aefc1b08-a573-466f-bdd0-706ae281cc99", "ec63aa9a-b189-419f-8e0b-7fcc4ff8c857"],
                required=True
            )
        ],
        response=ARG_RES__totp_mfa
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh

KEY__application_name = "name"
EXAMPLE__application_name = "Library Browser"
KEY__application_url = "url"
EXAMPLE__application_url = "https://jaaql.com/demos/library-application"

ARG_RES__application_name = SwaggerArgumentResponse(
    name=KEY__application_name,
    description="Application name",
    arg_type=str,
    example=[EXAMPLE__application_name, "Meeting Room Scheduling Assistant"],
    required=True
)
ARG_RES__application_description = SwaggerArgumentResponse(
    name="description",
    description="Application description",
    arg_type=str,
    example=["Browses books in the library", "Helps book meetings"],
    required=True
)
ARG_RES__application_uri = SwaggerArgumentResponse(
    name=KEY__application_url,
    description="Application url",
    arg_type=str,
    example=[EXAMPLE__application_url, "https://jaaql.com/demos/meeting-application"],
    required=True
)

EXAMPLE__db = "library"
EXAMPLE__address = "mydb.abbcdcec9afd.eu-west-1.rds.amazonaws.com"

KEY__is_console_level = "is_console_level"

ARG_RES__database_base = [
    SwaggerArgumentResponse(
        name=KEY__database_name,
        description="The name of the database on the database server",
        arg_type=str,
        example=[EXAMPLE__db, "meetings"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__description,
        description="Description of the database",
        arg_type=str,
        example=["The library database on PROD", "The meeting database on QA"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__port,
        description="Port on which the database runs",
        arg_type=int,
        example=[5432, 3306],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__address,
        description="Database host",
        arg_type=str,
        example=[EXAMPLE__address, "184.219.247.60"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__jaaql_name,
        description="The internal name of the database",
        arg_type=str,
        example=["Library database PROD", "Meeting database QA"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__is_console_level,
        description="Set to true if the database can be overwrote on a submit command with the db_name argument. "
        "For example, if the argument '" + KEY__database_name + "' is set to public and the db_name argument is set "
        "with sqmi on submit, the queries will be executed against the sqmi database. We recommend leaving on False",
        condition="If missing, set to false",
        arg_type=bool,
        example=[False, True],
        required=False
    )
]

ARG_RES__deleted = SwaggerArgumentResponse(
    name=KEY__show_deleted,
    description="Show deleted. If true will return all, deleted or not",
    condition="If not supplied will return only those not marked as deleted",
    arg_type=bool,
    example=[True, False]
)

ARG_RES__when_deleted = SwaggerArgumentResponse(
    name=ATTR__deleted,
    description="The timestamp at which the database was deleted (if deleted)",
    condition="Requested view of deleted. Null if requested and not deleted",
    arg_type=str,
    example=["2021-08-07 19:05:07.763189+01:00", "2021-08-07 18:04:41.156935+01:00"]
)

DOCUMENTATION__databases = SwaggerDocumentation(
    tags="Databases",
    methods=[
        SwaggerMethod(
            name="Add Database",
            description="Add a new database",
            arguments=ARG_RES__database_base,
            method=REST__POST,
            response=SwaggerFlatResponse(
                description="The database UUID",
                body="aaa901f2-fc92-4b8a-8a30-d35d36b9189e"
            )
        ),
        SwaggerMethod(
            name="Fetch Databases",
            description="Fetch a list of databases",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__database_name, KEY__address, EXAMPLE__db, EXAMPLE__address) + [
                ARG_RES__deleted
            ],
            response=SwaggerResponse(
                description="List of databases",
                response=gen_filtered_records(
                    "database",
                    [
                        SwaggerArgumentResponse(
                            name="id",
                            description="The internal id of the database",
                            arg_type=str,
                            example=["177237b2-f85c-4a68-a5dc-5b2bdfbd0c73", "2edf1af1-8fb5-4f8a-86bd-081bdaafcf48"],
                            required=True
                        ),
                        ARG_RES__when_deleted
                    ] + ARG_RES__database_base
                )
            )
        ),
        SwaggerMethod(
            name="Delete Database",
            description="Deletes a database",
            method=REST__DELETE,
            arguments=SwaggerArgumentResponse(
                name="id",
                description="Database id",
                arg_type=str,
                example=["177237b2-f85c-4a68-a5dc-5b2bdfbd0c73", "2edf1af1-8fb5-4f8a-86bd-081bdaafcf48"],
                required=True
            ),
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__databases_confirm_deletion = SwaggerDocumentation(
    tags="Databases",
    methods=SwaggerMethod(
        name="Confirm database deletion",
        description="Confirm the database deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

DOCUMENTATION__applications = SwaggerDocumentation(
    tags="Applications",
    methods=[
        SwaggerMethod(
            name="Add application",
            description="Add a new application",
            method=REST__POST,
            body=[
                ARG_RES__application_name,
                ARG_RES__application_description,
                ARG_RES__application_uri
            ]
        ),
        SwaggerMethod(
            name="Fetch applications",
            description="Fetches a list of all the applications in the system",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application_name, KEY__application_url, EXAMPLE__application_name,
                                                EXAMPLE__application_url),
            response=SwaggerResponse(
                description="List of applications",
                response=gen_filtered_records(
                    "application",
                    [
                        ARG_RES__application_name,
                        ARG_RES__application_description,
                        ARG_RES__application_uri,
                        SwaggerArgumentResponse(
                            name="created",
                            description="Application creation timestamp",
                            arg_type=str,
                            example=["2021-08-07 19:05:07.763189+01:00", "2021-08-07 18:04:41.156935+01:00"],
                            required=True
                        )
                    ]
                )
            )
        ),
        SwaggerMethod(
            name="Update application",
            description="Update a application",
            method=REST__PUT,
            body=[
                ARG_RES__application_name,
                SwaggerArgumentResponse(
                    name="new_name",
                    condition="Only updated if supplied",
                    description="New application name",
                    arg_type=str,
                    example=["Library Browser", "Meeting Room Scheduling Assistant"]
                ),
                SwaggerArgumentResponse(
                    name="new_description",
                    condition="Only updated if supplied",
                    description="New application description",
                    arg_type=str,
                    example=["Browses books in the library", "Helps book meetings"]
                ),
                SwaggerArgumentResponse(
                    name="new_url",
                    condition="Only updated if supplied",
                    description="New application url",
                    arg_type=str,
                    example=["https://jaaql.com/demos/library-application",
                             "https://jaaql.com/demos/meeting-application"]
                )
            ]
        ),
        SwaggerMethod(
            name="Delete application",
            description="Delete a application",
            method=REST__DELETE,
            arguments=[
                ARG_RES__application_name
            ],
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__applications_confirm_deletion = SwaggerDocumentation(
    tags="Applications",
    methods=SwaggerMethod(
        name="Confirm application deletion",
        description="Confirm the application deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

ARG__application_name = SwaggerArgumentResponse(
    name=KEY__application,
    description="The name of the application",
    arg_type=str,
    example=[EXAMPLE__application_name, "Meeting Room"],
    required=True
)

KEY__application_parameter_name = "name"
EXAMPLE__application_parameter_db = "library_db"

ARG_RES__application_parameter_key = [
    ARG__application_name,
    SwaggerArgumentResponse(
        name=KEY__application_parameter_name,
        description="The name of the parameter",
        arg_type=str,
        example=[EXAMPLE__application_parameter_db, "meeting_db"],
        required=True
    )
]

ARG_RES__application_parameter = ARG_RES__application_parameter_key + [
    SwaggerArgumentResponse(
        name="description",
        description="The parameter description",
        arg_type=str,
        example=["The library book database", "The meeting room spaces database"],
        required=True
    )
]

KEY__configuration_name = "name"
EXAMPLE__configuration_name = "Library QA"

ARG_RES__application_configuration_key = [
    SwaggerArgumentResponse(
        name=KEY__application,
        description="The name of the application",
        arg_type=str,
        example=[EXAMPLE__application_name, "Meeting Room"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__configuration_name,
        description="The name of the configuration",
        arg_type=str,
        example=[EXAMPLE__configuration_name, "Meeting DEV"],
        required=True
    )
]

ARG_RES__application_configuration = ARG_RES__application_configuration_key + [
    SwaggerArgumentResponse(
        name="description",
        description="The configuration description",
        arg_type=str,
        example=["Library configuration for QA", "Meeting room PROD configuration for client A"],
        required=True
    )
]

DOCUMENTATION__application_parameters = SwaggerDocumentation(
    tags="Applications",
    methods=[
        SwaggerMethod(
            name="Add Application Parameter",
            description="Add a new application parameter",
            arguments=ARG_RES__application_parameter,
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch Application Parameters",
            description="Fetch a list of application parameters",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application, KEY__application_parameter_name,
                                                EXAMPLE__application_name, EXAMPLE__application_parameter_db),
            response=SwaggerResponse(
                description="List of application parameters",
                response=gen_filtered_records(
                    "application parameter",
                    ARG_RES__application_parameter
                )
            )
        ),
        SwaggerMethod(
            name="Delete Application Parameter",
            description="Deletes a application parameter",
            method=REST__DELETE,
            arguments=ARG_RES__application_parameter_key,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__application_parameters_confirm_deletion = SwaggerDocumentation(
    tags="Applications",
    methods=SwaggerMethod(
        name="Confirm application parameter deletion",
        description="Confirm the application parameter deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

DOCUMENTATION__application_configurations = SwaggerDocumentation(
    tags="Application Configuration",
    methods=[
        SwaggerMethod(
            name="Add Application Configuration",
            description="Add a new application configuration",
            arguments=ARG_RES__application_configuration,
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch Application Configurations",
            description="Fetch a list of application configurations",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application, KEY__configuration_name, EXAMPLE__application_name,
                                                EXAMPLE__configuration_name),
            response=SwaggerResponse(
                description="List of application configurations",
                response=gen_filtered_records(
                    "application configuration",
                    ARG_RES__application_configuration
                )
            )
        ),
        SwaggerMethod(
            name="Delete Application Configuration",
            description="Deletes a application configuration",
            method=REST__DELETE,
            arguments=ARG_RES__application_configuration_key,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__application_configurations_confirm_deletion = SwaggerDocumentation(
    tags="Application Configuration",
    methods=SwaggerMethod(
        name="Confirm application configuration deletion",
        description="Confirm the application configuration deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

ARG_RES__application_argument_key = [
    ARG__application_name,
    SwaggerArgumentResponse(
        name=KEY__configuration,
        description="The name of the configuration which this argument is associated with",
        arg_type=str,
        example=[EXAMPLE__configuration_name, "Meeting DEV"],
        required=True
    ),
    SwaggerArgumentResponse(
        name="parameter",
        description="The name of the parameter which this argument is supplied for",
        arg_type=str,
        example=["library_db", "meeting_db"],
        required=True
    )
]

EXAMPLE__database = "0c44fc9b-d2de-4279-b686-1ce98f9a2ba4"

ARG_RES__database = SwaggerArgumentResponse(
    name=KEY__database,
    description="The associated database argument",
    arg_type=str,
    example=[EXAMPLE__database, "a289ce95-2e46-4944-af19-72c9b75c717e"],
    required=True
)

ARG_RES__application_argument = ARG_RES__application_argument_key + [
    ARG_RES__database
]

DOCUMENTATION__application_arguments = SwaggerDocumentation(
    tags="Application Configuration",
    methods=[
        SwaggerMethod(
            name="Add Application Argument",
            description="Add a new application argument",
            arguments=ARG_RES__application_argument,
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch Application Arguments",
            description="Fetch a list of application arguments",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application, KEY__configuration, EXAMPLE__application_name,
                                                EXAMPLE__configuration_name),
            response=SwaggerResponse(
                description="List of application arguments",
                response=gen_filtered_records(
                    "application argument",
                    ARG_RES__application_argument
                )
            )
        ),
        SwaggerMethod(
            name="Delete Application Argument",
            description="Deletes a application argument",
            method=REST__DELETE,
            arguments=ARG_RES__application_argument_key,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__application_arguments_confirm_deletion = SwaggerDocumentation(
    tags="Application Configuration",
    methods=SwaggerMethod(
        name="Confirm application argument deletion",
        description="Confirm the application argument deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

EXAMPLE__role = "jaaql"

ARG_RES__role = SwaggerArgumentResponse(
    name=KEY__role,
    description="The role associated with this authorization",
    arg_type=str,
    example=[EXAMPLE__role, "aaron@jaaql.com"],
    required=True
)

ARG_RES__authorization_application = [
    ARG__application_name,
    ARG_RES__role
]

DOCUMENTATION__authorization_application = SwaggerDocumentation(
    tags="Authorization",
    methods=[
        SwaggerMethod(
            name="Add application authorized role",
            description="Add an authorized role to the application",
            method=REST__POST,
            body=ARG_RES__authorization_application
        ),
        SwaggerMethod(
            name="Fetch Applications authorized Roles",
            description="Fetch a list of roles which have been authorized to use application",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application, KEY__role, EXAMPLE__application_name, EXAMPLE__role),
            response=SwaggerResponse(
                description="A list of roles authorized for an application",
                response=gen_filtered_records(
                    "application authorized role",
                    ARG_RES__authorization_application
                )
            )
        ),
        SwaggerMethod(
            name="Revoke role auth for application",
            description="Requests the revoke of a role authorization for an application, returning a confirmation key",
            method=REST__DELETE,
            arguments=ARG_RES__authorization_application,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__authorization_application_confirm_deletion = SwaggerDocumentation(
    tags="Authorization",
    methods=SwaggerMethod(
        name="Confirm revoke of a role for an application",
        description="Confirm the revoke of a role for an application, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

ARG_RES__authorization_database_id = SwaggerArgumentResponse(
    name="id",
    description="The id of the authorized database",
    arg_type=str,
    example=["f6306777-e6c8-4c7c-ba68-8b6b4a0d4432", "1c9f6227-d72f-4ebe-9d64-f851b3d3419e"],
    required=True
)

ARG_RES__authorization_database_input = [
    ARG_RES__database,
    ARG_RES__role,
    SwaggerArgumentResponse(
        name=KEY__username,
        description="The username for the database",
        arg_type=str,
        example=["postgres", "user"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__password,
        description="The password for the database",
        arg_type=str,
        example=["123456", "pa55word"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__precedence,
        description="The precedence of the authorization. Higher overrides lower",
        arg_type=int,
        example=[0, 1],
        required=False,
        condition="Defaults to 0"
    )
]

DOCUMENTATION__authorization_database = SwaggerDocumentation(
    tags="Authorization",
    methods=[
        SwaggerMethod(
            name="Add database authorization",
            description="Add a database and it's credentials for use with a specific role",
            method=REST__POST,
            body=ARG_RES__authorization_database_input
        ),
        SwaggerMethod(
            name="Fetch database authorizations",
            description="Fetch a list of roles which have been authorized to use application",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__database, KEY__role, EXAMPLE__database,
                                                EXAMPLE__role) + [ARG_RES__deleted],
            response=SwaggerResponse(
                description="A list of database authorizations and associated roles",
                response=gen_filtered_records(
                    "database authorization",
                    [ARG_RES__authorization_database_id] + ARG_RES__authorization_database_input + [
                        ARG_RES__when_deleted]
                )
            )
        ),
        SwaggerMethod(
            name="Revoke role auth for database",
            description="Requests the revoke of a database authorization, returning a confirmation key",
            method=REST__DELETE,
            arguments=ARG_RES__authorization_database_id,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__authorization_database_confirm_deletion = SwaggerDocumentation(
    tags="Authorization",
    methods=SwaggerMethod(
        name="Confirm revoke of a database authorization",
        description="Confirm the revoke of a database authorization, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

DOCUMENTATION__user_invite = SwaggerDocumentation(
    tags="User Management",
    methods=SwaggerMethod(
        name="Invite",
        description="Fetches an invite token, usable with a specific email address",
        method=REST__POST,
        body=[
            ARG_RES__email
        ],
        response=SwaggerFlatResponse(
            description="A JWT that can be used along with the email to sign up to the platform",
            body=JWT__invite
        )
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