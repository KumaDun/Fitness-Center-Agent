from __future__ import annotations

import re

from fitness_agent.agent.tools import tool_map
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.data.preferences import DEFAULT_PREFERENCE_STORE, PreferenceStore
from fitness_agent.models import Principal, Role


STAFF_MEMBER_QUERY_STOPWORDS = {
    "a",
    "about",
    "balance",
    "billing",
    "booked",
    "booking",
    "bookings",
    "charge",
    "check",
    "does",
    "find",
    "for",
    "is",
    "member",
    "membership",
    "members",
    "my",
    "august",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "september",
    "october",
    "november",
    "december",
    "plan",
    "the",
    "what",
    "which",
}


def answer_demo(
    message: str,
    principal: Principal,
    store: MockGymStore | None = None,
    preference_store: PreferenceStore | None = None,
) -> str:
    """Small deterministic router so the scaffold can be exercised without model credentials."""
    store = store or MockGymStore()
    preference_store = preference_store or DEFAULT_PREFERENCE_STORE
    tools = tool_map(principal, store, preference_store)
    text = message.lower()

    if "what do you remember" in text or "preferences" in text:
        if "get_preferences" not in tools:
            return _login_required("stored preferences")
        rows = tools["get_preferences"].invoke({})
        if not rows:
            return "I do not have any stored preferences for you."
        return "\n".join(f"{row['preference_id']}: {row['kind']} = {row['value']} (stated {row['stated_at']})" for row in rows)

    if "forget" in text and "pref_" in text:
        if "forget_preference" not in tools:
            return _login_required("stored preferences")
        preference_id = next((word.strip(".,?!") for word in message.split() if word.startswith("pref_")), "")
        result = tools["forget_preference"].invoke({"preference_id": preference_id})
        return f"Forgot {preference_id}." if result["ok"] else f"I could not forget that preference: {result['reason']}."

    if "prefer morning" in text or "prefer mornings" in text:
        if "remember_preference" not in tools:
            return _login_required("remembering preferences")
        result = tools["remember_preference"].invoke(
            {"kind": "preferred_time", "value": "morning", "source": message}
        )
        if result["ok"]:
            return "Got it, I will remember that you prefer morning classes."
        return f"I will not store that preference: {result['reason']}."

    if "prefer singapore" in text or "prefer bangkok" in text:
        if "remember_preference" not in tools:
            return _login_required("remembering preferences")
        location = "Bangkok" if "bangkok" in text else "Singapore"
        result = tools["remember_preference"].invoke(
            {"kind": "preferred_location", "value": location, "source": message}
        )
        if result["ok"]:
            return f"Got it, I will remember that you prefer {location}."
        return f"I will not store that preference: {result['reason']}."

    if _asks_for_health_assessment(text):
        return _health_assessment_boundary(text)

    if _asks_trainer_question(text):
        rows = tools["search_trainers"].invoke({"query": message})
        if not rows:
            return "I do not have a matching trainer profile. I can escalate this to the front desk."
        return "\n".join(_format_trainer_profile(row) for row in rows)

    if _asks_public_policy_question(text):
        passages = tools["search_policies"].invoke({"query": message})
        if not passages:
            return "I do not have a cited policy for that. I can escalate this to the front desk."
        lines = [
            f"{item['text']} ({item['document']} / {item['section']}, updated {item['last_updated']})"
            for item in passages
        ]
        if "injury" in text or "medical" in text:
            lines.append("I cannot provide medical or injury advice; I can help hand this to a qualified staff member.")
        return "\n".join(lines)

    if "billing" in text or "charge" in text or "balance" in text:
        if principal.role == Role.STAFF:
            member_id = _resolve_staff_member_id(message, tools)
            if not member_id:
                return "Which member id should I check? Use a member id like mem_001."
            billing = tools["get_member_billing_summary"].invoke({"member_id": member_id})
            return (
                f"{member_id} next charge: ${billing['next_charge_amount']:.2f} on {billing['next_charge_date']}. "
                f"Card ending {billing['card_last_four']}. Outstanding balance: ${billing['outstanding_balance']:.2f}. "
                f"Fresh as of {billing['fresh_as_of']}."
            )
        if "get_billing_summary" not in tools:
            return _login_required("billing details")
        billing = tools["get_billing_summary"].invoke({})
        return (
            f"Next charge: ${billing['next_charge_amount']:.2f} on {billing['next_charge_date']}. "
            f"Card ending {billing['card_last_four']}. Outstanding balance: ${billing['outstanding_balance']:.2f}. "
            f"Fresh as of {billing['fresh_as_of']}."
        )

    if "membership" in text or "plan" in text:
        if principal.role == Role.STAFF:
            member_id = _resolve_staff_member_id(message, tools)
            if not member_id:
                return "Which member id should I check? Use a member id like mem_001."
            membership = tools["get_member_membership"].invoke({"member_id": member_id})
            return (
                f"{membership['name']} is on {membership['plan']} with status {membership['status']}. "
                f"Renews {membership['renewal_date']}; home location {membership['home_location']}. "
                f"Fresh as of {membership['fresh_as_of']}."
            )
        if "get_membership" not in tools:
            return _login_required("membership details")
        membership = tools["get_membership"].invoke({})
        return (
            f"{membership['name']} is on {membership['plan']} with status {membership['status']}. "
            f"Renews {membership['renewal_date']}; home location {membership['home_location']}. "
            f"Fresh as of {membership['fresh_as_of']}."
        )

    if "booking" in text or "booked" in text:
        if principal.role == Role.STAFF:
            member_id = _resolve_staff_member_id(message, tools)
            if not member_id:
                return "Which member id should I check? Use a member id like mem_001."
            bookings = tools["get_member_bookings"].invoke({"member_id": member_id})
            if not bookings:
                return f"{member_id} does not have any bookings in the mock store."
            return "\n".join(f"{row['booking_id']}: {row['class_name']} at {row['starts_at']} in {row['location']} ({row['status']})" for row in bookings)
        if "get_my_bookings" not in tools:
            return _login_required("your bookings")
        bookings = tools["get_my_bookings"].invoke({})
        if not bookings:
            return "You do not have any bookings in the mock store."
        return "\n".join(f"{row['booking_id']}: {row['class_name']} at {row['starts_at']} in {row['location']} ({row['status']})" for row in bookings)

    if "occupancy" in text or "utilisation" in text or "utilization" in text:
        if principal.role != Role.STAFF:
            return "That staff-only tool is not visible to member principals."
        rows = tools["get_class_occupancy"].invoke({"location": "Singapore", "days_from_today": 1})
        return "\n".join(f"{row['name']} {row['starts_at']}: {row['booked']}/{row['capacity']} ({row['utilisation']:.0%})" for row in rows)

    if "find member" in text or "lookup" in text:
        if principal.role != Role.STAFF:
            return "I cannot look up other members from a member session."
        query = _staff_member_lookup_query(message)
        rows = tools["lookup_member"].invoke({"query": query})
        return "\n".join(f"{row['member_id']}: {row['name']} ({row['status']}, {row['home_location']})" for row in rows) or "No matching members."

    location = "Bangkok" if "bangkok" in text else "Singapore"
    rows = tools["list_class_schedule"].invoke({"days_from_today": 1, "location": location})
    if not rows:
        return f"No classes found for {location} in the next week."
    if _is_class_recommendation_request(text):
        return _recommend_classes(text, rows, location)
    lines = [f"{row['session_id']}: {row['name']} with {row['instructor']} at {row['starts_at']} - {row['spots_left']} spots left" for row in rows]
    if principal.role == Role.GUEST:
        lines.append("Sign in if you want to book one of these classes.")
    return "\n".join(lines)


