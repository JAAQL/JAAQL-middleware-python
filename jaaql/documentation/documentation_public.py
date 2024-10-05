import uuid

from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.mvc.generated_queries import *
from jaaql.documentation.documentation_shared import (ARG_RES__username, set_nullable, ARG_RES__password, RES__oauth_token, rename_arg,
                                                      ARG_RES__remember_me)

TITLE = "JAAQL API"
DESCRIPTION = "Collection of methods in the JAAQL API"
FILENAME = "jaaql_api"

# Not unused. Used to generate html files
from jaaql.documentation.documentation_shared import DOCUMENTATION__oauth_token, DOCUMENTATION__oauth_refresh

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
            ),
            SwaggerArgumentResponse(
                name=KEY__registered,
                description="Whether or not the user is to be marked as registered. Defaults to true",
                arg_type=bool,
                required=False,
                condition="Defaults to true"
            )
        ]
    )
)

DOCUMENTATION__create_account_batch = SwaggerDocumentation(
    tags="Admin",
    methods=SwaggerMethod(
        method=REST__POST,
        name="Create account batch",
        description="Will create a batch of accounts, if you have privileges to do so",
        body=SwaggerArgumentResponse(
            name=KEY__accounts,
            description="A list of the accounts",
            arg_type=SwaggerList(
                ARG_RES__username,
                set_nullable(ARG_RES__password, "Whether the user is given a password"),
                SwaggerArgumentResponse(
                    name=KEY__attach_as,
                    description="Whether the user will attach as a role",
                    arg_type=str,
                    required=False,
                    condition="Defaults to false",
                    example="my-role"
                ),
                SwaggerArgumentResponse(
                    name=KEY__registered,
                    description="Whether or not the user is to be marked as registered. Defaults to true",
                    arg_type=bool,
                    required=False,
                    condition="Defaults to true"
                )
            )
        )
    )
)

DOCUMENTATION__password = SwaggerDocumentation(
    tags="Account",
    methods=SwaggerMethod(
        method=REST__POST,
        name="Change password",
        description="Will change the logged in users password to the new one",
        body=[
            rename_arg(ARG_RES__password, KEY__old_password, "The old password for the user"),
            ARG_RES__password
        ],
        response=RES__oauth_token
    )
)

ARG_RES__event_application = SwaggerArgumentResponse(
    name=KG__security_event__application,
    description="The application of the dispatcher",
    arg_type=str,
    example=["out-and-about"]
)

ARG_RES__parameters = SwaggerArgumentResponse(
    name=KEY__parameters,
    description="Nonspecific data which is supplied as an object either for email or signup. Is validated",
    arg_type=ARG_RESP__allow_all,
    required=False,
    condition="Is signup data provided"
)

ARG_RES__query = SwaggerArgumentResponse(
    name=KEY__query,
    description="Nonspecific query which is supplied as an object either for sign up emails",
    arg_type=ARG_RESP__allow_all,
    required=True
)

ARG_RES__event_lock = SwaggerArgumentResponse(
    name=KG__security_event__event_lock,
    description="A key that is used to reference a security event",
    arg_type=str,
    example="0aff271e-bf0a-463b-b234-f558abd70edd"
)

ARG_RES__security_event_unlock_key = SwaggerArgumentResponse(
    name=KG__security_event__unlock_key,
    description="The unlock key",
    required=False,
    condition="Are you using a key to unlock or a code",
    arg_type=str,
    example="c9a941d5-2aea-4b96-967b-32a01e889d03"
)

ARG_RES__security_event_unlock_code = SwaggerArgumentResponse(
    name=KG__security_event__unlock_code,
    description="The unlock code",
    required=False,
    condition="Are you using a key to unlock or a code",
    arg_type=str,
    example="ABC123"
)

ARG_RES__oauth_token = SwaggerArgumentResponse(
    name=KEY__oauth_token,
    description="An auth token",
    arg_type=str,
    example=EXAMPLE__jwt
)

DOCUMENTATION__reset_password = SwaggerDocumentation(
    tags="Reset Password",
    security=False,
    methods=[
        SwaggerMethod(
            name="Request an password reset",
            description="Requests a password reset, sending an email to the user (or if the email template does not contain "
            "the reset code, they will then need to be approved by an admin).",
            method=REST__POST,
            body=[
                ARG_RES__username,
                ARG_RES__parameters,
                ARG_RES__event_application,
                SwaggerArgumentResponse(
                    name=KEY__reset_password_template,
                    description="The template to send if the user is already signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_r_et
                ),
                SwaggerArgumentResponse(
                    name=KEY__unregistered_user_reset_password_template,
                    description="The template to send if the user hasn't signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_u_et
                )
            ],
            response=[
                SwaggerResponse(
                    description="Reset password response",
                    response=ARG_RES__event_lock
                ),
                SwaggerFlatResponse(
                    description=ERR__too_many_reset_requests,
                    code=HTTPStatus.TOO_MANY_REQUESTS,
                    body=ERR__too_many_reset_requests
                )
            ]
        )
    ]
)

DOCUMENTATION__emails = SwaggerDocumentation(
    tags="Emails",
    security=True,
    methods=SwaggerMethod(
        name="Send email",
        description="Sends an email",
        method=REST__POST,
        body=[
            SwaggerArgumentResponse(
                name=KEY__template,
                description="The template to send",
                arg_type=str,
                example="my_template"
            ),
            ARG_RES__event_application,
            ARG_RES__parameters
        ]
    )
)

