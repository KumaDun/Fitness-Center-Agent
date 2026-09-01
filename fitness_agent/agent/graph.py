from __future__ import annotations

import os
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.errors import GraphRecursionError
from langgraph.checkpoint.memory import MemorySaver

from fitness_agent.agent.prompts import FRONT_DESK_PROMPT
from fitness_agent.agent.tools import build_tools, visible_tool_names
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.data.preferences import DEFAULT_PREFERENCE_STORE, PreferenceStore
from fitness_agent.models import Principal

DEFAULT_TEMPERATURE = 0.3
DEFAULT_RECURSION_LIMIT = 30


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
    effective_checkpointer = checkpointer or MemorySaver()
    agent = build_agent(principal, store, preference_store, model, temperature, effective_checkpointer)
    config = {"configurable": {"thread_id": principal.thread_id}, "recursion_limit": DEFAULT_RECURSION_LIMIT}
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config=config)
    except GraphRecursionError as exc:
        _delete_checkpoint_thread(effective_checkpointer, principal.thread_id)
        raise RuntimeError("Agent stopped before completing its tool calls. The conversation state was reset.") from exc
    except Exception as exc:
        if not _is_incomplete_tool_call_error(exc):
            raise
        _delete_checkpoint_thread(effective_checkpointer, principal.thread_id)
        agent = build_agent(principal, store, preference_store, model, temperature, effective_checkpointer)
        result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config=config)
    return result["messages"][-1].content


def _openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM mode with an OpenAI model.")
    return api_key


def _is_incomplete_tool_call_error(exc: Exception) -> bool:
    text = str(exc)
    return (
        "tool_calls" in text
        and "tool_call_id" in text
        and "did not have response messages" in text
    )


def _delete_checkpoint_thread(checkpointer: Any, thread_id: str) -> None:
    delete_thread = getattr(checkpointer, "delete_thread", None)
    if callable(delete_thread):
        delete_thread(thread_id)
