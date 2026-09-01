from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from fitness_agent.api.auth import authenticate
from fitness_agent.api.dependencies import bearer_token, current_session, get_app_state
from fitness_agent.api.schemas import LoginRequest, LoginResponse, OkResponse, SessionResponse, UserResponse
from fitness_agent.api.state import AppState


router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions", response_model=LoginResponse)
def create_session(
    request: LoginRequest,
    state: Annotated[AppState, Depends(get_app_state)],
) -> LoginResponse:
    if state.auth_config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_not_configured",
        )

    principal = authenticate(request.username, request.password, state.auth_config)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    session = state.sessions.create(request.username, principal)
    return LoginResponse(
        token=session.token,
        user=UserResponse(
            username=session.username,
            subject_id=principal.subject_id,
            role=principal.role.value,
        ),
    )


@router.post("/login", response_model=LoginResponse)
def login_alias(
    request: LoginRequest,
    state: Annotated[AppState, Depends(get_app_state)],
) -> LoginResponse:
    return create_session(request, state)


@router.get("/session", response_model=SessionResponse)
def get_session(session=Depends(current_session)) -> SessionResponse:
    return SessionResponse(
        username=session.username,
        subject_id=session.principal.subject_id,
        role=session.principal.role.value,
        expires_at=session.expires_at.isoformat(),
    )


@router.get("/me", response_model=SessionResponse)
def me_alias(session=Depends(current_session)) -> SessionResponse:
    return get_session(session)


@router.delete("/session", response_model=OkResponse)
def delete_session(
    token: Annotated[str, Depends(bearer_token)],
    state: Annotated[AppState, Depends(get_app_state)],
) -> OkResponse:
    state.sessions.revoke(token)
    return OkResponse(ok=True)


@router.post("/logout", response_model=OkResponse)
def logout_alias(
    token: Annotated[str, Depends(bearer_token)],
    state: Annotated[AppState, Depends(get_app_state)],
) -> OkResponse:
    state.sessions.revoke(token)
    return OkResponse(ok=True)
