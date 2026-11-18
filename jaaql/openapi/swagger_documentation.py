from typing import List, Optional, Union, Any, TypeVar
from types import ModuleType
from jaaql.exceptions.http_status_exception import *
from jaaql.constants import EXAMPLE__jwt
from monitor.main import HEADER__security
import html
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
ERR__form_body_needs_raw_request = "A form body is only allowed on a method whose request goes to the view as it came (raw_request)"
ERR__example_list_among_fields = "A list cannot be documented among other fields (%s) of an example"

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
OPEN_API__summary = "summary"
OPEN_API__tags = "tags"
OPEN_API__title = "title"
OPEN_API__type = "type"
OPEN_API__url = "url"
OPEN_API__version = "version"

# The documentation is built as data and dumped by yaml.safe_dump, so that a text in it is a string of the YAML whatever it holds (': ', '#',
# a leading '-', quotes, a line break), and an example or a flag keeps its type. Never folded, so that a line of the YAML holds a whole text
YAML__width = 1 << 30
ENCODING__documentation = "utf-8"

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
REST__HEAD = "HEAD"
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
                 exceptions: TYPE__exceptions = None, parallel_verification: bool = False, raw_request: bool = False,
                 form_body: bool = False):
        self._validate_exceptions(exceptions)
        self._validate_responses(response)
        validate_argument_responses(arguments)
        validate_argument_responses(body)

        self.name = name
        self.description = description
        self.method = method
        self.parallel_verification = parallel_verification
        # raw_request: the view reads the request's query and body as they came (a webhook's), so neither is merged with the path
        # variables, which are authoritative, nor validated. form_body (with raw_request): the body may also be form-encoded, which is
        # never parsed, besides JSON
        self.raw_request = raw_request
        self.form_body = form_body
        if form_body and not raw_request:
            raise Exception(ERR__form_body_needs_raw_request)

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
                found_methods.append(method.method)


def _http_status_to_integer(code: HTTPStatus) -> int:
    if isinstance(code, int):
        return code
    else:
        return code.value


def _text(value) -> str:
    # A description, a name, a summary: a string of the document, whatever characters it holds
    return str(value)


def _value(value):
    # An example or the body of a flat response: a flag or a number as it is, anything else as its text
    for kind in (bool, int, float):
        if isinstance(value, kind):
            return kind(value)
    return _text(value)


def _or_none(value):
    # An empty mapping or list of the document is none at all, as the hand-built YAML before wrote a key with nothing under it
    return value if value else None


def _to_openapi_type(python_type: type) -> str:
    if isinstance(python_type, list):
        return OPEN_API__object
    elif isinstance(python_type, SwaggerList):
        return OPEN_API__array
    elif isinstance(python_type, SwaggerArgumentResponse):
        return OPEN_API__object
    else:
        return OPEN_API__typemap[python_type]  # Lint issue PYC


def _is_complex(arg_type) -> bool:
    return isinstance(arg_type, List) or isinstance(arg_type, SwaggerList)


def _generate_examples(response: TYPE__listed_argument_response, is_prod: bool):
    """
    The example of a list (one element's example in a list, or a simple list's examples) or of a list of fields (each field's first example
    by its name, the example of a field that is a list or holds fields, {} for one that takes anything; none at all when no field has one)
    """
    if isinstance(response, SwaggerSimpleList):
        return [_value(example) for example in response.example]
    if isinstance(response, SwaggerList):
        return [_generate_examples(response.responses, is_prod)]
    if len(response) != 0 and all(isinstance(response_property, SwaggerList) for response_property in response):
        return [_generate_examples(response_property.responses, is_prod) for response_property in response]

    examples = {}
    for response_property in response:
        if isinstance(response_property, SwaggerList):
            raise SwaggerException(ERR__example_list_among_fields % ", ".join(
                _text(field.name) for field in response if not isinstance(field, SwaggerList)))
        if isinstance(response_property, SwaggerArgumentResponse) and response_property.local_only and is_prod:
            continue

        if _is_complex(response_property.arg_type):
            examples[_text(response_property.name)] = _generate_examples(response_property.arg_type, is_prod)
        elif len(response_property.example) != 0:
            examples[_text(response_property.name)] = _value(response_property.example[0])
        elif response_property.arg_type == ARG_RESP__allow_all:
            examples[_text(response_property.name)] = {}

    return _or_none(examples)


