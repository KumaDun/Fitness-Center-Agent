from fastapi import APIRouter, Depends, HTTPException, status

from fitness_agent.api.dependencies import bearer_token, current_session, get_app_state
from fitness_agent.api.schemas import LoginRequest, LoginResponse, OkResponse, SessionResponse, UserResponse
from fitness_agent.api.state import AppState, Session

router = APIRouter(tags=["sessions"])

@router.post("/sessions", response_model=LoginResponse)
def create_session(
        request: LoginRequest,
        state: AppState = Depends(get_app_state),
) -> LoginResponse:
    user = state.auth.authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session = state.sessions.create(
        username = request.username,
        role = user.role,
        subject_id = user.subject_id,
    )

    return LoginResponse(
        token = session.token,
        user = UserResponse(
            username = request.username,
            role = session.role,
            subject_id = session.subject_id,
        )
    )

@router.get("/session", response_model = SessionResponse)
def get_session(session: Session = Depends(current_session)) -> SessionResponse:
    return SessionResponse(
        user=UserResponse(
            username=session.username,
            role=session.role,
            subject_id=session.subject_id,
        ),
        expires_at=session.expires_at.isoformat(),
    )

@router.delete("/session", response_model=OkResponse)
def delete_session(
    token: str = Depends(bearer_token),
    state: AppState = Depends(get_app_state),
) -> OkResponse:
    state.sessions.delete(token)
    return OkResponse(ok=True)