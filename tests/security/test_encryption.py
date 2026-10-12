"""Tests for aetheros_security.encryption (AES-256-GCM)."""

import os

import pytest

from aetheros_security.encryption import (
    EncryptionManager,
    hmac_compare,
)


@pytest.fixture
def encryptor(tmp_path):
    return EncryptionManager(key_file=str(tmp_path / "test.key"))


class TestEncryption:
    def test_roundtrip_string(self, encryptor):
        plaintext = "hello world"
        encrypted = encryptor.encrypt(plaintext)
        assert encrypted != plaintext
        assert encryptor.decrypt(encrypted) == plaintext

    def test_roundtrip_bytes(self, encryptor):
        data = b"\x00\x01binary\xff"
        encrypted = encryptor.encrypt_bytes(data)
        assert encryptor.decrypt_bytes(encrypted) == data

    def test_aad_rejects_wrong_aad(self, encryptor):
        data = b"secret"
        encrypted = encryptor.encrypt_bytes(data, aad="correct")
        with pytest.raises(Exception):
            encryptor.decrypt_bytes(encrypted, aad="wrong")

    def test_tamper_detected(self, encryptor):
        import base64
        encrypted = encryptor.encrypt("sensitive")
        payload = bytearray(base64.b64decode(encrypted))
        payload[-1] ^= 0xFF
        with pytest.raises(Exception):
            encryptor.decrypt(base64.b64encode(bytes(payload)).decode("ascii"))

    def test_file_roundtrip(self, encryptor, tmp_path):
        src = tmp_path / "source.bin"
        enc = tmp_path / "data.enc"
        dec = tmp_path / "decoded.bin"
        src.write_bytes(os.urandom(4096))

        encryptor.encrypt_file(str(src), str(enc))
        assert enc.exists()
        encryptor.decrypt_file(str(enc), str(dec))
        assert src.read_bytes() == dec.read_bytes()

    def test_key_rotation_keeps_old_ciphertext(self, encryptor):
        ciphertext = encryptor.encrypt("before rotation")
        encryptor.rotate_key()
        assert encryptor.decrypt(ciphertext) == "before rotation"

    def test_password_derived_key(self, encryptor):
        key1, salt = encryptor.derive_key("correct horse battery staple")
        key2, _ = encryptor.derive_key("correct horse battery staple", salt=salt)
        key3, _ = encryptor.derive_key("different password", salt=salt)
        assert key1 == key2
        assert key1 != key3
        assert len(key1) == 32

    def test_hash_deterministic(self, encryptor):
        h1 = encryptor.hash("password123")
        h2 = encryptor.hash("password123")
        h3 = encryptor.hash("other")
        assert h1 == h2  # integrity hash (non-salted) is deterministic
        assert h1 != h3
        assert len(h1) == 64

    def test_hmac_compare_constant_time(self):
        assert hmac_compare("abc123", "abc123")
        assert not hmac_compare("abc123", "abc124")
        assert not hmac_compare("", "x")
