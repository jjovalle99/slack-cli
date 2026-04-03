import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from slack_cli.auth.cookies import decrypt_cookie_value, extract_xoxd


def _create_cookie_db(db_path: Path, encrypted_value: bytes | None = None) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB)")
        if encrypted_value is not None:
            conn.execute(
                "INSERT INTO cookies (host_key, name, encrypted_value) VALUES (?, ?, ?)",
                (".slack.com", "d", encrypted_value),
            )


def _encrypt_v10(plaintext: str, password: str = "peanuts", iterations: int = 1) -> bytes:
    """Encrypt a value the way Chromium does on Linux (v10)."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=16,
        salt=b"saltysalt",
        iterations=iterations,
    )
    key = kdf.derive(password.encode())
    iv = b" " * 16
    cipher = Cipher(algorithms.AES128(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return b"v10" + encrypted


def test_decrypt_v10_linux() -> None:
    original = "xoxd-test-cookie-value"
    encrypted = _encrypt_v10(original)
    result = decrypt_cookie_value(encrypted, password="peanuts", iterations=1)
    assert result == original


def test_decrypt_v10_with_domain_hash_prefix() -> None:
    """v24+ Chromium prepends a 32-byte SHA256 domain hash before the actual value."""
    domain_hash = b"\x00" * 32
    original = "xoxd-test-cookie-value"
    encrypted = _encrypt_v10(domain_hash.decode("latin-1") + original)
    result = decrypt_cookie_value(encrypted, password="peanuts", iterations=1)
    assert result == original


def test_decrypt_unencrypted_passthrough() -> None:
    raw = b"xoxd-plain-value"
    result = decrypt_cookie_value(raw, password="peanuts", iterations=1)
    assert result == "xoxd-plain-value"


def test_extract_xoxd_linux(tmp_path: Path) -> None:
    db_path = tmp_path / "Cookies"
    token = "xoxd-test-cookie-value"
    _create_cookie_db(db_path, _encrypt_v10(token))
    result = extract_xoxd(db_path, is_macos=False)
    assert result == token


def test_extract_xoxd_missing_cookie(tmp_path: Path) -> None:
    db_path = tmp_path / "Cookies"
    _create_cookie_db(db_path)

    with pytest.raises(ValueError, match="Cookie 'd' not found"):
        extract_xoxd(db_path, is_macos=False)


def test_extract_xoxd_missing_db(tmp_path: Path) -> None:
    db_path = tmp_path / "nonexistent" / "Cookies"
    with pytest.raises(FileNotFoundError, match="Cookie DB not found"):
        extract_xoxd(db_path, is_macos=False)


def test_extract_xoxd_macos(tmp_path: Path) -> None:
    db_path = tmp_path / "Cookies"
    token = "xoxd-test-cookie-value"
    _create_cookie_db(db_path, _encrypt_v10(token, password="keychain-pass", iterations=1003))

    with patch("slack_cli.auth.cookies._get_macos_keychain_password", return_value="keychain-pass"):
        result = extract_xoxd(db_path, is_macos=True)

    assert result == token
