from pydantic import BaseModel

class ConfigResponse(BaseModel):
    auth_configured: bool
    mode: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    role: str
    subject_id: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class SessionResponse(BaseModel):
    user: UserResponse
    expires_at: str

class OkResponse(BaseModel):
    ok: bool

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str