from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Literal


class Role(StrEnum):
    GUEST = "guest"
    MEMBER = "member"
    STAFF = "staff"


Tier = Literal["green", "yellow", "blue", "red"]
PreferenceKind = Literal[
    "preferred_time",
    "preferred_location",
    "avoid_instructor",
    "class_interest",
    "contact_channel",
    "name_pronunciation",
]


@dataclass(frozen=True)
class Principal:
    subject_id: str
    role: Role
    verification_level: Literal["anonymous", "verified"] = "verified"
    allowed_locations: tuple[str, ...] = field(default_factory=tuple)

    @property
    def thread_id(self) -> str:
        return f"{self.role}:{self.subject_id}"


def guest_principal(subject_id: str = "anonymous") -> Principal:
    return Principal(subject_id, Role.GUEST, verification_level="anonymous")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    tier: Tier
    roles: tuple[Role, ...]


@dataclass(frozen=True)
class ClassSession:
    session_id: str
    name: str
    location: str
    starts_at: datetime
    duration_minutes: int
    instructor: str
    capacity: int
    booked: int
    plan_required: str = "Basic"

    @property
    def spots_left(self) -> int:
        return max(self.capacity - self.booked, 0)


@dataclass(frozen=True)
class Membership:
    member_id: str
    name: str
    plan: str
    status: Literal["active", "frozen", "past_due"]
    start_date: date
    renewal_date: date
    home_location: str


@dataclass(frozen=True)
class BillingSummary:
    member_id: str
    next_charge_date: date
    next_charge_amount: float
    card_last_four: str
    outstanding_balance: float


@dataclass(frozen=True)
class Booking:
    booking_id: str
    member_id: str
    session_id: str
    status: Literal["booked", "cancelled", "waitlisted"]
    created_at: datetime


@dataclass(frozen=True)
class Preference:
    preference_id: str
    member_id: str
    kind: PreferenceKind
    value: str
    stated_at: datetime
    source: str
