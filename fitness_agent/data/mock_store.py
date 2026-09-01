from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date, datetime
from functools import lru_cache
from importlib import resources
import json
from typing import Any

from fitness_agent.models import BillingSummary, Booking, ClassSession, Membership


@dataclass(frozen=True)
class MockGymRepository:
    facilities: dict[str, dict[str, Any]]
    members: dict[str, dict[str, Any]]
    billing: dict[str, dict[str, Any]]
    classes: dict[str, dict[str, Any]]
    bookings: dict[str, dict[str, Any]]


class MockGymStore:
    """Purpose-built mock system of record for the first implementation phase."""

    def __init__(self, repository: MockGymRepository | None = None) -> None:
        self._repo = repository or create_mock_repository()

    def facility_info(self, location: str) -> dict[str, Any]:
        info = self._repo.facilities.get(location.title())
        if not info:
            return {"ok": False, "reason": "unknown_location", "fresh_as_of": datetime.now().isoformat(timespec="seconds")}
        return {"ok": True, **info, "fresh_as_of": datetime.now().isoformat(timespec="seconds")}

    def class_schedule(self, start: date, end: date, location: str | None = None) -> list[dict[str, Any]]:
        rows = []
        for class_row in self._repo.classes.values():
            session = _class_session_from_row(class_row)
            if start <= session.starts_at.date() <= end and (location is None or session.location.lower() == location.lower()):
                rows.append(asdict(session) | {"spots_left": session.spots_left, "fresh_as_of": datetime.now().isoformat(timespec="seconds")})
        return sorted(rows, key=lambda row: row["starts_at"])

    def membership_for(self, member_id: str) -> dict[str, Any]:
        membership = _membership_from_row(self._repo.members[member_id])
        return asdict(membership) | {"fresh_as_of": datetime.now().isoformat(timespec="seconds")}

    def billing_for(self, member_id: str) -> dict[str, Any]:
        billing = _billing_from_row(self._repo.billing[member_id])
        return asdict(billing) | {"fresh_as_of": datetime.now().isoformat(timespec="seconds")}

    def bookings_for(self, member_id: str) -> list[dict[str, Any]]:
        rows = []
        for booking_row in self._repo.bookings.values():
            booking = _booking_from_row(booking_row)
            if booking.member_id == member_id:
                session = _class_session_from_row(self._repo.classes[booking.session_id])
                rows.append(asdict(booking) | {"class_name": session.name, "starts_at": session.starts_at, "location": session.location})
        return sorted(rows, key=lambda row: row["starts_at"])

    def book_class(self, member_id: str, session_id: str) -> dict[str, Any]:
        prepared = self.prepare_booking(member_id, session_id)
        if not prepared.get("ok"):
            return prepared

        booking_id = self._next_booking_id()
        booking_row = {
            "booking_id": booking_id,
            "member_id": member_id,
            "session_id": session_id,
            "status": "booked",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._repo.bookings[booking_id] = booking_row
        self._repo.classes[session_id]["booked"] += 1

        session = _class_session_from_row(self._repo.classes[session_id])
        booking = _booking_from_row(booking_row)
        return asdict(booking) | {
            "ok": True,
            "class_name": session.name,
            "starts_at": session.starts_at,
            "location": session.location,
            "spots_left": session.spots_left,
            "fresh_as_of": datetime.now().isoformat(timespec="seconds"),
        }

    def prepare_booking(self, member_id: str, session_id: str) -> dict[str, Any]:
        session_row = self._repo.classes.get(session_id)
        if session_row is None:
            return {"ok": False, "reason": "unknown_session"}
        session = _class_session_from_row(session_row)
        membership = _membership_from_row(self._repo.members[member_id])
        if membership.status != "active":
            return {"ok": False, "reason": f"membership_{membership.status}"}
        if session.spots_left < 1:
            return {"ok": False, "reason": "class_full", "waitlist_available": True}
        if session.plan_required == "Premium" and membership.plan != "Premium":
            return {"ok": False, "reason": "plan_not_covered", "required_plan": session.plan_required}
        for booking in self.bookings_for(member_id):
            if booking["status"] == "booked" and booking["starts_at"] == session.starts_at:
                return {"ok": False, "reason": "schedule_clash", "existing_booking_id": booking["booking_id"]}
        return {
            "ok": True,
            "requires_confirmation": True,
            "message": "Booking is available but not written yet. Show this as a confirmation before committing.",
            "session": asdict(session) | {"spots_left": session.spots_left},
        }

    def lookup_member(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        matches = []
        for member_row in self._repo.members.values():
            member = _membership_from_row(member_row)
            if query_lower in member.name.lower() or query_lower in member.member_id.lower():
                matches.append({"member_id": member.member_id, "name": member.name, "home_location": member.home_location, "status": member.status})
        return matches

    def class_occupancy(self, location: str, day: date) -> list[dict[str, Any]]:
        return [
            {
                "session_id": row["session_id"],
                "name": row["name"],
                "starts_at": row["starts_at"],
                "capacity": row["capacity"],
                "booked": row["booked"],
                "utilisation": round(row["booked"] / row["capacity"], 2),
            }
            for row in self.class_schedule(day, day, location)
        ]

    def _next_booking_id(self) -> str:
        numeric_ids = [
            int(booking_id.removeprefix("bk_"))
            for booking_id in self._repo.bookings
            if booking_id.startswith("bk_") and booking_id.removeprefix("bk_").isdigit()
        ]
        return f"bk_{max(numeric_ids, default=0) + 1:03d}"


def load_mock_store_data() -> dict[str, Any]:
    return deepcopy(_load_mock_store_data_cached())


@lru_cache(maxsize=1)
def _load_mock_store_data_cached() -> dict[str, Any]:
    return {
        "facilities": _load_json_fixture("mock_facilities.json"),
        "members": _load_json_fixture("mock_members.json"),
        "billing": _load_json_fixture("mock_billing.json"),
        "classes": _load_json_fixture("mock_classes.json"),
        "bookings": _load_json_fixture("mock_bookings.json"),
    }


def _load_json_fixture(filename: str) -> list[dict[str, Any]]:
    return json.loads(resources.files("fitness_agent.data").joinpath(filename).read_text(encoding="utf-8"))


def create_mock_repository() -> MockGymRepository:
    data = load_mock_store_data()
    return _repository_from_data(data)


@lru_cache(maxsize=1)
def get_default_mock_repository() -> MockGymRepository:
    data = load_mock_store_data()
    return _repository_from_data(data)


def _repository_from_data(data: dict[str, Any]) -> MockGymRepository:
    return MockGymRepository(
        facilities={row["location"]: row for row in data["facilities"]},
        members={row["member_id"]: row for row in data["members"]},
        billing={row["member_id"]: row for row in data["billing"]},
        classes={row["session_id"]: row for row in data["classes"]},
        bookings={row["booking_id"]: row for row in data["bookings"]},
    )


def _membership_from_row(row: dict[str, Any]) -> Membership:
    return Membership(
        row["member_id"],
        row["name"],
        row["plan"],
        row["status"],
        date.fromisoformat(row["start_date"]),
        date.fromisoformat(row["renewal_date"]),
        row["home_location"],
    )


def _billing_from_row(row: dict[str, Any]) -> BillingSummary:
    return BillingSummary(
        row["member_id"],
        date.fromisoformat(row["next_charge_date"]),
        row["next_charge_amount"],
        row["card_last_four"],
        row["outstanding_balance"],
    )


def _class_session_from_row(row: dict[str, Any]) -> ClassSession:
    return ClassSession(
        row["session_id"],
        row["name"],
        row["location"],
        datetime.fromisoformat(row["starts_at"]),
        row["duration_minutes"],
        row["instructor"],
        row["capacity"],
        row["booked"],
        row["plan_required"],
    )


def _booking_from_row(row: dict[str, Any]) -> Booking:
    return Booking(
        row["booking_id"],
        row["member_id"],
        row["session_id"],
        row["status"],
        datetime.fromisoformat(row["created_at"]),
    )
