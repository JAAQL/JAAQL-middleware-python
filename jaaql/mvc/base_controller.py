import traceback
from werkzeug.datastructures import Headers
import uuid
from functools import wraps

import typing as t
from werkzeug.exceptions import InternalServerError, HTTPException, MethodNotAllowed, BadRequest, ClientDisconnected
from werkzeug.routing import Rule
import inspect
import json

try:
    import orjson
except ImportError:
    orjson = None
from datetime import datetime, date, time
from jaaql.exceptions.custom_http_status import CustomHTTPStatus
from jaaql.exceptions.jaaql_interpretable_handled_errors import UnhandledJaaqlServerError, NotYetInstalled, client_error
import dataclasses
import decimal
from queue import Queue
from jaaql.utilities.utils_no_project_imports import get_cookie_attrs, COOKIE_JAAQL_AUTH, COOKIE_LOGIN_MARKER, COOKIE_ATTR_PATH
from jaaql.utilities.utils import time_delta_ms, Profiler
from jaaql.utilities import sentinel, slow_queries, server_errors
from flask import Response, Flask, request, jsonify, current_app, has_request_context
from flask.json.provider import DefaultJSONProvider
from jaaql.constants import *
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.response import *
from typing import Union
from jaaql.db.db_utils import create_interface_for_db
from monitor.main import HEADER__security, HEADER__security_bypass_jaaql, HEADER__security_bypass, HEADER__security_specify_user

from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, TYPE__response, \
    SwaggerFlatResponse, REST__DELETE, REST__GET, REST__HEAD, REST__OPTIONS, REST__POST, REST__PUT, SwaggerList, SwaggerResponse, \
    MOCK__description, ARG_RESP__allow_all, RES__allow_all, SwaggerArgumentResponse, SwaggerSimpleList
from jaaql.exceptions.http_status_exception import *

ARG__http_inputs = "http_inputs"
ARG__account_id = "account_id"
ARG__ip_address = "ip_address"
ARG__request_headers = "request_headers"
ARG__response = "response"
ARG__username = "username"
ARG__profiler = "profiler"
ARG__headers = "headers"
ARG__body = "body"
ARG__args = "args"
ARG__flask_request = "flask_request"
ARG__auth_token = "auth_token"
ARG__auth_token_for_refresh = "auth_token_for_refresh"
ARG__connection = "connection"
ARG__is_the_anonymous_user = "is_the_anonymous_user"
ARG__verification_hook = "verification_hook"
ARG_START__connection = "connection__"
ARG_START__jaaql_connection = "jaaql_" + ARG_START__connection

CONTENT__encoding = "charset=utf-8"
CONTENT__json = "application/json"
CONTENT__form = "application/x-www-form-urlencoded"
CONTENT__text = "text/plain"
HEADER__content_type_options = "X-Content-Type-Options"

CORS__WILDCARD = "*"

ERR__argument_wrong_type = "Argument '%s' is of type '%s' but should be of type '%s'"
ERR__duplicated_field = "Field duplicated in request"
ERR__duplicated_route_method = "HTTP method '%s' is declared twice for the route '%s'"
ERR__expected_argument = "Expected argument '%s'"
ERR__expected_json = "Expected content-type " + CONTENT__json
ERR__expected_json_object = "Expected the request body to be a JSON object, not %s"
ERR__body_not_json = "Expected the request body to be JSON, which it is not (%s)"
JSON_ERROR__max_length = 200
ERR__item_wrong_type = "Item %d of argument '%s' is of type '%s' but should be an object"
ERR__expected_response_dict = "Expected response to be a dictionary type"
ERR__expected_response_list = "Expected response to be a array type"
ERR__expected_response_flat_type = "Expected response to be a flat type"
ERR__expected_response_field = "Expected response field '%s'"
ERR__expected_utf8 = "Please use UTF-8 encoding"
ERR__req_method_resp = "Please set the method response in the documentation if the model returns nothing"
ERR__response_wrong_type = "Response field '%s' is of type '%s' but should be of type '%s'"
ERR__unexpected_argument = "Unexpected argument '%s'"
ERR__unexpected_request_body = "Unexpected request body"
ERR__unexpected_response_code = "Response with code '%d' was not expected"
ERR__unexpected_response_field = "Unexpected response field '%s'"
ERR__method_required_security = "Method requires connection input yet marked as not secure in documentation"
ERR__method_required_token = "Method requires oauth token input yet marked as not secure in documentation"
ERR__method_required_connection = "Method requires connection input yet marked as not secure in documentation"
ERR__method_required_is_the_anonymous_user = "Method requires is_public input yet marked as not secure in documentation"
ERR__method_required_account_id = "Method requires account id input yet marked as not secure in documentation"
ERR__method_required_user_connection = "Method requires user connection input yet marked as not secure in documentation"
ERR__method_required_username = "Method requires username yet marked as not secure in documentation"

FLASK__json_sort_keys = "JSON_SORT_KEYS"
FLASK__max_content_length = "MAX_CONTENT_LENGTH"

HEADER__allow_headers = "Access-Control-Allow-Headers"
HEADER__allow_origin = "Access-Control-Allow-Origin"
HEADER__allow_methods = "Access-Control-Allow-Methods"
HEADER__real_ip = "X-Real-IP"
HEADER__user_agent = "User-Agent"

