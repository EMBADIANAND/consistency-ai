"""Demo data: a month of plausible history so every screen has something to show."""

import random
from datetime import date, datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from .core.database import db
from .models.checkin import DailyCheckIn
from .models.daily_task import DailyTask
from .models.goal import Goal
from .models.life_rule import LifeRule
from .models.user import User

RULES = [
    ("🏋️", "Move my body every day", "Gym · walk · stretching · mobility", 0.85),
    ("📚", "Learn something useful daily", "Books · coding · videos · ideas", 0.7),
    ("📵", "Protect my attention", "Less scrolling · more intentional time", 0.55),
    ("😴", "Prepare for tomorrow", "Plan the next day before bed", 0.6),
]

EXTRA_TASKS = [
    ("💻", "Work on the inventory project"),
    ("📖", "Read 10 pages"),
    ("🚶", "Reach 10,000 steps"),
    ("🧠", "Practice Python"),
]

MOODS = ["😄", "🙂", "🙂", "😐", "😕"]


def seed_demo_data(email: str, password: str, days: int = 45) -> User:
    user = User.query.filter_by(email=email.lower()).first()
    if user is None:
        user = User(
            email=email.lower(),
            password_hash=generate_password_hash(password),
            display_name="Anand",
        )
        db.session.add(user)
        db.session.flush()
    else:
        # Re-seeding replaces the history rather than stacking a second copy on it.
        DailyTask.query.filter_by(user_id=user.id).delete()
        DailyCheckIn.query.filter_by(user_id=user.id).delete()
        LifeRule.query.filter_by(user_id=user.id).delete()
        Goal.query.filter_by(user_id=user.id).delete()
        db.session.flush()

    db.session.add(
        Goal(
            user_id=user.id,
            title="Become someone who finishes what he starts",
            description="Ship the inventory project and keep a 30-day streak.",
            emoji="🎯",
        )
    )

    rules: list[LifeRule] = []
    for emoji, title, description, _ in RULES:
        rule = LifeRule(
            user_id=user.id, title=title, description=description, emoji=emoji
        )
        db.session.add(rule)
        rules.append(rule)
    db.session.flush()

    rng = random.Random(20260823)
    today = date.today()

    for offset in range(days, -1, -1):
        day = today - timedelta(days=offset)
        # Consistency improves gradually, which makes the weekly delta meaningful.
        momentum = 0.55 + 0.35 * (1 - offset / days)
        planned_today: list[DailyTask] = []

        for rule, (_, _, _, base_rate) in zip(rules, RULES):
            if rng.random() > 0.85:
                continue  # not every rule is planned every day
            completed = rng.random() < base_rate * momentum
            planned_today.append(
                DailyTask(
                    user_id=user.id,
                    life_rule_id=rule.id,
                    title=rule.title,
                    emoji=rule.emoji,
                    scheduled_for=day,
                    completed=completed,
                    completed_at=(
                        datetime.now(timezone.utc) - timedelta(days=offset)
                        if completed
                        else None
                    ),
                )
            )

        for emoji, title in rng.sample(EXTRA_TASKS, k=rng.randint(1, 2)):
            completed = rng.random() < 0.7 * momentum
            planned_today.append(
                DailyTask(
                    user_id=user.id,
                    title=title,
                    emoji=emoji,
                    scheduled_for=day,
                    completed=completed,
                    completed_at=(
                        datetime.now(timezone.utc) - timedelta(days=offset)
                        if completed
                        else None
                    ),
                )
            )

        db.session.add_all(planned_today)

        if offset > 0 and planned_today:
            done = sum(1 for t in planned_today if t.completed)
            db.session.add(
                DailyCheckIn(
                    user_id=user.id,
                    checkin_date=day,
                    mood=MOODS[min(len(MOODS) - 1, int((1 - done / len(planned_today)) * 5))],
                    reflection=None,
                    completed_tasks=done,
                    total_tasks=len(planned_today),
                )
            )

    db.session.commit()
    return user
