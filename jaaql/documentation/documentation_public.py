from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.documentation.documentation_shared import ARG_RES__username, EXAMPLE__password, ARG_RES__password, RES__oauth_token,\
    rename_arg, set_required, set_nullable, ARG_RES__application, ARG_RES__configuration

TITLE = "JAAQL API"
DESCRIPTION = "Collection of methods in the JAAQL API"
FILENAME = "jaaql_api"

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh

ARG_RES__application_nullable = SwaggerArgumentResponse(
    name=KEY__application,
    description="The application",
    example=["playground"],
    required=False,
    arg_type=str,
    condition="If this is required"
)
ARG_RES__configuration_nullable = SwaggerArgumentResponse(
    name=KEY__configuration,
    description="The configuration",
    example=["main"],
    required=False,
    arg_type=str,
    condition="If this is required"
)
ARG_RES__parameters = SwaggerArgumentResponse(
    name=KEY__parameters,
    description="Nonspecific data which is supplied as an object either for email or signup. Is validated",
    arg_type=ARG_RESP__allow_all,
    required=False,
    condition="Is signup data provided"
)

DOCUMENTATION__create_account = SwaggerDocumentation(
    tags="Admin",
    methods=SwaggerMethod(
        method=REST__POST,
        name="Create account",
        description="Will create an account, if you have privileges to do so",
        body=[
            ARG_RES__username,
            set_nullable(ARG_RES__password, "Whether the user is given a password"),
            SwaggerArgumentResponse(
                name=KEY__attach_as,
                description="Whether the user will attach as a role",
                arg_type=str,
                required=False,
                condition="Defaults to false",
                example="my-role"
            )
        ]
    )
)

ARG_RES__email_template = SwaggerArgumentResponse(
    name=KEY__email_template,
    description="Email template name",
    arg_type=str,
    example=["signup"]
)
ARG_RES__already_signed_up_email_template = rename_arg(ARG_RES__email_template, KEY__already_signed_up_email_template,
                                                       "The email template sent if the user already exists")

ARG_RES__reset_password_email_template = rename_arg(ARG_RES__email_template, KEY__email_template,
                                                    "The email template for resetting the password")

UUID__invite = "137adf50-76a3-4314-b933-b94e6686489e"

ARG_RES__invite_key = SwaggerArgumentResponse(
    name=KEY__invite_key,
    description="A sign up key that functions as an invite for a specific email address",
    arg_type=str,
    example=[UUID__invite],
)

ARG_RES__invite_poll_key = rename_arg(ARG_RES__invite_key,
                                      new_description="A key returned after signing up that can be used to sign up to the server once the signup "
                                                      "process has began with the other key or the 5 digit signup code has been input")

ARG_RES__reset_key = rename_arg(ARG_RES__invite_key, KEY__reset_key,
                                new_description="A key that can be used to reset a password of a specific user")

ARG_RES__reset_poll_key = rename_arg(ARG_RES__reset_key,
                                     new_description="A key returned after requesting a reset password email that can be used to reset "
                                     "password once the process has began with the other key or the 8 length reset code has been input")

ARG_RES__email = rename_arg(ARG_RES__username, KEY__email)

DOCUMENTATION__sign_up_request_invite = SwaggerDocumentation(
    tags="Signup",
    security=False,
    methods=SwaggerMethod(
        name="Request an invitation",
        description="Requests an invitation, sending an email to the user (or if the email template does not contain "
        "the signup id, they will then need to be approved by an admin).",
        method=REST__POST,
        body=[
            ARG_RES__email,
            ARG_RES__parameters,
            ARG_RES__configuration,
            ARG_RES__application,
            ARG_RES__email_template,
            ARG_RES__already_signed_up_email_template
        ],
        response=[
            SwaggerResponse(
                description="Sign up response",
                response=ARG_RES__invite_poll_key
            ),
            SwaggerFlatResponse(
                description=ERR__too_many_signup_attempts,
                code=HTTPStatus.TOO_MANY_REQUESTS,
                body=ERR__too_many_signup_attempts
            )
        ]
    )
)

