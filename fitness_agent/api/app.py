from fastapi import FastAPI

from fitness_agent.api.routes import system, sessions
from fitness_agent.api.state import build_state

def create_app() -> FastAPI:
    app = FastAPI(
        title="Fitness Agent API",
        version="0.1.0",
    )
    app.state.fitness_agent = build_state()
    app.include_router(system.router, prefix="/api/v1")
    app.include_router(sessions.router, prefix="/api/v1")

    return app

app = create_app()