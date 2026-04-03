import sqlite3
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

V10_PREFIX = b"v10"
SALT = b"saltysalt"
IV = b" " * 16
KEY_LENGTH = 16
# Newer Chromium cookie DB versions (v24+) prepend a 32-byte SHA256 domain hash
DOMAIN_HASH_LENGTH = 32


def decrypt_cookie_value(encrypted: bytes, *, password: str, iterations: int) -> str:
    """Decrypt a Chromium-encrypted cookie value.

    If the value doesn't start with v10/v11 prefix, it's treated as plaintext.
    """
    if not encrypted.startswith(V10_PREFIX):
        return encrypted.decode()

    ciphertext = encrypted[len(V10_PREFIX) :]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=KEY_LENGTH,
        salt=SALT,
        iterations=iterations,
    )
    key = kdf.derive(password.encode())

    cipher = Cipher(algorithms.AES128(key), modes.CBC(IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    # Newer Chromium (v24+) prepends a 32-byte SHA256 domain hash before the value
    if (
        not plaintext.startswith(b"xoxd-")
        and plaintext[DOMAIN_HASH_LENGTH : DOMAIN_HASH_LENGTH + 5] == b"xoxd-"
    ):
        plaintext = plaintext[DOMAIN_HASH_LENGTH:]

    return plaintext.decode()


def _get_macos_keychain_password(service: str, account: str) -> str:
    """Retrieve a password from macOS Keychain via the security CLI."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def extract_xoxd(cookie_db_path: Path, *, is_macos: bool = True) -> str:
    """Read and decrypt the 'd' cookie from Slack's cookie SQLite DB."""
    if not cookie_db_path.exists():
        raise FileNotFoundError(f"Cookie DB not found: {cookie_db_path}")

    if is_macos:
        print(
            "Accessing macOS Keychain for Slack cookie decryption "
            "(system password prompt incoming)",
            file=sys.stderr,
        )
        password = _get_macos_keychain_password("Slack Safe Storage", "Slack")
        iterations = 1003
    else:
        password = "peanuts"
        iterations = 1

    conn = sqlite3.connect(f"file:{cookie_db_path}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT encrypted_value FROM cookies WHERE host_key = '.slack.com' AND name = 'd'",
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise ValueError("Cookie 'd' not found in Slack cookie DB")

    return decrypt_cookie_value(row[0], password=password, iterations=iterations)
