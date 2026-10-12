"""Multi-Factor Authentication — TOTP, recovery codes."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time
from typing import Optional

logger = logging.getLogger(__name__)

TOTP_INTERVAL = 30
TOTP_DIGITS = 6
ISSUER = "AetherOS"


def _generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8")


def _totp(secret: str, timestamp: int = None) -> str:
    if timestamp is None:
        timestamp = int(time.time())
    counter = timestamp // TOTP_INTERVAL
    msg = struct.pack(">Q", counter)
    key = base64.b32decode(secret.upper(), True)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF) % (
        10 ** TOTP_DIGITS)
    return str(code).zfill(TOTP_DIGITS)


def _generate_recovery_codes(count: int = 8) -> list[str]:
    codes = []
    for _ in range(count):
        code = secrets.token_hex(4).upper()
        codes.append(f"{code[:4]}-{code[4:]}")
    return codes


class TOTPProvider:
    def __init__(self, issuer: str = ISSUER):
        self.issuer = issuer

    def generate_secret(self) -> str:
        return _generate_totp_secret()

    def generate_uri(self, username: str, secret: str) -> str:
        return (f"otpauth://totp/{self.issuer}:{username}?"
                f"secret={secret}&issuer={self.issuer}&digits={TOTP_DIGITS}")

    def validate(self, secret: str, code: str) -> bool:
        if not code or not secret:
            return False
        code = code.strip().replace(" ", "")
        current = _totp(secret)
        if code == current:
            return True
        prev = _totp(secret, int(time.time()) - TOTP_INTERVAL)
        if code == prev:
            return True
        next_code = _totp(secret, int(time.time()) + TOTP_INTERVAL)
        return code == next_code


class MFAManager:
    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self.provider = TOTPProvider()

    def setup_mfa(self, username: str) -> dict:
        secret = self.provider.generate_secret()
        uri = self.provider.generate_uri(username, secret)
        codes = _generate_recovery_codes()
        return {
            "secret": secret,
            "uri": uri,
            "qrcode_url": uri,
            "recovery_codes": codes,
        }

    def verify_setup(self, secret: str, code: str) -> bool:
        return self.provider.validate(secret, code)

    def verify_mfa(self, user_id: str, secret: str, code: str) -> bool:
        return self.provider.validate(secret, code)

    def verify_recovery_code(self, code: str,
                              stored_codes: list[str]) -> bool:
        clean = code.strip().upper()
        if clean in stored_codes:
            stored_codes.remove(clean)
            return True
        return False

    def validate_backup_code(self, code: str,
                              backup_codes: list[str]) -> bool:
        return self.verify_recovery_code(code, backup_codes)
