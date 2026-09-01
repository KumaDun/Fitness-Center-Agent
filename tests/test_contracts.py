from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from fitness_agent.agent import AgentMode, FitnessAgentService, answer_demo, build_agent
from fitness_agent.agent.graph import DEFAULT_RECURSION_LIMIT, answer_with_llm
from fitness_agent.agent.tools import build_tools, visible_tool_names
from fitness_agent.data.mock_store import MockGymStore
from fitness_agent.data import load_mock_store_data
from fitness_agent.data.policies import load_policy_clauses
from fitness_agent.data.trainers import load_trainer_profiles
from fitness_agent.models import Principal, Role, guest_principal
from fitness_agent.data.preferences import JsonPreferenceStore, PreferenceStore
from fitness_agent.persistence import PersistenceEvent, should_persist_immediately


class FitnessAgentContractTests(unittest.TestCase):
    def test_policy_corpus_loads_from_json(self) -> None:
        policies = load_policy_clauses()

        self.assertGreaterEqual(len(policies), 1)
        self.assertEqual("Member Handbook", policies[0].document)
        self.assertNotIn("Trainer Directory", {policy.document for policy in policies})

    def test_trainer_profiles_load_from_json(self) -> None:
        trainers = load_trainer_profiles()

        self.assertGreaterEqual(len(trainers), 1)
        self.assertEqual("trn_001", trainers[0].trainer_id)
        self.assertIn("HIIT", trainers[0].courses)

    def test_mock_store_loads_from_json(self) -> None:
        data = load_mock_store_data()

        self.assertGreaterEqual(len(data["members"]), 1)
        self.assertEqual("mem_001", data["members"][0]["member_id"])
        self.assertEqual("2026-09-02T19:00:00", data["classes"][0]["starts_at"])
        self.assertEqual("2026-08-30T10:00:00", data["bookings"][0]["created_at"])

    def test_member_tools_do_not_expose_staff_tools(self) -> None:
        principal = Principal("mem_001", Role.MEMBER)
        names = {tool.name for tool in build_tools(principal)}

        self.assertNotIn("lookup_member", names)
        self.assertNotIn("get_class_occupancy", names)
        self.assertNotIn("lookup_member", visible_tool_names(principal))

    def test_staff_uses_target_member_tools_not_member_scoped_tools(self) -> None:
        principal = Principal("staff_001", Role.STAFF, allowed_locations=("Singapore", "Bangkok"))
        names = {tool.name for tool in build_tools(principal)}

        self.assertNotIn("get_membership", names)
        self.assertIn("get_member_membership", names)
        membership = {tool.name: tool for tool in build_tools(principal)}["get_member_membership"].invoke(
            {"member_id": "mem_001"}
        )
        self.assertEqual("mem_001", membership["member_id"])

    def test_guest_tools_only_include_green_tier_tools(self) -> None:
        principal = guest_principal()
        names = {tool.name for tool in build_tools(principal)}

        self.assertEqual(
            {"search_policies", "search_trainers", "get_facility_info", "list_class_schedule", "escalate_to_human"},
            names,
        )
        self.assertNotIn("get_membership", visible_tool_names(principal))

    def test_guest_personal_request_requires_login(self) -> None:
        response = answer_demo("What is my billing balance?", guest_principal())

        self.assertIn("need to log in", response)

    def test_guest_schedule_answer_points_to_sign_in_for_booking(self) -> None:
        response = answer_demo("What classes are open tomorrow in Singapore?", guest_principal())

        self.assertIn("Yoga Flow", response)
        self.assertIn("Sign in if you want to book", response)

    def test_personal_reads_are_principal_scoped(self) -> None:
        store = MockGymStore()
        avery = Principal("mem_001", Role.MEMBER)
        daniel = Principal("mem_002", Role.MEMBER)

        avery_membership = {tool.name: tool for tool in build_tools(avery, store)}["get_membership"].invoke({})
        daniel_membership = {tool.name: tool for tool in build_tools(daniel, store)}["get_membership"].invoke({})

        self.assertEqual("mem_001", avery_membership["member_id"])
        self.assertEqual("mem_002", daniel_membership["member_id"])

    def test_booking_proposal_refuses_full_class_without_write(self) -> None:
        store = MockGymStore()
        principal = Principal("mem_001", Role.MEMBER)
        tools = {tool.name: tool for tool in build_tools(principal, store)}

        result = tools["prepare_book_class"].invoke({"session_id": "cls_101"})

        self.assertEqual({"ok": False, "reason": "class_full", "waitlist_available": True}, result)

    def test_member_booking_commit_persists_in_store(self) -> None:
        store = MockGymStore()
        principal = Principal("mem_001", Role.MEMBER)
        tools = {tool.name: tool for tool in build_tools(principal, store)}

        result = tools["book_class"].invoke({"session_id": "cls_104"})
        bookings = store.bookings_for("mem_001")
        session = store.class_schedule(
            start=bookings[-1]["starts_at"].date(),
            end=bookings[-1]["starts_at"].date(),
            location="Singapore",
        )[0]

        self.assertTrue(result["ok"])
        self.assertEqual("bk_003", result["booking_id"])
        self.assertIn("bk_003", {booking["booking_id"] for booking in bookings})
        self.assertEqual(2, session["spots_left"])

    def test_staff_booking_commit_persists_for_target_member(self) -> None:
        store = MockGymStore()
        principal = Principal("staff_001", Role.STAFF, allowed_locations=("Singapore", "Bangkok"))
        tools = {tool.name: tool for tool in build_tools(principal, store)}

        result = tools["book_member_class"].invoke({"member_id": "mem_001", "session_id": "cls_104"})
        bookings = tools["get_member_bookings"].invoke({"member_id": "mem_001"})

        self.assertTrue(result["ok"])
        self.assertIn("bk_003", {booking["booking_id"] for booking in bookings})

    def test_staff_booking_commit_returns_validation_failure_without_write(self) -> None:
        store = MockGymStore()
        principal = Principal("staff_001", Role.STAFF, allowed_locations=("Singapore", "Bangkok"))
        tools = {tool.name: tool for tool in build_tools(principal, store)}

        result = tools["book_member_class"].invoke({"member_id": "mem_002", "session_id": "cls_103"})
        bookings = tools["get_member_bookings"].invoke({"member_id": "mem_002"})

        self.assertEqual({"ok": False, "reason": "membership_frozen"}, result)
        self.assertEqual([], bookings)

    def test_preference_capture_stores_allowed_stated_preference(self) -> None:
        preference_store = PreferenceStore()
        principal = Principal("mem_001", Role.MEMBER)
        tools = {tool.name: tool for tool in build_tools(principal, preference_store=preference_store)}

        result = tools["remember_preference"].invoke(
            {"kind": "preferred_time", "value": "morning", "source": "I prefer morning classes"}
        )
        rows = tools["get_preferences"].invoke({})

        self.assertTrue(result["ok"])
        self.assertEqual(1, len(rows))
        self.assertEqual("preferred_time", rows[0]["kind"])

    def test_preference_capture_blocks_health_data(self) -> None:
        preference_store = PreferenceStore()
        principal = Principal("mem_001", Role.MEMBER)
        tools = {tool.name: tool for tool in build_tools(principal, preference_store=preference_store)}

        result = tools["remember_preference"].invoke(
            {"kind": "class_interest", "value": "knee rehab", "source": "Remember that I need knee rehab classes"}
        )
        rows = tools["get_preferences"].invoke({})

        self.assertFalse(result["ok"])
        self.assertEqual("health_or_body_data_not_stored", result["reason"])
        self.assertEqual([], rows)

    def test_agent_builds_can_share_injected_preference_store(self) -> None:
        preference_store = PreferenceStore()
        principal = Principal("mem_001", Role.MEMBER)
        first_tools = {tool.name: tool for tool in build_tools(principal, preference_store=preference_store)}
        second_tools = {tool.name: tool for tool in build_tools(principal, preference_store=preference_store)}

        first_tools["remember_preference"].invoke(
            {"kind": "preferred_location", "value": "Singapore", "source": "I prefer Singapore"}
        )

        rows = second_tools["get_preferences"].invoke({})
        self.assertEqual(1, len(rows))
        self.assertEqual("Singapore", rows[0]["value"])

    def test_json_preference_store_persists_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            first_store = JsonPreferenceStore(path)
            principal = Principal("mem_001", Role.MEMBER)
            first_tools = {tool.name: tool for tool in build_tools(principal, preference_store=first_store)}
            first_tools["remember_preference"].invoke(
                {"kind": "preferred_time", "value": "morning", "source": "I prefer morning classes"}
            )

            second_store = JsonPreferenceStore(path)
            second_tools = {tool.name: tool for tool in build_tools(principal, preference_store=second_store)}
            rows = second_tools["get_preferences"].invoke({})

        self.assertEqual(1, len(rows))
        self.assertEqual("morning", rows[0]["value"])

    def test_persistence_policy_marks_important_events(self) -> None:
        self.assertFalse(should_persist_immediately(PersistenceEvent.NORMAL_CHAT_TURN))
        self.assertTrue(should_persist_immediately(PersistenceEvent.PREFERENCE_REMEMBERED))
        self.assertTrue(should_persist_immediately(PersistenceEvent.BOOKING_PREPARED))

    def test_llm_agent_builds_openai_model_with_temperature_and_api_key(self) -> None:
        principal = Principal("mem_001", Role.MEMBER)
        chat_model = object()

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("fitness_agent.agent.graph.init_chat_model", return_value=chat_model) as init_chat_model,
            patch("fitness_agent.agent.graph.create_agent") as create_agent,
        ):
            build_agent(principal, model="openai:gpt-4.1-mini", temperature=0.6)

        init_chat_model.assert_called_once_with(
            model="openai:gpt-4.1-mini",
            temperature=0.6,
            api_key="test-key",
        )
        self.assertIs(chat_model, create_agent.call_args.kwargs["model"])

    def test_service_reuses_one_checkpointer_for_llm_calls(self) -> None:
        service = FitnessAgentService(mode=AgentMode.LLM)

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("fitness_agent.agent.service.answer_with_llm", return_value="llm answer") as answer_with_llm,
        ):
            service.answer("hello", Principal("mem_001", Role.MEMBER))

        self.assertIs(service.checkpointer, answer_with_llm.call_args.kwargs["checkpointer"])
        self.assertIs(service.store, answer_with_llm.call_args.kwargs["store"])

    def test_llm_agent_uses_expanded_recursion_limit(self) -> None:
        principal = Principal("mem_001", Role.MEMBER)
        agent = MagicMock()
        agent.invoke.return_value = {"messages": [MagicMock(content="llm answer")]}

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("fitness_agent.agent.graph.build_agent", return_value=agent),
        ):
            response = answer_with_llm("hello", principal)

        self.assertEqual("llm answer", response)
        self.assertEqual(DEFAULT_RECURSION_LIMIT, agent.invoke.call_args.kwargs["config"]["recursion_limit"])

    def test_llm_agent_resets_corrupt_tool_call_checkpoint_and_retries(self) -> None:
        principal = Principal("mem_001", Role.MEMBER)
        checkpointer = MagicMock()
        bad_request = RuntimeError(
            "An assistant message with 'tool_calls' must be followed by tool messages responding to each "
            "'tool_call_id'. The following tool_call_ids did not have response messages: call_123"
        )
        first_agent = MagicMock()
        first_agent.invoke.side_effect = bad_request
        second_agent = MagicMock()
        second_agent.invoke.return_value = {"messages": [MagicMock(content="recovered answer")]}

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("fitness_agent.agent.graph.build_agent", side_effect=[first_agent, second_agent]) as build_agent_mock,
        ):
            response = answer_with_llm("hello again", principal, checkpointer=checkpointer)

        self.assertEqual("recovered answer", response)
        checkpointer.delete_thread.assert_called_once_with(principal.thread_id)
        self.assertEqual(2, build_agent_mock.call_count)

    def test_auto_mode_uses_llm_when_openai_key_exists(self) -> None:
        service = FitnessAgentService(mode=AgentMode.AUTO)

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch("fitness_agent.agent.service.answer_with_llm", return_value="llm answer") as answer_with_llm,
            patch("fitness_agent.agent.service.answer_demo", return_value="demo answer") as answer_demo_mock,
        ):
            response = service.answer("Which class is suitable?", Principal("mem_001", Role.MEMBER))

        self.assertEqual("llm answer", response)
        answer_with_llm.assert_called_once()
        answer_demo_mock.assert_not_called()

    def test_auto_mode_uses_demo_without_openai_key(self) -> None:
        service = FitnessAgentService(mode=AgentMode.AUTO)

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("fitness_agent.agent.service.answer_with_llm", return_value="llm answer") as answer_with_llm,
            patch("fitness_agent.agent.service.answer_demo", return_value="demo answer") as answer_demo_mock,
        ):
            response = service.answer("Which class is suitable?", Principal("mem_001", Role.MEMBER))

        self.assertEqual("demo answer", response)
        answer_with_llm.assert_not_called()
        answer_demo_mock.assert_called_once()

    def test_policy_answers_include_citations(self) -> None:
        response = answer_demo("Can I bring a guest?", Principal("mem_001", Role.MEMBER))

        self.assertIn("Member Handbook", response)
        self.assertIn("updated", response)

    def test_public_membership_prices_include_plan_levels(self) -> None:
        response = answer_demo("What are the membership prices and plan levels?", guest_principal())

        self.assertIn("Basic membership is $89 per month", response)
        self.assertIn("Premium membership is $129 per month", response)
        self.assertIn("Student membership is $69 per month", response)
        self.assertIn("Family membership starts at $219 per month", response)
        self.assertIn("Membership Guide", response)

    def test_public_membership_buying_conditions_are_cited(self) -> None:
        response = answer_demo("What conditions should I know before buying a membership?", guest_principal())

        self.assertIn("New memberships require", response)
        self.assertIn("Before You Buy", response)
        self.assertIn("updated 2026-09-01", response)

    def test_public_trainer_backgrounds_use_trainer_data(self) -> None:
        response = answer_demo("Tell me about the physical tutors and trainers", guest_principal())

        self.assertIn("Nora Lim (trn_001)", response)
        self.assertIn("Certified group fitness trainer", response)
        self.assertIn("Marcus Wong (trn_003)", response)
        self.assertIn("Courses:", response)

    def test_member_cannot_lookup_other_members_in_demo(self) -> None:
        response = answer_demo("Find member Daniel", Principal("mem_001", Role.MEMBER))

        self.assertIn("cannot look up other members", response)

    def test_staff_can_lookup_members_by_name_in_demo(self) -> None:
        response = answer_demo("Find member Daniel", Principal("staff_001", Role.STAFF))

        self.assertIn("mem_002: Daniel Lim", response)

    def test_staff_can_read_target_member_details_by_name_in_demo(self) -> None:
        response = answer_demo("What is Daniel's membership plan?", Principal("staff_001", Role.STAFF))

        self.assertIn("Daniel Lim is on Basic", response)
        self.assertIn("status frozen", response)

    def test_staff_can_read_target_member_billing_by_full_name_with_month_in_demo(self) -> None:
        response = answer_demo("What's the August billing for Daniel Lim", Principal("staff_001", Role.STAFF))

        self.assertIn("mem_002 next charge", response)
        self.assertIn("Outstanding balance", response)

    def test_demo_recommends_cardio_class_conversationally(self) -> None:
        response = answer_demo("I want to do some oxygen work", Principal("mem_001", Role.MEMBER))

        self.assertIn("I would start with Spin", response)
        self.assertIn("aerobic work", response)
        self.assertIn("cls_104", response)
        self.assertIn("HIIT (cls_101)", response)
        self.assertIn("full", response)

    def test_demo_explains_recommendation_for_muscle_and_weight_loss(self) -> None:
        response = answer_demo(
            "How is the classes. I want to build some muscle and lose weight in the meanwhile.",
            Principal("mem_001", Role.MEMBER),
        )

        self.assertIn("I would start with Spin", response)
        self.assertIn("calorie burn", response)
        self.assertIn("spots left", response)

    def test_demo_does_not_turn_bmi_assessment_into_class_recommendation(self) -> None:
        response = answer_demo(
            "My target is to lose weight. My BMI is about 2.5. Is it a warning indicator? What should I do",
            Principal("mem_001", Role.MEMBER),
        )

        self.assertIn("cannot assess BMI", response)
        self.assertIn("qualified clinician", response)
        self.assertNotIn("I would start with Spin", response)


if __name__ == "__main__":
    unittest.main()
