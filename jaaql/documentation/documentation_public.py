from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.mvc.generated_queries import *
from jaaql.documentation.documentation_shared import ARG_RES__username, set_nullable, ARG_RES__password, RES__oauth_token, rename_arg

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

ARG_RES__event_lock = SwaggerArgumentResponse(
    name=KG__security_event__event_lock,
    description="A key that is used to reference a security event",
    arg_type=str,
    example="0aff271e-bf0a-463b-b234-f558abd70edd"
)

DOCUMENTATION__sign_up_request_invite = SwaggerDocumentation(
    tags="Signup",
    security=False,
    methods=SwaggerMethod(
        name="Request an invitation",
        description="Requests an invitation, sending an email to the user (or if the email template does not contain "
        "the signup id, they will then need to be approved by an admin).",
        method=REST__POST,
        body=[
            ARG_RES__username,
            ARG_RES__parameters,
            ARG_RES__event_application,
            SwaggerArgumentResponse(
                name=KEY__sign_up_template,
                description="The template to send if the user is already signed up",
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
                example=KG__application__default_s_et
            )
        ],
        response=[
            SwaggerResponse(
                description="Sign up response",
                response=ARG_RES__event_lock
            ),
            SwaggerFlatResponse(
                description=ERR__too_many_signup_attempts,
                code=HTTPStatus.TOO_MANY_REQUESTS,
                body=ERR__too_many_signup_attempts
            )
        ]
    )
)
