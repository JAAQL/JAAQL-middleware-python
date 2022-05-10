import os
from jaaql.utilities import crypt_utils
import json

FILE__vault = "vault"
FILE__vault_salt = "vault_salt"

DIR__vault = "vault"

ENCODING_utf = "UTF-8"


class Vault:

    def __init__(self, vault_key: str, vault_dir: str):
        crypt_utils.validate_password(vault_key)

        if not os.path.exists(vault_dir) or not os.path.isdir(vault_dir):
            os.makedirs(vault_dir)

        self._vault_dir = vault_dir
        self._vault_key = self._gen_key(vault_key)
        self._vault = self._load()

    def _load(self):
        vault_path = self._get_store_path(FILE__vault)

        vault = {}

        if os.path.exists(vault_path):
            f = open(vault_path, "rb")
            vault = json.loads(crypt_utils.decrypt(self._vault_key, f.read().decode(ENCODING_utf)))
        else:
            self._vault = {}
            self.insert_obj("init", "val")

        return vault

    def reload(self):
        self._load()

    def _persist(self):
        data = crypt_utils.encrypt(self._vault_key, json.dumps(self._vault)).encode(ENCODING_utf)
        f = open(self._get_store_path(FILE__vault), "wb")
        f.write(data)
        f.close()

    def insert_obj(self, key: str, value: str):
        self._vault[key] = value
        self._persist()
        self._load()

    def has_obj(self, key: str) -> bool:
        return key in self._vault

    def get_obj(self, key: str):
        return self._vault[key]

    def _get_store_path(self, file: str) -> str:
        return os.path.join(self._vault_dir, file)

    def _gen_key(self, vault_key: str) -> bytes:
        salt = None
        vault_salt_path = self._get_store_path(FILE__vault_salt)

        if os.path.exists(vault_salt_path):
            f = open(vault_salt_path, "rb")
            salt = f.read()
            f.close()

        salt, vault_key = crypt_utils.key_stretcher(vault_key, salt)

        if not os.path.exists(vault_salt_path):
            f = open(vault_salt_path, "wb")
            f.write(salt)
            f.close()

        return vault_key
