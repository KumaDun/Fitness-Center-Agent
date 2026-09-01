from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

from langchain_core.tools import BaseTool, tool

from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.data.policies import search_policy_clauses
from fitness_agent.data.preferences import DEFAULT_PREFERENCE_STORE, PreferenceStore
from fitness_agent.data.trainers import search_trainer_profiles
from fitness_agent.models import Principal, Role, ToolSpec


TOOL_SPECS = {
    "search_policies": ToolSpec("search_policies", "green", (Role.GUEST, Role.MEMBER, Role.STAFF)),
    "search_trainers": ToolSpec("search_trainers", "green", (Role.GUEST, Role.MEMBER, Role.STAFF)),
    "get_facility_info": ToolSpec("get_facility_info", "green", (Role.GUEST, Role.MEMBER, Role.STAFF)),
    "list_class_schedule": ToolSpec("list_class_schedule", "green", (Role.GUEST, Role.MEMBER, Role.STAFF)),
    "get_membership": ToolSpec("get_membership", "yellow", (Role.MEMBER,)),
    "get_billing_summary": ToolSpec("get_billing_summary", "yellow", (Role.MEMBER,)),
    "get_my_bookings": ToolSpec("get_my_bookings", "yellow", (Role.MEMBER,)),
    "prepare_book_class": ToolSpec("prepare_book_class", "blue", (Role.MEMBER,)),
    "book_class": ToolSpec("book_class", "blue", (Role.MEMBER,)),
    "get_preferences": ToolSpec("get_preferences", "yellow", (Role.MEMBER,)),
    "remember_preference": ToolSpec("remember_preference", "blue", (Role.MEMBER,)),
    "forget_preference": ToolSpec("forget_preference", "blue", (Role.MEMBER,)),
    "lookup_member": ToolSpec("lookup_member", "red", (Role.STAFF,)),
    "get_member_membership": ToolSpec("get_member_membership", "red", (Role.STAFF,)),
    "get_member_billing_summary": ToolSpec("get_member_billing_summary", "red", (Role.STAFF,)),
    "get_member_bookings": ToolSpec("get_member_bookings", "red", (Role.STAFF,)),
    "prepare_member_booking": ToolSpec("prepare_member_booking", "red", (Role.STAFF,)),
    "book_member_class": ToolSpec("book_member_class", "red", (Role.STAFF,)),
    "get_member_preferences": ToolSpec("get_member_preferences", "red", (Role.STAFF,)),
    "get_class_occupancy": ToolSpec("get_class_occupancy", "red", (Role.STAFF,)),
    "escalate_to_human": ToolSpec("escalate_to_human", "green", (Role.GUEST, Role.MEMBER, Role.STAFF)),
}


def visible_tool_names(principal: Principal) -> list[str]:
    return [name for name, spec in TOOL_SPECS.items() if principal.role in spec.roles]


def _is_visible(tool_name: str, principal: Principal) -> bool:
    return principal.role in TOOL_SPECS[tool_name].roles


def build_tools(
    principal: Principal,
    store: MockGymStore | None = None,
    preference_store: PreferenceStore | None = None,
) -> list[BaseTool]:
    store = store or MockGymStore()
    preference_store = preference_store or DEFAULT_PREFERENCE_STORE

    @tool
    def search_policies(query: str) -> list[dict[str, str]]:
        """Search fitness centre policy clauses and return cited passages.

        Args:
            query: Policy question or keywords, such as guest policy or cancellation fee.
        """
        return search_policy_clauses(query)

    @tool
    def search_trainers(query: str) -> list[dict]:
        """Search public trainer and tutor profiles by name, specialty, course, certification, or location.

        Args:
            query: Trainer question or keywords, such as strength coach, yoga tutor, Spin, or Singapore.
        """
        return search_trainer_profiles(query)

    @tool
    def get_facility_info(location: str) -> dict:
        """Get live facility hours, address, amenities, and freshness for one location.

        Args:
            location: Fitness centre location name, such as Singapore or Bangkok.
        """
        return store.facility_info(location)

    @tool
    def list_class_schedule(days_from_today: int = 1, location: str | None = None) -> list[dict]:
        """List class sessions with instructor, capacity, and spots left.

        Args:
            days_from_today: Start day offset from today. Use 0 for today and 1 for tomorrow.
            location: Optional location filter, such as Singapore or Bangkok.
        """
        start = date.today() + timedelta(days=days_from_today)
        return store.class_schedule(start, start + timedelta(days=6), location)

    @tool
    def get_membership() -> dict:
        """Get membership details for the authenticated principal only."""
        return store.membership_for(principal.subject_id)

    @tool
    def get_billing_summary() -> dict:
        """Get billing summary for the authenticated principal only."""
        return store.billing_for(principal.subject_id)

    @tool
    def get_my_bookings() -> list[dict]:
        """Get bookings for the authenticated principal only."""
        return store.bookings_for(principal.subject_id)

    @tool
    def prepare_book_class(session_id: str) -> dict:
        """Check whether the authenticated principal can book a class without writing it.

        Args:
            session_id: Class session id returned by list_class_schedule.
        """
        return store.prepare_booking(principal.subject_id, session_id)

    @tool
    def book_class(session_id: str) -> dict:
        """Book a class for the authenticated member after explicit user confirmation.

        Call prepare_book_class first. Use this only after the user clearly confirms
        they want to process, confirm, or finalize the booking.

        Args:
            session_id: Class session id returned by list_class_schedule.
        """
        return store.book_class(principal.subject_id, session_id)

    @tool
    def get_preferences() -> list[dict]:
        """Get stored preferences for the authenticated principal only."""
        return preference_store.list_for_member(principal.subject_id)

    @tool
    def remember_preference(kind: str, value: str, source: str) -> dict:
        """Store a stated user preference after deterministic validation.

        Use only when the user explicitly states a preference from the closed
        vocabulary. Never store health, injury, body, medical, inferred,
        membership, billing, booking, or attendance facts.

        Args:
            kind: One of preferred_time, preferred_location, avoid_instructor, class_interest, contact_channel, name_pronunciation.
            value: Typed preference value to remember.
            source: The user's statement that explicitly expressed this preference.
        """
        return preference_store.remember(principal.subject_id, kind, value, source)

    @tool
    def forget_preference(preference_id: str) -> dict:
        """Hard-delete one stored preference for the authenticated principal only.

        Args:
            preference_id: Preference id returned by get_preferences.
        """
        return preference_store.forget(principal.subject_id, preference_id)

    @tool
    def escalate_to_human(reason: str) -> dict:
        """Create a human handoff ticket for unsupported, risky, or uncertain requests.

        Args:
            reason: Short reason for escalation.
        """
        return {"ticket_id": f"ticket_{principal.subject_id}_001", "reason": reason, "expected_response_window": "1 business day"}

    candidate_tools: list[BaseTool] = [
        search_policies,
        search_trainers,
        get_facility_info,
        list_class_schedule,
        get_membership,
        get_billing_summary,
        get_my_bookings,
        prepare_book_class,
        book_class,
        get_preferences,
        remember_preference,
        forget_preference,
        escalate_to_human,
    ]
    tools = [candidate for candidate in candidate_tools if _is_visible(candidate.name, principal)]

    if principal.role == Role.STAFF:
        tools.extend(_staff_tools(principal, store, preference_store))

    return tools


