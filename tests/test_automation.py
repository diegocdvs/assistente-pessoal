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


def test_automation_planner_creates_dry_run_action_plans():
    planner = AutomationPlanner(dry_run=True)
    classification = Classification(Category.EVENTO, Priority.ALTA, "Possivel evento.", 0.8)

    actions = planner.plan(make_email(), classification)

    assert [action.type for action in actions] == ["review_high_priority", "review_event_candidate"]
    assert all(action.dry_run is True for action in actions)
    assert all(action.status == "planned" for action in actions)


def test_automation_planner_does_not_execute_noise():
    planner = AutomationPlanner(dry_run=True)
    classification = Classification(Category.NEWSLETTER, Priority.RUIDO, "Newsletter.", 0.8)

    assert planner.plan(make_email(), classification) == []
