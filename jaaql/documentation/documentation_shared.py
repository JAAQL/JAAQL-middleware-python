from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, SwaggerArgumentResponse, SwaggerResponse, SwaggerList,\
    SwaggerFlatResponse, REST__POST
from jaaql.constants import *
from typing import Union, List

import copy

OUTPUT = False

ENDPOINT__refresh = "/oauth/refresh"

ARG_RES__application = SwaggerArgumentResponse(
    name=KEY__application,
    description="The application",
    example=["playground"],
    required=False,
    arg_type=str,
    condition="If this is a public user"
)

ARG_RES__configuration = SwaggerArgumentResponse(
    name=KEY__configuration,
    description="The application configuration",
    example=["main"],
    arg_type=str
)

ARG_RES__deletion_key = SwaggerArgumentResponse(
    name=KEY__deletion_key,
    description="Single use deletion key",
    arg_type=str,
    example=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkZWxldGlvbl9wdXJwb3NlIjoiZXhhbXBsZSJ9.aJEPcEJBkyM9vEKT_D6AXT-hZAZ"
             "9UvagKGtljvsBj8w"],
    required=True
)

RES__deletion_key = SwaggerResponse(
    description="Returns a single use key that must be sent to the server to confirm. Key expires in 30 seconds",
    response=ARG_RES__deletion_key
)

ARG_RES__filtered_records = [
    SwaggerArgumentResponse(
        name=KEY__records_total,
        description="Total number of records without any searches etc.",
        required=True,
        arg_type=int,
        example=[100, 200]
    ),
    SwaggerArgumentResponse(
        name=KEY__records_filtered,
        description="Number of filtered records, after searches",
        required=True,
        arg_type=int,
        example=[80, 160]
    )
]


def rename_arg(arg_res: SwaggerArgumentResponse, new_name: str = None, new_description: str = None, new_examples=None):
    return SwaggerArgumentResponse(
        arg_res.name if new_name is None else new_name,
        arg_res.description if new_description is None else new_description,
        arg_res.arg_type,
        arg_res.example if new_examples is None else new_examples,
        arg_res.required,
        arg_res.condition
    )


def set_required(arg_res: SwaggerArgumentResponse, new_name: str = None, new_description: str = None):
    return SwaggerArgumentResponse(
        arg_res.name if new_name is None else new_name,
        arg_res.description if new_description is None else new_description,
        arg_res.arg_type,
        arg_res.example,
        True
    )


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


def gen_filtered_records(name: str, data: [SwaggerArgumentResponse]):
    wrapper = SwaggerArgumentResponse(
        name=KEY__data,
        description="List of " + name + " records",
        required=True,
        arg_type=SwaggerList(*data)
    )
    return ARG_RES__filtered_records + [wrapper]


ARG_RES__part_sort_pageable = [
    SwaggerArgumentResponse(
        name=KEY__size,
        condition="If not supplied, will return all records",
        description="The size of the page",
        arg_type=int,
        required=False,
        example=[10, 20]
    ),
    SwaggerArgumentResponse(
        name=KEY__page,
        description="The page number to select, 0-based indexing",
        condition="If not supplied will default to 0",
        arg_type=int,
        required=False,
        example=[0, 1]
    )
]


def gen_arg_res_sort_pageable(col_one: str, col_two: str = None, example_one: str = None, example_two: str = None):
    if example_one is None:
        example_one = "jaaql"
    if example_two is None:
        example_two = "jaaql"

    if col_two is None:
        sort_arg = SwaggerArgumentResponse(
            name=KEY__sort,
            description="Comma separated sort",
            condition="If not supplied uses default database ordering",
            arg_type=str,
            required=False,
            example=[col_one + " ASC", col_one + " DESC"]
        )
        search_arg = SwaggerArgumentResponse(
            name=KEY__search,
            description="OR/AND separated search. Uses a limited subset of SQL",
            condition="If not supplied all records will match",
            arg_type=str,
            required=False,
            example=[col_one + " LIKE '%" + example_one + "%'"]
        )
    else:
        sort_arg = SwaggerArgumentResponse(
            name=KEY__sort,
            description="Comma separated sort",
            condition="If not supplied uses default database ordering",
            arg_type=str,
            required=False,
            example=[col_one + " ASC, " + col_two + " DESC", col_two + " ASC, " + col_one + " DESC"]
        )
        search_arg = SwaggerArgumentResponse(
            name=KEY__search,
            description="OR/AND separated search. Uses a limited subset of SQL",
            condition="If not supplied all records will match",
            arg_type=str,
            required=False,
            example=[col_one + " LIKE '%" + example_one + "%' OR " + col_two + " LIKE '%" + example_two + "%'",
                     col_two + " LIKE '%" + example_two + "%' AND " + col_one + " LIKE '%" + example_one + "%'"]
        )

    return [sort_arg, search_arg] + ARG_RES__part_sort_pageable


def combine_response(res: SwaggerResponse, args: Union[SwaggerArgumentResponse, List[SwaggerArgumentResponse]]):
    res = copy.deepcopy(res)
    if not isinstance(args, list):
        args = [args]

    res.responses = res.responses + args
    return res


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

RES__oauth_token = SwaggerFlatResponse(
    description="A temporary JWT token that can be used to authenticate with the server",
    body=EXAMPLE__jwt
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

DOCUMENTATION__oauth_refresh = SwaggerDocumentation(
    tags="OAuth",
    security=True,
    methods=SwaggerMethod(
        name="OAuth Refresh Token",
        description="Refresh your token",
        method=REST__POST,
        response=RES__oauth_token
    )
)
