import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoService:
    NONCE_SIZE = 12

    def __init__(self, key_b64: str):
        key_bytes = base64.b64decode(key_b64)
        if len(key_bytes) != 32:
            raise ValueError("ENCRYPTION_KEY must be 32 bytes (base64-encoded)")
        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ciphertext

    def decrypt(self, data: bytes) -> str:
        nonce = data[: self.NONCE_SIZE]
        ciphertext = data[self.NONCE_SIZE :]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
