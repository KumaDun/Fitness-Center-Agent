from __future__ import annotations

import argparse

from fitness_agent.agent import AgentMode, FitnessAgentService, answer_demo
from fitness_agent.agent.graph import DEFAULT_TEMPERATURE
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.env import load_env_file
from fitness_agent.models import Principal, Role, guest_principal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fitness front-desk agent scaffold")
    parser.add_argument("message", nargs="*", help="Message to send to the agent")
    parser.add_argument("--role", choices=[role.value for role in Role], default=Role.MEMBER.value)
    parser.add_argument("--member-id", default="mem_001", help="Authenticated member id for member sessions")
    parser.add_argument("--staff-id", default="staff_001", help="Authenticated staff id for staff sessions")
    parser.add_argument("--llm", action="store_true", help="Require LangChain create_agent and the configured model provider")
    parser.add_argument("--model", default="openai:gpt-4.1-mini", help="LangChain model string")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="LLM sampling temperature")
    parser.add_argument("--demo", action="store_true", help="Run a few deterministic demo turns")
    return parser.parse_args()


def make_principal(args: argparse.Namespace) -> Principal:
    if args.role == Role.GUEST.value:
        return guest_principal()
    if args.role == Role.STAFF.value:
        return Principal(args.staff_id, Role.STAFF, allowed_locations=("Singapore", "Bangkok"))
    return Principal(args.member_id, Role.MEMBER)


def main() -> None:
    load_env_file()
    args = parse_args()
    principal = make_principal(args)

    if args.demo:
        messages = [
            "What classes are open tomorrow in Singapore?",
            "What is my membership plan?",
            "Can I bring a guest?",
            "What is my billing balance?",
        ]
        for message in messages:
            print(f"\n> {message}")
            print(answer_demo(message, principal))
        return

    message = " ".join(args.message).strip() or "What classes are open tomorrow in Singapore?"
    mode = AgentMode.LLM if args.llm else AgentMode.AUTO
    service = FitnessAgentService(mode=mode, model=args.model, temperature=args.temperature, store=MockGymStore())
    print(service.answer(message, principal))


if __name__ == "__main__":
    main()
