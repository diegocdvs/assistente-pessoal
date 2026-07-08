from __future__ import annotations

from app.core.automation import AutomationPlanner
from app.core.models import Category, Classification, EmailEntity, Priority


def make_email() -> EmailEntity:
    return EmailEntity(
        id="msg-1",
        provider="gmail",
        account_id="acc",
        account_email="acc@example.com",
        thread_id="thread-1",
        subject="Reuniao",
        sender="sender@example.com",
        recipients=["acc@example.com"],
        snippet="",
    )


def test_automation_planner_creates_dry_run_action_plans_with_payload():
    planner = AutomationPlanner(dry_run=True)
    classification = Classification(Category.EVENTO, Priority.ALTA, 0.8, "Possivel evento.", possible_event=True)

    actions = planner.plan(make_email(), classification)

    assert [action.type for action in actions] == ["review_high_priority", "review_event_candidate"]
    assert all(action.dry_run is True for action in actions)
    assert all(action.status == "planned" for action in actions)
    assert actions[0].payload["email_id"] == "msg-1"
    assert actions[0].id == "acc:msg-1:review_high_priority"
    assert actions[0].source == "rule_based_classifier"
    assert actions[0].audit_metadata["classification_confidence"] == 0.8
    assert actions[0].audit_metadata["thread_id"] == "thread-1"


def test_automation_planner_does_not_plan_noise_actions():
    planner = AutomationPlanner(dry_run=True)
    classification = Classification(Category.NEWSLETTER, Priority.RUIDO, 0.8, "Newsletter.")

    assert planner.plan(make_email(), classification) == []
