from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from fitness_agent.api.dependencies import get_app_state, optional_session
from fitness_agent.api.schemas import ChatRequest, ChatResponse
from fitness_agent.api.state import AppState
from fitness_agent.models import guest_principal


router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat/messages", response_model=ChatResponse)
def create_chat_message(
    request: ChatRequest,
    state: Annotated[AppState, Depends(get_app_state)],
    session=Depends(optional_session),
) -> ChatResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_message")

    try:
        principal = session.principal if session is not None else guest_principal(request.guest_thread_id or "anonymous")
        answer = state.agent_service.answer(message, principal)
    except Exception as exc:
        logger.exception("Agent response failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="agent_failed") from exc
    return ChatResponse(answer=answer)


@router.post("/chat", response_model=ChatResponse)
def chat_alias(
    request: ChatRequest,
    state: Annotated[AppState, Depends(get_app_state)],
    session=Depends(optional_session),
) -> ChatResponse:
    return create_chat_message(request, state, session)
