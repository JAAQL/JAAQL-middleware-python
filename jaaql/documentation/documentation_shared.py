from http import HTTPStatus

from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, SwaggerArgumentResponse,\
    SwaggerResponse, SwaggerList, SwaggerFlatResponse, REST__POST, ARG_RESP__allow_all
from jaaql.constants import *
from typing import Union, List

import copy

OUTPUT = False

JWT__invite = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImFhcm9uQGphYXFsLmNvbSJ9.6HcT-BIJEozzy9j8mxMppFpThpMp" \
              "u02crWWx1ZPh8Pw"

ENDPOINT__refresh = "/oauth/refresh"
EXAMPLE__email = "aaron@jaaql.com"

EXAMPLE__db = "meeting"
ARG_RES__database_name = SwaggerArgumentResponse(
    name=KEY__database_name,
    description="The name of the database on the database server",
    arg_type=str,
    example=[EXAMPLE__db],
    required=True
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


def rename_arg(arg_res: SwaggerArgumentResponse, new_name: str, new_description: str = None, new_examples = None):
    return SwaggerArgumentResponse(
        new_name,
        arg_res.description if new_description is None else new_description,
        arg_res.arg_type,
        arg_res.example if new_examples is None else new_examples,
        arg_res.required,
        arg_res.condition
    )


def set_required(arg_res: SwaggerArgumentResponse, new_name: str = None):
    return SwaggerArgumentResponse(
        arg_res.name if new_name is None else new_name,
        arg_res.description,
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


ARG_RES__jaaql_password = SwaggerArgumentResponse(
    name=KEY__password,
    description="JAAQL login password",
    arg_type=str,
    example=["pa55word", "p@ssword"],
    required=True
)

ARG_RES__email = SwaggerArgumentResponse(
    name=KEY__email,
    description="The email of the user",
    arg_type=str,
    example=["aaron@jaaql.com", "graham@jaaql.com"],
    required=True,
)

ARG_RES__totp_mfa = [
    SwaggerArgumentResponse(
        name=KEY__otp_uri,
        description="OTP URI",
        arg_type=str,
        example=["otpauth://totp/%test?secret=supersecret&issuer=JAAQL",
                 "otpauth://totp/%mylabel?secret=pa55word&issuer=MyIssuer"],
        required=True
    ),
    SwaggerArgumentResponse(
        name=KEY__otp_qr,
        description="OTP QR code, as a inlined base64 encoded png image",
        arg_type=str,
        example=["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKsAAADV...",
                 "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..."],
        required=True
    )
]
RES__totp_mfa = SwaggerResponse(
    description="Contains information to setup authenticator app",
    response=ARG_RES__totp_mfa
)
RES__totp_mfa_nullable = SwaggerResponse(
    description="Contains information to setup authenticator app",
    response=set_nullable(ARG_RES__totp_mfa, ["Is mfa forced on"] * len(ARG_RES__totp_mfa))
)


def combine_response(res: SwaggerResponse, args: Union[SwaggerArgumentResponse, List[SwaggerArgumentResponse]]):
    res = copy.deepcopy(res)
    if not isinstance(args, list):
        args = [args]

    res.responses = res.responses + args
    return res


RES__oauth_token = SwaggerFlatResponse(
    description="A temporary JWT token that can be used to authenticate with the server",
    body=EXAMPLE__jwt
)

DESC__expecting_mfa_key = "A temporary JWT token that can be submitted to the server along with an MFA key for full "\
                          "access"

RES__expecting_mfa_key = SwaggerFlatResponse(
    description=DESC__expecting_mfa_key,
    body=EXAMPLE__jwt,
    code=HTTPStatus.ACCEPTED
)

EXAMPLE__occurred = "2021-08-07 19:05:07.763189+01:00"
ARG_RES__occurred = SwaggerArgumentResponse(
    name="occurred",
    description="When this event occurred",
    arg_type=str,
    example=[EXAMPLE__occurred, "2021-08-07 18:04:41.156935+01:00"],
    required=True
)

ARG_RES__expecting_mfa_key = SwaggerArgumentResponse(
    name=KEY__pre_auth_key,
    description=DESC__expecting_mfa_key,
    arg_type=str,
    example=[EXAMPLE__jwt],
    required=False,
    condition="Is during the first round of authentication"
)

ARG_RES__mfa_key = SwaggerArgumentResponse(
    name=KEY__mfa_key,
    description="6-digit Multi Factor Authentication key, generated by google authenticator or similar",
    arg_type=str,
    example=["571208", "222104"],
    required=False,
    condition="MFA is turned on"
)

ARG_RES__parameters = SwaggerArgumentResponse(
    name=KEY__parameters,
    description="Nonspecific data which is supplied as an object either for email or signup. Is validated",
    arg_type=ARG_RESP__allow_all,
    required=False,
    condition="Is signup data provided"
)

EXAMPLE__email_template_name = "signup"
ARG_RES__email_template_name = SwaggerArgumentResponse(
    name=KEY__email_template_name,
    description="Internal template name",
    arg_type=str,
    example=[EXAMPLE__email_template_name]
)
ARG_RES__email_template = rename_arg(ARG_RES__email_template_name, KEY__email_template)
ARG_RES__already_signed_up_email_template = rename_arg(ARG_RES__email_template_name, KEY__already_signed_up_email_template)

EXAMPLE__application_name = "Library Browser"
EXAMPLE__application_url = "https://jaaql.com/demos/library-application"

ARG_RES__application_name = SwaggerArgumentResponse(
    name=KEY__application_name,
    description="Application name",
    arg_type=str,
    example=[EXAMPLE__application_name, "Meeting Room Scheduling Assistant"],
    required=True
)
ARG_RES__application = rename_arg(ARG_RES__application_name, KEY__application)
ARG_RES__application_description = SwaggerArgumentResponse(
    name="description",
    description="Application description",
    arg_type=str,
    example=["Browses books in the library", "Helps book meetings"],
    required=True
)
ARG_RES__application_uri = SwaggerArgumentResponse(
    name=KEY__application_url,
    description="Application url. Please use '{{DEFAULT}}/myappurl' if you want to host it in the same place as jaaql. "
    "For example '{{DEFAULT}}/console' would be the URL for the console",
    arg_type=str,
    example=[EXAMPLE__application_url, "https://jaaql.com/demos/meeting-application"],
    required=True
)
EXAMPLE__application_dataset = "library"
ARG_RES__dataset_name = SwaggerArgumentResponse(
    name=KEY__dataset_name,
    description="The name of the dataset",
    arg_type=str,
    example=[EXAMPLE__application_dataset, "meeting"],
    required=True
)
ARG_RES__dataset_description = SwaggerArgumentResponse(
    name="description",
    description="The dataset description",
    arg_type=str,
    example=["The library book dataset", "The meeting room spaces dataset"],
    required=True
)
ARG_RES__reference_dataset = rename_arg(ARG_RES__dataset_name, KEY__dataset)

ARG_RES__application_body = [ARG_RES__application_name, ARG_RES__application_description, ARG_RES__application_uri]

CONDITION__pre_auth = "Is during 1st stage authentication"

ARG_RES__username = SwaggerArgumentResponse(
    name=KEY__username,
    description="JAAQL login username",
    arg_type=str,
    example=["jaaql", "aaron@jaaql.com"]
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
            set_nullable(ARG_RES__username, CONDITION__pre_auth),
            set_nullable(ARG_RES__jaaql_password, CONDITION__pre_auth),
            ARG_RES__mfa_key,
            ARG_RES__expecting_mfa_key
        ],
        response=[
            RES__oauth_token,
            RES__expecting_mfa_key
        ]
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