def _staff_tools(principal: Principal, store: MockGymStore, preference_store: PreferenceStore) -> list[BaseTool]:
    @tool
    def lookup_member(query: str) -> list[dict]:
        """Staff-only: look up member candidates by name or member id.

        Args:
            query: Name or member id fragment.
        """
        _audit(principal, "lookup_member", query)
        return store.lookup_member(query)

    @tool
    def get_member_membership(member_id: str) -> dict:
        """Staff-only: get membership details for a target member id.

        Args:
            member_id: Member id returned by lookup_member, such as mem_001.
        """
        _audit(principal, "get_member_membership", member_id)
        return store.membership_for(member_id)

    @tool
    def get_member_billing_summary(member_id: str) -> dict:
        """Staff-only: get billing summary for a target member id.

        Use after lookup_member when staff asks about a named member's billing,
        balance, charge, payment card, or month-specific billing. This mock store
        returns the current billing summary rather than a full monthly invoice ledger.

        Args:
            member_id: Member id returned by lookup_member, such as mem_001.
        """
        _audit(principal, "get_member_billing_summary", member_id)
        return store.billing_for(member_id)

    @tool
    def get_member_bookings(member_id: str) -> list[dict]:
        """Staff-only: get bookings for a target member id.

        Args:
            member_id: Member id returned by lookup_member, such as mem_001.
        """
        _audit(principal, "get_member_bookings", member_id)
        return store.bookings_for(member_id)

    @tool
    def prepare_member_booking(member_id: str, session_id: str) -> dict:
        """Staff-only: check whether a target member can book a class without writing it.

        Use after lookup_member and list_class_schedule when staff asks to book
        a class for a named member. This validates membership status, plan access,
        capacity, and schedule clashes.

        Args:
            member_id: Member id returned by lookup_member, such as mem_001.
            session_id: Class session id returned by list_class_schedule.
        """
        _audit(principal, "prepare_member_booking", f"{member_id}:{session_id}")
        return store.prepare_booking(member_id, session_id)

    @tool
    def book_member_class(member_id: str, session_id: str) -> dict:
        """Staff-only: book a class for a target member after explicit confirmation.

        Call prepare_member_booking first. Use this only after the staff user
        clearly confirms they want to process, confirm, or finalize the booking.
        If validation fails, report the returned reason and do not claim success.

        Args:
            member_id: Member id returned by lookup_member, such as mem_001.
            session_id: Class session id returned by list_class_schedule.
        """
        _audit(principal, "book_member_class", f"{member_id}:{session_id}")
        return store.book_class(member_id, session_id)

    @tool
    def get_member_preferences(member_id: str) -> list[dict]:
        """Staff-only: get stored preferences for a target member id.

        Args:
            member_id: Member id returned by lookup_member, such as mem_001.
        """
        _audit(principal, "get_member_preferences", member_id)
        return preference_store.list_for_member(member_id)

    @tool
    def get_class_occupancy(location: str, days_from_today: int = 0) -> list[dict]:
        """Staff-only: get utilisation per class session for an allowed location.

        Args:
            location: Location to inspect. Must be in the staff principal's allowed locations.
            days_from_today: Day offset from today.
        """
        if principal.allowed_locations and location.title() not in principal.allowed_locations:
            return [{"ok": False, "reason": "location_not_allowed"}]
        _audit(principal, "get_class_occupancy", location)
        return store.class_occupancy(location, date.today() + timedelta(days=days_from_today))

    return [
        lookup_member,
        get_member_membership,
        get_member_billing_summary,
        get_member_bookings,
        prepare_member_booking,
        book_member_class,
        get_member_preferences,
        get_class_occupancy,
    ]


def _audit(principal: Principal, action: str, target: str) -> None:
    # Hook for a durable audit sink in the write-enabled phase.
    _ = (principal, action, target)


def tool_map(
    principal: Principal,
    store: MockGymStore | None = None,
    preference_store: PreferenceStore | None = None,
) -> dict[str, Callable]:
    return {item.name: item for item in build_tools(principal, store, preference_store)}