DOCUMENTATION__sign_up_status = SwaggerDocumentation(
    tags="Signup",
    # The security is in the invite key. User has not signed up yet so cannot get an oauth token
    security=False,
    methods=SwaggerMethod(
        name="Request invite status",
        description="Requesting status with the invite key sent to the email will allow the poll key to be used as an invite key",
        method=REST__GET,
        arguments=[
            SwaggerArgumentResponse(
                name=KEY__invite_or_poll_key,
                description="Either an invite or invite poll key",
                arg_type=str,
                example=[UUID__invite]
            ),
            SwaggerArgumentResponse(
                name=KEY__invite_code,
                description="An 5 length invite code received only via email. Used only with the invite poll key and valid only for 15 minutes. "
                "The invite key in the email is valid much longer (2 weeks default) but due to the ease of guessing a 5 letter code (~13M "
                "combinations) it is kept short for security reasons",
                arg_type=str,
                example=["AGZSB"],
                required=False,
                condition="Is this the invite poll key"
            )
        ],
        response=[
            SwaggerResponse(
                description="Invite status enumeration",
                response=SwaggerArgumentResponse(
                    name=KEY__invite_key_status,
                    description="An enumeration of the statuses of an invite key. 0->New signup, 1->Sign up process started, "
                    "2->Signing up again with same email, 3->Sign up already finished",
                    arg_type=int,
                    example=[0]
                )
            ),
            SwaggerFlatResponse(
                description=ERR__too_many_code_attempts,
                code=HTTPStatus.LOCKED,
                body=ERR__too_many_code_attempts
            )
        ]
    )
)

DOCUMENTATION__sign_up_with_invite = SwaggerDocumentation(
    tags="Signup",
    # The security is in the invite key. User has not signed up yet so cannot get an oauth token
    security=False,
    methods=SwaggerMethod(
        name="Signup with invite",
        description="Signs up to JAAQL using either the key fetched either from internal methods or from the email. "
        "Returns the signup parameters if supplied upon signup",
        method=REST__POST,
        body=[
            ARG_RES__invite_key,
            ARG_RES__password
        ],
        response=[
            SwaggerResponse(
                description="Information relating to the sign up",
                response=ARG_RES__email
            ),
            SwaggerFlatResponse(
                description=ERR__already_signed_up,
                code=HTTPStatus.CONFLICT,
                body=ERR__already_signed_up
            )
        ]
    )
)

DOCUMENTATION__sign_up_fetch = SwaggerDocumentation(
    tags="Signup",
    methods=SwaggerMethod(
        name="Fetch signup data",
        description="Fetches the signup data",
        method=REST__GET,
        arguments=ARG_RES__invite_key,
        response=[
            SwaggerResponse(
                description="Finish signup response",
                response=ARG_RES__parameters
            )
        ]
    )
)

DOCUMENTATION__sign_up_finish = SwaggerDocumentation(
    tags="Signup",
    methods=SwaggerMethod(
        name="Finish signup",
        description="Deletes the signup data",
        method=REST__POST,
        body=ARG_RES__invite_key
    )
)

DOCUMENTATION__reset_password = SwaggerDocumentation(
    security=False,
    tags="Account",
    methods=SwaggerMethod(
        name="Reset Password",
        description="Send reset password email",
        method=REST__POST,
        body=[
            ARG_RES__email,
            ARG_RES__reset_password_email_template,
            ARG_RES__application,
            ARG_RES__configuration,
            ARG_RES__parameters
        ],
        response=[
            SwaggerResponse(
                description="Sign up response",
                response=ARG_RES__reset_poll_key
            ),
            SwaggerFlatResponse(
                description=ERR__too_many_reset_requests,
                code=HTTPStatus.TOO_MANY_REQUESTS,
                body=ERR__too_many_signup_attempts
            )
        ]
    )
)

