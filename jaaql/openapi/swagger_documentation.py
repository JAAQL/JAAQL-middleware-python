from typing import List, Optional, Union, Any, TypeVar
from types import ModuleType
from jaaql.exceptions.http_status_exception import *
from jaaql.constants import EXAMPLE__jwt
from monitor.main import HEADER__security
import os
import shutil
import yaml as yaml_utils
import json
from jaaql.utilities.utils import get_jaaql_root
from jaaql.constants import VERSION

ERR__empty_example_list = "Empty examples list for argument '%s'"
ERR__null_example = "No examples found for argument '%s'"
ERR__example_type = "Found type '%s' for example #%d, argument '%s'. Doesn't match type '%s'"
ERR__response_type = "Flat response with http code #%d, argument '%s'. Doesn't match type '%s'"
ERR__duplicated_response_exception_code = "HTTP response error code #%d was duplicated"
ERR__duplicated_argument_response_name = "Field '%s' was duplicated in the argument or response"
ERR__duplicated_example = "Example was duplicated for '%s'"
ERR__duplicated_method = "HTTP method '%s' was duplicated"
ERR__condition_not_needed = "Condition supplied for '%s' but is argument is required. Please remove condition"
ERR__condition_needed = "Condition not supplied for '%s' but is argument is not required. Please supply condition"
ERR__documentation_variable_expected = "Expected '%s' variable in documentation module '%s'"
ERR__empty_path = "Empty path for documentation. Variable unused or documentation occuring before controller import"
ERR__nested_not_allowed = "Nested objects are not allowed in method arguments. Please place in the body"
ERR__list_not_allowed = "Lists now allowed in method arguments. Please place in the body"
ERR__delete_not_allowed_body = "HTTP method delete isn't allowed a body. Please use the arguments parameter instead"
ERR__get_not_allowed_body = "HTTP method get isn't allowed a body. Please use the arguments parameter instead"

TYPE__example = Union[List[Any], Any]

T = TypeVar('T')

ATTR__description = "DESCRIPTION"
ATTR__title = "TITLE"
ATTR__output = "OUTPUT"
ATTR__version = "VERSION"
ATTR__filename = "FILENAME"

PATH__empty = ""

VERSION__open_api = "3.0.3"

CONTENT_TYPE__json = "application/json"  # This isn't a python constant so it is defined here

TYPE__string = "string"

OPEN_API__typemap = {
    bool: "boolean",
    float: "number",
    int: "integer",
    str: TYPE__string
}

OPEN_API__array = "array"
OPEN_API__content = "content"
OPEN_API__description = "description"
OPEN_API__example = "example"
OPEN_API__in = "in"
OPEN_API__in_header = "header"
OPEN_API__in_path = "path"
OPEN_API__in_query = "query"
OPEN_API__info = "info"
OPEN_API__items = "items"
OPEN_API__name = "name"
OPEN_API__object = "object"
OPEN_API__openapi = "openapi"
OPEN_API__parameters = "parameters"
OPEN_API__paths = "paths"
FLASK__path_var_open = "<"
FLASK__path_var_close = ">"
OPEN_API__path_var_open = "{"
OPEN_API__path_var_close = "}"
OPEN_API__properties = "properties"
OPEN_API__request_body = "requestBody"
OPEN_API__required = "required"
OPEN_API__responses = "responses"
OPEN_API__schema = "schema"
OPEN_API__servers = "servers"
OPEN_API__spacer = "  "
OPEN_API__summary = "summary"
OPEN_API__tags = "tags"
OPEN_API__title = "title"
OPEN_API__type = "type"
OPEN_API__url = "url"
OPEN_API__version = "version"

YAML__array_close = "]"
YAML__array_open = "["
YAML__array_separator = ", "
YAML__double_quote = '"'
YAML__quote = "'"
YAML__list_separator = "- "
YAML__new_line = '\n'
YAML__separator = ":"

DIR__swagger = "swagger"
DIR__apps = "apps"
DIR__scripts = "scripts"
FILE__swagger_template = "swagger_template.html"
EXTENSION__html = ".html"
EXTENSION__json = ".json"
EXTENSION__yaml = ".yaml"

