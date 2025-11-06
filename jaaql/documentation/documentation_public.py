import uuid

from jaaql.openapi.swagger_documentation import *
from jaaql.constants import *
from jaaql.mvc.generated_queries import *
from jaaql.documentation.documentation_shared import (ARG_RES__username, set_nullable, ARG_RES__password, RES__oauth_token, rename_arg,
                                                      ARG_RES__remember_me, ARG_RES__provider, ARG_RES__tenant)

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
                SwaggerArgumentResponse(
                    name=KG__account__sub,
                    description="The sub of the user (OIDC)",
                    arg_type=str,
                    required=False,
                    condition="Are we federating the user",
                    example="556c0002-40d2-4bd8-99ea-48c61de4acb9"
                ),
                set_nullable(ARG_RES__password, "Whether the user is given a password"),
                set_nullable(ARG_RES__provider, "Whether this user is federated"),
                set_nullable(ARG_RES__tenant, "Whether this user is federated"),
                SwaggerArgumentResponse(
                    name=KEY__attach_as,
                    description="Whether the user will attach as a role",
                    arg_type=str,
                    required=False,
                    condition="Defaults to false",
                    example="my-role"
                )
            )
        )
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

ARG_RES__oauth_token = SwaggerArgumentResponse(
    name=KEY__oauth_token,
    description="An auth token",
    arg_type=str,
    example=EXAMPLE__jwt
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
            arguments=ARG_RESP__allow_all
        )
    ]
)

DOCUMENTATION__secure_webhook = SwaggerDocumentation(
    tags="Webhook",
    security=True,  # Security is handled at the webhook implementation itself
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
            arguments=ARG_RESP__allow_all
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
    )
]

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
                ),
                SwaggerArgumentResponse(
                    name=KEY__application,
                    description="The application of the document template",
                    arg_type=str,
                    example=["out-and-about"]
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
            arguments=[
                ARG_RES__document_id,
                SwaggerArgumentResponse(
                    name=KEY__as_attachment,
                    description="Whether in the browser the 'Content-Disposition' header should be set as attachment",
                    arg_type=bool,
                    required=False,
                    condition="Defaults to false"
                )
            ],
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
