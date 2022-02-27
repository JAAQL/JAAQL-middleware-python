from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.documentation.documentation_shared import ARG_RES__jaaql_password, ARG_RES__email,\
    JWT__invite, gen_arg_res_sort_pageable, gen_filtered_records, ARG_RES__deletion_key, RES__deletion_key,\
    set_nullable, rename_arg, ARG_RES__is_node, ARG_RES__database_name, EXAMPLE__db, ARG_RES__application_name,\
    ARG_RES__application_description, ARG_RES__application_uri, EXAMPLE__application_name

TITLE = "JAAQL Internal API"
DESCRIPTION = "Collection of methods in the JAAQL internal API"
FILENAME = "jaaql_internal_api"

ARG_RES__double_mfa = SwaggerResponse(
    description="Contains information to setup authenticator app for jaaql and potentially postgres user",
    response=[
        SwaggerArgumentResponse(
            name=KEY__jaaql_otp_uri,
            description="OTP URI for the jaaql user",
            arg_type=str,
            example=["otpauth://totp/%test?secret=supersecret&issuer=JAAQL",
                     "otpauth://totp/%mylabel?secret=pa55word&issuer=MyIssuer"],
            required=True
        ),
        SwaggerArgumentResponse(
            name=KEY__jaaql_otp_qr,
            description="OTP QR code for the jaaql user, as a inlined base64 encoded png image",
            arg_type=str,
            example=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKsAAADV...",
                     "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."],
            required=True
        ),
        SwaggerArgumentResponse(
            name=KEY__superjaaql_otp_uri,
            description="OTP URI for the superjaaql user",
            arg_type=str,
            example=["otpauth://totp/%test?secret=supersecret&issuer=JAAQL",
                     "otpauth://totp/%mylabel?secret=pa55word&issuer=MyIssuer"],
            required=False,
            condition="Was the superjaaql password supplied"
        ),
        SwaggerArgumentResponse(
            name=KEY__superjaaql_otp_qr,
            description="OTP QR code for the superjaaql user, as a inlined base64 encoded png image",
            arg_type=str,
            example=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKsAAADV...",
                     "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."],
            required=False,
            condition="Was the superjaaql password supplied"
        )
    ]
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
                description="Database connection string",
                arg_type=str,
                example=["postgresql://postgres:123456@localhost:5432/jaaql",
                         "postgresql://postgres:pa55word@localhost:5432/jaaql"],
                required=True,
                local_only=True
            ),
            ARG_RES__jaaql_password,
            SwaggerArgumentResponse(
                name=KEY__install_key,
                description="Single use/purpose key. Find in the logs, line starting with 'INSTALL KEY:' at startup",
                arg_type=str,
                example=["aefc1b08-a573-466f-bdd0-706ae281cc99", "ec63aa9a-b189-419f-8e0b-7fcc4ff8c857"],
                required=True
            ),
            SwaggerArgumentResponse(
                name=KEY__superjaaql_password,
                description="At the postgres level, the postgres user is used to set up the jaaql user. If you want "
                "access to the postgres user through JAAQL, please provide a password and this user will be setup for "
                "you. This is a JAAQL login for superjaaql so it is entirely independent of the postgres password "
                "at the database level. If you do not supply this password, you will not be able to login to jaaql "
                "authenticating as postgres with the local database node. You can set this up later if you want ",
                example=["sup3rjaaqlpa55word"],
                condition="If you want to give the superjaaql user a login",
                required=False,
                arg_type=str
            )
        ],
        response=ARG_RES__double_mfa
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__login_details, DOCUMENTATION__oauth_token,\
    DOCUMENTATION__oauth_refresh, DOCUMENTATION__fetch_applications


EXAMPLE__node = "PROD library"
EXAMPLE__address = "mydb.abbcdcec9afd.eu-west-1.rds.amazonaws.com"

