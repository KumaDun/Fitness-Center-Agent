from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json
from typing import Any, get_args
from uuid import uuid4

from fitness_agent.models import Preference, PreferenceKind
from fitness_agent.persistence import PersistenceEvent, should_persist_immediately


ALLOWED_PREFERENCE_KINDS = set(get_args(PreferenceKind))
HEALTH_BLOCK_TERMS = {
    "acl",
    "allergy",
    "asthma",
    "blood",
    "calorie",
    "condition",
    "diet",
    "injury",
    "knee",
    "medical",
    "medication",
    "pain",
    "physio",
    "pregnant",
    "rehab",
    "surgery",
    "weight",
}


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PREFERENCES_PATH = ROOT_DIR / "fitness_agent.preferences.local.json"


class PreferenceStore:
    """Durable preference store boundary.

    The in-memory implementation is for local development. In production this
    should sit on a database table with the same contract.
    """

    def __init__(self) -> None:
        self._rows: dict[str, Preference] = {}

    def list_for_member(self, member_id: str) -> list[dict[str, Any]]:
        rows = [row for row in self._rows.values() if row.member_id == member_id]
        rows.sort(key=lambda row: row.stated_at)
        return [asdict(row) for row in rows]

    def remember(self, member_id: str, kind: str, value: str, source: str) -> dict[str, Any]:
        decision = validate_preference(kind, value, source)
        if not decision["ok"]:
            return decision

        preference = Preference(
            preference_id=f"pref_{uuid4().hex[:10]}",
            member_id=member_id,
            kind=kind,  # type: ignore[arg-type]
            value=value.strip(),
            stated_at=datetime.now(),
            source=source.strip(),
        )
        self._rows[preference.preference_id] = preference
        return {"ok": True, "preference": asdict(preference)}

    def forget(self, member_id: str, preference_id: str) -> dict[str, Any]:
        preference = self._rows.get(preference_id)
        if preference is None or preference.member_id != member_id:
            return {"ok": False, "reason": "preference_not_found"}
        del self._rows[preference_id]
        return {"ok": True, "forgotten_preference_id": preference_id}


def validate_preference(kind: str, value: str, source: str) -> dict[str, Any]:
    if kind not in ALLOWED_PREFERENCE_KINDS:
        return {"ok": False, "reason": "unsupported_preference_kind", "allowed_kinds": sorted(ALLOWED_PREFERENCE_KINDS)}
    if not value.strip():
        return {"ok": False, "reason": "empty_preference_value"}
    evidence = f"{value} {source}".lower()
    if any(term in evidence for term in HEALTH_BLOCK_TERMS):
        return {"ok": False, "reason": "health_or_body_data_not_stored"}
    if source.strip() == "":
        return {"ok": False, "reason": "missing_user_statement"}
    return {"ok": True}


class JsonPreferenceStore(PreferenceStore):
    def __init__(self, path: Path = DEFAULT_PREFERENCES_PATH) -> None:
        self._path = path
        self._rows = self._load_rows()

    def remember(self, member_id: str, kind: str, value: str, source: str) -> dict[str, Any]:
        result = super().remember(member_id, kind, value, source)
        if result["ok"] and should_persist_immediately(PersistenceEvent.PREFERENCE_REMEMBERED):
            self._save_rows()
        return result

    def forget(self, member_id: str, preference_id: str) -> dict[str, Any]:
        result = super().forget(member_id, preference_id)
        if result["ok"] and should_persist_immediately(PersistenceEvent.PREFERENCE_FORGOTTEN):
            self._save_rows()
        return result

    def _load_rows(self) -> dict[str, Preference]:
        if not self._path.exists():
            return {}
        raw_rows = json.loads(self._path.read_text(encoding="utf-8"))
        rows = {}
        for row in raw_rows:
            preference = Preference(
                preference_id=str(row["preference_id"]),
                member_id=str(row["member_id"]),
                kind=str(row["kind"]),  # type: ignore[arg-type]
                value=str(row["value"]),
                stated_at=datetime.fromisoformat(str(row["stated_at"])),
                source=str(row["source"]),
            )
            rows[preference.preference_id] = preference
        return rows

    def _save_rows(self) -> None:
        rows = []
        for preference in self._rows.values():
            row = asdict(preference)
            row["stated_at"] = preference.stated_at.isoformat()
            rows.append(row)
        rows.sort(key=lambda row: row["stated_at"])
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


DEFAULT_PREFERENCE_STORE = JsonPreferenceStore()
