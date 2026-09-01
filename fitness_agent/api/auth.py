from __future__ import annotations

import hmac
import hashlib
import os
import secrets
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fitness_agent.models import Principal, Role


ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_CONFIG_PATH = ROOT_DIR / "fitness_agent.local.ini"
AUTH_CONFIG_SECTION = "demo_auth"
AUTH_USERS_SECTION = "demo_users"
USERNAME_ENV = "FITNESS_DEMO_USERNAME"
PASSWORD_ENV = "FITNESS_DEMO_PASSWORD"
PASSWORD_HASH_ENV = "FITNESS_DEMO_PASSWORD_HASH"
ROLE_ENV = "FITNESS_DEMO_ROLE"
MEMBER_ID_ENV = "FITNESS_DEMO_MEMBER_ID"
STAFF_ID_ENV = "FITNESS_DEMO_STAFF_ID"
@dataclass(frozen=True)
class DemoAuthConfig:
    username: str
    password_hash: str | None
    password: str | None
    role: Role
    member_id: str
    staff_id: str

    @classmethod
    def from_env(cls) -> "DemoAuthConfig | None":
        username = os.getenv(USERNAME_ENV)
        password_hash = os.getenv(PASSWORD_HASH_ENV)
        password = os.getenv(PASSWORD_ENV)
        if not username or not (password_hash or password):
            return None

        role = _parse_login_role(os.getenv(ROLE_ENV, Role.MEMBER.value))
        return cls(
            username=username,
            password_hash=password_hash,
            password=password,
            role=role,
            member_id=os.getenv(MEMBER_ID_ENV, "mem_001"),
            staff_id=os.getenv(STAFF_ID_ENV, "staff_001"),
        )

    @classmethod
    def from_sources(cls, config_path: Path = LOCAL_CONFIG_PATH) -> "DemoAuthConfig | None":
        values = _read_auth_config(config_path)

        username = values.get("username") or os.getenv(USERNAME_ENV)
        password_hash = values.get("password_hash") or os.getenv(PASSWORD_HASH_ENV)
        password = values.get("password") or os.getenv(PASSWORD_ENV)
        if not username or not (password_hash or password):
            return None

        role = _parse_login_role(values.get("role") or os.getenv(ROLE_ENV) or Role.MEMBER.value)
        return cls(
            username=username,
            password_hash=password_hash,
            password=password,
            role=role,
            member_id=values.get("member_id") or os.getenv(MEMBER_ID_ENV) or "mem_001",
            staff_id=values.get("staff_id") or os.getenv(STAFF_ID_ENV) or "staff_001",
        )

    def principal(self) -> Principal:
        if self.role == Role.STAFF:
            return Principal(self.staff_id, Role.STAFF, allowed_locations=("Singapore", "Bangkok"))
        return Principal(self.member_id, Role.MEMBER)


@dataclass(frozen=True)
class DemoAuthStore:
    users: tuple[DemoAuthConfig, ...]

    @classmethod
    def from_env(cls) -> "DemoAuthStore | None":
        config = DemoAuthConfig.from_env()
        if config is None:
            return None
        return cls((config,))

    @classmethod
    def from_sources(cls, config_path: Path = LOCAL_CONFIG_PATH) -> "DemoAuthStore | None":
        configs = _read_auth_users_config(config_path)
        if configs:
            return cls(tuple(configs))

        config = DemoAuthConfig.from_sources(config_path)
        if config is None:
            return None
        return cls((config,))

    def authenticate(self, username: str, password: str) -> Principal | None:
        for config in self.users:
            principal = authenticate_single_user(username, password, config)
            if principal is not None:
                return principal
        return None


@dataclass(frozen=True)
class Session:
    token: str
    principal: Principal
    username: str
    expires_at: datetime


class InMemorySessionStore:
    def __init__(self, ttl_minutes: int = 120) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[str, Session] = {}

    def create(self, username: str, principal: Principal) -> Session:
        token = secrets.token_urlsafe(32)
        session = Session(
            token=token,
            principal=principal,
            username=username,
            expires_at=datetime.now(timezone.utc) + self._ttl,
        )
        self._sessions[token] = session
        return session

    def get(self, token: str) -> Session | None:
        session = self._sessions.get(token)
        if session is None:
            return None
        if session.expires_at <= datetime.now(timezone.utc):
            self._sessions.pop(token, None)
            return None
        return session

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)


def authenticate(username: str, password: str, config: DemoAuthConfig | DemoAuthStore) -> Principal | None:
    if isinstance(config, DemoAuthStore):
        return config.authenticate(username, password)
    return authenticate_single_user(username, password, config)


def authenticate_single_user(username: str, password: str, config: DemoAuthConfig) -> Principal | None:
    username_ok = hmac.compare_digest(username, config.username)
    password_ok = verify_password(password, config.password_hash) if config.password_hash else hmac.compare_digest(password, config.password or "")
    if not username_ok or not password_ok:
        return None
    return config.principal()


def hash_password(password: str, *, iterations: int = 600_000, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not encoded_hash:
        return False
    try:
        algorithm, iterations_text, salt, expected = encoded_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hash_password(password, iterations=iterations, salt=salt).split("$", 3)[3]
    return hmac.compare_digest(actual, expected)


def _read_auth_config(config_path: Path) -> dict[str, str]:
    if not config_path.exists():
        return {}

    parser = ConfigParser()
    parser.optionxform = str
    parser.read(config_path)
    if not parser.has_section(AUTH_CONFIG_SECTION):
        return {}

    return {
        key: value.strip()
        for key, value in parser.items(AUTH_CONFIG_SECTION)
        if value.strip()
    }


def _read_auth_users_config(config_path: Path) -> list[DemoAuthConfig]:
    if not config_path.exists():
        return []

    parser = ConfigParser()
    parser.optionxform = str
    parser.read(config_path)
    if not parser.has_section(AUTH_USERS_SECTION):
        return []

    configs = []
    for username, raw_value in parser.items(AUTH_USERS_SECTION):
        parts = [part.strip() for part in raw_value.split(",")]
        values = {}
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            values[key.strip()] = value.strip()

        password_hash = values.get("password_hash")
        password = values.get("password")
        if not (password_hash or password):
            continue

        configs.append(
            DemoAuthConfig(
                username=username.strip(),
                password_hash=password_hash,
                password=password,
                role=_parse_login_role(values.get("role", Role.MEMBER.value)),
                member_id=values.get("member_id", "mem_001"),
                staff_id=values.get("staff_id", "staff_001"),
            )
        )
    return configs


def _parse_login_role(value: str) -> Role:
    role_value = value.lower().strip()
    if role_value == Role.MEMBER.value:
        return Role.MEMBER
    if role_value == Role.STAFF.value:
        return Role.STAFF
    raise ValueError(
        f"Invalid demo login role {value!r}. Use 'member' or 'staff'. Guest access is anonymous and does not use demo credentials."
    )
