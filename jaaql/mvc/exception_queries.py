"""
This script was generated from jaaql.exceptions.fxli at 2024-10-05, 22:03:06
"""

from jaaql.utilities.crypt_utils import get_repeatable_salt
from .generated_queries import *


def add_account_password(
    connection: DBInterface, encryption_key: bytes, vault_repeatable_salt: str,
    account__id, account_password__hash
):
    account_password__uuid = account_password__insert(
        connection, encryption_key, account__id, 
        account_password__hash, 
        encryption_salts={KG__account_password__hash: get_repeatable_salt(vault_repeatable_salt, account__id)}
    )[KG__account_password__uuid]

    account__update(
        connection, encryption_key, account__id,
        most_recent_password=account_password__uuid
    )


QUERY__fetch_most_recent_password = """
    SELECT
        A.id,
        P.uuid,
        P.hash
    FROM account_password P
    INNER JOIN account A ON P.uuid = A.most_recent_password
    WHERE
        A.id = :id
"""


def fetch_most_recent_password(
    connection: DBInterface, encryption_key: bytes, account__id
):
    return execute_supplied_statement_singleton(
        connection, QUERY__fetch_most_recent_password, {KG__account__id: account__id},
        decrypt_columns=[KG__account_password__hash], encryption_key=encryption_key, as_objects=True
    )[KG__account_password__hash]


QUERY__fetch_most_recent_password_from_username = """
    SELECT
        A.id,
        P.uuid,
        P.hash
    FROM account_password P
    INNER JOIN account A ON P.uuid = A.most_recent_password
    WHERE
        A.username = :username
"""