RESPONSE__OK = "OK"
RESPONSE__200_ok = "200 OK"

REST__DELETE = "DELETE"
REST__GET = "GET"
REST__OPTIONS = "OPTIONS"
REST__POST = "POST"
REST__PUT = "PUT"

TEMPLATE__url = "url: '%s'"
TEMPLATE__spec = "spec: "

DESCRIPTION__security = "A JWT token fetched from /oauth/token"

DOCUMENTATION__allow_all = "ALLOW_ALL"  # Set as the name to allow all input/output


def isinstance_union(arg, check: Union) -> bool:
    return any([isinstance(arg, cls) for cls in check.__args__])


def force_list(potential_list: Union[List[T], T]) -> List[T]:
    return potential_list if isinstance(potential_list, list) else ([] if potential_list is None else [potential_list])


class SwaggerException(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)


class SwaggerResponseException:

    def __init__(self, code: HTTPStatus = RESP__default_err_code, message: str = RESP__default_err_message):
        self.code = code
        self.message = message


TYPE__exceptions = Optional[Union[List[SwaggerResponseException], SwaggerResponseException]]


class SwaggerSimpleList:

    def __init__(self, arg_type: type, description: str, example: Optional[TYPE__example] = None,
                 required: bool = True, condition: str = None):
        self.arg_type = arg_type
        self.description = description
        self.example = example
        self.required = required
        self.condition = condition

        if not required and condition is None:
            raise SwaggerException(ERR__condition_needed % "simple list")

        self._validate_example(arg_type, self.example)

    @staticmethod
    def _validate_example(arg_type: type, example: Optional[TYPE__example] = None):
        if example is None:
            raise SwaggerException(ERR__null_example % "simple list")
        if len(example) == 0:
            raise SwaggerException(ERR__empty_example_list % "simple list")

        for ex, ex_id in zip(example, range(len(example))):
            if not isinstance(ex, arg_type):
                raise SwaggerException(ERR__example_type % (str(type(ex)), ex_id + 1, "simple list", str(arg_type)))

        if len(example) != len(set(example)):
            raise SwaggerException(ERR__duplicated_example % "simple list")


class SwaggerArgumentResponse:

    def __init__(self, name: str, description: str,
                 arg_type: Union[type, List['SwaggerArgumentResponse'], 'SwaggerList', SwaggerSimpleList],
                 example: Optional[TYPE__example] = None, required: bool = True, condition: str = None,
                 local_only: bool = False, strip: bool = True, lower: bool = False):
        self.name = name
        self.description = description
        if arg_type == bool and example is None:
            example = [True, False]
        self.example = force_list(example)
        self.required = required
        self.arg_type = arg_type
        self.condition = condition
        self.local_only = local_only
        self.strip = strip
        self.lower = lower

        if not required and condition is None and name != DOCUMENTATION__allow_all:
            raise SwaggerException(ERR__condition_needed % name)
        if required and condition is not None:
            raise SwaggerException(ERR__condition_not_needed % name)

        arg_type_sub_list = isinstance(arg_type, list)
        if arg_type_sub_list:
            arg_type_sub_list = all([isinstance(x, SwaggerArgumentResponse) for x in arg_type])

        if not arg_type_sub_list and not isinstance_union(arg_type, TYPE__swagger_list_like) and not self.is_arg_all():
            self._validate_example(name, arg_type, self.example)

    @staticmethod
    def _validate_example(name: str, arg_type: type, example: Optional[TYPE__example] = None):
        if example is None:
            raise SwaggerException(ERR__null_example % name)
        if len(example) == 0:
            raise SwaggerException(ERR__empty_example_list % name)

        for ex, ex_id in zip(example, range(len(example))):
            if not isinstance(ex, arg_type):
                raise SwaggerException(ERR__example_type % (str(type(ex)), ex_id + 1, name, str(arg_type)))

        if len(example) != len(set(example)):
            raise SwaggerException(ERR__duplicated_example % name)

    def is_arg_all(self):
        if isinstance(self.arg_type, SwaggerArgumentResponse):
            if self.arg_type.name == DOCUMENTATION__allow_all:
                return True
        return self.name == DOCUMENTATION__allow_all


