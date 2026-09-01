from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT_DIR / ".env"


@dataclass(frozen=True)
class EnvLoadResult:
    loaded_path: Path | None
    set_keys: tuple[str, ...]
    overwritten_keys: tuple[str, ...]
    preserved_keys: tuple[str, ...]


def load_env_file(path: Path = DEFAULT_ENV_PATH, override: bool = True) -> EnvLoadResult:
    """Load simple KEY=VALUE lines from .env.

    By default, .env overrides inherited process values so local app startup is
    controlled by the project file instead of a stale terminal environment.
    """
    if not path.exists():
        return EnvLoadResult(None, (), (), ())

    set_keys: list[str] = []
    overwritten_keys: list[str] = []
    preserved_keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _clean_env_value(value.strip())
        if not key:
            continue
        existing_value = os.environ.get(key)
        if not existing_value:
            os.environ[key] = value
            set_keys.append(key)
        elif override:
            os.environ[key] = value
            overwritten_keys.append(key)
        else:
            preserved_keys.append(key)

    return EnvLoadResult(path, tuple(set_keys), tuple(overwritten_keys), tuple(preserved_keys))


def env_value_fingerprint(key: str) -> dict[str, str | int | bool | None]:
    value = os.getenv(key)
    if not value:
        return {"configured": False, "prefix": None, "suffix": None, "length": 0}
    return {
        "configured": True,
        "prefix": value[:8],
        "suffix": value[-4:],
        "length": len(value),
    }


def _clean_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
