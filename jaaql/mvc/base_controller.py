import traceback
from functools import wraps
from werkzeug.exceptions import HTTPException
import inspect
import json
from datetime import datetime

from flask import Response, Flask, request, jsonify, current_app
from jaaql.documentation.documentation_shared import ENDPOINT__refresh
from jaaql.constants import *
from jaaql.mvc.model import JAAQLModel
from jaaql.mvc.response import JAAQLResponse

from jaaql.openapi.swagger_documentation import SwaggerDocumentation, SwaggerMethod, TYPE__response,\
    SwaggerFlatResponse, REST__DELETE, REST__GET, REST__OPTIONS, REST__POST, REST__PUT, SwaggerList, SwaggerResponse,\
    MOCK__description, ARG_RESP__allow_all, RES__allow_all, SwaggerArgumentResponse
from jaaql.exceptions.http_status_exception import *

ARG__http_inputs = "http_inputs"
ARG__sql_inputs = "sql_inputs"
ARG__totp_iv = "totp_iv"
ARG__user_id = "user_id"
ARG__user_agent = "user_agent"
ARG__jaaql_connection = "jaaql_connection"
ARG__ip_address = "ip_address"
ARG__response = "response"
ARG__oauth_token = "oauth_token"
ARG__password_hash = "password_hash"
ARG__last_totp = "last_totp"

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
ERR__method_required_totp = "Method requires totp iv input yet marked as not secure in documentation"
ERR__method_required_user_id = "Method requires user id input yet marked as not secure in documentation"
ERR__method_required_password_hash = "Method requires password hash input yet marked as not secure in documentation"
ERR__missing_user_id = "Expected user id in response from method as method is without security"

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