class SwaggerList:

    def __init__(self, *args: Union[SwaggerArgumentResponse, 'SwaggerList']):
        self.responses = list(args)


TYPE__swagger_list_like = Union[SwaggerSimpleList, SwaggerList]

ARG_RESP__allow_all = SwaggerArgumentResponse(DOCUMENTATION__allow_all, DOCUMENTATION__allow_all, str)
BODY__file = "JAAQL_IS_FILE"

TYPE__argument_response = Optional[Union[List[SwaggerArgumentResponse], SwaggerArgumentResponse, SwaggerList,
                                         SwaggerSimpleList]]
TYPE__flat_argument_response = Optional[Union[List[SwaggerArgumentResponse], SwaggerArgumentResponse]]
TYPE__listed_argument_response = Union[List[SwaggerArgumentResponse], SwaggerList, SwaggerSimpleList]


def validate_argument_responses(arg_responses: TYPE__argument_response):
    if isinstance(arg_responses, SwaggerList):
        arg_responses = arg_responses.responses

    if arg_responses is not None and isinstance(arg_responses, list):
        found_names = []
        for arg_resp in arg_responses:
            if isinstance(arg_resp, SwaggerList):
                validate_argument_responses(arg_resp.responses)
            else:
                try:
                    is_list = isinstance(arg_resp.arg_type, SwaggerList)
                    is_resp = isinstance(arg_resp.arg_type, SwaggerArgumentResponse)
                    is_resp_list = isinstance(arg_resp.arg_type, List)
                    if is_list or is_resp or is_resp_list:
                        validate_argument_responses(arg_resp.arg_type)

                    if arg_resp.name in found_names:
                        raise SwaggerException(ERR__duplicated_argument_response_name % arg_resp.name)
                    found_names.append(arg_resp.name)
                except:
                    pass


class SwaggerFlatResponse:

    def __init__(self, description: str = "HTTP OK", code: Union[HTTPStatus, int] = HTTPStatus.OK, resp_type: type = str,
                 body: str = RESPONSE__OK):
        self.code = code
        self.description = description
        self.body = body
        self.resp_type = resp_type

        if not isinstance(body, resp_type):
            raise SwaggerException(ERR__response_type % (code, str(resp_type)))


MOCK__description = ""


class SwaggerResponse:

    def __init__(self, description: str, code: HTTPStatus = HTTPStatus.OK, response: TYPE__argument_response = None,
                 error_on_unexpected_field: bool = False):
        self.code = code
        self.description = description
        self.error_on_unexpected_field = error_on_unexpected_field

        validate_argument_responses(response)

        self.responses = response if isinstance_union(response, TYPE__swagger_list_like) else force_list(response)


RES__allow_all = SwaggerResponse(
    description="Allows all",
    response=ARG_RESP__allow_all
)

TYPE__response = Union[SwaggerFlatResponse, SwaggerResponse]
TYPE__responses = Optional[Union[TYPE__response, List[TYPE__response]]]


class SwaggerMethod:

    def __init__(self, name: str, description: str, method: str, arguments: TYPE__flat_argument_response = None,
                 body: TYPE__argument_response = None, response: TYPE__responses = None,
                 exceptions: TYPE__exceptions = None, parallel_verification: bool = False):
        self._validate_exceptions(exceptions)
        self._validate_responses(response)
        validate_argument_responses(arguments)
        validate_argument_responses(body)

        self.name = name
        self.description = description
        self.method = method
        self.parallel_verification = parallel_verification

        self.responses = response if isinstance_union(response, TYPE__swagger_list_like) else force_list(response)
        self.arguments = force_list(arguments)
        self._validate_arguments(arguments)
        self.body = force_list(body)
        self.exceptions = force_list(exceptions)

        found_500 = any([_http_status_to_integer(ex.code) == RESP__default_err_code for ex in self.exceptions])
        if not found_500:
            self.exceptions.append(SwaggerResponseException())

        if self.method == REST__DELETE and len(self.body) != 0:
            raise Exception(ERR__delete_not_allowed_body)

        if self.method == REST__GET and len(self.body) != 0:
            raise Exception(ERR__get_not_allowed_body)

    @staticmethod
    def _validate_exceptions(exceptions: TYPE__exceptions):
        if exceptions is not None and isinstance(exceptions, list):
            found_codes = []
            for ex in exceptions:
                if _http_status_to_integer(ex.code) in found_codes:
                    raise SwaggerException(ERR__duplicated_response_exception_code % ex.code)
                found_codes.append(_http_status_to_integer(ex.code))

    @staticmethod
    def _validate_responses(responses: TYPE__responses):
        if responses is not None and isinstance(responses, list):
            found_codes = []
            for ex in responses:
                if _http_status_to_integer(ex.code) in found_codes:
                    raise SwaggerException(ERR__duplicated_response_exception_code % _http_status_to_integer(ex.code))
                found_codes.append(_http_status_to_integer(ex.code))

    @staticmethod
    def _validate_arguments(arguments: List[Union[SwaggerArgumentResponse, SwaggerList]]):
        arguments = force_list(arguments)
        for arg in arguments:
            if isinstance(arg.arg_type, SwaggerArgumentResponse) and arg.arg_type != ARG_RESP__allow_all:
                raise Exception(ERR__nested_not_allowed)
            elif isinstance(arg, SwaggerList):
                raise Exception(ERR__list_not_allowed)


