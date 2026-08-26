from app.core.config import Settings
from app.services.ai_service import AIService, RuleBasedProvider


def rule(title: str, rate: int, planned: int, kept: int = 0, rule_id: int = 1) -> dict:
    return {
        "id": rule_id,
        "title": title,
        "emoji": "✅",
        "planned": planned,
        "kept": kept,
        "rate": rate,
    }


def test_mock_provider_is_used_without_a_key():
    service = AIService(Settings(ai_provider="anthropic", ai_api_key=None))
    assert service.provider_name == "mock"


def test_daily_reflection_scales_with_the_day():
    provider = RuleBasedProvider()
    assert provider.daily_reflection(0, 0, None).title == "Start small"
    assert provider.daily_reflection(5, 5, None).title == "Strong day"
    assert provider.daily_reflection(3, 5, None).title == "Progress counts"
    assert provider.daily_reflection(1, 5, None).title == "Reset, don't restart"


def test_a_hard_mood_is_acknowledged():
    body = RuleBasedProvider().daily_reflection(1, 5, "😔").body
    assert "hard day" in body


def test_coach_ignores_rules_that_were_never_planned():
    """An unplanned rule sits at 0% and must not be reported as the weak one."""
    context = {
        "consistency": 80,
        "current_streak": 4,
        "longest_streak": 9,
        "rule_breakdown": [
            rule("Never planned", rate=0, planned=0, rule_id=1),
            rule("Actually slipping", rate=40, planned=5, kept=2, rule_id=2),
        ],
    }
    answer = RuleBasedProvider().coach_answer("Where am I losing consistency?", context)
    assert "Actually slipping" in answer
    assert "Never planned" not in answer


def test_coach_falls_back_gracefully_with_no_rules():
    answer = RuleBasedProvider().coach_answer(
        "Where am I losing consistency?",
        {"consistency": 0, "current_streak": 0, "rule_breakdown": []},
    )
    assert "Nothing is clearly slipping" in answer


def test_weekly_patterns_need_enough_data_before_naming_a_rule():
    thin = {"delta": 0, "consistency": 50, "rule_breakdown": [rule("Once", 100, 1, 1)]}
    titles = [i.title for i in RuleBasedProvider().weekly_patterns(thin)]
    assert "🌱 Your strongest pattern" not in titles

    solid = {
        "delta": 5,
        "consistency": 70,
        "best_day": "Tue",
        "rule_breakdown": [
            rule("Strong habit", 90, 6, 5, rule_id=1),
            rule("Fragile habit", 30, 6, 2, rule_id=2),
        ],
    }
    insights = RuleBasedProvider().weekly_patterns(solid)
    joined = " ".join(f"{i.title} {i.body}" for i in insights)
    assert "Strong habit" in joined
    assert "Fragile habit" in joined
