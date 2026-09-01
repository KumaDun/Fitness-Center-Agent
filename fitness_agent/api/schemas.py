from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    subject_id: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class SessionResponse(UserResponse):
    expires_at: str


class ChatRequest(BaseModel):
    message: str
    guest_thread_id: str | None = None


class ChatResponse(BaseModel):
    answer: str


class ConfigResponse(BaseModel):
    auth_configured: bool
    required_env: list[str]
    mode: str
    openai_api_key: dict[str, str | int | bool | None]
    env_file: dict[str, str | list[str] | bool | None]


class OkResponse(BaseModel):
    ok: bool
