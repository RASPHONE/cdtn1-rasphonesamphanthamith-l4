"""Password hashing for login accounts (BT3 security checklist item 4, BUG-014).

PBKDF2-HMAC-SHA256 from the Python standard library, 600,000 iterations
(OWASP Password Storage Cheat Sheet value for PBKDF2-SHA256), 16-byte random salt.
Stored format, one string per account:

    pbkdf2_sha256$<iterations>$<salt, base64>$<hash, base64>

The iteration count is stored with the hash, so it can be raised later without
breaking existing accounts.
"""
import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join([
        ALGORITHM,
        str(iterations),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ])


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


# Checked when the username does not exist, so a wrong username takes about as long
# as a wrong password and response time does not reveal which usernames exist.
_DUMMY_HASH = hash_password("not-a-real-password")


def verify_against_dummy(password: str) -> None:
    verify_password(password, _DUMMY_HASH)