DOCUMENTATION__reset_password_status = SwaggerDocumentation(
    tags="Account",
    # The security is in the invite key. User has not signed up yet so cannot get an oauth token
    security=False,
    methods=SwaggerMethod(
        name="Request password reset status",
        description="Requesting status with the reset key sent to the email will allow the poll key to be used as a reset key",
        method=REST__GET,
        arguments=[
            SwaggerArgumentResponse(
                name=KEY__reset_or_poll_key,
                description="Either an reset or reset poll key",
                arg_type=str,
                example=[UUID__invite]
            ),
            SwaggerArgumentResponse(
                name=KEY__reset_code,
                description="An 8 length reset code received only via email. Used only with the reset poll key and valid only for 15 minutes. "
                "The reset key in the email is valid much longer (2 hours default)",
                arg_type=str,
                example=["7UYJ1TVX"],
                required=False,
                condition="Is this the reset poll key"
            )
        ],
        response=[
            SwaggerResponse(
                description="Reset status enumeration",
                response=SwaggerArgumentResponse(
                    name=KEY__reset_key_status,
                    description="An enumeration of the statuses of a reset key. 0->New reset key, 1->Reset process started, "
                    "2->Reset process finished ",
                    arg_type=int,
                    example=[0]
                )
            ),
            SwaggerFlatResponse(
                description=ERR__too_many_code_attempts,
                code=HTTPStatus.LOCKED,
                body=ERR__too_many_code_attempts
            )
        ]
    )
)

DOCUMENTATION__reset_password_with_invite = SwaggerDocumentation(
    tags="Account",
    # The security is in the invite key. User has not signed up yet so cannot get an oauth token
    security=False,
    methods=SwaggerMethod(
        name="Reset password with key",
        description="Resets password using either the key fetched either from internal methods or from the email",
        method=REST__POST,
        body=[
            ARG_RES__reset_key,
            ARG_RES__password
        ],
        response=[
            SwaggerResponse(
                description="The email address of the user that has had their password reset it's password",
                response=[ARG_RES__email, ARG_RES__parameters]
            )
        ]
    )
)

DOCUMENTATION__password = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        method=REST__POST,
        name="Change password",
        description="Will change the logged in users password to the new one",
        arguments=[
            rename_arg(ARG_RES__username, KEY__old_password, "The old password for the user"),
            ARG_RES__password
        ],
        response=RES__oauth_token
    )
)

DOCUMENTATION__submit = SwaggerDocumentation(
    tags="Queries",
    methods=SwaggerMethod(
        name="Execute JAAQL query",
        description="Executes a JAAQL query which is either a single SQL query or a list of queries. Returns results",
        method=REST__POST,
        arguments=ARG_RESP__allow_all,
        response=RES__allow_all,
        parallel_verification=True
    )
)

ARG_RES__renderable_document = [
    SwaggerArgumentResponse(
        name=KEY__attachment_name,
        description="The name of the renderable document in the database",
        arg_type=str,
        example=["my_pdf_template"]
    ),
    SwaggerArgumentResponse(
        name=KEY__parameters,
        description="Any parameters to pass to the url as http GET parameters",
        arg_type=ARG_RESP__allow_all
    ),
    set_nullable(ARG_RES__application, "Not required if being sent in an email as this is specified in the email"),
    set_nullable(ARG_RES__configuration, "Not required if being sent in an email as this is specified in the email"),
]

ARG_RES__attachments_for_send = SwaggerArgumentResponse(
    name=KEY__attachments,
    description="Any email attachments, if supplied. Uses server side template rendering",
    arg_type=SwaggerList(*ARG_RES__renderable_document),
    required=False,
    condition="If emails are attached"
)

ARG_RES__email_recipient = SwaggerArgumentResponse(
    name=KEY__recipient,
    description="The recipient of the email, null if sent to self",
    required=False,
    condition="Is the email being sent to someone else",
    arg_type=str,
    example=["my_manager", "client_a"]
)