def _generate_properties(response: TYPE__listed_argument_response, is_prod: bool) -> dict:
    """
    What a schema says of a list (its items) or of a list of fields: the names of the required ones, then each one's description and type, a
    field that is a list or holds fields with what its own schema says of them
    """
    if isinstance(response, SwaggerList):
        return {OPEN_API__items: _generate_properties(response.responses, is_prod)}
    elif isinstance(response, SwaggerSimpleList):
        return {OPEN_API__items: {OPEN_API__type: _to_openapi_type(response.arg_type)}}

    schema = {}
    has_properties = len(response) == 0 or not isinstance(response[0], SwaggerList)
    if has_properties:
        required_props = [_text(response_property.name) for response_property in response
                          if not isinstance(response_property, SwaggerList) and response_property.required]
        if len(required_props) != 0:
            schema[OPEN_API__required] = required_props
        schema[OPEN_API__properties] = None

    properties = {}
    for response_property in response:
        if isinstance(response_property, SwaggerList):
            schema.update(_generate_properties(response_property, is_prod))
        else:
            if isinstance(response_property, SwaggerArgumentResponse) and response_property.local_only and is_prod:
                continue
            documented = {
                OPEN_API__description: _text(response_property.description),
                OPEN_API__type: _to_openapi_type(response_property.arg_type)
            }
            if _is_complex(response_property.arg_type):
                documented.update(_generate_properties(response_property.arg_type, is_prod))
            properties[_text(response_property.name)] = documented

    if has_properties or len(properties) != 0:
        schema[OPEN_API__properties] = _or_none(properties)

    return schema


def _build_parameter(doc: SwaggerDocumentation, arg: SwaggerArgumentResponse, is_prod: bool) -> Optional[dict]:
    if is_prod and arg.local_only:
        return None

    path_var = FLASK__path_var_open + arg.name + FLASK__path_var_close
    is_path = path_var in doc.path

    parameter = {
        OPEN_API__in: OPEN_API__in_path if is_path else OPEN_API__in_query,
        OPEN_API__name: _text(arg.name),
        OPEN_API__required: arg.required
    }
    if len(arg.example) != 0:
        parameter[OPEN_API__example] = _value(arg.example[0])
    parameter[OPEN_API__description] = _text(arg.description)
    parameter[OPEN_API__schema] = {OPEN_API__type: _to_openapi_type(arg.arg_type)}

    return parameter


def _object_schema(responses: TYPE__listed_argument_response, is_prod: bool) -> dict:
    # The schema of a body or an answer: an array of a list's elements, an array of a simple list's type, or an object of fields
    if isinstance(responses, SwaggerList):
        items = {OPEN_API__type: OPEN_API__array if isinstance(responses.responses[0], SwaggerList) else OPEN_API__object}
        items.update(_generate_properties(responses.responses, is_prod))
        return {OPEN_API__type: OPEN_API__array, OPEN_API__example: _generate_examples(responses, is_prod), OPEN_API__items: items}
    elif isinstance(responses, SwaggerSimpleList):
        schema = {OPEN_API__type: OPEN_API__array, OPEN_API__example: _generate_examples(responses, is_prod)}
    else:
        schema = {OPEN_API__type: OPEN_API__object, OPEN_API__example: _generate_examples(responses, is_prod)}
    schema.update(_generate_properties(responses, is_prod))
    return schema


def _produce_path(doc: SwaggerDocumentation, is_prod: bool) -> (str, dict):
    """
    The path of the documentation's route as OpenAPI writes it, and what it says of each of the route's methods. A method that declares no
    200 is given one (200 OK) here, which is what the route answers when its view returns nothing (BaseJAAQLController.get_response)
    """
    if doc.path == PATH__empty:
        raise Exception(ERR__empty_path)

    path = doc.path.replace(FLASK__path_var_open, OPEN_API__path_var_open).replace(FLASK__path_var_close, OPEN_API__path_var_close)

    operations = {}
    for method in doc.methods:
        operation = {}
        if doc.tags is not None:
            operation[OPEN_API__tags] = [_text(doc.tags)]
        operation[OPEN_API__summary] = _text(method.name)

        parameters = None
        if doc.security:
            parameters = [{
                OPEN_API__in: OPEN_API__in_header,
                OPEN_API__name: HEADER__security,
                OPEN_API__example: _text(EXAMPLE__jwt),
                OPEN_API__description: DESCRIPTION__security,
                OPEN_API__required: True,
                OPEN_API__schema: {OPEN_API__type: TYPE__string}
            }]
        if len(method.arguments) != 0:
            if not doc.security:
                parameters = []
            for arg in method.arguments:
                parameter = _build_parameter(doc, arg, is_prod)
                if parameter is not None:
                    parameters.append(parameter)
        if parameters is not None:
            operation[OPEN_API__parameters] = _or_none(parameters)

        if isinstance(method.body, SwaggerList) or len(method.body) != 0:
            if isinstance(method.body, SwaggerList):
                schema = {
                    OPEN_API__type: OPEN_API__array,
                    OPEN_API__example: _generate_examples(method.body, is_prod),
                    OPEN_API__items: {OPEN_API__type: OPEN_API__object, **_generate_properties(method.body.responses, is_prod)}
                }
            else:
                schema = {OPEN_API__type: OPEN_API__object, OPEN_API__example: _generate_examples(method.body, is_prod),
                          **_generate_properties(method.body, is_prod)}
            operation[OPEN_API__request_body] = {
                OPEN_API__required: True,
                OPEN_API__content: {CONTENT_TYPE__json: {OPEN_API__schema: schema}}
            }
        operation[OPEN_API__description] = _text(method.description)

        if not any([resp.code == HTTPStatus.OK for resp in method.responses]):
            method.responses.append(SwaggerFlatResponse(RESPONSE__200_ok))

        responses = {}
        for response in method.responses:
            if isinstance(response, SwaggerResponse):
                schema = _object_schema(response.responses, is_prod)
            else:
                schema = {OPEN_API__type: _to_openapi_type(response.resp_type), OPEN_API__example: _value(response.body)}
            responses[str(_http_status_to_integer(response.code))] = {
                OPEN_API__description: _text(response.description),
                OPEN_API__content: {CONTENT_TYPE__json: {OPEN_API__schema: schema}}
            }

        for exception in method.exceptions:
            responses[str(_http_status_to_integer(exception.code))] = {OPEN_API__description: _text(exception.message)}

        operation[OPEN_API__responses] = responses
        operations[method.method.lower()] = operation

    return path, operations


