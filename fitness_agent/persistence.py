from __future__ import annotations

from enum import StrEnum


class PersistenceEvent(StrEnum):
    NORMAL_CHAT_TURN = "normal_chat_turn"
    PREFERENCE_REMEMBERED = "preference_remembered"
    PREFERENCE_FORGOTTEN = "preference_forgotten"
    BOOKING_PREPARED = "booking_prepared"
    BOOKING_COMMITTED = "booking_committed"
    BOOKING_CANCELLED = "booking_cancelled"
    WAITLIST_JOINED = "waitlist_joined"
    STAFF_MEMBER_READ = "staff_member_read"
    STAFF_OVERRIDE_PREPARED = "staff_override_prepared"
    STAFF_OVERRIDE_COMMITTED = "staff_override_committed"
    HUMAN_ESCALATION_CREATED = "human_escalation_created"


IMPORTANT_EVENTS = {
    PersistenceEvent.PREFERENCE_REMEMBERED,
    PersistenceEvent.PREFERENCE_FORGOTTEN,
    PersistenceEvent.BOOKING_PREPARED,
    PersistenceEvent.BOOKING_COMMITTED,
    PersistenceEvent.BOOKING_CANCELLED,
    PersistenceEvent.WAITLIST_JOINED,
    PersistenceEvent.STAFF_MEMBER_READ,
    PersistenceEvent.STAFF_OVERRIDE_PREPARED,
    PersistenceEvent.STAFF_OVERRIDE_COMMITTED,
    PersistenceEvent.HUMAN_ESCALATION_CREATED,
}


def should_persist_immediately(event: PersistenceEvent) -> bool:
    return event in IMPORTANT_EVENTS
