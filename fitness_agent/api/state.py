from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fitness_agent.agent import AgentMode, FitnessAgentService
from fitness_agent.agent.graph import DEFAULT_TEMPERATURE
from fitness_agent.api.auth import DemoAuthStore, InMemorySessionStore
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.env import EnvLoadResult


@dataclass
class AppState:
    agent_service: FitnessAgentService
    auth_config: DemoAuthStore | None
    sessions: InMemorySessionStore
    env_load_result: EnvLoadResult | None = None


def build_state(
    mode: AgentMode = AgentMode.AUTO,
    model: str = "openai:gpt-4.1-mini",
    temperature: float = DEFAULT_TEMPERATURE,
    auth_config_path: Path | None = None,
) -> AppState:
    auth_config = DemoAuthStore.from_env() if auth_config_path is None else DemoAuthStore.from_sources(auth_config_path)
    return AppState(
        agent_service=FitnessAgentService(
            mode=mode,
            model=model,
            temperature=temperature,
            store=MockGymStore(),
        ),
        auth_config=auth_config,
        sessions=InMemorySessionStore(),
    )