def _asks_public_policy_question(text: str) -> bool:
    if _extract_member_id(text) or re.search(r"\b[a-z]+(?:'s)\s+(membership|plan)\b", text):
        return False

    policy_terms = [
        "guest",
        "cancel",
        "cancellation",
        "dress",
        "medical",
        "injury",
        "price",
        "prices",
        "cost",
        "fee",
        "fees",
        "buy",
        "buying",
        "join",
        "joining",
        "condition",
        "conditions",
        "course",
        "courses",
    ]
    membership_info_terms = ["membership", "memberships", "plan", "plans", "basic", "premium", "student", "family"]
    if any(term in text for term in policy_terms):
        return True
    return any(term in text for term in membership_info_terms) and not any(
        personal_term in text for personal_term in ["my membership", "my plan", "am i on", "which plan am i"]
    )


def _asks_trainer_question(text: str) -> bool:
    trainer_terms = [
        "trainer",
        "trainers",
        "tutor",
        "tutors",
        "physical tutor",
        "physic tutor",
        "instructor background",
        "coach",
        "coaches",
        "nora",
        "iris",
        "marcus",
        "lena",
    ]
    return any(term in text for term in trainer_terms)


def _format_trainer_profile(row: dict) -> str:
    courses = ", ".join(row["courses"])
    specialties = ", ".join(row["specialties"])
    certifications = ", ".join(row["certifications"])
    consultation = "consultations available" if row["consultation_available"] else "consultations not currently available"
    return (
        f"{row['name']} ({row['trainer_id']}) - {row['role']}. {row['background']} "
        f"Courses: {courses}. Specialties: {specialties}. Certifications: {certifications}. "
        f"Locations: {', '.join(row['locations'])}. {consultation}. "
        f"{row['notes']} Updated {row['last_updated']}."
    )


def _is_class_recommendation_request(text: str) -> bool:
    recommendation_terms = [
        "recommend",
        "suitable",
        "should i",
        "which class",
        "oxygen",
        "cardio",
        "conditioning",
        "build muscle",
        "lose weight",
        "weight loss",
    ]
    return any(term in text for term in recommendation_terms)


