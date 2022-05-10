from jaaql.openapi.swagger_documentation import *


TITLE = "CTP API"
DESCRIPTION = "Access ctp specific function calls"
FILENAME = "ctp_api"

KEY__name = "name"
KEY__response = "response"

DOCUMENTATION__hello = SwaggerDocumentation(
    tags="Hello",
    # User has not signed up yet so cannot get an oauth token
    security=False,
    methods=SwaggerMethod(
        name="Hello",
        description="Can be polled and will return 200 OK if the service is up",
        method=REST__GET
    )
)

KEY__email_data = "email_data"

DOCUMENTATION__send_email = SwaggerDocumentation(
    tags="Email Test",
    methods=SwaggerMethod(
        name="Send email",
        description="Send an email",
        method=REST__POST,
        body=SwaggerArgumentResponse(
            name=KEY__email_data,
            description="The data that is inserted into the email",
            arg_type=str,
            example=["insertion data"]
        )
    )
)