DOCUMENTATION__sign_up = SwaggerDocumentation(
    tags="sign_up",
    # Explicitly set sign up to true to enforce design decision. We use the attempted insert of the current user (which can be the public user) as security
    # If the insert fails then the user cannot sign up
    security=False,
    methods=[
        SwaggerMethod(
            name="Signs up to the Platform",
            description="Requests an invitation, sending an email to the user.",
            method=REST__POST,
            body=[
                ARG_RES__username,
                set_nullable(ARG_RES__password, "Is the user going through an unconfirmed signup"),
                ARG_RES__parameters,
                ARG_RES__remember_me,
                ARG_RES__query,
                ARG_RES__event_application,
                SwaggerArgumentResponse(
                    name=KEY__sign_up_template,
                    description="The template to send if the user hasn't signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_s_et
                ),
                SwaggerArgumentResponse(
                    name=KEY__already_signed_up_template,
                    description="The template to send if the user is already signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_a_et
                )
            ],
            response=RES__allow_all
        )
    ]
)

DOCUMENTATION__resend_sign_up = SwaggerDocumentation(
    tags="sign_up",
    security=True,
    methods=[
        SwaggerMethod(
            name="Resend sign up email",
            description="Allows an unconfirmed user to resend themselves a signup email when they are logged in.",
            method=REST__POST,
            body=[
                ARG_RES__event_application,
                SwaggerArgumentResponse(
                    name=KEY__sign_up_template,
                    description="The template to send if the user hasn't signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_s_et
                ),
                SwaggerArgumentResponse(
                    name=KEY__already_signed_up_template,
                    description="The template to send if the user is already signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_a_et
                )
            ],
            response=RES__allow_all
        )
    ]
)

DOCUMENTATION__invite = SwaggerDocumentation(
    tags="invite",
    # Explicitly set sign up to true to enforce design decision. We use the attempted insert of the current user (which can be the public user) as security
    # If the insert fails then the user cannot sign up
    security=True,
    methods=[
        SwaggerMethod(
            name="Request an invitation",
            description="Requests an invitation, sending an email to the user (or if the email template does not contain "
            "the unlock code, they will then need to be approved by an admin).",
            method=REST__POST,
            body=[
                set_nullable(ARG_RES__username, "Potentially if the user is not known"),
                ARG_RES__parameters,
                ARG_RES__event_application,
                SwaggerArgumentResponse(
                    name=KEY__sign_up_template,
                    description="The template to send if the user hasn't signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_s_et
                ),
                SwaggerArgumentResponse(
                    name=KEY__already_signed_up_template,
                    description="The template to send if the user is already signed up",
                    required=False,
                    condition="Should an email be sent or the default be used",
                    arg_type=str,
                    example=KG__application__default_a_et
                )
            ],
            response=RES__allow_all
        )
    ]
)

from jaaql.mvc.handmade_queries import EMAIL_TYPE__signup

DOCUMENTATION__security_event = SwaggerDocumentation(
    tags="Security Event",
    security=False,
    methods=[
        SwaggerMethod(
            name="Check Event and Key",
            description="Checks a security event is unused and that the key is valid",
            method=REST__POST,
            body=[
                set_nullable(ARG_RES__event_lock, "Just the unlock key can be provided"),
                ARG_RES__security_event_unlock_key,
                ARG_RES__security_event_unlock_code
            ],
            response=SwaggerFlatResponse(
                description="Will receive the type of the description if unlock code is correct",
                body=EMAIL_TYPE__signup
            )
        ),
        SwaggerMethod(
            name="Finish Security Event",
            description="Finishes the security event, supplying a password which can either be a new password or your login password, if using the "
            "already signed up flow",
            method=REST__PUT,
            body=[
                set_nullable(ARG_RES__event_lock, "Just the unlock key can be provided"),
                ARG_RES__security_event_unlock_key,
                ARG_RES__security_event_unlock_code,
                set_nullable(ARG_RES__password, "only if it's required")
            ],
            response=SwaggerResponse(
                description="Signup parameters",
                response=[
                    ARG_RES__parameters,
                    ARG_RES__username
                ]
            )
        )
    ]
)

ARG_RES__proc = [
    SwaggerArgumentResponse(
        name=KG__remote_procedure__application,
        description="The remote procedure application",
        arg_type=str,
        example="out-and-about"
    ),
    SwaggerArgumentResponse(
        name=KG__remote_procedure__name,
        description="The name of the remote procedure",
        arg_type=str,
        example="my_proc"
    )
]

DOCUMENTATION__remote_procedures = SwaggerDocumentation(
    tags="Remote Procedure",
    methods=SwaggerMethod(
        name="Execute remote procedure",
        description="Executes a remote procedure",
        method=REST__POST,
        body=ARG_RES__proc + [
            SwaggerArgumentResponse(
                name=KEY__args,
                arg_type=ARG_RESP__allow_all,
                description="The arguments that will be passed through to the function, as a JSON object"
            )
        ],
        response=RES__allow_all
    )
)

DOCUMENTATION__webhook = SwaggerDocumentation(
    tags="Webhook",
    security=False,  # Security is handled at the webhook implementation itself
    methods=[
        SwaggerMethod(
            name="Receive Webhook GET",
            description="Receives a webhook as a GET",
            method=REST__GET,
            arguments=ARG_RES__proc + [ARG_RES__parameters]
        ),
        SwaggerMethod(
            name="Receive Webhook POST",
            description="Receives a webhook as a POST",
            method=REST__POST,
            arguments=[
                SwaggerArgumentResponse(
                    name=KG__remote_procedure__application,
                    description="The remote procedure application",
                    arg_type=str,
                    example="out-and-about"
                ),
                SwaggerArgumentResponse(
                    name=KG__remote_procedure__name,
                    description="The name of the remote procedure",
                    arg_type=str,
                    example="my_proc"
                )
            ],
            body=ARG_RESP__allow_all
        )
    ]
)
