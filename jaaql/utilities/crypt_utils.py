from argon2 import PasswordHasher, low_level
from argon2.exceptions import *
from jaaql.exceptions.http_status_exception import HttpStatusException
import os
from typing import Optional, Union
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
import jwt
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from jaaql.constants import ENCODING__ascii


FERNET__key_length = 32
AES__key_length = 24  # A key of length 24 that is base64 encoded is length 32. This corresponds to AES-256
AES__iv_length = 16
AES__iv_length_b64 = 12  # A iv of length 12 will be base64 encoded (url safe) to be length 16
PKCS7__length = 128

ERR__password_not_long_enough = "Password needs to be at least of length %d"
ERR__password_not_complex_enough = "Password must contain either a number, upper case letter or special character."
ERR__password_no_letters = "Password must contain letters"

PASSWORD__min_length = 8

JWT__hour_expiry = 1000 * 60 * 60
JWT__exp = "__expires_at"
JWT__purpose = "__purpose"
JWT__algo = "HS256"

MAX_LONG = 2**63-1


def fetch_epoch_ms():
    return int(datetime.now().replace(tzinfo=timezone.utc).timestamp() * 1000)


def jwt_encode(secret_key: bytes, data: dict, purpose: str, expiry_ms: int = JWT__hour_expiry) -> str:
    data[JWT__exp] = (fetch_epoch_ms() + expiry_ms) if expiry_ms != 0 else MAX_LONG
    data[JWT__purpose] = purpose
    return jwt.encode(data, secret_key, algorithm=JWT__algo).decode(ENCODING__ascii)


def jwt_decode(secret_key: bytes, data: str, purpose: str, allow_expired: bool = False) -> Union[dict, bool]:
    try:
        jwt_obj = jwt.decode(data, secret_key, algorithms=[JWT__algo])
    except:
        return False

    if jwt_obj[JWT__exp] < fetch_epoch_ms() and not allow_expired:
        return False

    if jwt_obj[JWT__purpose] != purpose:
        return False

    jwt_obj.pop(JWT__exp)

    return jwt_obj


def decrypt(secret_key: bytes, data: Optional[str] = None) -> Optional[str]:
    if data is None:
        return None
    data = data.encode(ENCODING__ascii)
    return Fernet(secret_key).decrypt(data).decode(ENCODING__ascii)


def encrypt(secret_key: bytes, data: str) -> str:
    message = data.encode(ENCODING__ascii)
    return Fernet(secret_key).encrypt(message).decode(ENCODING__ascii)


def encrypt_raw(secret_key: bytes, data: any, iv: bytes = None) -> str:
    data = str(data)

    if iv is None:
        iv = os.urandom(AES__iv_length)

    if len(iv) != AES__iv_length:
        _, iv = key_stretcher(iv.decode(ENCODING__ascii), iv, AES__iv_length_b64)

    backend = default_backend()
    padder = padding.PKCS7(PKCS7__length).padder()

    data = data.encode(ENCODING__ascii)
    data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(secret_key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    ct = encryptor.update(data) + encryptor.finalize()

    return b64e(iv).decode(ENCODING__ascii) + "." + b64e(ct).decode(ENCODING__ascii)


def decrypt__raw(secret_key: bytes, data: str) -> str:
    unpadder = padding.PKCS7(PKCS7__length).unpadder()
    iv = b64d(data.split(".")[0])
    data = b64d(data.split(".")[1])

    backend = default_backend()
    cipher = Cipher(algorithms.AES(secret_key), modes.CBC(iv), backend=backend)

    decryptor = cipher.decryptor()
    plain = decryptor.update(data) + decryptor.finalize()
    plain = unpadder.update(plain) + unpadder.finalize()

    return plain.decode(ENCODING__ascii)


def validate_password(password: str):
    if password is None or len(password) < PASSWORD__min_length:
        raise HttpStatusException(ERR__password_not_long_enough % PASSWORD__min_length)

    has_number = any([str(num) in password for num in list(range(0, 9))])
    has_special_character = any([not letter.isnumeric() and not letter.isdigit() for letter in password])
    has_upper_case = password.lower() != password

    if not has_number and not has_special_character and not has_upper_case:
        raise HttpStatusException(ERR__password_not_complex_enough)

    has_letters = not all([str(num) in password for num in list(range(0, 9))])
    if not has_letters:
        raise HttpStatusException(ERR__password_no_letters)


def key_stretcher(key: str, salt: bytes = None, length: int = FERNET__key_length):
    defaults = PasswordHasher()

    if salt is None:
        salt = os.urandom(defaults.salt_len)

    return salt, b64e(low_level.hash_secret_raw(
        secret=key.encode(ENCODING__ascii),
        salt=salt,
        time_cost=defaults.time_cost,
        memory_cost=defaults.memory_cost,
        parallelism=defaults.parallelism,
        hash_len=length,
        type=low_level.Type.ID
    ))


def hash_password(data: str, salt: bytes = None):
    if salt is not None:
        salt, data_hash = key_stretcher(data, salt)
        return data_hash.decode(ENCODING__ascii)
    return PasswordHasher().hash(data)


def verify_password_hash(check_hash: str, password: str, salt: bytes = None):
    try:
        if salt is not None:
            return key_stretcher(password, salt=salt)[1].decode(ENCODING__ascii) == check_hash
        return PasswordHasher().verify(check_hash, password)
    except VerifyMismatchError:
        return False
