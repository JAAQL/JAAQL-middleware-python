from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.documentation.documentation_shared import ARG_RES__jaaql_password, ARG_RES__email,\
    JWT__invite, gen_arg_res_sort_pageable, gen_filtered_records, ARG_RES__deletion_key, RES__deletion_key,\
    set_nullable, rename_arg, ARG_RES__database_name, EXAMPLE__db, ARG_RES__application_name,\
    EXAMPLE__application_name, EXAMPLE__application_url, ARG_RES__application_body, EXAMPLE__application_dataset,\
    ARG_RES__dataset_name, ARG_RES__dataset_description, RES__totp_mfa_nullable, ARG_RES__reference_dataset

TITLE = "JAAQL Internal API"
DESCRIPTION = "Collection of methods in the JAAQL internal API"
FILENAME = "jaaql_internal_api"

CONDITION_force_mfa = "Was MFA requested or forced on"

ARG_RES__double_mfa = SwaggerResponse(
    description="Contains information to setup authenticator app for jaaql and potentially postgres user",
    response=[
        SwaggerArgumentResponse(
            name=KEY__jaaql_otp_uri,
            description="OTP URI for the jaaql user",
            arg_type=str,
            example=["otpauth://totp/%test?secret=supersecret&issuer=JAAQL",
                     "otpauth://totp/%mylabel?secret=pa55word&issuer=MyIssuer"],
            required=False,
            condition=CONDITION_force_mfa
        ),
        SwaggerArgumentResponse(
            name=KEY__jaaql_otp_qr,
            description="OTP QR code for the jaaql user, as a inlined base64 encoded png image",
            arg_type=str,
            example=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKsAAADV...",
                     "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."],
            required=False,
            condition=CONDITION_force_mfa
        ),
        SwaggerArgumentResponse(
            name=KEY__superjaaql_otp_uri,
            description="OTP URI for the superjaaql user",
            arg_type=str,
            example=["otpauth://totp/%test?secret=supersecret&issuer=JAAQL",
                     "otpauth://totp/%mylabel?secret=pa55word&issuer=MyIssuer"],
            required=False,
            condition="Was the superjaaql password supplied and mfa requested or forced on"
        ),
        SwaggerArgumentResponse(
            name=KEY__superjaaql_otp_qr,
            description="OTP QR code for the superjaaql user, as a inlined base64 encoded png image",
            arg_type=str,
            example=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKsAAADV...",
                     "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."],
            required=False,
            condition="Was the superjaaql password supplied and mfa requested or forced on"
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
                name=KEY__use_mfa,
                description="To use MFA, if MFA is not forced, otherwise will be true. It is highly recommended that "
                "mfa is enabled for open production systems due to the access level of the created account(s)",
                arg_type=bool,
                example=[True, False],
                required=False,
                condition="Is MFA force enabled"
            ),
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
                "you. This is a JAAQL login for superjaaql so it is entirely independent of the postgres password at "
                "the database level. If you do not supply this password, you will not be able to login to jaaql "
                "authenticating as postgres with the local database node. You can set this up later if you want ",
                example=["sup3rjaaqlpa55word"],
                condition="If you want to give the superjaaql user a login",
                required=False,
                arg_type=str
            )
        ],
        response=[
            ARG_RES__double_mfa,
            SwaggerFlatResponse(
                description=ERR__already_installed,
                code=HTTPStatus.UNPROCESSABLE_ENTITY,
                body=ERR__already_installed
            )
        ]
    )
)

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh


EXAMPLE__address = "mydb.abbcdcec9afd.eu-west-1.rds.amazonaws.com"

EXAMPLE__node_label = "lion"
ARG_RES__node_label = SwaggerArgumentResponse(
    name=KEY__node_name,
    description="The label of the node, provides real world semantic meaning",
    arg_type=str,
    example=[EXAMPLE__node_label],
    required=True
)