class BaseJAAQLController:

    def __init__(self, model: JAAQLModel):
        super().__init__()
        self.app = Flask(__name__, instance_relative_config=True)
        self.app.config[FLASK__json_sort_keys] = False
        self.app.config[FLASK__max_content_length] = 1024 * 8  # 8kB
        self._init_error_handlers(self.app)
        self.model = model

    def diff_ms(self, start, now):
        return round((now - start).total_seconds() * 1000)

    @staticmethod
    def enforce_content_type_json():
        if request.content_type.split(";")[0] != CONTENT__json:
            raise HttpStatusException(ERR__expected_json, HTTPStatus.BAD_REQUEST)
        if len(request.content_type.split(";")) > 1:
            if request.content_type.split(";")[1].strip().lower() != CONTENT__encoding:
                raise HttpStatusException(ERR__expected_utf8, HTTPStatus.BAD_REQUEST)

    @staticmethod
    def validate_data_rec(arguments: [SwaggerArgumentResponse], data: dict, fill_missing: bool = True):
        for arg in arguments:
            if arg.required is True and arg.name not in data:
                raise HttpStatusException(ERR__expected_argument % arg.name, HTTPStatus.BAD_REQUEST)

            if isinstance(arg.arg_type, SwaggerList):
                if not isinstance(data[arg.name], list):
                    raise HttpStatusException(ERR__argument_wrong_type % (arg.name, str(type(data[arg.name])),
                                                                          str(type(list)), HTTPStatus.BAD_REQUEST))
                for itm in data[arg.name]:
                    BaseJAAQLController.validate_data_rec(arg.arg_type.responses, itm, fill_missing)
            elif arg.name in data and not isinstance(data[arg.name], arg.arg_type):
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
                    raise HttpStatusException(ERR__argument_wrong_type % (arg.name, str(type(data[arg.name])),
                                                                          str(arg.arg_type)), HTTPStatus.BAD_REQUEST)
            elif arg.name not in data and fill_missing:
                data[arg.name] = None

        for key, _ in data.items():
            found = any([arg.name == key for arg in arguments])
            if not found:
                raise HttpStatusException(ERR__unexpected_argument % key, HTTPStatus.BAD_REQUEST)

    @staticmethod
    def validate_data(method: SwaggerMethod, data: dict, fill_missing: bool = True):
        BaseJAAQLController.validate_data_rec(method.arguments + method.body, data, fill_missing)

    @staticmethod
    def get_method(swagger_documentation: SwaggerDocumentation):
        for method in swagger_documentation.methods:
            if request.method == method.method:
                return method

    @staticmethod
    def get_response(method: SwaggerMethod, status: HTTPStatus) -> TYPE__response:
        for resp in method.responses:
            if resp.code == status:
                return resp

        raise Exception(ERR__unexpected_response_code % status.value)

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
        else:
            if not isinstance(real_resp, dict):
                raise Exception(ERR__expected_response_dict)

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
                if not is_complex and not isinstance(real_resp[swag_resp.name], swag_resp.arg_type):
                    err_mess = ERR__response_wrong_type % (swag_resp.name, str(type(real_resp[swag_resp.name])),
                                                           str(swag_resp.arg_type))

                    if real_resp[swag_resp.name] is not None or swag_resp.required:
                        bi_cast = None
                        try:
                            # Bi directional cast. Cast to expected type and then cast back
                            bi_cast = type(real_resp[swag_resp.name])(swag_resp.arg_type(real_resp[swag_resp.name]))
                        except:
                            pass
                        if real_resp[swag_resp.name] == bi_cast:
                            real_resp[swag_resp.name] = swag_resp.arg_type(real_resp[swag_resp.name])
                        else:
                            raise Exception(err_mess)

                if is_complex:
                    mock_resp = SwaggerResponse(MOCK__description, response=swag_resp.arg_type)
                    real_resp[swag_resp.name] = BaseJAAQLController.validate_output(mock_resp,
                                                                                    real_resp[swag_resp.name])

                match_alpha_resp[swag_resp.name] = real_resp[swag_resp.name]
            real_resp = match_alpha_resp

            for key, _ in real_resp.items():
                if not any([swag_resp.name == key for swag_resp in response.responses]):
                    raise Exception(ERR__unexpected_response_field % key)

        return real_resp

    @staticmethod
    def get_input_as_dictionary(method: SwaggerMethod, fill_missing: bool = True):
        data = {}

        was_allow_all = False
        if len(method.arguments) != 0:
            if method.arguments[0] == ARG_RESP__allow_all:
                was_allow_all = True

        if len(method.body) != 0 or was_allow_all:
            BaseJAAQLController.enforce_content_type_json()
            data = request.json
        else:
            if len(request.data.decode(request.charset)) != 0:
                raise HttpStatusException(ERR__unexpected_request_body, HTTPStatus.BAD_REQUEST)

        combined_data = {**request.form, **request.args, **data}

        if len(combined_data) != len(request.form) + len(request.args) + len(data):
            raise HttpStatusException(ERR__duplicated_field, HTTPStatus.BAD_REQUEST)

        if not was_allow_all:
            BaseJAAQLController.validate_data(method, combined_data, fill_missing)

        return combined_data

    @staticmethod
    def _cors(resp):
        resp.headers.add(HEADER__allow_origin, CORS__WILDCARD)
        resp.headers.add(HEADER__allow_headers, CORS__WILDCARD)
        resp.headers.add(HEADER__allow_methods, CORS__WILDCARD)
        return resp

    def cors_route(self, route: str, swagger_documentation: SwaggerDocumentation):
        swagger_documentation.path = route

        methods = [method.method for method in swagger_documentation.methods]
        methods.append(REST__OPTIONS)

        def wrap_func(view_func):
            @wraps(view_func)
            def routed_function(view_func_local):
                start_time = datetime.now()
                resp = None
                resp_type = current_app.config["JSONIFY_MIMETYPE"]
                jaaql_resp = JAAQLResponse()
                jaaql_resp.response_type = resp_type

                if not BaseJAAQLController.is_options():
                    method = BaseJAAQLController.get_method(swagger_documentation)

                    user_agent = request.headers.get('User-Agent', None)

                    jaaql_connection = None
                    user_id = None
                    ip_id = None
                    ua_id = None
                    totp_iv = None
                    password_hash = None
                    l_totp = None

                    ip_addr = request.headers.get(HEADER__real_ip, request.remote_addr).split(",")[0]

                    if swagger_documentation.security:
                        jaaql_connection, user_id, ip_id, ua_id, totp_iv, password_hash, l_totp = self.model.verify_jwt(
                            request.headers.get(HEADER__security), ip_addr, user_agent,
                            route == ENDPOINT__refresh)

                    supply_dict = {}

                    throw_ex = None
                    ex_msg = None
                    method_input = None
                    try:
                        if ARG__http_inputs in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__http_inputs] = BaseJAAQLController.get_input_as_dictionary(method)
                            method_input = json.dumps(supply_dict[ARG__http_inputs])

                        if ARG__sql_inputs in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__sql_inputs] = BaseJAAQLController.get_input_as_dictionary(
                                method, fill_missing=False)
                            method_input = json.dumps(supply_dict[ARG__sql_inputs])

                        if ARG__totp_iv in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_totp)
                            supply_dict[ARG__totp_iv] = totp_iv

                        if ARG__user_id in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_user_id)
                            supply_dict[ARG__user_id] = user_id

                        if ARG__password_hash in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_password_hash)
                            supply_dict[ARG__password_hash] = password_hash

                        if ARG__last_totp in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_password_hash)
                            supply_dict[ARG__last_totp] = l_totp

                        if ARG__user_agent in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__user_agent] = user_agent

                        if ARG__ip_address in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__ip_address] = ip_addr

                        has_jaaql_connection = ARG__jaaql_connection in inspect.getfullargspec(view_func_local).args
                        if ARG__jaaql_connection in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__jaaql_connection] = jaaql_connection
                        if has_jaaql_connection and jaaql_connection is None:
                            raise Exception(ERR__method_required_security)

                        if ARG__response in inspect.getfullargspec(view_func_local).args:
                            supply_dict[ARG__response] = jaaql_resp

                        if ARG__oauth_token in inspect.getfullargspec(view_func_local).args:
                            if not swagger_documentation.security:
                                raise Exception(ERR__method_required_token)
                            supply_dict[ARG__oauth_token] = request.headers.get(HEADER__security)

                        resp = view_func_local(**supply_dict)

                        if not swagger_documentation.security:
                            user_id = jaaql_resp.user_id
                            ip_id = jaaql_resp.ip_id
                            ua_id = jaaql_resp.ua_id

                        status = jaaql_resp.response_code
                        method_response = BaseJAAQLController.get_response(method, status)
                        do_allow_all = False
                        if len(method.responses) != 0:
                            if method.responses[0] == RES__allow_all:
                                do_allow_all = True
                        if not do_allow_all:
                            resp = BaseJAAQLController.validate_output(method_response, resp)
                        ret_status = status
                    except Exception as ex:
                        if not isinstance(ex, HttpStatusException):
                            ret_status = RESP__default_err_code
                            ex_msg = RESP__default_err_message
                        else:
                            ret_status = ex.response_code
                            ex_msg = ex.message
                        throw_ex = ex

                    if jaaql_connection is not None:
                        jaaql_connection.pg_pool.closeall()

                    duration = round((datetime.now() - start_time).total_seconds() * 1000)
                    if user_id is not None:
                        self.model.log(user_id, start_time, duration, ex_msg, method_input, ip_id, ua_id, ret_status,
                                       route)

                    if throw_ex is not None:
                        raise throw_ex

                if jaaql_resp.response_type == resp_type:
                    resp = jsonify(resp)
                else:
                    resp = Response(resp, mimetype=jaaql_resp.response_type)

                self._cors(resp)
                return resp

            self.app.add_url_rule(route, view_func=lambda: routed_function(view_func), methods=methods,
                                  endpoint=route)

            return routed_function

        return wrap_func

    @staticmethod
    def _init_error_handlers(app):
        @app.errorhandler(HTTPStatus.INTERNAL_SERVER_ERROR)
        def handle_server_error(error: Exception):
            traceback.print_tb(error.__traceback__)
            return BaseJAAQLController._cors(Response(RESP__default_err_message, RESP__default_err_code))

        @app.errorhandler(HTTPException)
        def handle_other_server_error(error: HTTPException):
            return BaseJAAQLController._cors(Response(error.description, error.code))

        @app.errorhandler(HttpStatusException)
        def handle_pipeline_exception(error: HttpStatusException):
            return BaseJAAQLController._cors(Response(error.message, error.response_code))

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
