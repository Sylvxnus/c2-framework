"""
Shared AES-256-GCM helpers for encrypting individual field values
(cmd going down, stdout/stderr coming back up) before they ride over HTTP.

PSK comes from the C2_PSK env var — a base64-encoded 32-byte key, baked
into both containers at compose time. A real deployment would derive a
per-implant key instead of sharing one PSK everywhere; noted in the README.
"""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key() -> bytes:
    return base64.b64decode(os.environ["C2_PSK"])


def encrypt(plaintext: str) -> str:
    aesgcm = AESGCM(_key())
    nonce = os.urandom(12)  # fresh nonce every call — never reuse with GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(token: str) -> str:
    aesgcm = AESGCM(_key())
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:12], raw[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode()