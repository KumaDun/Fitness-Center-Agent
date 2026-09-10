from fastapi import APIRouter, Depends
from pydantic import BaseModel

from fitness_agent.api.dependencies import get_app_state
from fitness_agent.api.schemas import ConfigResponse
from fitness_agent.api.state import AppState

router = APIRouter(tags=["system"])

class HealthResponse(BaseModel):
    status: str
    version: str

@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0"
    )

@router.get("/config", response_model=ConfigResponse)
def config(state: AppState = Depends(get_app_state)) -> ConfigResponse:
    return ConfigResponse(
        auth_configured=state.auth_configured,
        mode=state.mode,
    )