from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from fitness_agent.api.auth import PASSWORD_ENV, PASSWORD_HASH_ENV, USERNAME_ENV
from fitness_agent.api.dependencies import get_app_state
from fitness_agent.api.schemas import ConfigResponse
from fitness_agent.api.state import AppState
from fitness_agent.env import env_value_fingerprint


router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=ConfigResponse)
def get_config(state: Annotated[AppState, Depends(get_app_state)]) -> ConfigResponse:
    env_load_result = state.env_load_result
    return ConfigResponse(
        auth_configured=state.auth_config is not None,
        required_env=[USERNAME_ENV, f"{PASSWORD_HASH_ENV} or {PASSWORD_ENV}"],
        mode=state.agent_service.mode.value,
        openai_api_key=env_value_fingerprint("OPENAI_API_KEY"),
        env_file={
            "loaded": env_load_result is not None and env_load_result.loaded_path is not None,
            "path": str(env_load_result.loaded_path) if env_load_result and env_load_result.loaded_path else None,
            "set_keys": list(env_load_result.set_keys) if env_load_result else [],
            "overwritten_keys": list(env_load_result.overwritten_keys) if env_load_result else [],
            "preserved_keys": list(env_load_result.preserved_keys) if env_load_result else [],
        },
    )
