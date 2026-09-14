from fastapi import APIRouter, Depends, HTTPException, status

from fitness_agent.api.dependencies import get_app_state, optional_session
from fitness_agent.api.schemas import ChatResponse, ChatRequest
from fitness_agent.api.state import AppState, Session

router = APIRouter(tags=["chat"])

@router.post("/chat/messages", response_model=ChatResponse)
def create_chat_message(
        request: ChatRequest,
        state: AppState = Depends(get_app_state),
        session: Session | None = Depends(optional_session),
) -> ChatResponse:
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message cannot be empty",
        )

    if session is None:
        role = "guest"
        subject_id = "anonymous"
    else:
        role = session.role
        subject_id = session.subject_id

    answer = state.chat.answer(
        message=message,
        role=role,
        subject_id=subject_id,
    )

    return ChatResponse(answer=answer)