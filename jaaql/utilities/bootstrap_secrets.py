import os
import secrets

from jaaql.utilities.vault import Vault


def forget_env_var(env_name: str) -> None:
    if env_name in os.environ:
        del os.environ[env_name]


def get_or_seed_vault_secret(vault: Vault, vault_key: str, env_name: str | None = None,
                             generate_if_missing: bool = False) -> str | None:
    if vault.has_obj(vault_key):
        if env_name is not None:
            forget_env_var(env_name)
        return vault.get_obj(vault_key)

    env_value = os.environ.get(env_name) if env_name is not None else None
    if env_value is not None and len(env_value.strip()) > 0:
        vault.insert_obj(vault_key, env_value)
        forget_env_var(env_name)
        return vault.get_obj(vault_key)

    if generate_if_missing:
        vault.insert_obj(vault_key, secrets.token_urlsafe(24))
        if env_name is not None:
            forget_env_var(env_name)
        return vault.get_obj(vault_key)

    if env_name is not None:
        forget_env_var(env_name)
    return None
