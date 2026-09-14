import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fitness_agent.env import load_env_file

DATABASE_URL_ENV = "DATABASE_URL"
load_env_file()

def get_database_url() -> str:
    database_url = os.environ.get(DATABASE_URL_ENV)

    if database_url is None:
        raise RuntimeError(f"Missing environment variable: {DATABASE_URL_ENV}")

    return database_url

engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)