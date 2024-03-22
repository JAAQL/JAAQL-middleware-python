from .exception_queries import *  # Do not remove as others refer to this import

QUERY__setup_jaaql_role = "SELECT setup_jaaql_role();"
QUERY__setup_jaaql_role_with_password = "SELECT setup_jaaql_role_with_password(%(password)s);"


QUERY__count_security_events_of_type_succeeded_ever = """
    SELECT
        COUNT(*) as count
    FROM security_event S
    INNER JOIN email_template E ON E.name = S.email_template AND E.application = S.application
    WHERE E.type IN (:type_one, :type_two) AND account = :account AND finish_timestamp is not null
"""


def count_succeeded_for_security_event(
    connection: DBInterface,
    type_one: str, type_two: str,
    account
):
    return execute_supplied_statement(
        connection, QUERY__count_security_events_of_type_succeeded_ever, {
            "type_one": type_one, "type_two": type_two,
            KG__security_event__account: account,
        }, as_objects=True
    )[KEY__count]