TYPE__swagger_method = Union[List[SwaggerMethod], SwaggerMethod]


class SwaggerDocumentation:

    def __init__(self, methods: TYPE__swagger_method, tags: str = None, security: bool = True):
        self._validate_methods(methods)
        self.methods = force_list(methods)
        self.security = security
        self.path: str = PATH__empty  # Attached later to the method
        self.tags = tags

    @staticmethod
    def _validate_methods(methods: TYPE__swagger_method):
        if isinstance(methods, list):
            found_methods = []
            for method in methods:
                if method.method in found_methods:
                    raise SwaggerException(ERR__duplicated_method % method.method)
                found_methods.append(method)


def _gen_yaml_indent(indent: int) -> str:
    return ''.join(indent * [OPEN_API__spacer])


def _build_yaml(yaml: str, indent: int, attr: str, value: Union[str, List[str]] = "") -> str:
    line = _gen_yaml_indent(indent)
    if value != "" and not isinstance(value, list):
        value = " " + str(value)
    line = line + attr + YAML__separator

    if not isinstance(value, list):
        line = line + str(value) + YAML__new_line
    else:
        line += YAML__new_line
        list_indent = ''.join((indent + 1) * [OPEN_API__spacer])
        for itm in value:
            line = line + list_indent + YAML__list_separator + itm + YAML__new_line

    return yaml + line


def _http_status_to_integer(code: HTTPStatus) -> int:
    if isinstance(code, int):
        return code
    else:
        return code.value


def _insert_yaml_line(yaml: str) -> str:
    return yaml + YAML__new_line


def _to_openapi_type(python_type: type) -> str:
    if isinstance(python_type, list):
        return OPEN_API__object
    elif isinstance(python_type, SwaggerList):
        return OPEN_API__array
    elif isinstance(python_type, SwaggerArgumentResponse):
        return OPEN_API__object
    else:
        return OPEN_API__typemap[python_type]  # Lint issue PYC


def _generate_examples(yaml: str, depth: int, response: TYPE__listed_argument_response, is_prod: bool) -> str:
    if isinstance(response, SwaggerList):
        yaml = yaml + _gen_yaml_indent(depth) + YAML__list_separator + YAML__new_line
        response = response.responses
        depth += 1
    elif isinstance(response, SwaggerSimpleList):
        yaml = _build_yaml(yaml, depth, OPEN_API__example, response.example)
        return yaml

    for response_property in response:
        if isinstance(response_property, SwaggerList):
            yaml = _generate_examples(yaml, depth + 1, response_property, is_prod)
        else:
            is_complex = isinstance(response_property.arg_type, List)

            if isinstance(response_property, SwaggerArgumentResponse) and response_property.local_only and is_prod:
                continue

            if is_complex or isinstance(response_property.arg_type, SwaggerList):
                yaml = _build_yaml(yaml, depth, response_property.name)
                yaml = _generate_examples(yaml, depth + 1, response_property.arg_type, is_prod)
            elif len(response_property.example) != 0:
                raw_example = response_property.example[0]
                if response_property.arg_type == str:
                    raw_example = YAML__double_quote + str(raw_example) + YAML__double_quote
                yaml = _build_yaml(yaml, depth, response_property.name, raw_example)
            elif response_property.arg_type == ARG_RESP__allow_all:
                yaml = _build_yaml(yaml, depth, response_property.name, "{}")

    return yaml


