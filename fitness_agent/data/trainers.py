from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache
from importlib import resources
import json
import re
from typing import Any


@dataclass(frozen=True)
class TrainerProfile:
    trainer_id: str
    name: str
    role: str
    locations: list[str]
    specialties: list[str]
    background: str
    courses: list[str]
    certifications: list[str]
    consultation_available: bool
    notes: str
    last_updated: date


def load_trainer_profiles() -> list[TrainerProfile]:
    return [_trainer_from_row(row) for row in load_trainer_data()]


def load_trainer_data() -> list[dict[str, Any]]:
    return json.loads(resources.files("fitness_agent.data").joinpath("mock_trainers.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _trainer_profiles_cached() -> tuple[TrainerProfile, ...]:
    return tuple(load_trainer_profiles())


def search_trainer_profiles(query: str, limit: int = 6) -> list[dict[str, Any]]:
    stop_words = {"can", "could", "would", "should", "the", "and", "for", "with", "that", "this", "what"}
    terms = _search_terms(query, stop_words)
    if not terms:
        return []

    scored = []
    for trainer in _trainer_profiles_cached():
        haystack = " ".join(
            [
                trainer.trainer_id,
                trainer.name,
                trainer.role,
                " ".join(trainer.locations),
                " ".join(trainer.specialties),
                trainer.background,
                " ".join(trainer.courses),
                " ".join(trainer.certifications),
                trainer.notes,
            ]
        )
        score = len(terms & _search_terms(haystack, stop_words))
        if score:
            scored.append((score, trainer))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [_trainer_to_dict(trainer) for _, trainer in scored[:limit]]


def _trainer_from_row(row: dict[str, Any]) -> TrainerProfile:
    return TrainerProfile(
        trainer_id=str(row["trainer_id"]),
        name=str(row["name"]),
        role=str(row["role"]),
        locations=list(row["locations"]),
        specialties=list(row["specialties"]),
        background=str(row["background"]),
        courses=list(row["courses"]),
        certifications=list(row["certifications"]),
        consultation_available=bool(row["consultation_available"]),
        notes=str(row["notes"]),
        last_updated=date.fromisoformat(str(row["last_updated"])),
    )


def _trainer_to_dict(trainer: TrainerProfile) -> dict[str, Any]:
    row = asdict(trainer)
    row["last_updated"] = trainer.last_updated.isoformat()
    return row


def _search_terms(text: str, stop_words: set[str]) -> set[str]:
    terms = set()
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        if len(term) <= 2 or term in stop_words:
            continue
        terms.add(term)
        if len(term) > 3 and term.endswith("s"):
            terms.add(term[:-1])
    return terms
