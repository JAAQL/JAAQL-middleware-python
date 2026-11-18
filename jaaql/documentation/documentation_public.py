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
        ],
        exceptions=SwaggerResponseException(HTTPStatus.CONFLICT, "error_code 1001, an account with this username, or the role it would "
                                                                 "attach as, exists already")
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
        ),
        exceptions=SwaggerResponseException(HTTPStatus.CONFLICT, "error_code 1001, an account with one of these usernames, or for one of "
                                                                 "these users of an identity provider, exists already")
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

RES__public_procedure_busy = SwaggerFlatResponse(
    description="The procedure is public and the worker already runs PUBLIC_PROCEDURE_MAX_RUNNING public procedures and no place came free "
                "in time, so the procedure is not started. Retry-After gives the seconds to wait",
    code=HTTPStatus.SERVICE_UNAVAILABLE,
    body="Too many public procedures are running. Try again later"
)

DOCUMENTATION__remote_procedures = SwaggerDocumentation(
    tags="Remote Procedure",
    methods=SwaggerMethod(
        name="Execute remote procedure",
        description="Executes a remote procedure in a node process of its own. A worker runs at most PUBLIC_PROCEDURE_MAX_RUNNING (default " +
                    str(PUBLIC_PROCEDURE__default_max_running) + ") public procedures at once, and at most PUBLIC_PROCEDURE_MAX_WAITING "
                    "(default " + str(PUBLIC_PROCEDURE__default_max_waiting) + ") more wait for a place, each at most " +
                    str(SLOT__wait_seconds) + " s. A public procedure that finds no place is not started, and the answer is 503 with "
                    "Retry-After. Private procedures are not bounded",
        method=REST__POST,
        body=ARG_RES__proc + [
            SwaggerArgumentResponse(
                name=KEY__args,
                arg_type=ARG_RESP__allow_all,
                description="The arguments that will be passed through to the function, as a JSON object"
            )
        ],
        response=[RES__allow_all, RES__public_procedure_busy]
    )
)

DESCRIPTION__webhook_process = (" in a node process of its own, which answers it. A worker runs at most WEBHOOK_MAX_RUNNING (default " +
                                 str(WEBHOOK__default_max_running) + ") webhook processes at once, and at most WEBHOOK_MAX_WAITING "
                                 "(default " + str(WEBHOOK__default_max_waiting) + ") more wait for a place, each at most " +
                                 str(SLOT__wait_seconds) + " s. A webhook that finds no place is not started, and the answer is 503 "
                                 "with Retry-After")
DESCRIPTION__webhook_query = (". The query parameters reach the webhook as they came, as its parameters, whatever their names, a name or "
                              "application among them; the path's application and name say which webhook runs")
DESCRIPTION__webhook_no_head = (". A HEAD is answered 405 and starts no webhook, which cannot tell a HEAD from a GET and would act on it as "
                                "on the GET")
DESCRIPTION__webhook_post_size = (" reaches the webhook byte for byte on the process's stdin, whatever its size up to the request size limit "
                                  "(Flask's MAX_CONTENT_LENGTH, 2 MiB, and before it nginx's client_max_body_size, by default 1 MiB, each "
                                  "answering 413)")
DESCRIPTION__webhook_post = (". The body, JSON or form-encoded (application/x-www-form-urlencoded, as payment providers such as Mollie send "
                             "it, never parsed by JAAQL)" + DESCRIPTION__webhook_post_size + DESCRIPTION__webhook_query)
DESCRIPTION__secure_webhook_post = (". The JSON body" + DESCRIPTION__webhook_post_size + ". A secure webhook, which the login cookie "
                                    "authorises, takes JSON only, as a browser sends JSON to another site only after a CORS preflight" +
                                    DESCRIPTION__webhook_query)