def fetch_most_recent_password_from_username(
    connection: DBInterface, encryption_key: bytes, vault_repeatable_salt: str,
    account__username, singleton_code: int = None, singleton_message: str = None
):
    return execute_supplied_statement_singleton(
        connection, QUERY__fetch_most_recent_password_from_username, {KG__account__username: account__username},
        encryption_key=encryption_key, encrypt_parameters=[KG__account__username], encryption_salts={
            KG__account__username: get_repeatable_salt(vault_repeatable_salt)
        },
        decrypt_columns=[KG__account_password__hash], as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


QUERY__fetch_account_from_username = "SELECT * FROM account WHERE username = :username"


def fetch_account_from_username(
    connection: DBInterface, encryption_key: bytes, vault_repeatable_salt: str,
    username, singleton_code: int = None, singleton_message: str = None
):
    return execute_supplied_statement_singleton(
        connection, QUERY__fetch_account_from_username, {KG__account__username: username},
        encryption_key=encryption_key, encrypt_parameters=[KG__account__username], encryption_salts={
            KG__account__username: get_repeatable_salt(vault_repeatable_salt)
        }, as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


QUERY__mark_account_registered = "SELECT mark_account_registered(:id)"


def mark_account_registered(
    connection: DBInterface, _id
):
    execute_supplied_statement_singleton(
        connection, QUERY__mark_account_registered, {
            KG__account__id: _id
        }
    )


QUERY__create_account = "SELECT create_account(:username, :attach_as, :already_exists, :is_the_anonymous_user, :allow_already_exists) as account_id"
KEY__attach_as = "attach_as"
KEY__already_exists = "already_exists"
KEY__allow_already_exists = "allow_already_exists"
KEY__username = "username"
KEY__is_the_anonymous_user = "is_the_anonymous_user"
KEY__account_id = "account_id"


def create_account(
    connection: DBInterface, encryption_key: bytes, vault_repeatable_salt: str,
    username, attach_as=None, already_exists=False, is_the_anonymous_user=False,
    allow_already_exists=False
):
    return execute_supplied_statement_singleton(
        connection, QUERY__create_account, {
            KEY__username: username,
            KEY__attach_as: attach_as,
            KEY__already_exists: already_exists,
            KEY__is_the_anonymous_user: is_the_anonymous_user,
            KEY__allow_already_exists: allow_already_exists
        }, encryption_salts={
            KG__account__username: get_repeatable_salt(vault_repeatable_salt)
        }, as_objects=True, encryption_key=encryption_key, encrypt_parameters=[KG__account__username]
    )[KEY__account_id]


QUERY__validate_most_recent_password = "SELECT * FROM account WHERE id = :id AND most_recent_password = :most_recent_password"


def validate_is_most_recent_password(
    connection: DBInterface, account,
    uuid, singleton_code: int = None, singleton_message: str = None
):
    return execute_supplied_statement_singleton(
        connection, QUERY__validate_most_recent_password, {
            KG__account__id: account,
            KG__account__most_recent_password: uuid
        }, singleton_code=singleton_code, singleton_message=singleton_message, skip_commit=True
    )


QUERY__exists_matching_validated_ip_address = "SELECT COUNT(*) FROM validated_ip_address WHERE encrypted_salted_ip_address = :encrypted_salted_ip_address"
KEY__count = "count"


def exists_matching_validated_ip_address(
    connection: DBInterface, encrypted_salted_ip_address
):
    return execute_supplied_statement_singleton(
        connection, QUERY__exists_matching_validated_ip_address, {
            KG__validated_ip_address__encrypted_salted_ip_address: encrypted_salted_ip_address
        }, as_objects=True
    )[KEY__count] == 1


QUERY___add_or_update_validated_ip_address = "INSERT INTO validated_ip_address (account, encrypted_salted_ip_address) VALUES (:account, :encrypted_salted_ip_address) ON CONFLICT ON CONSTRAINT validated_ip_address_encrypted_salted_ip_address_key DO UPDATE SET last_authentication_timestamp = current_timestamp RETURNING uuid as uuid"


QUERY__fetch_application_schemas = "SELECT S.name, S.database, (A.default_schema = S.name) as is_default, A.is_live FROM application_schema S INNER JOIN application A ON A.name = S.application WHERE S.application = :application"
KEY__is_default = "is_default"

QUERY__count_security_events_of_type_in_24hr_window = """
    SELECT
        COUNT(*) as count
    FROM security_event S
    INNER JOIN email_template E ON E.name = S.email_template AND E.application = S.application
    WHERE E.type IN (:type_one, :type_two) AND ((:account::postgres_role is not null AND account = :account) OR (:fake_account::encrypted__jaaql_username is not null AND fake_account = :fake_account)) AND (creation_timestamp + interval '24 hour') > current_timestamp
"""


def count_for_security_event(
    connection: DBInterface, encryption_key: bytes, vault_repeatable_salt: str,
    type_one: str, type_two: str,
    account, fake_account=None
):
    return execute_supplied_statement_singleton(
        connection, QUERY__count_security_events_of_type_in_24hr_window, {
            "type_one": type_one, "type_two": type_two,
            KG__security_event__account: account,
            KG__security_event__fake_account: fake_account
        }, as_objects=True, encryption_key=encryption_key, encrypt_parameters=[KG__security_event__fake_account],
        encryption_salts={KG__security_event__fake_account: get_repeatable_salt(vault_repeatable_salt, fake_account)}
    )[KEY__count]


RPC_ACCESS__private = "P"
RPC_ACCESS__public = "U"
RPC_ACCESS__webhook = "W"

KEY__type_one = "type_one"
KEY__type_two = "type_two"

EMAIL_TYPE__signup = "S"
EMAIL_TYPE__already_signed_up = "A"
EMAIL_TYPE__reset_password = "R"
EMAIL_TYPE__unregistered_password_reset = "U"
EMAIL_TYPE__general = "G"

KEY__key_fits = "key_fits"
QUERY__check_security_event_unlock = """
    UPDATE
        security_event S
    SET
        wrong_key_attempt_count = S.wrong_key_attempt_count + (case when (S.unlock_code = :unlock_code OR S.unlock_key = :unlock_key OR S.wrong_key_attempt_count >= 3) then 0 else 1 end)
    FROM application A
    WHERE
        S.application = A.name AND
        (S.event_lock = :event_lock OR S.unlock_key = :unlock_key) AND S.finish_timestamp is null AND
        S.creation_timestamp + (A.unlock_key_validity_period || ' seconds')::interval > current_timestamp
    RETURNING S.*, A.unlock_code_validity_period, (S.unlock_code = :unlock_code OR S.unlock_key = :unlock_key) as key_fits
"""


def check_security_event_unlock(
    connection: DBInterface, event_lock, unlock_code,
    unlock_key, singleton_code: int = None, singleton_message: str = None
):
    return execute_supplied_statement_singleton(
        connection, QUERY__check_security_event_unlock, {
            KG__security_event__event_lock: event_lock,
            KG__security_event__unlock_code: unlock_code,
            KG__security_event__unlock_key: unlock_key
        }, as_objects=True, singleton_code=singleton_code, singleton_message=singleton_message
    )


QUERY__fetch_document_templates_for_email_template = """
    SELECT
        *
    FROM
        document_template T
    WHERE
        T.application = :application AND
        T.email_template = :email_template
"""


def fetch_document_templates_for_email_template(
    connection: DBInterface, application, email_template
):
    return execute_supplied_statement(
        connection, QUERY__fetch_document_templates_for_email_template, {
            KG__document_template__application: application,
            KG__document_template__email_template: email_template
        }, as_objects=True
    )
