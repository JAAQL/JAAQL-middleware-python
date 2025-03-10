from jaaql.mvc.generated_queries import KG__user_registry__provider, KG__user_registry__tenant
from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, SwaggerArgumentResponse,\
    SwaggerFlatResponse, REST__POST, ARG_RESP__allow_all, RES__allow_all
from jaaql.constants import *
from typing import Union


OUTPUT = False

ENDPOINT__refresh = "/oauth/refresh"


def set_nullable(arg_res: Union[SwaggerArgumentResponse, list], condition: Union[str, list] = None,
                 new_name: Union[str, list] = None):
    if isinstance(arg_res, list):
        if new_name is None:
            new_name = [None] * len(arg_res)
        return [set_nullable(cur, condition) for cur, condition, new_name in zip(arg_res, condition, new_name)]
    else:
        return SwaggerArgumentResponse(
            arg_res.name if new_name is None else new_name,
            arg_res.description,
            arg_res.arg_type,
            arg_res.example,
            False,
            condition=condition
        )


def rename_arg(arg_res: SwaggerArgumentResponse, new_name: str = None, new_description: str = None, new_examples=None):
    return SwaggerArgumentResponse(
        arg_res.name if new_name is None else new_name,
        arg_res.description if new_description is None else new_description,
        arg_res.arg_type,
        arg_res.example if new_examples is None else new_examples,
        arg_res.required,
        arg_res.condition
    )


RES__oauth_token = SwaggerFlatResponse(
    description="A temporary JWT token that can be used to authenticate with the server",
    body=EXAMPLE__jwt
)

ARG_RES__provider = SwaggerArgumentResponse(
    name=KG__user_registry__provider,
    description="The provider",
    arg_type=str,
    example=["AzureAD"]
)

ARG_RES__tenant = SwaggerArgumentResponse(
    name=KG__user_registry__tenant,
    description="The associated tenant",
    arg_type=str,
    example=["relay"]
)

ARG_RES__username = SwaggerArgumentResponse(
    name=KEY__username,
    description="JAAQL login username",
    arg_type=str,
    lower=True,
    strip=True,
    example=["jaaql", "aaron@jaaql.com"]
)

EXAMPLE__password = ["pa55word", "p@ssword"]

ARG_RES__password = SwaggerArgumentResponse(
    name=KEY__password,
    description="JAAQL login password",
    arg_type=str,
    strip=True,
    example=EXAMPLE__password,
    required=True
)

DOCUMENTATION__oauth_token = SwaggerDocumentation(
    tags="OAuth",
    security=False,  # This _is_ the security method, therefore it is not expecting a jwt token
    methods=SwaggerMethod(
        name="OAuth Fetch Token",
        description="Authenticate with the server. Send username and password and server will respond with 200 and a "
                    "token which can be used to access the service. The server may also respond with a 202 and a "
                    "token, this indicates that an mfa key is expected. Send the token back to the service along with "
                    "an MFA key and you will returned the aforementioned 200 response",
        method=REST__POST,
        body=[
            ARG_RES__username,
            ARG_RES__password
        ],
        response=RES__oauth_token
    )
)

ARG_RES__remember_me = SwaggerArgumentResponse(
    name=KEY__remember_me,
    arg_type=bool,
    description="Whether or not the returned cookie will act as a remember me cookie",
    required=False,
    condition="Defaults to false"
)

DOCUMENTATION__oauth_cookie = SwaggerDocumentation(
    tags="OAuth",
    security=False,  # This _is_ the security method, therefore it is not expecting a jwt token
    methods=SwaggerMethod(
        name="OAuth Fetch Token",
        description="Authenticate with the server. Send username and password and server will respond with 200 and a "
                    "token which can be used to access the service. The server may also respond with a 202 and a "
                    "token, this indicates that an mfa key is expected. Send the token back to the service along with "
                    "an MFA key and you will returned the aforementioned 200 response",
        method=REST__POST,
        body=[
            ARG_RES__username,
            ARG_RES__password,
            ARG_RES__remember_me
        ],
        response=SwaggerFlatResponse()
    )
)

DOCUMENTATION__logout_cookie = SwaggerDocumentation(
    tags="OAuth",
    security=False,
    methods=SwaggerMethod(
        name="OAuth Fetch Token",
        description="Authenticate with the server. Send username and password and server will respond with 200 and a "
                    "token which can be used to access the service. The server may also respond with a 202 and a "
                    "token, this indicates that an mfa key is expected. Send the token back to the service along with "
                    "an MFA key and you will returned the aforementioned 200 response",
        method=REST__POST,
        response=SwaggerFlatResponse()
    )
)

DOCUMENTATION__oauth_refresh = SwaggerDocumentation(
    tags="OAuth",
    security=False,
    methods=SwaggerMethod(
        name="OAuth Refresh Token",
        description="Refresh your token",
        method=REST__POST,
        response=RES__oauth_token
    )
)

DOCUMENTATION__oauth_refresh_cookie = SwaggerDocumentation(
    tags="OAuth",
    security=False,
    methods=SwaggerMethod(
        name="OAuth Refresh Cookie",
        description="Refresh your Cookie",
        method=REST__POST,
        response=SwaggerFlatResponse()
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

DOCUMENTATION__execute = SwaggerDocumentation(
    tags="Queries",
    methods=SwaggerMethod(
        name="Execute JAAQL pre-prepared query",
        description="Executes a query from a list of pre-prepared queries. Returns results",
        method=REST__POST,
        arguments=ARG_RESP__allow_all,
        response=RES__allow_all,
        parallel_verification=True
    )
)

DOCUMENTATION__call_proc = SwaggerDocumentation(
    tags="Queries",
    methods=SwaggerMethod(
        name="Execute JAAQL database procedure",
        description="Executes a procedure, returns results",
        method=REST__POST,
        arguments=ARG_RESP__allow_all,
        response=RES__allow_all,
        parallel_verification=True
    )
)
