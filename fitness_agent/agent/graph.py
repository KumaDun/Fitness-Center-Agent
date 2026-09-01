from __future__ import annotations

import os
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver

from fitness_agent.agent.prompts import FRONT_DESK_PROMPT
from fitness_agent.agent.tools import build_tools, visible_tool_names
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.data.preferences import DEFAULT_PREFERENCE_STORE, PreferenceStore
from fitness_agent.models import Principal

DEFAULT_TEMPERATURE = 0.3


def build_agent(
    principal: Principal,
    store: MockGymStore | None = None,
    preference_store: PreferenceStore | None = None,
    model: str = "openai:gpt-4.1-mini",
    temperature: float = DEFAULT_TEMPERATURE,
    checkpointer: Any | None = None,
):
    chat_model_kwargs = {"temperature": temperature}
    if model.startswith("openai:"):
        chat_model_kwargs["api_key"] = _openai_api_key()
    chat_model = init_chat_model(model=model, **chat_model_kwargs)
    return create_agent(
        model=chat_model,
        tools=build_tools(principal, store, preference_store),
        system_prompt=(
            FRONT_DESK_PROMPT
            + f"\nCurrent principal role: {principal.role.value}; subject_id: {principal.subject_id}."
            + f"\nVisible tools: {', '.join(visible_tool_names(principal))}"
        ),
        checkpointer=checkpointer or MemorySaver(),
    )


def answer_with_llm(
    message: str,
    principal: Principal,
    store: MockGymStore | None = None,
    preference_store: PreferenceStore | None = None,
    model: str = "openai:gpt-4.1-mini",
    temperature: float = DEFAULT_TEMPERATURE,
    checkpointer: Any | None = None,
) -> str:
    agent = build_agent(principal, store, preference_store, model, temperature, checkpointer)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": principal.thread_id}, "recursion_limit": 10},
    )
    return result["messages"][-1].content


def _openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM mode with an OpenAI model.")
    return api_key
