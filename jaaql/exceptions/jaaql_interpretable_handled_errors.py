from jaaql.exceptions.http_status_exception import JaaqlInterpretableHandledError


class AccountAlreadyExists(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1001,
            http_response_code=422,
            table_name="account",
            message="A user like this already exists",
            column_name="sub",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class DatabaseOperationalError(JaaqlInterpretableHandledError):
    def __init__(self, message, descriptor=None):
        super().__init__(
            error_code=1002,
            http_response_code=422,
            table_name=None,
            message=message,
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class HandledProcedureError(JaaqlInterpretableHandledError):
    def __init__(self, message, index, table_name, column_name=None, descriptor=None):
        super().__init__(
            error_code=1003,
            http_response_code=422,
            table_name=table_name,
            message=message,
            column_name=column_name,
            _set=None,
            index=index,
            descriptor=descriptor
        )


class UnhandledQueryError(JaaqlInterpretableHandledError):
    def __init__(self, message, _set, table_name=None, column_name=None, descriptor=None):
        super().__init__(
            error_code=1004,
            http_response_code=422,
            table_name=table_name,
            message=message,
            column_name=column_name,
            _set=_set,
            index=None,
            descriptor=descriptor
        )


class UnhandledProcedureError(JaaqlInterpretableHandledError):
    def __init__(self, message, table_name=None, column_name=None, descriptor=None):
        super().__init__(
            error_code=1005,
            http_response_code=422,
            table_name=table_name,
            message=message,
            column_name=column_name,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class AccountAlreadyConfirmed(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1006,
            http_response_code=422,
            table_name="security_event",
            message="Your account is already confirmed. You cannot request another confirmation.",
            column_name="finish_timestamp",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class PasswordAlreadyUsedBefore(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1007,
            http_response_code=422,
            table_name="account_password",
            message="You have used this password with your account before. Please enter a password you have never used.",
            column_name="hash",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class TooManySignUpConfirmationRequests(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1008,
            http_response_code=422,
            table_name="email_template",
            message="You have made too many requests for sign up confirmation in the past 24 hours. Please wait",
            column_name="type",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class UserUnauthorized(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1009,
            http_response_code=401,
            table_name=None,
            message="You are not permitted to access this resource",
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class UnhandledJaaqlServerError(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1010,
            http_response_code=500,
            table_name=None,
            message="An unhandled exception has occurred with JAAQL.",
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class SingletonExpected(JaaqlInterpretableHandledError):
    def __init__(self, _set, descriptor=None):
        super().__init__(
            error_code=1011,
            http_response_code=422,
            table_name=None,
            message="A singleton was requested but this set does not contain exactly one row",
            column_name=None,
            _set=_set,
            index=None,
            descriptor=descriptor
        )


class NotYetInstalled(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1012,
            http_response_code=422,
            table_name=None,
            message="Jaaql has not yet performed it's installation operation",
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class InvalidSecurityEventLock(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1013,
            http_response_code=422,
            table_name="security_event",
            message="Either security event does not exist, has already been used, has expired",
            column_name="event_lock",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class MissingParameterInQuery(JaaqlInterpretableHandledError):
    def __init__(self, message, _set, descriptor=None):
        super().__init__(
            error_code=1014,
            http_response_code=422,
            table_name=None,
            message=message,
            column_name=None,
            _set=_set,
            index=None,
            descriptor=descriptor
        )


class ExpectedParameterInQuery(JaaqlInterpretableHandledError):
    def __init__(self, message, descriptor=None):
        super().__init__(
            error_code=1015,
            http_response_code=422,
            table_name=None,
            message=message,
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class TooManyUnlockAttempts(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1016,
            http_response_code=422,
            table_name="security_event",
            message="Too many attempts have been made to unlock this security event",
            column_name="unlock_code",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class TooManyPasswordResetRequests(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1017,
            http_response_code=422,
            table_name="email_template",
            message="You have made too many requests to change your password in the past 24 hours. Please wait.",
            column_name="type",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class DocumentStillRendering(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1018,
            http_response_code=422,
            table_name="document_request",
            message="The document has not finished rendering yet, please wait before requesting again.",
            column_name="render_timestamp",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class SecurityEventShortCodeExpired(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1019,
            http_response_code=422,
            table_name="security_event",
            message="The short unlock code has expired. Please use the long link found in your email.",
            column_name="unlock_code",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class SecurityEventIncorrectShortUnlockCode(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1020,
            http_response_code=422,
            table_name="security_event",
            message="Incorrect unlock code. Please try again.",
            column_name="unlock_code",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class UnsatisfactoryPasswordComplexity(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1021,
            http_response_code=422,
            table_name="account_password",
            message="The supplied password is not complex enough! It must contain either a number, a special character or an upper case character and not consist entirely of numbers. It must also be at least length 8.",
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class IncorrectPasswordVerification(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1022,
            http_response_code=422,
            table_name="account_password",
            message="Verification password incorrect.",
            column_name="hash",
            _set=None,
            index=None,
            descriptor=descriptor
        )


class UnhandledRemoteProcedureError(JaaqlInterpretableHandledError):
    def __init__(self, descriptor=None):
        super().__init__(
            error_code=1023,
            http_response_code=500,
            table_name=None,
            message="An unhandled exception has occurred with the remote procedure.",
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )


class CronExpressionError(JaaqlInterpretableHandledError):
    def __init__(self, message, descriptor=None):
        super().__init__(
            error_code=1024,
            http_response_code=422,
            table_name=None,
            message=message,
            column_name=None,
            _set=None,
            index=None,
            descriptor=descriptor
        )