ARG_RES__email_base = [
    ARG_RES__email_template,
    ARG_RES__email_recipient
]

DOCUMENTATION__email = SwaggerDocumentation(
    tags="Emails",
    methods=[
        SwaggerMethod(
            name="Send email",
            description="Sends an email template",
            method=REST__POST,
            body=[
                ARG_RES__application,
                ARG_RES__configuration,
                ARG_RES__parameters,
                ARG_RES__attachments_for_send
            ] + ARG_RES__email_base
        )
    ]
)

EXAMPLE__document_id = "b47dc954-d608-4e1b-8a8c-d8b754ee554b"

ARG_RES__document_id = SwaggerArgumentResponse(
    name=KEY__document_id,
    description="A document that can be used to fetch the document",
    arg_type=str,
    example=EXAMPLE__document_id
)

DOCUMENTATION__document = SwaggerDocumentation(
    tags="Documents",
    methods=[
        SwaggerMethod(
            name="Triggers a document render",
            description="Triggers a render of a document which can then be downloaded. Document is available for 5 minutes after the document has "
            "been rendered",
            method=REST__POST,
            body=ARG_RES__renderable_document + [
                SwaggerArgumentResponse(
                    name=KEY__create_file,
                    description="Whether or not to create the file. You will then be provided with a URL when it is ready which can be downloaded "
                                "from. Otherwise you will be sent back a boolean",
                    arg_type=bool
                )
            ],
            response=SwaggerResponse(
                description="A document id",
                response=ARG_RES__document_id
            )
        ),
        SwaggerMethod(
            name="Download document",
            description="Downloads the document. Can also be used as a polling endpoint to see if the document is ready",
            method=REST__GET,
            arguments=ARG_RES__document_id,
            response=[
                SwaggerFlatResponse(
                    description="A link to the raw file data. This URL is called with GET and no security parameters. Can only be called once",
                    body="https://www.jaaql.io/api/rendered_documents/" + EXAMPLE__document_id + ".pdf"
                ),
                SwaggerFlatResponse(
                    description="The url to the document. Will be deleted after 5 minutes",
                    code=HTTPStatus.CREATED,
                    body="https://www.jaaql.io/rendered_documents/" + EXAMPLE__document_id + ".pdf"
                ),
                SwaggerFlatResponse(
                    description="Document still rendering",
                    code=HTTPStatus.TOO_EARLY,
                    body=ERR__document_still_rendering
                ),
                SwaggerFlatResponse(
                    description="Document id not found. Either expired or did not exist",
                    body=ERR__document_id_not_found,
                    code=HTTPStatus.NOT_FOUND
                )
            ]
        )
    ]
)

DOCUMENTATION__rendered_document = SwaggerDocumentation(
    tags="Documents",
    security=False,
    methods=SwaggerMethod(
        name="Stream rendered document",
        description="Streams a rendered document as a downlaod",
        method=REST__GET,
        arguments=[ARG_RES__document_id, SwaggerArgumentResponse(
            name=KEY__as_attachment,
            description="Whether in the browser the 'Content-Disposition' header should be set as attachment",
            arg_type=bool,
            required=False,
            condition="Defaults to false"
        )],
        response=SwaggerFlatResponse(
            description="The raw file data. Cannot be re-downloaded after this",
            body=BODY__file
        )
    )
)

DOCUMENTATION__drop_email_account = SwaggerDocumentation(
    tags="Emails",
    methods=SwaggerMethod(
        name="Drop email account",
        description="Drops the email account",
        method=REST__DELETE,
        arguments=SwaggerArgumentResponse(
            name=KEY__name,
            description="The name of the email account",
            arg_type=str,
            example=["noreply"]
        )
    )
)

ARG_RES__database_name = SwaggerArgumentResponse(
    name=KEY__name,
    description="The name of the database",
    arg_type=str,
    example=["invoicing_live"]
)