def _generate_properties(yaml: str, depth: int, response: TYPE__listed_argument_response, is_prod: bool) -> str:
    if isinstance(response, SwaggerList):
        yaml = _build_yaml(yaml, depth, OPEN_API__items)
        response = response.responses
        depth += 1
    elif isinstance(response, SwaggerSimpleList):
        yaml = _build_yaml(yaml, depth, OPEN_API__items)
        yaml = _build_yaml(yaml, depth + 1, OPEN_API__type, _to_openapi_type(response.arg_type))
        return yaml

    required_props = [YAML__double_quote + response_property.name + YAML__double_quote
                      for response_property in response
                      if not isinstance(response_property, SwaggerList) and response_property.required]
    required = YAML__array_separator.join(required_props)

    if len(response) == 0 or not isinstance(response[0], SwaggerList):
        if len(required_props) != 0:
            yaml = _build_yaml(yaml, depth, OPEN_API__required, YAML__array_open + required + YAML__array_close)
        yaml = _build_yaml(yaml, depth, OPEN_API__properties)

    for response_property in response:
        if isinstance(response_property, SwaggerList):
            yaml = _generate_properties(yaml, depth, response_property, is_prod)
        else:
            if isinstance(response_property, SwaggerArgumentResponse) and response_property.local_only and is_prod:
                continue
            yaml = _build_yaml(yaml, depth + 1, response_property.name)
            yaml = _build_yaml(yaml, depth + 2, OPEN_API__description, response_property.description)

            is_complex = isinstance(response_property.arg_type, List) or isinstance(response_property.arg_type,
                                                                                    SwaggerList)

            yaml = _build_yaml(yaml, depth + 2, OPEN_API__type, _to_openapi_type(response_property.arg_type))

            if is_complex:
                yaml = _generate_properties(yaml, depth + 2, response_property.arg_type, is_prod)

    return yaml


def _build_parameter(yaml: str, depth: int, doc: SwaggerDocumentation, arg: SwaggerArgumentResponse,
                     is_prod: bool) -> str:
    if is_prod and arg.local_only:
        return yaml

    path_var = FLASK__path_var_open + arg.name + FLASK__path_var_close
    is_path = path_var in doc.path

    yaml = _build_yaml(yaml, depth, YAML__list_separator + OPEN_API__in,
                       OPEN_API__in_path if is_path else OPEN_API__in_query)
    yaml = _build_yaml(yaml, depth + 1, OPEN_API__name, arg.name)
    yaml = _build_yaml(yaml, depth + 1, OPEN_API__required, str(arg.required))
    if len(arg.example) != 0:
        yaml = _build_yaml(yaml, depth + 1, OPEN_API__example, str(arg.example[0]))
    yaml = _build_yaml(yaml, depth + 1, OPEN_API__description, arg.description)
    yaml = _build_yaml(yaml, depth + 1, OPEN_API__schema)
    yaml = _build_yaml(yaml, depth + 2, OPEN_API__type, _to_openapi_type(arg.arg_type))

    return yaml


