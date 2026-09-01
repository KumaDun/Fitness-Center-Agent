from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib import resources
import json
import re
from typing import Any


@dataclass(frozen=True)
class PolicyClause:
    document: str
    section: str
    text: str
    last_updated: date


def load_policy_clauses() -> list[PolicyClause]:
    policy_file = resources.files("fitness_agent.data").joinpath("policies.json")
    raw_rows = json.loads(policy_file.read_text(encoding="utf-8"))
    return [_policy_from_row(row) for row in raw_rows]


def _policy_from_row(row: dict[str, Any]) -> PolicyClause:
    return PolicyClause(
        document=str(row["document"]),
        section=str(row["section"]),
        text=str(row["text"]),
        last_updated=date.fromisoformat(str(row["last_updated"])),
    )


POLICIES = load_policy_clauses()


def search_policy_clauses(query: str, limit: int = 6) -> list[dict[str, str]]:
    stop_words = {"can", "could", "would", "should", "the", "and", "for", "with", "that", "this", "what"}
    terms = _search_terms(query, stop_words)
    scored = []
    for clause in POLICIES:
        haystack_terms = _search_terms(f"{clause.document} {clause.section} {clause.text}", stop_words)
        score = len(terms & haystack_terms)
        if score:
            scored.append((score, clause))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "document": clause.document,
            "section": clause.section,
            "text": clause.text,
            "last_updated": clause.last_updated.isoformat(),
        }
        for _, clause in scored[:limit]
    ]


def _search_terms(text: str, stop_words: set[str]) -> set[str]:
    terms = set()
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        if len(term) <= 2 or term in stop_words:
            continue
        terms.add(term)
        if len(term) > 3 and term.endswith("s"):
            terms.add(term[:-1])
    return terms