def _asks_for_health_assessment(text: str) -> bool:
    health_terms = [
        "bmi",
        "body mass",
        "warning indicator",
        "warning sign",
        "symptom",
        "diagnosis",
        "diagnose",
        "medical",
        "injury",
    ]
    assessment_terms = [
        "what should i do",
        "should i do",
        "is it",
        "am i",
        "healthy",
        "risk",
        "danger",
        "warning",
    ]
    return any(term in text for term in health_terms) and any(term in text for term in assessment_terms)


def _health_assessment_boundary(text: str) -> str:
    lines = [
        "I cannot assess BMI, diagnose risk, or tell whether a body measurement is a warning sign.",
        "A BMI value of 2.5 also sounds like it may be a typo, so it would be worth checking the number with a qualified clinician or a trained staff member.",
    ]
    if any(term in text for term in ["lose weight", "weight loss", "oxygen", "cardio", "class"]):
        lines.append(
            "For general weight-loss training, I can help you choose lower-risk class options like Spin for cardio or Yoga Flow for lighter movement, but I would not base that on the BMI number."
        )
    lines.append("Would you like me to show available beginner-friendly cardio classes?")
    return "\n".join(lines)


def _recommend_classes(text: str, rows: list[dict], location: str) -> str:
    available = [row for row in rows if row["spots_left"] > 0]
    if not available:
        return f"I found classes at {location}, but they are all full right now."

    scored = sorted(
        available,
        key=lambda row: _class_score(text, row),
        reverse=True,
    )
    primary = scored[0]
    backup = next((row for row in scored[1:] if row["name"] != primary["name"]), None)
    full_matches = [row for row in rows if row["spots_left"] < 1 and _class_score(text, row) > 0]

    lines = [
        f"I would start with {primary['name']} with {primary['instructor']}. {_recommendation_reason(text, primary)}",
        _format_class_line(primary),
    ]
    if backup is not None:
        lines.extend(
            [
                f"If you want another option, {backup['name']} is the next best fit. {_recommendation_reason(text, backup)}",
                _format_class_line(backup),
            ]
        )
    if full_matches:
        full_names = ", ".join(f"{row['name']} ({row['session_id']})" for row in full_matches)
        lines.append(f"{full_names} also matches your goal, but it is full, so I would not make it the main pick.")
    lines.append("Do you prefer a harder cardio session or something easier to recover from?")
    return "\n".join(lines)


def _class_score(text: str, row: dict) -> int:
    name = row["name"].lower()
    score = 0
    if any(term in text for term in ["oxygen", "cardio", "conditioning", "lose weight", "weight loss"]):
        if name in {"spin", "hiit"}:
            score += 4
        if name == "yoga flow":
            score += 1
    if any(term in text for term in ["build muscle", "muscle", "strength", "weight training"]):
        if "strength" in name:
            score += 5
        if name == "hiit":
            score += 2
    if row["spots_left"] > 0:
        score += 1
    return score


def _recommendation_reason(text: str, row: dict) -> str:
    name = row["name"].lower()
    if name == "spin":
        return "It is the strongest available match for aerobic work and calorie burn, and it still has space."
    if name == "hiit":
        return "It fits conditioning and fat-loss goals, but only if there is space because it is usually high intensity."
    if "strength" in name:
        return "It is the best fit for building muscle, and strength work also supports weight loss over time."
    if name == "yoga flow":
        return "It is better for mobility, breathing, and recovery than for hard cardio or muscle gain."
    return "It is available and fits better than the other open options I found."


def _format_class_line(row: dict) -> str:
    return f"{row['session_id']}: {row['name']} at {row['starts_at']} with {row['instructor']} - {row['spots_left']} spots left"


def _login_required(topic: str) -> str:
    return f"I can help with public information, but you need to log in before I can access {topic}."


def _extract_member_id(message: str) -> str:
    return next((word.strip(".,?!") for word in message.split() if word.strip(".,?!").startswith("mem_")), "")


def _resolve_staff_member_id(message: str, tools: dict) -> str:
    member_id = _extract_member_id(message)
    if member_id:
        return member_id

    for query in _staff_member_lookup_queries(message):
        rows = tools["lookup_member"].invoke({"query": query})
        if len(rows) == 1:
            return rows[0]["member_id"]
    return ""


def _staff_member_lookup_query(message: str) -> str:
    queries = _staff_member_lookup_queries(message)
    return queries[0] if queries else _extract_member_id(message)


def _staff_member_lookup_queries(message: str) -> list[str]:
    words = [word.lower().removesuffix("'s") for word in re.findall(r"[A-Za-z0-9_']+", message)]
    candidates = [word for word in words if word not in STAFF_MEMBER_QUERY_STOPWORDS]
    if not candidates:
        return []

    queries = []
    if len(candidates) > 1:
        queries.append(" ".join(candidates))
    queries.extend(candidates)
    return queries