ARG_RES__node_base = [
    SwaggerArgumentResponse(
        name=KEY__node_name,
        description="The internal name used to identify the node",
        arg_type=str,
        example=[EXAMPLE__node, "office QA"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__port,
        description="Port on which the node runs",
        arg_type=int,
        example=[5432, 3306],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__address,
        description="Node host address",
        arg_type=str,
        example=[EXAMPLE__address, "184.219.247.60"],
        required=True
    )
]

ARG_RES__deleted = SwaggerArgumentResponse(
    name=KEY__show_deleted,
    description="Show deleted. If true will return all, deleted or not",
    condition="If not supplied will return only those not marked as deleted",
    required=False,
    arg_type=bool,
    example=[True, False]
)

ARG_RES__when_deleted = SwaggerArgumentResponse(
    name=ATTR__deleted,
    description="The timestamp at which the item was deleted (if deleted)",
    condition="Requested view of deleted. Null if requested and not deleted",
    arg_type=str,
    required=False,
    example=["2021-08-07 19:05:07.763189+01:00", "2021-08-07 18:04:41.156935+01:00"]
)

EXAMPLE__node_id = "aaa901f2-fc92-4b8a-8a30-d35d36b9189e"
ARG_RES__node_id = SwaggerArgumentResponse(
    name="id",
    description="The internal id of the node",
    arg_type=str,
    example=[EXAMPLE__node_id],
    required=True
)

DOCUMENTATION__nodes = SwaggerDocumentation(
    tags="Nodes",
    methods=[
        SwaggerMethod(
            name="Add node",
            description="Adds a new node",
            arguments=ARG_RES__node_base + [SwaggerArgumentResponse(
                name=KEY__description,
                description="Description of the node",
                arg_type=str,
                condition="Imputed from the node name if not required",
                example=["The PROD library node", "The office QA node"],
                required=False,
            )],
            method=REST__POST,
            response=SwaggerFlatResponse(
                description="The node UUID",
                body=EXAMPLE__node_id
            )
        ),
        SwaggerMethod(
            name="Fetch nodes",
            description="Fetch a list of nodes",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__node_name, KEY__address, EXAMPLE__node, EXAMPLE__address),
            response=SwaggerResponse(
                description="List of nodes",
                response=gen_filtered_records(
                    "node",
                    [
                        ARG_RES__node_id,
                        ARG_RES__when_deleted
                    ] + ARG_RES__node_base + [
                        SwaggerArgumentResponse(
                            name=KEY__description,
                            description="Description of the node",
                            arg_type=str,
                            example=["The PROD library node", "The office QA node"],
                            required=True,
                        )
                    ]
                )
            )
        ),
        SwaggerMethod(
            name="Delete node",
            description="Deletes a node",
            method=REST__DELETE,
            arguments=SwaggerArgumentResponse(
                name="id",
                description="node id",
                arg_type=str,
                example=[EXAMPLE__node_id],
                required=True
            ),
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__nodes_confirm_deletion = SwaggerDocumentation(
    tags="Nodes",
    methods=SwaggerMethod(
        name="Confirm node deletion",
        description="Confirm the node deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

EXAMPLE__database_id = "31f295d4-1be4-4534-9fb8-164c6c53c985"

ARG_RES__database_base = [
    ARG_RES__database_name,
    SwaggerArgumentResponse(
        name=KEY__node,
        description="The internal id of the node",
        arg_type=str,
        example=[EXAMPLE__node_id],
        required=True
    )
]

ARG_RES__database_id = SwaggerArgumentResponse(
    name="id",
    description="The internal id of the database",
    arg_type=str,
    example=[EXAMPLE__database_id],
    required=True
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
                body=EXAMPLE__database_id
            )
        ),
        SwaggerMethod(
            name="Fetch Databases",
            description="Fetch a list of databases",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__database_name, KEY__id, EXAMPLE__db, EXAMPLE__database_id) + [
                ARG_RES__deleted
            ],
            response=SwaggerResponse(
                description="List of databases",
                response=gen_filtered_records(
                    "database",
                    [
                        ARG_RES__database_id,
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
                example=[EXAMPLE__database_id],
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
    ),
    ARG_RES__is_node
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

ARG_RES__node = SwaggerArgumentResponse(
    name=KEY__node,
    description="The internal id of the node",
    arg_type=str,
    example=[EXAMPLE__node_id],
    required=True
)

ARG_RES__application_argument = ARG_RES__application_argument_key + [
    set_nullable(ARG_RES__database, "Is this parameter a database"),
    set_nullable(ARG_RES__node, "Is this parameter a node")
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
    tags="App Authorization",
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
    tags="App Authorization",
    methods=SwaggerMethod(
        name="Confirm revoke of a role for an application",
        description="Confirm the revoke of a role for an application, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

EXAMPLE__node_auth_id = "2d4f88f7-c133-4a0f-8593-59b179fafab7"
DESC__node_auth_id = "An id representing the relationship between role and node"

ARG_RES__authorization_node_id = SwaggerArgumentResponse(
    name="id",
    description=DESC__node_auth_id,
    arg_type=str,
    example=[EXAMPLE__node_auth_id],
    required=True
)

ARG_RES__authorization_node_credentials = [
    SwaggerArgumentResponse(
        name=KEY__username,
        description="The username for the node",
        arg_type=str,
        example=["postgres", "user"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__password,
        description="The password for the node",
        arg_type=str,
        example=["123456", "pa55word"],
        required=True
    ),
]

ARG_RES__authorization_node_input = [
    ARG_RES__node,
    ARG_RES__role,
    SwaggerArgumentResponse(
        name=KEY__precedence,
        description="The precedence of the authorization. Higher overrides lower",
        arg_type=int,
        example=[0, 1],
        required=False,
        condition="Defaults to 0"
    )
]

DOCUMENTATION__authorization_node = SwaggerDocumentation(
    tags="Node Authorization",
    methods=[
        SwaggerMethod(
            name="Add node authorization",
            description="Add a node and it's credentials for use with a specific role",
            method=REST__POST,
            body=ARG_RES__authorization_node_input + ARG_RES__authorization_node_credentials,
            response=SwaggerFlatResponse(
                description=DESC__node_auth_id,
                body=EXAMPLE__node_auth_id
            )
        ),
        SwaggerMethod(
            name="Fetch node authorizations",
            description="Fetch a list of roles which have been authorized to use nodes",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__node, KEY__role, EXAMPLE__node_id, EXAMPLE__role) + [
                ARG_RES__deleted],
            response=SwaggerResponse(
                description="A list of node authorizations and associated roles",
                response=gen_filtered_records(
                    "node authorization",
                    [ARG_RES__authorization_node_id] + ARG_RES__authorization_node_input + [ARG_RES__when_deleted]
                )
            )
        ),
        SwaggerMethod(
            name="Revoke role auth for node",
            description="Requests the revoke of a node authorization, returning a confirmation key",
            method=REST__DELETE,
            arguments=ARG_RES__authorization_node_id,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__authorization_node_confirm_deletion = SwaggerDocumentation(
    tags="Node Authorization",
    methods=SwaggerMethod(
        name="Confirm revoke of a node authorization",
        description="Confirm the revoke of a node authorization, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

DOCUMENTATION__authorization_node_databases = SwaggerDocumentation(
    tags="Node Authorization",
    methods=[
        SwaggerMethod(
            name="Add node/role DB",
            description="Adds a database for which a role is authorised to connect to on a node",
            method=REST__POST,
            arguments=[rename_arg(ARG_RES__authorization_node_id, KEY__authorization), rename_arg(ARG_RES__database_id,
                                                                                                  KEY__database)],
        ),
        SwaggerMethod(
            name="Trigger node/role DB refresh",
            description="Triggers a refresh of available databases on a node for role",
            method=REST__PUT,
            arguments=rename_arg(ARG_RES__authorization_node_id, KEY__authorization)
        ),
        SwaggerMethod(
            name="Fetch node/role DBs",
            description="Fetches the list of databases for which a role is authorized for on a node",
            method=REST__GET,
            arguments=rename_arg(ARG_RES__authorization_node_id, KEY__authorization),
            response=SwaggerResponse(
                description="A database object, representing a database on a node",
                response=SwaggerList(ARG_RES__database_id, ARG_RES__database_name)
            )
        )
    ]
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