def _produce_path(doc: SwaggerDocumentation, yaml: str, is_prod: bool) -> str:
    if doc.path == PATH__empty:
        raise Exception(ERR__empty_path)

    yaml = _build_yaml(yaml, 1, doc.path.replace(FLASK__path_var_open, OPEN_API__path_var_open).replace(FLASK__path_var_close, OPEN_API__path_var_close))

    for method in doc.methods:
        yaml = _build_yaml(yaml, 2, method.method.lower())
        if doc.tags is not None:
            yaml = _build_yaml(yaml, 3, OPEN_API__tags, [doc.tags])
        yaml = _build_yaml(yaml, 3, OPEN_API__summary, method.name)
        if doc.security:
            yaml = _build_yaml(yaml, 3, OPEN_API__parameters)
            yaml = _build_yaml(yaml, 4, YAML__list_separator + OPEN_API__in, OPEN_API__in_header)
            yaml = _build_yaml(yaml, 5, OPEN_API__name, HEADER__security)
            yaml = _build_yaml(yaml, 5, OPEN_API__example, str(EXAMPLE__jwt))
            yaml = _build_yaml(yaml, 5, OPEN_API__description, DESCRIPTION__security)
            yaml = _build_yaml(yaml, 5, OPEN_API__required, str(True))
            yaml = _build_yaml(yaml, 5, OPEN_API__schema)
            yaml = _build_yaml(yaml, 6, OPEN_API__type, TYPE__string)
        if len(method.arguments) != 0:
            if not doc.security:
                yaml = _build_yaml(yaml, 3, OPEN_API__parameters)
            for arg in method.arguments:
                yaml = _build_parameter(yaml, 4, doc, arg, is_prod)
        if isinstance(method.body, SwaggerList) or len(method.body) != 0:
            yaml = _build_yaml(yaml, 3, OPEN_API__request_body)
            yaml = _build_yaml(yaml, 4, OPEN_API__required, str(True))
            yaml = _build_yaml(yaml, 4, OPEN_API__content)
            yaml = _build_yaml(yaml, 5, CONTENT_TYPE__json)
            yaml = _build_yaml(yaml, 7, OPEN_API__schema)
            use_body = method.body
            use_depth = 8
            if isinstance(method.body, SwaggerList):
                yaml = _build_yaml(yaml, 8, OPEN_API__type, OPEN_API__array)
                yaml = _build_yaml(yaml, 8, OPEN_API__example)
                yaml = _generate_examples(yaml, 9, method.body, is_prod)
                yaml = _build_yaml(yaml, 8, OPEN_API__items)
                yaml = _build_yaml(yaml, 9, OPEN_API__type, OPEN_API__object)
                use_body = method.body.responses
                use_depth = 9
            else:
                yaml = _build_yaml(yaml, 8, OPEN_API__type, OPEN_API__object)
                yaml = _build_yaml(yaml, 8, OPEN_API__example)
                yaml = _generate_examples(yaml, 9, method.body, is_prod)
            yaml = _generate_properties(yaml, use_depth, use_body, is_prod)
        yaml = _build_yaml(yaml, 3, OPEN_API__description, method.description)
        yaml = _build_yaml(yaml, 3, OPEN_API__responses)

        if not any([resp.code == HTTPStatus.OK for resp in method.responses]):
            method.responses.append(SwaggerFlatResponse(RESPONSE__200_ok))

        for response in method.responses:
            yaml = _build_yaml(yaml, 4, YAML__quote + str(_http_status_to_integer(response.code)) + YAML__quote)
            yaml = _build_yaml(yaml, 5, OPEN_API__description, response.description)
            yaml = _build_yaml(yaml, 5, OPEN_API__content)
            yaml = _build_yaml(yaml, 6, CONTENT_TYPE__json)
            yaml = _build_yaml(yaml, 7, OPEN_API__schema)
            if isinstance(response, SwaggerFlatResponse):
                yaml = _build_yaml(yaml, 8, OPEN_API__type, _to_openapi_type(response.resp_type))
            if isinstance(response, SwaggerResponse):
                use_response = response.responses
                use_depth = 8
                if isinstance(response.responses, SwaggerList):
                    yaml = _build_yaml(yaml, 8, OPEN_API__type, OPEN_API__array)
                    yaml = _build_yaml(yaml, 8, OPEN_API__example)
                    yaml = _generate_examples(yaml, 9, response.responses, is_prod)
                    yaml = _build_yaml(yaml, 8, OPEN_API__items)
                    if isinstance(response.responses.responses[0], SwaggerList):
                        yaml = _build_yaml(yaml, 9, OPEN_API__type, OPEN_API__array)
                    else:
                        yaml = _build_yaml(yaml, 9, OPEN_API__type, OPEN_API__object)
                    use_depth = 9
                    use_response = response.responses.responses
                elif isinstance(response.responses, SwaggerSimpleList):
                    yaml = _build_yaml(yaml, 8, OPEN_API__type, OPEN_API__array)
                    yaml = _generate_examples(yaml, 8, response.responses, is_prod)
                else:
                    yaml = _build_yaml(yaml, 8, OPEN_API__type, OPEN_API__object)
                    yaml = _build_yaml(yaml, 8, OPEN_API__example)
                    yaml = _generate_examples(yaml, 9, response.responses, is_prod)
                yaml = _generate_properties(yaml, use_depth, use_response, is_prod)
            else:
                yaml = _build_yaml(yaml, 8, OPEN_API__example, str(response.body))

        for exception in method.exceptions:
            yaml = _build_yaml(yaml, 4, YAML__quote + str(_http_status_to_integer(exception.code)) + YAML__quote)
            yaml = _build_yaml(yaml, 5, OPEN_API__description, exception.message)

    return yaml


