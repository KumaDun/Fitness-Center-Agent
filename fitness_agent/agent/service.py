from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from fitness_agent.agent.deterministic import answer_demo
from fitness_agent.agent.graph import DEFAULT_TEMPERATURE, answer_with_llm
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.data.preferences import DEFAULT_PREFERENCE_STORE, PreferenceStore
from fitness_agent.models import Principal


class AgentMode(StrEnum):
    AUTO = "auto"
    DEMO = "demo"
    LLM = "llm"


@dataclass
class FitnessAgentService:
    mode: AgentMode = AgentMode.AUTO
    model: str = "openai:gpt-4.1-mini"
    temperature: float = DEFAULT_TEMPERATURE
    store: MockGymStore = field(default_factory=MockGymStore)
    preference_store: PreferenceStore = DEFAULT_PREFERENCE_STORE
    checkpointer: Any = field(default_factory=MemorySaver)

    def answer(self, message: str, principal: Principal) -> str:
        if self._should_use_llm():
            return answer_with_llm(
                message,
                principal,
                store=self.store,
                preference_store=self.preference_store,
                model=self.model,
                temperature=self.temperature,
                checkpointer=self.checkpointer,
            )
        return answer_demo(message, principal, store=self.store, preference_store=self.preference_store)

    def _should_use_llm(self) -> bool:
        if self.mode == AgentMode.LLM:
            return True
        if self.mode == AgentMode.AUTO:
            return bool(os.getenv("OPENAI_API_KEY")) or not self.model.startswith("openai:")
        return False
