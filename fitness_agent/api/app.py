from __future__ import annotations

import argparse
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fitness_agent.agent import AgentMode
from fitness_agent.agent.graph import DEFAULT_TEMPERATURE
from fitness_agent.api.auth import LOCAL_CONFIG_PATH
from fitness_agent.api.routes import chat, config, sessions
from fitness_agent.api.state import build_state
from fitness_agent.env import load_env_file


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"


def create_app(
    mode: AgentMode = AgentMode.AUTO,
    model: str = "openai:gpt-4.1-mini",
    temperature: float = DEFAULT_TEMPERATURE,
    auth_config_path: Path | None = LOCAL_CONFIG_PATH,
    load_dotenv: bool = True,
) -> FastAPI:
    env_load_result = None
    if load_dotenv:
        env_load_result = load_env_file()

    app = FastAPI(title="Fitness Agent API", version="0.2.0")
    app.state.fitness_agent = build_state(
        mode=mode,
        model=model,
        temperature=temperature,
        auth_config_path=auth_config_path,
    )
    app.state.fitness_agent.env_load_result = env_load_result
    app.include_router(config.router)
    app.include_router(sessions.router)
    app.include_router(chat.router)

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        target = FRONTEND_DIR / path
        if target.is_file() and target.resolve().is_relative_to(FRONTEND_DIR.resolve()):
            return FileResponse(target)
        return FileResponse(FRONTEND_DIR / "index.html")

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Fitness Agent FastAPI app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--llm", action="store_true", help="Use the LangChain agent instead of the deterministic router")
    parser.add_argument("--demo", action="store_true", help="Force the deterministic offline demo router")
    parser.add_argument("--model", default="openai:gpt-4.1-mini")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    return parser.parse_args()


def main() -> None:
    import uvicorn

    args = parse_args()
    mode = AgentMode.DEMO if args.demo else AgentMode.LLM if args.llm else AgentMode.AUTO
    uvicorn.run(
        create_app(mode=mode, model=args.model, temperature=args.temperature),
        host=args.host,
        port=args.port,
    )


app = create_app()


if __name__ == "__main__":
    main()
