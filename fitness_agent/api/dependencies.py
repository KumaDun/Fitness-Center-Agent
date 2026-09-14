from fastapi import Depends, Request, Header, HTTPException, status

from fitness_agent.api.state import AppState, Session

def get_app_state(request: Request) -> AppState:
    return request.app.state.fitness_agent

def bearer_token(authorization: str | None = Header(default = None)) -> str:
    prefix = "Bearer "

    if authorization is None or not authorization.startswith(prefix):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="bearer_token: None authorization or not stating with correct prefix",
        )

    return authorization[len(prefix):].strip()

def current_session(
        state: AppState = Depends(get_app_state),
        token: str = Depends(bearer_token),
) -> Session:
    session = state.sessions.get(token)

    if session is None:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="current_session: Cannot find session with token:",
        )
    return session

def optional_bearer_token(
        authorization: str | None = Header(default = None),
) -> str | None:
    prefix = "Bearer "
    if authorization is None:
        return None
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="optional_bearer_token: None authorization or not stating with correct prefix",
        )

    return authorization[len(prefix):].strip()

def optional_session(
        state: AppState = Depends(get_app_state),
        token: str | None = Depends(optional_bearer_token),
) -> Session | None:
    if token is None:
        return None

    session = state.sessions.get(token)

    if session is None:
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="optional_session: Cannot find session with token:",
        )

    return session
