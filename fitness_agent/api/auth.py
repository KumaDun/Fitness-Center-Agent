import hashlib
import hmac
import secrets
from dataclasses import dataclass

@dataclass
class DemoUser:
    username: str
    password: str
    role: str
    subject_id: str

class AuthStore:
    def __init__(self):
        self.users = {
            "Avery-Tan": DemoUser(
                username="Avery-Tan",
                password_hash = hash_password("local-password", salt="demo-salt"),
                role="member",
                subject_id="mem_001",
            )
        }

    def authenticate(self, username: str, password: str) -> DemoUser | None:
        user = self.users.get(username)

        if user is None:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

def hash_password(password: str, *, salt: str | None = None, iterations: int = 600_000) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected_digest = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pdkdf2_sha256":
        return False

    actual_hash = hash_password(
        password,
        salt = salt,
        iterations = int(iterations_text)
    )

    actual_digest = actual_hash.split("$", 3)[3]
    return hmac.compare_digest(actual_digest, expected_digest)