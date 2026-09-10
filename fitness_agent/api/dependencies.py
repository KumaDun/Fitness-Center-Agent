from fastapi import Request, Header, HTTPException, status
from fastapi.params import Depends

from fitness_agent.api.state import AppState, Session

def get_app_state(request: Request) -> AppState:
    return request.app.state.fitness_agent

def bearer_token(authorization: str | None = Header(default = None)) -> str:
    prefix = "Bearer "

    if authorization is None or not authorization.startswith(prefix):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
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
            detail="unauthorized",
        )
    return session