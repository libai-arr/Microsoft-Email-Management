import base64
import os

import pytest

from app.services.crypto import CryptoService


@pytest.fixture
def crypto(encryption_key: str) -> CryptoService:
    return CryptoService(encryption_key)


class TestCryptoService:
    def test_encrypt_decrypt_roundtrip(self, crypto: CryptoService):
        plaintext = "my-secret-password"
        encrypted = crypto.encrypt(plaintext)
        assert encrypted != plaintext.encode()
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self, crypto: CryptoService):
        plaintext = "same-input"
        enc1 = crypto.encrypt(plaintext)
        enc2 = crypto.encrypt(plaintext)
        assert enc1 != enc2

    def test_decrypt_with_wrong_key_raises(self, crypto: CryptoService):
        encrypted = crypto.encrypt("secret")
        wrong_key = base64.b64encode(os.urandom(32)).decode()
        wrong_crypto = CryptoService(wrong_key)
        with pytest.raises(Exception):
            wrong_crypto.decrypt(encrypted)

    def test_encrypt_empty_string(self, crypto: CryptoService):
        encrypted = crypto.encrypt("")
        assert crypto.decrypt(encrypted) == ""

    def test_encrypt_unicode(self, crypto: CryptoService):
        plaintext = "密码123"
        encrypted = crypto.encrypt(plaintext)
        assert crypto.decrypt(encrypted) == plaintext
