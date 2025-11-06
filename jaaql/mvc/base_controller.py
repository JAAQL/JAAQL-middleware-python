import threading
import traceback
from werkzeug.datastructures import Headers
import uuid
from functools import wraps

import typing as t
from werkzeug.exceptions import InternalServerError, HTTPException
import inspect
import json
import requests
from datetime import datetime, date, time
from jaaql.exceptions.custom_http_status import CustomHTTPStatus
from jaaql.exceptions.jaaql_interpretable_handled_errors import UnhandledJaaqlServerError, NotYetInstalled
import sys
import dataclasses
import decimal
from queue import Queue
from jaaql.utilities.utils_no_project_imports import get_cookie_attrs, COOKIE_JAAQL_AUTH, COOKIE_LOGIN_MARKER, COOKIE_ATTR_PATH
from jaaql.utilities.utils import time_delta_ms, Profiler
from flask import Response, Flask, request, jsonify, current_app
from flask.json.provider import DefaultJSONProvider
from jaaql.constants import *
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.response import *
from typing import Union
from jaaql.db.db_utils import create_interface_for_db
from monitor.main import HEADER__security, HEADER__security_bypass_jaaql, HEADER__security_bypass, HEADER__security_specify_user

from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, TYPE__response, \
    SwaggerFlatResponse, REST__DELETE, REST__GET, REST__OPTIONS, REST__POST, REST__PUT, SwaggerList, SwaggerResponse, \
    MOCK__description, ARG_RESP__allow_all, RES__allow_all, SwaggerArgumentResponse, SwaggerSimpleList
from jaaql.exceptions.http_status_exception import *

ARG__http_inputs = "http_inputs"
ARG__account_id = "account_id"
ARG__ip_address = "ip_address"
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

CORS__WILDCARD = "*"

ERR__argument_wrong_type = "Argument '%s' is of type '%s' but should be of type '%s'"
ERR__duplicated_field = "Field duplicated in request"
ERR__expected_argument = "Expected argument '%s'"
ERR__expected_json = "Expected content-type " + CONTENT__json
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
ERR__sentinel_failed = "Sentinel failed. Reponse code '%d' and content '%s'"

FLASK__json_sort_keys = "JSON_SORT_KEYS"
FLASK__max_content_length = "MAX_CONTENT_LENGTH"

HEADER__allow_headers = "Access-Control-Allow-Headers"
HEADER__allow_origin = "Access-Control-Allow-Origin"
HEADER__allow_methods = "Access-Control-Allow-Methods"
HEADER__real_ip = "X-Real-IP"

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


