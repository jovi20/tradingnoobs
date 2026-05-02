"""
Trading Noobs Backend - Credential Encryption Helpers
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from config import get_settings


settings = get_settings()


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(secret_value: str) -> str:
    return _fernet().encrypt(secret_value.encode("utf-8")).decode("utf-8")


def decrypt_secret(secret_ciphertext: str) -> str:
    return _fernet().decrypt(secret_ciphertext.encode("utf-8")).decode("utf-8")


def mask_secret(secret_value: str | None) -> str | None:
    if not secret_value:
        return None
    if len(secret_value) <= 8:
        return "*" * len(secret_value)
    return f"{secret_value[:4]}{'*' * (len(secret_value) - 8)}{secret_value[-4:]}"
