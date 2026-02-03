from __future__ import annotations

import os
from typing import Optional

def _get_key_bytes() -> Optional[bytes]:
    """
    EMAIL_CRED_MASTER_KEY should be a urlsafe-base64 32-byte key (Fernet key).
    Example to generate:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    k = os.getenv("EMAIL_CRED_MASTER_KEY")
    if not k:
        return None
    return k.encode("utf-8")

def encrypt_secret(plaintext: str) -> str:
    key = _get_key_bytes()
    if not plaintext:
        return ""
    if not key:
        # Dev-friendly fallback (NOT secure). Prefer setting EMAIL_CRED_MASTER_KEY in production.
        return "plain:" + plaintext
    from cryptography.fernet import Fernet
    f = Fernet(key)
    return "enc:" + f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    if ciphertext.startswith("plain:"):
        return ciphertext[len("plain:"):]
    if not ciphertext.startswith("enc:"):
        return ciphertext  # unknown format; best-effort
    key = _get_key_bytes()
    if not key:
        raise RuntimeError("EMAIL_CRED_MASTER_KEY is required to decrypt secrets")
    from cryptography.fernet import Fernet
    f = Fernet(key)
    token = ciphertext[len("enc:"):]
    return f.decrypt(token.encode("utf-8")).decode("utf-8")