class BaseJAAQLController:

    sentinel_errors = None
    internal_sentinel = False
    base_url = None

    def __init__(self, model: JAAQLModel, is_prod: bool, base_url: str, do_profiling: bool = False):
        super().__init__()
        BaseJAAQLController.base_url = base_url
        self.app = Flask(__name__, instance_relative_config=True)
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
        BaseJAAQLController.sentinel_errors = Queue()
        self.sentinel_url = os.environ.get(ENVIRON__sentinel_url)
        if self.sentinel_url:
            if self.sentinel_url == "_":
                self.sentinel_url = base_url + ENDPOINT__report_sentinel_error
                BaseJAAQLController.internal_sentinel = True
            else:
                if not self.sentinel_url.startswith("http"):
                    self.sentinel_url = "https://" + self.sentinel_url
                if not self.sentinel_url.endswith("/api") and not self.sentinel_url.endswith(ENDPOINT__report_sentinel_error):
                    self.sentinel_url = self.sentinel_url + "/api"
                if not self.sentinel_url.endswith(ENDPOINT__report_sentinel_error):
                    self.sentinel_url = self.sentinel_url + ENDPOINT__report_sentinel_error

            threading.Thread(target=self.sentinel_reporter).start()

    def sentinel_reporter(self):
        while True:
            try:
                se = BaseJAAQLController.sentinel_errors.get()
                res = requests.post(self.sentinel_url, json=se)
                if res.status_code != HTTPStatus.OK:
                    raise Exception(ERR__sentinel_failed % (res.status_code, res.text))
            except:
                traceback.print_exc()

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
                                                                          type(list).__name__), HTTPStatus.BAD_REQUEST)
                for itm in data[arg.name]:
                    BaseJAAQLController.validate_data_rec(arg.arg_type.responses, itm, fill_missing)
            elif arg.name in data and arg.arg_type == ARG_RESP__allow_all:
                continue
            elif arg.name in data and not isinstance(data[arg.name], arg.arg_type):
                if data[arg.name] is None and not arg.required:
                    continue
                was_err = True
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
                    try:
                        if data[arg.name] in BOOL__allowed:
                            was_err = False
                            data[arg.name] = BOOL__allowed[data[arg.name]]
                    except ValueError:
                        pass

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
    def get_method(swagger_documentation: SwaggerDocumentation):
        for method in swagger_documentation.methods:
            if request.method == method.method:
                return method

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
    def get_input_as_dictionary(method: SwaggerMethod, is_prod: bool, fill_missing: bool = True, **kwargs):
        data = {}

        was_allow_all = False
        if len(method.arguments) != 0:
            if method.arguments[0] == ARG_RESP__allow_all:
                was_allow_all = True

        only_args = False
        if len(method.body) != 0 or was_allow_all:
            BaseJAAQLController.enforce_content_type_json()
            data = request.json
        else:
            content_type = request.headers.get('Content-Type', '')
            if 'charset=' not in content_type and len(kwargs) == 0:
                only_args = True

        if isinstance(data, list):
            combined_data = data
        else:
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

    def publish_route(self, route: str, swagger_documentation: Union[list, SwaggerDocumentation], use_cors: bool = False):
        documentation_as_lists = swagger_documentation
        if not isinstance(documentation_as_lists, list):
            documentation_as_lists = [documentation_as_lists]

        methods = []
        for cur_documentation in documentation_as_lists:
            cur_documentation.path = route
            for method in cur_documentation.methods:
                methods.append(method.method)

        if not self.model.is_container:
            use_cors = True

        if use_cors:
            methods.append(REST__OPTIONS)
            swagger_documentation = documentation_as_lists[0]

        def wrap_func(view_func):
            @wraps(view_func)
            def routed_function(view_func_local, **kwargs):
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
                    the_method = BaseJAAQLController.get_method(swagger_documentation)
                    self.perform_profile(request_id, "Fetch method")

                    account_id = None
                    ip_id = None
                    username = None
                    is_public = None
                    verification_hook = None
                    if method.parallel_verification:
                        verification_hook = Queue()

                    ip_addr = request.headers.get(HEADER__real_ip, request.remote_addr).split(",")[0]

                    if ip_addr is None or ip_addr == "":
                        ip_addr = "127.0.0.1"

                    security_key = request.headers.get(HEADER__security)
                    auth_cookie = request.cookies.get(COOKIE_JAAQL_AUTH)
                    if auth_cookie is not None:
                        security_key = auth_cookie

                    if swagger_documentation.security:
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

                    supply_dict = {}

                    throw_ex = None
                    ex_msg = None
                    try:
                        if ARG__http_inputs in inspect.getfullargspec(view_func_local).args or any([key in inspect.getfullargspec(view_func_local).args for key in kwargs.keys()]):
                            validated = BaseJAAQLController.get_input_as_dictionary(the_method, self.is_prod, **kwargs)
                            if ARG__http_inputs in inspect.getfullargspec(view_func_local).args:
                                supply_dict[ARG__http_inputs] = validated

                        if ARG__account_id in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_account_id)
                            supply_dict[ARG__account_id] = account_id

                        if method.parallel_verification:
                            supply_dict[ARG__verification_hook] = verification_hook

                        # Do not close created interfaces as they are re-used
                        for arg in inspect.getfullargspec(view_func_local).args:
                            if arg.startswith(ARG_START__connection):
                                if not swagger_documentation.security:
                                    raise Exception(ERR__method_required_user_connection)
                                connect_db = arg.split(ARG_START__connection)[1]
                                supply_dict[arg] = create_interface_for_db(self.model.vault, self.model.config, account_id, connect_db,
                                                                           sub_role=account_id)

                        for arg in inspect.getfullargspec(view_func_local).args:
                            if arg.startswith(ARG_START__jaaql_connection):
                                connect_db = arg.split(ARG_START__jaaql_connection)[1]
                                supply_dict[arg] = create_interface_for_db(self.model.vault, self.model.config, account_id, connect_db,
                                                                           sub_role=ROLE__jaaql)

                        if ARG__username in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_username)
                            supply_dict[ARG__username] = username

                        if ARG__ip_address in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__ip_address] = ip_addr

                        if ARG__response in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__response] = jaaql_resp

                        if ARG__auth_token in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_token)
                            supply_dict[ARG__auth_token] = request.headers.get(HEADER__security)
                            if supply_dict[ARG__auth_token] is None:
                                supply_dict[ARG__auth_token] = auth_cookie

                        if ARG__auth_token_for_refresh in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__auth_token_for_refresh] = request.headers.get(HEADER__security)
                            if supply_dict[ARG__auth_token_for_refresh] is None:
                                supply_dict[ARG__auth_token_for_refresh] = auth_cookie

                        if ARG__connection in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_connection)
                            supply_dict[ARG__connection] = create_interface_for_db(self.model.vault, self.model.config, account_id, DB__jaaql)

                        if ARG__is_the_anonymous_user in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_is_the_anonymous_user)
                            supply_dict[ARG__is_the_anonymous_user] = is_public

                        self.perform_profile(request_id, "Fetch args")
                        if ARG__profiler in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__profiler] = Profiler(request_id, self.do_profiling)

                        if ARG__headers in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__headers] = dict(request.headers)

                        if ARG__body in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__body] = request.get_data()

                        if ARG__args in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__args] = dict(request.args)

                        if ARG__flask_request in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__flask_request] = request

                        for k, v in kwargs.items():
                            if k in inspect.getfullargspec(view_func_local).args:
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
                                  endpoint=route)

            return routed_function

        return wrap_func

    @staticmethod
    def _init_error_handlers(app):
        @app.errorhandler(HTTPStatus.INTERNAL_SERVER_ERROR)
        def handle_server_error(error: InternalServerError):
            if os.environ.get(ENVIRON__sentinel_url):
                orig = error.original_exception

                tb_frame = sys.exc_info()[2]
                while tb_frame.tb_next:
                    tb_frame = tb_frame.tb_next
                source_file = tb_frame.tb_frame.f_code.co_filename[len(os.getcwd()) + 1:]
                source_file = source_file.replace("\\", "/")

                BaseJAAQLController.sentinel_errors.put({
                    "location": BaseJAAQLController.base_url,
                    "error_condensed": str(orig),
                    "version": VERSION,
                    "source_system": "Sentinel" if BaseJAAQLController.internal_sentinel else "JAAQL",
                    "source_file": source_file,
                    "file_line_number": tb_frame.tb_lineno,
                    "stacktrace": ''.join(traceback.format_exception(type(orig), value=orig, tb=orig.__traceback__))
                })

            traceback.print_tb(error.__traceback__)
            return BaseJAAQLController._cors(Response(RESP__default_err_message, RESP__default_err_code))

        @app.errorhandler(Exception)
        def handle_other_server_error(ex):
            if isinstance(ex, HTTPException):
                return ex
            traceback.print_tb(ex.__traceback__)
            return handle_interpretable_pipeline_exception(UnhandledJaaqlServerError())

        @app.errorhandler(JaaqlInterpretableHandledError)
        def handle_interpretable_pipeline_exception(error: JaaqlInterpretableHandledError):
            res = jsonify({
                "error_code": error.error_code,
                "message": error.message,
                "table_name": error.table_name,
                "index": error.index,
                "column_name": error.column_name,
                "descriptor": error.descriptor,
                "set": error.set
            })
            res.status = error.response_code
            return BaseJAAQLController._cors(res)

        @app.errorhandler(HttpStatusException)
        def handle_pipeline_exception(error: HttpStatusException):
            if not isinstance(error.response_code, int) or isinstance(error.response_code, CustomHTTPStatus):
                error.response_code = error.response_code.value
            if not isinstance(error.message, str):
                res = jsonify(error.message)
            else:
                res = Response(error.message)
            res.status = error.response_code
            return BaseJAAQLController._cors(res)

    @staticmethod
    def is_post():
        return request.method == REST__POST

    @staticmethod
    def is_get():
        return request.method == REST__GET

    @staticmethod
    def is_delete():
        return request.method == REST__DELETE

    @staticmethod
    def is_put():
        return request.method == REST__PUT

    @staticmethod
    def is_options():
        return request.method == REST__OPTIONS