ARG_RES__node_base = [
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

DOCUMENTATION__nodes = SwaggerDocumentation(
    tags="Nodes",
    methods=[
        SwaggerMethod(
            name="Add node",
            description="Adds a new node",
            body=[set_nullable(ARG_RES__node_label, condition="If not provided will be automatically generated")] +
                 ARG_RES__node_base + [
                SwaggerArgumentResponse(
                    name=KEY__description,
                    description="Description of the node",
                    arg_type=str,
                    condition="Imputed from the node name if not required",
                    example=["The PROD library node", "The office QA node"],
                    required=False,
                )
            ],
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch nodes",
            description="Fetch a list of nodes",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__node_name, KEY__address, EXAMPLE__node_label, EXAMPLE__address),
            response=SwaggerResponse(
                description="List of nodes",
                response=gen_filtered_records(
                    KEY__node,
                    [
                        ARG_RES__node_label
                    ] + ARG_RES__node_base + [
                        SwaggerArgumentResponse(
                            name=KEY__description,
                            description="Description of the node",
                            arg_type=str,
                            example=["The PROD library node", "The office QA node"],
                            required=True,
                        ),
                        ARG_RES__when_deleted
                    ]
                )
            )
        ),
        SwaggerMethod(
            name="Delete node",
            description="Deletes a node",
            method=REST__DELETE,
            arguments=ARG_RES__node_label,
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

ARG_RES__reference_node = rename_arg(ARG_RES__node_label, KEY__node)

ARG_RES__database_base = [
    ARG_RES__database_name,
    ARG_RES__reference_node
]

ARG_RES__database_create = SwaggerArgumentResponse(
    name=KEY__create,
    description="Whether or not to create the database on the node",
    arg_type=bool,
    example=[True],
    required=True
)

ARG_RES__database_drop = SwaggerArgumentResponse(
    name=KEY__drop,
    description="Whether or not to drop the database on the node",
    arg_type=bool,
    example=[True],
    required=True
)

DOCUMENTATION__databases = SwaggerDocumentation(
    tags="Databases",
    methods=[
        SwaggerMethod(
            name="Add Database",
            description="Add a new database",
            arguments=ARG_RES__database_base + [ARG_RES__database_create],
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch Databases",
            description="Fetch a list of databases",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__database_name, KEY__node, EXAMPLE__db, EXAMPLE__node_label) + [
                ARG_RES__deleted
            ],
            response=SwaggerResponse(
                description="List of databases",
                response=gen_filtered_records(
                    KEY__database,
                    [ARG_RES__when_deleted] + ARG_RES__database_base
                )
            )
        ),
        SwaggerMethod(
            name="Delete Database",
            description="Deletes a database",
            method=REST__DELETE,
            arguments=[ARG_RES__reference_node, ARG_RES__database_name, ARG_RES__database_drop],
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
            body=ARG_RES__application_body
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
                    ARG_RES__application_body + [
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

ARG_RES__dataset_key = [
    ARG__application_name,
    ARG_RES__dataset_name
]

ARG_RES__application_dataset = ARG_RES__dataset_key + [
    ARG_RES__dataset_description
]

EXAMPLE__configuration_name = "Library QA"

ARG_RES__configuration_name = SwaggerArgumentResponse(
    name=KEY__configuration_name,
    description="The name of the configuration",
    arg_type=str,
    example=[EXAMPLE__configuration_name, "Meeting DEV"],
    required=True
)
ARG_RES__reference_configuration = rename_arg(ARG_RES__configuration_name, KEY__configuration)

ARG_RES__application_configuration_key = [
    SwaggerArgumentResponse(
        name=KEY__application,
        description="The name of the application",
        arg_type=str,
        example=[EXAMPLE__application_name, "Meeting Room"],
        required=True
    ),
    ARG_RES__configuration_name
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

DOCUMENTATION__application_datasets = SwaggerDocumentation(
    tags="Applications",
    methods=[
        SwaggerMethod(
            name="Add Application Dataset",
            description="Add a new dataset to an application",
            arguments=ARG_RES__application_dataset,
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch Application Dataset",
            description="Fetch a list of dataset",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application, KEY__database_name,
                                                EXAMPLE__application_name, EXAMPLE__application_dataset),
            response=SwaggerResponse(
                description="List of application datasets",
                response=gen_filtered_records(
                    "application dataset",
                    ARG_RES__application_dataset
                )
            )
        ),
        SwaggerMethod(
            name="Delete Application Dataset",
            description="Deletes a application dataset",
            method=REST__DELETE,
            arguments=ARG_RES__dataset_key,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__application_datasets_confirm_deletion = SwaggerDocumentation(
    tags="Applications",
    methods=SwaggerMethod(
        name="Confirm application dataset deletion",
        description="Confirm the application dataset deletion, providing a single use deletion key",
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

ARG_RES__assigned_database_key = [
    ARG__application_name,
    ARG_RES__reference_configuration,
    ARG_RES__reference_dataset
]

ARG_RES__reference_database = rename_arg(ARG_RES__database_name, KEY__database)

ARG_RES__assigned_database = ARG_RES__assigned_database_key + [
    ARG_RES__reference_database,
    ARG_RES__reference_node
]

DOCUMENTATION__assigned_databases = SwaggerDocumentation(
    tags="Application Configuration",
    methods=[
        SwaggerMethod(
            name="Assign Database",
            description="Add a database to a configuration",
            arguments=ARG_RES__assigned_database,
            method=REST__POST
        ),
        SwaggerMethod(
            name="Fetch Assigned Databases",
            description="Fetch a list of assigned databases",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__application, KEY__configuration, EXAMPLE__application_name,
                                                EXAMPLE__configuration_name),
            response=SwaggerResponse(
                description="List of assigned databases",
                response=gen_filtered_records(
                    "assigned database",
                    ARG_RES__assigned_database
                )
            )
        ),
        SwaggerMethod(
            name="Remove database assignment",
            description="Removes the assignment of a database",
            method=REST__DELETE,
            arguments=ARG_RES__assigned_database_key,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__database_assignment_confirm_deletion = SwaggerDocumentation(
    tags="Application Configuration",
    methods=SwaggerMethod(
        name="Confirm removal of database assignment",
        description="Confirm the removal of the database assignment, providing a single use deletion key",
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

ARG_RES__authorization_configuration = [
    ARG__application_name,
    ARG_RES__reference_configuration,
    ARG_RES__role
]

DOCUMENTATION__authorization_configuration = SwaggerDocumentation(
    tags="Authorization",
    methods=[
        SwaggerMethod(
            name="Add configuration authorized role",
            description="Add an authorized role to the application configuration",
            method=REST__POST,
            body=ARG_RES__authorization_configuration
        ),
        SwaggerMethod(
            name="Fetch Configuration authorized Roles",
            description="Fetch a list of roles which have been authorized to use an application configuration",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__configuration, KEY__role, EXAMPLE__configuration_name,
                                                EXAMPLE__role),
            response=SwaggerResponse(
                description="A list of roles authorized for a configuration",
                response=gen_filtered_records(
                    "application authorized role",
                    ARG_RES__authorization_configuration
                )
            )
        ),
        SwaggerMethod(
            name="Revoke role auth for application",
            description="Requests the revoke of a role authorization for an application configuration, returning a "
            "confirmation key",
            method=REST__DELETE,
            arguments=ARG_RES__authorization_configuration,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__authorization_configuration_confirm_deletion = SwaggerDocumentation(
    tags="Authorization",
    methods=SwaggerMethod(
        name="Confirm revoke of a authorization configuration",
        description="Confirm the revoke of a authorization for a configuration, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
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

ARG_RES__authorization_node_key = [
    ARG_RES__reference_node,
    ARG_RES__role
]

ARG_RES__authorization_node_precedence = SwaggerArgumentResponse(
    name=KEY__precedence,
    description="The precedence of the authorization. Higher overrides lower",
    arg_type=int,
    example=[0, 1],
    required=False,
    condition="Defaults to 0"
)

DOCUMENTATION__authorization_node = SwaggerDocumentation(
    tags="Authorization",
    methods=[
        SwaggerMethod(
            name="Add node credentials",
            description="Add a node and it's credentials for use with a specific role",
            method=REST__POST,
            body=ARG_RES__authorization_node_key + [ARG_RES__authorization_node_precedence] +
                 ARG_RES__authorization_node_credentials,
        ),
        SwaggerMethod(
            name="Fetch node credentialed roles",
            description="Fetch a list of roles which have credentials for a node",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__node, KEY__role, EXAMPLE__node_label, EXAMPLE__role) + [
                ARG_RES__deleted],
            response=SwaggerResponse(
                description="A list of node authorizations and associated roles",
                response=gen_filtered_records(
                    "node authorization",
                    ARG_RES__authorization_node_key + [ARG_RES__authorization_node_precedence] + [ARG_RES__when_deleted]
                )
            )
        ),
        SwaggerMethod(
            name="Revoke role credentials for node",
            description="Requests the revoke of node credentials for a role, returning a confirmation key",
            method=REST__DELETE,
            arguments=ARG_RES__authorization_node_key,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__authorization_node_confirm_deletion = SwaggerDocumentation(
    tags="Authorization",
    methods=SwaggerMethod(
        name="Confirm revoke of a node credentials",
        description="Confirm the revoke of a node credentials for a role, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

ARG_RES__roles = SwaggerArgumentResponse(
    name=KEY__roles,
    description="The internal roles for which to assign to the user along with the default roles (if "
    "any). Comma separated. The user must be signed up with an invite key before usage",
    arg_type=str,
    example=["admin,moderator"],
    required=False,
    condition="If you want to assign roles to the user"
)

DOCUMENTATION__users = SwaggerDocumentation(
    tags="User Management",
    methods=[
        SwaggerMethod(
            name="Create User",
            description="Creates a user",
            body=[ARG_RES__email, ARG_RES__roles],
            method=REST__POST
        ),
        SwaggerMethod(
            name="Invite User",
            description="Fetches an invite token, usable with a specific email address for a pre-created user",
            method=REST__PUT,
            body=[ARG_RES__email],
            response=SwaggerFlatResponse(
                description="A JWT that can be used along with the email to sign up to the platform",
                body=JWT__invite
            )
        ),
        SwaggerMethod(
            name="Revoke User",
            description="Requests the revoke of user, returning a confirmation key",
            method=REST__DELETE,
            body=[ARG_RES__email]
        )
    ]
)

DOCUMENTATION__activate = SwaggerDocumentation(
    tags="User Management",
    methods=SwaggerMethod(
        name="Activate",
        description="Activates a JAAQL user with the email and a password",
        method=REST__POST,
        body=[
            ARG_RES__email,
            ARG_RES__jaaql_password
        ],
        response=RES__totp_mfa_nullable
    )
)

DOCUMENTATION__users_confirm_revoke = SwaggerDocumentation(
    tags="Users",
    methods=SwaggerMethod(
        name="Confirm user revoke",
        description="Confirm the revoke of a user, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
    )
)

DOCUMENTATION__user_default_roles = SwaggerDocumentation(
    tags="User Management",
    methods=[
        SwaggerMethod(
            name="Fetch default user roles",
            description="A default user role is a role that is assigned to a user automatically upon creation of "
            "the user which can occur from the internal endpoint public or the sign up endpoint. ",
            method=REST__GET,
            arguments=gen_arg_res_sort_pageable(KEY__role, example_one=EXAMPLE__role),
            response=SwaggerResponse(
                description="List of default user roles",
                response=gen_filtered_records(KEY__role, [ARG_RES__role])
            )
        ),
        SwaggerMethod(
            name="Add default user role",
            description="Adds a default user role",
            method=REST__POST,
            arguments=ARG_RES__role
        ),
        SwaggerMethod(
            name="Delete default user role",
            description="Deletes a default user role",
            method=REST__DELETE,
            arguments=ARG_RES__role,
            response=RES__deletion_key
        )
    ]
)

DOCUMENTATION__user_default_roles_confirm_deletion = SwaggerDocumentation(
    tags="User Management",
    methods=SwaggerMethod(
        name="Confirm default role deletion",
        description="Confirm the default role deletion, providing a single use deletion key",
        method=REST__POST,
        body=ARG_RES__deletion_key
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