BOOL__allowed = {
    "True": True,
    "False": False,
    "true": True,
    "false": False
}


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, date):
        return obj.isoformat()

    if isinstance(obj, datetime):
        return obj.isoformat().split(".")[0]

    if isinstance(obj, (decimal.Decimal, uuid.UUID)):
        return str(obj)

    if dataclasses and dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)

    if isinstance(obj, time):
        return obj.isoformat()

    if hasattr(obj, "__html__"):
        return str(obj.__html__())

    print(f"Object of type {type(obj).__name__} is not JSON serializable")

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class JAAQLJSONProvider(DefaultJSONProvider):
    default: t.Callable[[t.Any], t.Any] = staticmethod(
        json_serial
    )  # type: ignore[assignment]

    # Flask removed the JSON_SORT_KEYS config in 2.3, so the app-level setting of it below no
    # longer has any effect; the provider attribute is what controls sorting now. Sorting is both
    # unwanted (per that config) and slower, and orjson does not sort either
    sort_keys = False

    if orjson is not None:
        # OPT_PASSTHROUGH_DATETIME routes datetime/date/time through json_serial so the wire format
        # (e.g. microseconds stripped from datetimes) stays identical to the stdlib provider.
        # orjson natively serializes UUIDs and dataclasses to the same output json_serial produces;
        # Decimal is not natively supported so it still reaches json_serial via default=.
        _ORJSON_OPTS = orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_NON_STR_KEYS

        def dumps(self, obj: t.Any, **kwargs: t.Any) -> str:
            opts = self._ORJSON_OPTS
            if kwargs.get("indent"):
                opts |= orjson.OPT_INDENT_2
            return orjson.dumps(obj, default=json_serial, option=opts).decode("utf-8")

        def loads(self, s: t.Union[str, bytes], **kwargs: t.Any) -> t.Any:
            return orjson.loads(s)


class JAAQLRule(Rule):
    """
    The rule of a route. werkzeug gives every rule that takes GET HEAD too; the rule of a route published with answers_head False, whose GET
    acts, is left without it, so that Flask's router answers a HEAD to the route 405 before any of JAAQL's code runs, and Flask's own answer
    to OPTIONS does not name HEAD among the methods the route takes. error_body False: the route's client errors are answered as they always
    were (plain text, werkzeug's HTML) rather than with JAAQL's error body (BaseJAAQLController.answers_with_error_body). answers_head and
    error_body are keywords only: werkzeug's own arguments, by position (defaults, subdomain, methods, ...) or by keyword, are werkzeug's
    """

    def __init__(self, string: str, *args, answers_head: bool = True, error_body: bool = True, **kwargs):
        super().__init__(string, *args, **kwargs)
        self.answers_head = answers_head
        self.error_body = error_body
        if not answers_head and self.methods is not None:
            self.methods.discard(REST__HEAD)

    def get_empty_kwargs(self) -> t.Mapping[str, t.Any]:
        return dict(super().get_empty_kwargs(), answers_head=self.answers_head, error_body=self.error_body)


