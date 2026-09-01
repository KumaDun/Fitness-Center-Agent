from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from fitness_agent.api.auth import Session
from fitness_agent.api.state import AppState


def get_app_state(request: Request) -> AppState:
    return request.app.state.fitness_agent


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return authorization[len(prefix) :].strip()


def optional_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str | None:
    prefix = "Bearer "
    if not authorization:
        return None
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return authorization[len(prefix) :].strip()


def current_session(
    state: Annotated[AppState, Depends(get_app_state)],
    token: Annotated[str, Depends(bearer_token)],
) -> Session:
    session = state.sessions.get(token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return session


def optional_session(
    state: Annotated[AppState, Depends(get_app_state)],
    token: Annotated[str | None, Depends(optional_bearer_token)],
) -> Session | None:
    if token is None:
        return None
    session = state.sessions.get(token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return session