RES__webhook_answer = SwaggerFlatResponse(description="The webhook's own answer, with the status, headers and body it gives")
RES__webhook_body_too_large = SwaggerFlatResponse(
    description="The body is larger than the request size limit, so the webhook is not started",
    code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    body="Request Entity Too Large"
)
RES__webhook_busy = SwaggerFlatResponse(
    description="The worker already runs WEBHOOK_MAX_RUNNING webhook processes and no place came free in time, so the webhook is not "
                "started. Retry-After gives the seconds to wait",
    code=HTTPStatus.SERVICE_UNAVAILABLE,
    body="Too many webhooks are running. Try again later"
)

DOCUMENTATION__webhook = SwaggerDocumentation(
    tags="Webhook",
    security=False,  # Security is handled at the webhook implementation itself
    methods=[
        SwaggerMethod(
            name="Receive Webhook GET",
            description="Receives a webhook as a GET" + DESCRIPTION__webhook_process + DESCRIPTION__webhook_query +
                        DESCRIPTION__webhook_no_head,
            method=REST__GET,
            arguments=ARG_RES__proc + [ARG_RES__parameters],
            response=[RES__webhook_answer, RES__webhook_busy],
            raw_request=True
        ),
        SwaggerMethod(
            name="Receive Webhook POST",
            description="Receives a webhook as a POST" + DESCRIPTION__webhook_process + DESCRIPTION__webhook_post,
            method=REST__POST,
            arguments=ARG_RESP__allow_all,
            response=[RES__webhook_answer, RES__webhook_body_too_large, RES__webhook_busy],
            raw_request=True,
            form_body=True
        )
    ]
)

DOCUMENTATION__secure_webhook = SwaggerDocumentation(
    tags="Webhook",
    security=True,  # Security is handled at the webhook implementation itself
    methods=[
        SwaggerMethod(
            name="Receive Webhook GET",
            description="Receives a webhook as a GET" + DESCRIPTION__webhook_process + DESCRIPTION__webhook_query +
                        DESCRIPTION__webhook_no_head,
            method=REST__GET,
            arguments=ARG_RES__proc + [ARG_RES__parameters],
            response=[RES__webhook_answer, RES__webhook_busy],
            raw_request=True
        ),
        SwaggerMethod(
            name="Receive Webhook POST",
            description="Receives a webhook as a POST" + DESCRIPTION__webhook_process + DESCRIPTION__secure_webhook_post,
            method=REST__POST,
            arguments=ARG_RESP__allow_all,
            response=[RES__webhook_answer, RES__webhook_body_too_large, RES__webhook_busy],
            raw_request=True
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
            description="Downloads the document. Can also be used as a polling endpoint to see if the document is ready. Client errors of "
                        "/documents (GET and POST) are plain text (text/plain), as BATON's document rendering reads them, not JAAQL's error body",
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
                    description="A link to the raw file data. This URL is called with GET and no security parameters. Can only be called once "
                                "with GET (a HEAD leaves the document)",
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
        description="Streams a rendered document as a download, and deletes it. A HEAD answers the same headers without the file and "
                    "leaves the document to be downloaded",
        method=REST__GET,
        arguments=[ARG_RES__document_id, SwaggerArgumentResponse(
            name=KEY__as_attachment,
            description="Whether in the browser the 'Content-Disposition' header should be set as attachment",
            arg_type=bool,
            required=False,
            condition="Defaults to false"
        )],
        response=[
            SwaggerFlatResponse(
                description="The raw file data. Cannot be re-downloaded after this",
                body=BODY__file
            ),
            SwaggerFlatResponse(
                description="Document still rendering, as JAAQL's error body with error_code 1018 (DocumentStillRendering)",
                code=HTTPStatus.TOO_EARLY,
                body=ERR__document_still_rendering
            ),
            SwaggerFlatResponse(
                description="Document id not found. Either expired, downloaded already or did not exist",
                body=ERR__document_id_not_found,
                code=HTTPStatus.NOT_FOUND
            )
        ]
    )
)