class BaseJAAQLController:

    internal_sentinel = False
    base_url = None

    def __init__(self, model: JAAQLModel, is_prod: bool, base_url: str, do_profiling: bool = False):
        super().__init__()
        BaseJAAQLController.base_url = base_url
        self.app = Flask(__name__, instance_relative_config=True)
        self.app.url_rule_class = JAAQLRule
        self.json_serializer = JAAQLJSONProvider(self.app)
        self.app.config[FLASK__json_sort_keys] = False
        self.app.config[FLASK__max_content_length] = 1024 * 1024 * 2  # 2 MB
        self._init_error_handlers(self.app)
        self.model = model
        self.do_profiling = do_profiling
        self.documentation_memory = {}
        self.profiling_request_ids = {}
        self.app.model = model
        self.is_prod = is_prod
        # Reports reach Sentinel through one sender per process, started by the first report (jaaql/utilities/sentinel.py)
        BaseJAAQLController.internal_sentinel = sentinel.configure(os.environ.get(ENVIRON__sentinel_url), base_url)
        slow_queries.configure(getattr(model, "url", None), getattr(model, "is_container", False))
        # A server error of a request that names no application is filed under the application this box serves
        server_errors.configure(lambda: (getattr(model, "query_caches", None) or {}).get("application"))

    def diff_ms(self, start, now):
        return round((now - start).total_seconds() * 1000)

    @staticmethod
    def enforce_content_type_json():
        if request.content_type is None or request.content_type.split(";")[0] != CONTENT__json:
            raise HttpStatusException(ERR__expected_json, HTTPStatus.BAD_REQUEST)
        if len(request.content_type.split(";")) > 1:
            if request.content_type.split(";")[1].strip().lower() != CONTENT__encoding:
                raise HttpStatusException(ERR__expected_utf8, HTTPStatus.BAD_REQUEST)

    @staticmethod
    def validate_data_rec(arguments: [SwaggerArgumentResponse], data: dict, is_prod: bool, fill_missing: bool = True):
        for arg in arguments:
            if arg.required is True and arg.name not in data:
                if arg.local_only and is_prod:
                    if fill_missing:
                        data[arg.name] = None
                    continue
                raise HttpStatusException(ERR__expected_argument % arg.name, HTTPStatus.BAD_REQUEST)

            if isinstance(arg.arg_type, SwaggerList) and arg.name in data:
                if not isinstance(data[arg.name], list):
                    raise HttpStatusException(ERR__argument_wrong_type % (arg.name, type(data[arg.name]).__name__,
                                                                          list.__name__), HTTPStatus.BAD_REQUEST)
                for idx, itm in enumerate(data[arg.name]):
                    if not isinstance(itm, dict):
                        raise HttpStatusException(ERR__item_wrong_type % (idx, arg.name, type(itm).__name__), HTTPStatus.BAD_REQUEST)
                    BaseJAAQLController.validate_data_rec(arg.arg_type.responses, itm, is_prod, fill_missing)
            elif arg.name in data and arg.arg_type == ARG_RESP__allow_all:
                continue
            elif arg.name in data and (not isinstance(data[arg.name], arg.arg_type) or
                                       # JSON's true and false, which Python takes for numbers
                                       (isinstance(data[arg.name], bool) and arg.arg_type in (int, float))):
                if data[arg.name] is None and not arg.required:
                    continue
                was_err = True
                # Only a text (of the query or a form) is read as the number or the flag it spells; a value of any other type is of the
                # wrong type, a list or an object as much as a null where a value is required
                if isinstance(data[arg.name], str):
                    if arg.arg_type == int:
                        try:
                            test = int(data[arg.name])
                            if str(test) == data[arg.name]:
                                was_err = False
                                data[arg.name] = test
                        except ValueError:
                            pass
                    elif arg.arg_type == float:
                        try:
                            test = float(data[arg.name])
                            if str(test) == data[arg.name]:
                                was_err = False
                                data[arg.name] = test
                        except ValueError:
                            pass
                    elif arg.arg_type == bool:
                        if data[arg.name] in BOOL__allowed:
                            was_err = False
                            data[arg.name] = BOOL__allowed[data[arg.name]]

                if was_err:
                    raise HttpStatusException(ERR__argument_wrong_type % (arg.name, type(data[arg.name]).__name__,
                                                                          arg.arg_type.__name__), HTTPStatus.BAD_REQUEST)
            elif arg.name not in data and fill_missing:
                data[arg.name] = None
            elif arg.arg_type == str and arg.name in data and data[arg.name] is not None:
                if arg.strip:
                    data[arg.name] = data[arg.name].strip()
                if arg.lower:
                    data[arg.name] = data[arg.name].lower()

        for key, _ in data.items():
            found = any([arg.name == key or arg.arg_type == ARG_RESP__allow_all for arg in arguments])
            if not found:
                raise HttpStatusException(ERR__unexpected_argument % key, HTTPStatus.BAD_REQUEST)

    @staticmethod
    def validate_data(method: SwaggerMethod, data: dict, is_prod: bool = False, fill_missing: bool = True):
        BaseJAAQLController.validate_data_rec(method.arguments + method.body, data, is_prod, fill_missing)

    @staticmethod
    def resolve_method(documentations: [SwaggerDocumentation], answers_head: bool = True):
        """
        The documentation of the route and its method that answer the request, or (None, None) when none of them declares the request's
        method. A HEAD that no documentation declares is answered by the route's GET, as HTTP has it (RFC 9110, 9.3.2): with the GET's
        status and headers, which werkzeug sends without the body. Flask routes HEAD to every view that takes GET but one published with
        answers_head False, whose GET does what a HEAD must not (JAAQLRule)
        """
        wanted = [request.method] + ([REST__GET] if request.method == REST__HEAD and answers_head else [])
        for method_name in wanted:
            for documentation in documentations:
                for method in documentation.methods:
                    if method.method == method_name:
                        return documentation, method
        return None, None

    @staticmethod
    def get_method(swagger_documentation: Union[list, SwaggerDocumentation]):
        documentations = swagger_documentation if isinstance(swagger_documentation, list) else [swagger_documentation]
        return BaseJAAQLController.resolve_method(documentations)[1]

    @staticmethod
    def get_response(method: SwaggerMethod, status: Union[HTTPStatus, Namespace, int]) -> TYPE__response:
        match_value = status
        if not isinstance(status, int):
            match_value = status.value
        for resp in method.responses:
            if isinstance(resp.code, int):
                if resp.code == match_value:
                    return resp
            else:
                if resp.code.value == match_value:
                    return resp

        if isinstance(status, int):
            raise Exception(ERR__unexpected_response_code % status)
        else:
            raise Exception(ERR__unexpected_response_code % status.value)

    @staticmethod
    def bi_cast(real_resp, name, arg_type: type):
        """
        Attempt to cast a response to it's intended type. Then check equality when casting back. If this can happen e.g.
        '5' can be cast to 5 and then back to '5' it's considered equal and the cast is performed
        :return:
        """
        err_mess = ERR__response_wrong_type % (str(name), type(real_resp[name]).__name__, arg_type.__name__)
        bi_cast = None
        try:
            # Bi directional cast. Cast to expected type and then cast back
            bi_cast = type(real_resp[name])(arg_type(real_resp[name]))
        except:
            pass
        if real_resp[name] == bi_cast:
            real_resp[name] = arg_type(real_resp[name])
        else:
            raise Exception(err_mess)

    @staticmethod
    def validate_output(response: TYPE__response, real_resp: any) -> any:
        if isinstance(response, SwaggerFlatResponse):
            check_resp = response.body
            if isinstance(real_resp, dict) or isinstance(real_resp, list):
                raise Exception(ERR__expected_response_flat_type)

            if real_resp is None and check_resp is not None:
                real_resp = check_resp
            elif real_resp is None and check_resp is None:
                raise Exception(ERR__req_method_resp)
            elif real_resp is not None and check_resp is None:
                pass  # do not update resp with method response body
            else:
                pass  # take the supplied response as gospel
        elif isinstance(response.responses, SwaggerList):
            if not isinstance(real_resp, list):
                raise Exception(ERR__expected_response_list)
            else:
                for idx in range(len(real_resp)):
                    mock_resp = SwaggerResponse(MOCK__description, response=response.responses.responses)
                    real_resp[idx] = BaseJAAQLController.validate_output(mock_resp, real_resp[idx])
        elif isinstance(response.responses, SwaggerSimpleList):
            if not isinstance(real_resp, list):
                raise Exception(ERR__expected_response_list)
            else:
                for idx in range(len(real_resp)):
                    if isinstance(real_resp[idx], datetime):
                        real_resp[idx] = str(real_resp[idx])
                    BaseJAAQLController.bi_cast(real_resp, idx, response.responses.arg_type)
        else:
            if not isinstance(real_resp, dict):
                raise Exception(ERR__expected_response_dict)

            if response.error_on_unexpected_field:
                for key, _ in real_resp.items():
                    if not any([swag_resp.name == key for swag_resp in response.responses]):
                        raise Exception(ERR__unexpected_response_field % key)

            match_alpha_resp = {}
            for swag_resp in response.responses:
                is_complex = isinstance(swag_resp.arg_type, SwaggerList)
                if swag_resp.name not in real_resp:
                    if swag_resp.required:
                        raise Exception(ERR__expected_response_field % swag_resp.name)
                    else:
                        continue
                if isinstance(real_resp[swag_resp.name], datetime):
                    real_resp[swag_resp.name] = str(real_resp[swag_resp.name])
                if swag_resp.arg_type != ARG_RESP__allow_all:
                    if not is_complex and not isinstance(real_resp[swag_resp.name], swag_resp.arg_type):
                        if real_resp[swag_resp.name] is not None or swag_resp.required:
                            BaseJAAQLController.bi_cast(real_resp, swag_resp.name, swag_resp.arg_type)

                    if is_complex:
                        mock_resp = SwaggerResponse(MOCK__description, response=swag_resp.arg_type)
                        real_resp[swag_resp.name] = BaseJAAQLController.validate_output(mock_resp,
                                                                                        real_resp[swag_resp.name])

                match_alpha_resp[swag_resp.name] = real_resp[swag_resp.name]
            real_resp = match_alpha_resp

        return real_resp

    @staticmethod
    def get_raw_request_inputs(method: SwaggerMethod, was_allow_all: bool, is_prod: bool, fill_missing: bool, **kwargs):
        # A webhook's request (raw_request): the webhook gets the query, the headers and the body as they came (handle_webhook), so
        # neither the query nor the body is merged with the path's application and name, which are authoritative: a key "name" or
        # "application" in either is no duplicated field (400) and reaches the webhook, a JSON string, number or null is no mapping (500).
        # The inputs are the path variables alone. A POST's body is JSON, which must parse (400 otherwise), or, where the method allows it
        # (form_body), application/x-www-form-urlencoded, as payment providers send it, which is never parsed here: parsing request.form
        # would consume the body the webhook reads (request.get_data())
        if len(method.body) != 0 or was_allow_all:
            if not (method.form_body and request.mimetype == CONTENT__form):
                BaseJAAQLController.enforce_content_type_json()
                request.get_json()
        data = dict(kwargs)
        if not was_allow_all:
            BaseJAAQLController.validate_data(method, data, is_prod, fill_missing)
        return data

    @staticmethod
    def json_body():
        """
        The request's JSON body. A body that is no JSON is the client's malformed request, answered 400 saying why it could not be read, where
        Flask's own answer named nothing ("The browser (or proxy) sent a request that this server could not understand."). A client gone
        while it was read (ClientDisconnected, a BadRequest too) and a body over the size limit (413) are raised as werkzeug raised them
        """
        try:
            return request.json
        except ClientDisconnected:
            raise
        except BadRequest as ex:
            # werkzeug's error, raised while it handled the decoder's ValueError, is the cause of Flask's
            reason, seen = ex, 0
            while reason is not None and not isinstance(reason, ValueError) and seen < 5:
                reason, seen = reason.__cause__ or reason.__context__, seen + 1
            detail = str(reason)[:JSON_ERROR__max_length] if isinstance(reason, ValueError) else type(ex).__name__
            raise HttpStatusException(ERR__body_not_json % detail, HTTPStatus.BAD_REQUEST) from ex

    @staticmethod
    def get_input_as_dictionary(method: SwaggerMethod, is_prod: bool, fill_missing: bool = True, **kwargs):
        data = {}

        was_allow_all = False
        if len(method.arguments) != 0:
            if method.arguments[0] == ARG_RESP__allow_all:
                was_allow_all = True

        if method.raw_request:
            return BaseJAAQLController.get_raw_request_inputs(method, was_allow_all, is_prod, fill_missing, **kwargs)

        only_args = False
        if len(method.body) != 0 or was_allow_all:
            BaseJAAQLController.enforce_content_type_json()
            data = BaseJAAQLController.json_body()
            if not isinstance(data, dict):
                # A JSON array, string, number, true, false or null, which no route takes
                raise HttpStatusException(ERR__expected_json_object % ("an array" if isinstance(data, list) else json.dumps(data)[:20]),
                                          HTTPStatus.BAD_REQUEST)
        else:
            content_type = request.headers.get('Content-Type', '')
            if 'charset=' not in content_type and len(kwargs) == 0:
                only_args = True

        if only_args:
            combined_data = {**request.args}
        else:
            combined_data = {**request.form, **request.args, **data, **kwargs}

        if len(combined_data) != len(request.form) + len(request.args) + len(data) + len(kwargs):
            raise HttpStatusException(ERR__duplicated_field, HTTPStatus.BAD_REQUEST)

        if not was_allow_all:
            BaseJAAQLController.validate_data(method, combined_data, is_prod, fill_missing)

        return combined_data

    @staticmethod
    def _cors(resp, use_cors: bool = False):
        if use_cors:
            resp.headers.add(HEADER__allow_origin, CORS__WILDCARD)
            resp.headers.add(HEADER__allow_headers, CORS__WILDCARD)
            resp.headers.add(HEADER__allow_methods, CORS__WILDCARD)
        return resp

    def log_safe_dump_recursive(self, data):
        if isinstance(data, list):
            return [self.log_safe_dump_recursive(itm) for itm in data]
        elif isinstance(data, dict):
            return {
                idx: "*******" if "password" in idx.lower() else itm
                for idx, itm in data.items()
            }
        else:
            return data

    def perform_profile(self, profile_id, description: str = None, route: str = None, method: str = None):
        if not self.do_profiling:
            return

        if profile_id in self.profiling_request_ids:
            if description is None:
                raise Exception("Expected profiling description")
            if route is not None:
                raise Exception("Expected no profiling route")
            if method is not None:
                raise Exception("Expected no profiling method")
            cur_time = str(time_delta_ms(self.profiling_request_ids[profile_id], datetime.now()))
            print("PROFILING: " + str(profile_id) + " " + cur_time + " " + description)
            self.profiling_request_ids[profile_id] = datetime.now()
        elif description is not None:
            raise Exception("Expected no profiling description")
        else:
            if route is None:
                raise Exception("Expected profiling route")
            if method is None:
                raise Exception("Expected profiling method")
            print("PROFILING: " + str(profile_id) + " " + method + " " + route)
            self.profiling_request_ids[profile_id] = datetime.now()

    def log_safe_dump(self, data):
        """
        Performs a log safe json dump of the data
        :return:
        """
        return json.dumps(self.log_safe_dump_recursive(data))

    def publish_route(self, route: str, swagger_documentation: Union[list, SwaggerDocumentation], use_cors: bool = False,
                      answers_head: bool = True, error_body: bool = True):
        # answers_head False: a HEAD is not answered by the route's GET but 405 (by Flask's router, JAAQLRule), for a route whose GET acts
        # (a webhook's runs a process of the application's, which cannot tell a HEAD from a GET; /cron starts jobs; a login or a logout
        # sets and consumes its cookies), so that a link checker, a mail scanner or an uptime checker sending HEAD never does what it does.
        # error_body False: the route's client errors are answered as plain text (text/plain, or werkzeug's HTML), as they always were, for
        # a route whose callers read them so (a webhook's, which payment providers and the like call; /email, whose failure BATON's
        # sendEmail reads as text; /documents, whose 425 BATON's render polling reads as text and polls again), instead of with JAAQL's
        # error body
        documentation_as_lists = swagger_documentation
        if not isinstance(documentation_as_lists, list):
            documentation_as_lists = [documentation_as_lists]

        methods = []
        for cur_documentation in documentation_as_lists:
            cur_documentation.path = route
            for declared in cur_documentation.methods:
                if declared.method in methods:
                    raise Exception(ERR__duplicated_route_method % (declared.method, route))
                methods.append(declared.method)

        if not self.model.is_container:
            use_cors = True

        if use_cors:
            methods.append(REST__OPTIONS)

        # What the route's 405 names (a request with a method it does not declare): its methods, HEAD wherever it has GET and answers it,
        # and OPTIONS, which it declares above or Flask answers itself
        allowed = sorted(set(methods) | {REST__OPTIONS} | ({REST__HEAD} if REST__GET in methods and answers_head else set()))

        def wrap_func(view_func):
            # getfullargspec is expensive and the result never changes for a given view function, so
            # resolve it once at registration instead of ~20 times per request
            view_func_args = inspect.getfullargspec(view_func).args

            @wraps(view_func)
            def routed_function(view_func_local, **kwargs):
                # The request's scope: who asked, on which route, the server faults noted while it runs. Its queries are timed for
                # slow-query reports unless those are off or the route is a deploy or tooling one. A failed request is seen here, before
                # Flask answers it, for a server-error report (jaaql/utilities/server_errors.py), and raised on unchanged
                with slow_queries.request_scope(route, request.method, request.path, request.headers.get(HEADER__user_agent),
                                                slow=route not in SLOW_QUERY__unreported_routes and slow_queries.enabled()):
                    try:
                        return handle_route(view_func_local, **kwargs)
                    except BaseException as ex:
                        server_errors.request_failed(ex, route, self.model.has_installed)
                        raise

            def handle_route(view_func_local, **kwargs):
                the_documentation, the_method = None, None
                if not BaseJAAQLController.is_options():
                    the_documentation, the_method = BaseJAAQLController.resolve_method(documentation_as_lists, answers_head)
                    if the_method is None:
                        # Flask answers a method the route does not take with 405 before it gets here, a HEAD to a route that does not
                        # answer it among them (JAAQLRule); one it takes that no documentation of the route declares is answered the same
                        # way, as the client's and never as a server error
                        raise MethodNotAllowed(valid_methods=allowed)
                if not self.model.has_installed and not route.startswith('/internal'):
                    resp = Response("Still installing. Be patient", status=HTTPStatus.SERVICE_UNAVAILABLE)
                    self._cors(resp, use_cors)
                    return resp
                start_time = datetime.now()
                request_id = uuid.uuid4()
                self.perform_profile(request_id, route=route, method=request.method)
                resp = None
                resp_type = current_app.json.mimetype
                jaaql_resp = JAAQLResponse()
                jaaql_resp.response_type = resp_type
                remember_me = False

                if not BaseJAAQLController.is_options():
                    self.perform_profile(request_id, "Fetch method")

                    account_id = None
                    ip_id = None
                    username = None
                    is_public = None
                    verification_hook = None
                    if the_method.parallel_verification:
                        verification_hook = Queue()

                    ip_addr = request.headers.get(HEADER__real_ip, request.remote_addr).split(",")[0]

                    if ip_addr is None or ip_addr == "":
                        ip_addr = "127.0.0.1"

                    security_key = request.headers.get(HEADER__security)
                    auth_cookie = request.cookies.get(COOKIE_JAAQL_AUTH)
                    if auth_cookie is not None:
                        security_key = auth_cookie

                    easyauth_resolved = False
                    used_bypass = False
                    if self.model.use_easyauth and security_key is None:
                        easyauth_principal_id = request.headers.get("X-MS-CLIENT-PRINCIPAL-ID")
                        if easyauth_principal_id:
                            account_id, username, ip_id, is_public, remember_me = \
                                self.model.authenticate_via_easyauth(request.headers, ip_addr, jaaql_resp)
                            easyauth_resolved = True
                            self.perform_profile(request_id, "EasyAuth")

                    if the_documentation.security and not easyauth_resolved:
                        bypass_super = request.headers.get(HEADER__security_bypass)
                        bypass_jaaql = request.headers.get(HEADER__security_bypass_jaaql)
                        bypass_user = request.headers.get(HEADER__security_specify_user)
                        if bypass_super or bypass_jaaql or bypass_user:
                            if ip_addr not in IPS__local:
                                raise HttpStatusException("Bypass used in none local context: " + ip_addr, HTTPStatus.UNAUTHORIZED)
                            miss_super_bypass = (bypass_super or bypass_user) and bypass_super != self.model.local_super_access_key
                            miss_jaaql_bypass = bypass_jaaql and bypass_jaaql != self.model.local_jaaql_access_key
                            if miss_super_bypass or miss_jaaql_bypass:
                                raise HttpStatusException("Invalid bypass key", HTTPStatus.UNAUTHORIZED)

                            is_public = False
                            used_bypass = True
                            username = USERNAME__super_db if bypass_super else USERNAME__jaaql
                            if bypass_user:
                                username = bypass_user
                            account_id, ip_id = self.model.get_bypass_user(username, ip_addr)

                            if verification_hook:
                                verification_hook.put((True, None, None))

                        elif verification_hook:
                            account_id, username, ip_id, is_public, remember_me = self.model.verify_auth_token_threaded(security_key,
                                                                                                                        ip_addr, verification_hook)
                            self.perform_profile(request_id, "Verify JWT Threaded")
                        else:
                            account_id, username, ip_id, is_public, remember_me = self.model.verify_auth_token(security_key, ip_addr)
                            self.perform_profile(request_id, "Verify JWT")

                    slow_queries.note_caller(account_id, used_bypass)

                    supply_dict = {}

                    throw_ex = None
                    ex_msg = None
                    try:
                        if ARG__http_inputs in view_func_args or any([key in view_func_args for key in kwargs.keys()]):
                            # A body of another shape than the route takes (a JSON scalar where an object goes) is the client's
                            with server_errors.reading_request():
                                validated = BaseJAAQLController.get_input_as_dictionary(the_method, self.is_prod, **kwargs)
                            slow_queries.note_application(validated)
                            if ARG__http_inputs in view_func_args:
                                supply_dict[ARG__http_inputs] = validated

                        if ARG__account_id in view_func_args:
                            if not the_documentation.security:
                                raise Exception(ERR__method_required_account_id)
                            supply_dict[ARG__account_id] = account_id

                        if the_method.parallel_verification:
                            supply_dict[ARG__verification_hook] = verification_hook

                        # Do not close created interfaces as they are re-used
                        for arg in view_func_args:
                            if arg.startswith(ARG_START__connection):
                                if not the_documentation.security:
                                    raise Exception(ERR__method_required_user_connection)
                                connect_db = arg.split(ARG_START__connection)[1]
                                supply_dict[arg] = create_interface_for_db(self.model.vault, self.model.config, account_id, connect_db,
                                                                           sub_role=account_id)

                        for arg in view_func_args:
                            if arg.startswith(ARG_START__jaaql_connection):
                                connect_db = arg.split(ARG_START__jaaql_connection)[1]
                                supply_dict[arg] = create_interface_for_db(self.model.vault, self.model.config, account_id, connect_db,
                                                                           sub_role=ROLE__jaaql)

                        if ARG__username in view_func_args:
                            if not the_documentation.security:
                                raise Exception(ERR__method_required_username)
                            supply_dict[ARG__username] = username

                        if ARG__ip_address in view_func_args:
                            supply_dict[ARG__ip_address] = ip_addr

                        if ARG__request_headers in view_func_args:
                            supply_dict[ARG__request_headers] = request.headers

                        if ARG__response in view_func_args:
                            supply_dict[ARG__response] = jaaql_resp

                        if ARG__auth_token in view_func_args:
                            if not the_documentation.security:
                                raise Exception(ERR__method_required_token)
                            supply_dict[ARG__auth_token] = request.headers.get(HEADER__security)
                            if supply_dict[ARG__auth_token] is None:
                                supply_dict[ARG__auth_token] = auth_cookie

                        if ARG__auth_token_for_refresh in view_func_args:
                            supply_dict[ARG__auth_token_for_refresh] = request.headers.get(HEADER__security)
                            if supply_dict[ARG__auth_token_for_refresh] is None:
                                supply_dict[ARG__auth_token_for_refresh] = auth_cookie

                        if ARG__connection in view_func_args:
                            if not the_documentation.security:
                                raise Exception(ERR__method_required_connection)
                            supply_dict[ARG__connection] = create_interface_for_db(self.model.vault, self.model.config, account_id, DB__jaaql)

                        if ARG__is_the_anonymous_user in view_func_args:
                            if not the_documentation.security:
                                raise Exception(ERR__method_required_is_the_anonymous_user)
                            supply_dict[ARG__is_the_anonymous_user] = is_public

                        self.perform_profile(request_id, "Fetch args")
                        if ARG__profiler in view_func_args:
                            supply_dict[ARG__profiler] = Profiler(request_id, self.do_profiling)

                        if ARG__headers in view_func_args:
                            supply_dict[ARG__headers] = dict(request.headers)

                        if ARG__body in view_func_args:
                            supply_dict[ARG__body] = request.get_data()

                        if ARG__args in view_func_args:
                            supply_dict[ARG__args] = dict(request.args)

                        if ARG__flask_request in view_func_args:
                            supply_dict[ARG__flask_request] = request

                        for k, v in kwargs.items():
                            if k in view_func_args:
                                supply_dict[k] = v

                        resp = view_func_local(**supply_dict)

                        self.perform_profile(request_id, "Perform work")

                        status = jaaql_resp.response_code
                        if jaaql_resp.raw_response is None:
                            method_response = BaseJAAQLController.get_response(the_method, status)
                        do_allow_all = False
                        if len(the_method.responses) != 0:
                            if the_method.responses[0] == RES__allow_all:
                                do_allow_all = True
                        if not do_allow_all and jaaql_resp.raw_response is None:
                            resp = BaseJAAQLController.validate_output(method_response, resp)

                        self.perform_profile(request_id, "Validate output")
                    except Exception as ex:
                        if not self.is_prod and not isinstance(ex, NotYetInstalled):
                            traceback.print_exc()  # Debugging
                        if not isinstance(ex, HttpStatusException):
                            ret_status = RESP__default_err_code
                            ex_msg = RESP__default_err_message
                        else:
                            ret_status = ex.response_code
                            ex_msg = ex.message

                        do_allow_all = False
                        if len(the_method.responses) != 0:
                            if the_method.responses[0] == RES__allow_all:
                                do_allow_all = True

                        if not do_allow_all and ret_status != HTTPStatus.UNAUTHORIZED and ret_status != \
                                HTTPStatus.NOT_IMPLEMENTED and ret_status != HTTPStatus.BAD_REQUEST and \
                                ret_status != HTTPStatus.UNPROCESSABLE_ENTITY and \
                                ret_status != CustomHTTPStatus.DATABASE_NO_EXIST and \
                                ret_status != HTTPStatus.INTERNAL_SERVER_ERROR:
                            try:
                                self.get_response(the_method, ret_status)
                            except Exception as sub_ex:
                                # The expected response code was not allowed
                                traceback.print_exc()
                                ex = sub_ex

                        throw_ex = ex

                    self.perform_profile(request_id, "Cleanup")

                    if throw_ex is not None:
                        raise throw_ex

                if jaaql_resp.response_type == resp_type and jaaql_resp.raw_response is None:
                    if not isinstance(resp, Response):
                        resp = self.json_serializer.response(resp)
                    resp.status = jaaql_resp.response_code
                else:
                    if jaaql_resp.raw_response is not None:
                        resp = jaaql_resp.raw_response
                    if jaaql_resp.is_binary:
                        hdrs = Headers(jaaql_resp.raw_headers or {})
                        content_type = hdrs.pop("Content-Type", None)
                        try:
                            del jaaql_resp.raw_headers["Content-Type"]
                        except:
                            pass
                        resp = Response(resp, status=jaaql_resp.response_code, content_type=content_type or "application/octet-stream")
                    else:
                        resp = Response(resp, mimetype=jaaql_resp.response_type, status=jaaql_resp.response_code)

                for key, val in jaaql_resp.raw_headers.items():
                    resp.headers.add(key, val)

                if request.cookies.get(COOKIE_JAAQL_AUTH) is not None and COOKIE_JAAQL_AUTH not in jaaql_resp.cookies:
                    resp.headers.add("Set-Cookie", format_cookie(COOKIE_JAAQL_AUTH, request.cookies.get(COOKIE_JAAQL_AUTH),
                                                                 get_cookie_attrs(self.model.vigilant_sessions, remember_me, self.model.is_container),
                                                                 self.model.is_https))

                if request.cookies.get(COOKIE_LOGIN_MARKER) is not None:
                    resp.headers.add("Set-Cookie", format_cookie(COOKIE_LOGIN_MARKER, "",
                                                                 {COOKIE_ATTR_EXPIRES: format_date_time(0), COOKIE_ATTR_PATH: "/"},
                                                                 self.model.is_https))

                for _, cookie in jaaql_resp.cookies.items():
                    resp.headers.add("Set-Cookie", cookie)

                self._cors(resp, use_cors)

                self.perform_profile(request_id, "Jsonify")

                return resp

            self.app.add_url_rule(route, view_func=lambda **kwargs: routed_function(view_func, **kwargs), methods=methods,
                                  endpoint=route, answers_head=answers_head, error_body=error_body)

            return routed_function

        return wrap_func

    @staticmethod
    def answers_with_error_body() -> bool:
        """
        Whether the request's client errors (4xx) are answered with JAAQL's error body: on every route but one published with error_body False
        (JAAQLRule), and when no route takes the request's path (404). Flask's router answers a method the route does not take before the
        request has its rule, so the route is then looked up by a method it does take
        """
        if not has_request_context():
            return True
        rule = request.url_rule
        routing = request.routing_exception
        if rule is None and isinstance(routing, MethodNotAllowed) and routing.valid_methods:
            try:
                rule = current_app.create_url_adapter(request).match(method=sorted(routing.valid_methods)[0], return_rule=True)[0]
            except Exception:
                rule = None
        return getattr(rule, "error_body", True) is not False

    @staticmethod
    def is_client_error(status) -> bool:
        try:
            return 400 <= int(status) < 500
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _init_error_handlers(app):
        # Every handler first reports, by the rule of jaaql/utilities/server_errors.py, an exception no routed request has seen (a route added
        # to the app directly); routed_function has already seen every other one. Flask picks the Exception handler for every exception that
        # is not an HTTPException, so the 500 handler answers only an explicit InternalServerError. A client error (4xx) is answered with
        # JAAQL's error body (error_code, message, table_name, index, column_name, set, descriptor), whoever raised it, the error code by its
        # status (client_error), so that BATON hands it to the request's own error handler as it does every JAAQL error, where it took a plain
        # text or an HTML page for an unexpected answer; except on a route published with error_body False (answers_with_error_body). A
        # server error (5xx) is answered as it always was

        @app.errorhandler(HTTPStatus.INTERNAL_SERVER_ERROR)
        def handle_server_error(error: InternalServerError):
            server_errors.unrouted_failure(error)
            traceback.print_tb(error.__traceback__)
            return BaseJAAQLController._cors(Response(RESP__default_err_message, RESP__default_err_code))

        @app.errorhandler(Exception)
        def handle_other_server_error(ex):
            server_errors.unrouted_failure(ex)
            if isinstance(ex, HTTPException):
                if isinstance(ex, MethodNotAllowed) and ex.valid_methods:
                    # Flask's router names the methods a route takes in no fixed order, which differs from one worker to the next
                    ex.valid_methods = sorted(ex.valid_methods)
                if ex.response is None and BaseJAAQLController.is_client_error(ex.code) and BaseJAAQLController.answers_with_error_body():
                    # werkzeug's own: no route for the path, a method the route does not take, a body over the size limit, a client gone.
                    # Its headers but its Content-Type are kept (a 405's Allow)
                    res = interpretable_response(client_error(ex.code, ex.description))
                    for name, value in ex.get_headers():
                        if name.lower() != "content-type":
                            res.headers[name] = value
                    return res
                return ex
            traceback.print_tb(ex.__traceback__)
            return interpretable_response(UnhandledJaaqlServerError())

        @app.errorhandler(JaaqlInterpretableHandledError)
        def handle_interpretable_pipeline_exception(error: JaaqlInterpretableHandledError):
            server_errors.unrouted_failure(error)
            return interpretable_response(error)

        def interpretable_body(error: JaaqlInterpretableHandledError) -> dict:
            return {
                "error_code": error.error_code,
                "message": error.message,
                "table_name": error.table_name,
                "index": error.index,
                "column_name": error.column_name,
                "descriptor": error.descriptor,
                "set": error.set
            }

        def interpretable_response(error: JaaqlInterpretableHandledError):
            res = jsonify(interpretable_body(error))
            res.status = error.response_code
            return BaseJAAQLController._cors(res)

        @app.errorhandler(HttpStatusException)
        def handle_pipeline_exception(error: HttpStatusException):
            server_errors.unrouted_failure(error)
            if not isinstance(error.response_code, int) or isinstance(error.response_code, CustomHTTPStatus):
                error.response_code = error.response_code.value
            if BaseJAAQLController.is_client_error(error.response_code) and BaseJAAQLController.answers_with_error_body():
                if isinstance(error.message, str):
                    return interpretable_response(client_error(error.response_code, error.message))
                if isinstance(error.message, dict):
                    # A query of a dict query refused: its error, set, query and parameters (and a store's row) as ever, in JAAQL's error body
                    answer = client_error(error.response_code, error.message.get(KEY__error))
                    res = jsonify({**interpretable_body(answer), **error.message})
                    res.status = answer.response_code
                    return BaseJAAQLController._cors(res)
            if not isinstance(error.message, str):
                res = jsonify(error.message)
            else:
                # As text, never a page: a message can name what the request sent ("Unexpected argument '<key>'"), and nginx adds its
                # nosniff and CSP to a 2xx or 3xx only
                res = Response(error.message, mimetype=CONTENT__text)
                res.headers[HEADER__content_type_options] = "nosniff"
            res.status = error.response_code
            return BaseJAAQLController._cors(res)

    @staticmethod
    def is_post():
        return request.method == REST__POST

    @staticmethod
    def is_get():
        # Also for a HEAD, which is answered as the GET is (resolve_method)
        return request.method in (REST__GET, REST__HEAD)

    @staticmethod
    def is_head():
        return request.method == REST__HEAD

    @staticmethod
    def is_delete():
        return request.method == REST__DELETE

    @staticmethod
    def is_put():
        return request.method == REST__PUT

    @staticmethod
    def is_options():
        return request.method == REST__OPTIONS