def documentation_of(docs: ModuleType, url: str, is_prod: bool = False) -> Optional[dict]:
    """
    The OpenAPI document of a documentation module (its TITLE, DESCRIPTION, VERSION and every SwaggerDocumentation in it) as data, which
    produce_all_documentation dumps; None for a module whose OUTPUT is False
    """
    title: str
    description: str
    version: str

    try:
        output = bool(getattr(docs, ATTR__output))
        if not output:
            return None
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
    if not hasattr(docs, ATTR__filename):
        raise Exception(ERR__documentation_variable_expected % (ATTR__filename, docs.__name__))

    paths = {}
    all_docs = [getattr(docs, item) for item in docs.__dict__ if isinstance(getattr(docs, item), SwaggerDocumentation)]
    for documentation in all_docs:
        path, operations = _produce_path(documentation, is_prod)
        paths[path] = operations

    return {
        OPEN_API__openapi: VERSION__open_api,
        OPEN_API__info: {
            OPEN_API__title: title,
            OPEN_API__description: description,
            OPEN_API__version: version
        },
        OPEN_API__servers: [{OPEN_API__url: _text(url)}],
        OPEN_API__paths: _or_none(paths)
    }


class _DocumentationDumper(yaml_utils.SafeDumper):
    # Every mapping and list written out where it is, never as an anchor and its aliases
    def ignore_aliases(self, data):
        return True


def dump_documentation(document: dict) -> str:
    # The YAML of a document: block style, in the document's order, every string quoted wherever YAML would read it as anything else
    return yaml_utils.dump(document, Dumper=_DocumentationDumper, sort_keys=False, allow_unicode=True, default_flow_style=False,
                           width=YAML__width)


def _produce_documentation(docs: ModuleType, url: str, base_path: str, is_prod: bool = False):
    document = documentation_of(docs, url, is_prod)
    if document is None:
        return
    title = document[OPEN_API__info][OPEN_API__title]
    filename = str(getattr(docs, ATTR__filename))

    with open(os.path.join(base_path, filename + EXTENSION__yaml), "w", encoding=ENCODING__documentation) as swagger_output_file:
        swagger_output_file.write(dump_documentation(document))

    with open(os.path.join(get_jaaql_root(), DIR__scripts, FILE__swagger_template), "r", encoding=ENCODING__documentation) as swagger_template_file:
        swagger_template = swagger_template_file.read()

    as_json = json.dumps(document)
    # In a <script> of the page: a text holding "</script>" would end it
    template_replace = TEMPLATE__url % (filename + EXTENSION__json) if is_prod else TEMPLATE__spec + as_json.replace("</", "<\\/")
    swagger_template = swagger_template % (html.escape(title), template_replace)
    with open(os.path.join(base_path, filename + EXTENSION__html), "w", encoding=ENCODING__documentation) as swagger_output_file:
        swagger_output_file.write(swagger_template)
    with open(os.path.join(base_path, filename + EXTENSION__json), "w", encoding=ENCODING__documentation) as swagger_json_output_file:
        swagger_json_output_file.write(as_json)


def produce_all_documentation(all_docs: List[ModuleType], url: str, is_prod: bool = False, base_path: str = None):
    create_dir = DIR__swagger
    if base_path is not None:
        create_dir = os.path.join(base_path, create_dir)

    if os.path.exists(create_dir):
        shutil.rmtree(create_dir)
    os.makedirs(create_dir)

    for docs in all_docs:
        _produce_documentation(docs, url, create_dir, is_prod)