def _produce_documentation(docs: ModuleType, url: str, base_path: str, is_prod: bool = False):
    title: str
    description: str
    version: str
    filename: str

    try:
        output = bool(getattr(docs, ATTR__output))
        if not output:
            return
    except AttributeError:
        pass  # Assume that output is True when cannot find flag

    try:
        title = str(getattr(docs, ATTR__title))
    except AttributeError:
        raise Exception(ERR__documentation_variable_expected % (ATTR__title, docs.__name__))
    try:
        version = str(getattr(docs, ATTR__version))
    except AttributeError:
        version = VERSION
    try:
        description = str(getattr(docs, ATTR__description))
    except AttributeError:
        raise Exception(ERR__documentation_variable_expected % (ATTR__description, docs.__name__))
    try:
        filename = str(getattr(docs, ATTR__filename))
    except AttributeError:
        raise Exception(ERR__documentation_variable_expected % (ATTR__filename, docs.__name__))

    yaml = _build_yaml("", 0, OPEN_API__openapi, VERSION__open_api)
    yaml = _build_yaml(yaml, 0, OPEN_API__info)
    yaml = _build_yaml(yaml, 1, OPEN_API__title, title)
    yaml = _build_yaml(yaml, 1, OPEN_API__description, description)
    yaml = _build_yaml(yaml, 1, OPEN_API__version, version)
    yaml = _insert_yaml_line(yaml)

    yaml = _build_yaml(yaml, 0, OPEN_API__servers)
    yaml = _build_yaml(yaml, 1, YAML__list_separator + OPEN_API__url, url)
    yaml = _insert_yaml_line(yaml)

    yaml = _build_yaml(yaml, 0, OPEN_API__paths)

    all_docs = [getattr(docs, item) for item in docs.__dict__ if isinstance(getattr(docs, item), SwaggerDocumentation)]

    for documentation in all_docs:
        yaml = _produce_path(documentation, yaml, is_prod)

    swagger_output_file = open(os.path.join(base_path, filename + EXTENSION__yaml), "w")
    swagger_output_file.write(yaml)
    swagger_output_file.close()

    yaml = yaml_utils.safe_load(yaml)

    swagger_template_file = open(os.path.join(get_jaaql_root(), DIR__scripts, FILE__swagger_template), "r")
    swagger_template = swagger_template_file.read()
    swagger_template_file.close()

    template_replace = TEMPLATE__url % (filename + EXTENSION__json) if is_prod else TEMPLATE__spec + json.dumps(yaml)
    swagger_template = swagger_template % (title, template_replace)
    swagger_output_file = open(os.path.join(base_path, filename + EXTENSION__html), "w")
    swagger_output_file.write(swagger_template)
    swagger_output_file.close()
    swagger_json_output_file = open(os.path.join(base_path, filename + EXTENSION__json), "w")
    swagger_json_output_file.write(json.dumps(yaml))
    swagger_json_output_file.close()


def produce_all_documentation(all_docs: List[ModuleType], url: str, is_prod: bool = False, base_path: str = None):
    create_dir = DIR__swagger
    if base_path is not None:
        create_dir = os.path.join(base_path, create_dir)

    if os.path.exists(create_dir):
        shutil.rmtree(create_dir)
    os.makedirs(create_dir)

    for docs in all_docs:
        _produce_documentation(docs, url, create_dir, is_prod)
