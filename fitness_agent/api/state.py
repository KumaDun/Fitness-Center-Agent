from dataclasses import dataclass, field

"""
Session store in-memory for temporary
Will replace with Postgres/Redis
"""

import secrets
from datetime import datetime, timedelta, timezone

@dataclass
class Session:
    token: str
    username: str
    role: str
    subject_id: str
    expires_at: datetime

class SessionStore:
    def __init__(self, ttl_minutes: int = 120):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.sessions: dict[str, Session] = {}

    def create(self, username: str, role: str, subject_id: str) -> Session:
        token = secrets.token_urlsafe(32)
        session = Session(
            token = token,
            username = username,
            role = role,
            subject_id = subject_id,
            expires_at = datetime.now(timezone.utc) + self.ttl
        )
        self.sessions[token] = session
        return session

    def get(self, token: str) -> Session | None:
        session = self.sessions.get(token, None)
        if session is None:
            return None

        if session.expires_at < datetime.now(timezone.utc):
            self.sessions.pop(token, None)
            return None

        return session

    def delete(self, token: str) -> None:
        self.sessions.pop(token, None)

from fitness_agent.api.auth import AuthStore

@dataclass
class AppState:
    mode: str = "demo"
    auth_configured: bool = False
    sessions: SessionStore = field(default_factory=SessionStore)
    auth: AuthStore = field(default_factory=AuthStore)

def build_state() -> AppState:
    return AppState()