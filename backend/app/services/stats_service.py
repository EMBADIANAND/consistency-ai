"""Derived statistics: streaks, daily summaries, weekly reports, journey scores.

Nothing here is stored. Streaks and scores are computed from the raw task and
check-in rows, so they can never drift out of sync with the underlying data.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from ..models.checkin import DailyCheckIn
from ..models.daily_task import DailyTask
from ..models.life_rule import LifeRule
from .date_utils import WEEKDAY_LABELS, day_range, percentage, week_start


@dataclass(frozen=True)
class DayStats:
    day: date
    total: int
    completed: int

    @property
    def rate(self) -> int:
        return percentage(self.completed, self.total)

    @property
    def is_consistent(self) -> bool:
        """A day counts toward a streak once at least one intention is kept."""
        return self.completed > 0


class StatsService:
    """Reads task/check-in history for one user and turns it into insight inputs."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    # ------------------------------------------------------------------ raw

    def tasks_between(self, start: date, end: date) -> list[DailyTask]:
        return (
            DailyTask.query.filter(
                DailyTask.user_id == self.user_id,
                DailyTask.scheduled_for >= start,
                DailyTask.scheduled_for <= end,
            )
            .order_by(DailyTask.scheduled_for.asc(), DailyTask.id.asc())
            .all()
        )

    def day_stats(self, start: date, end: date) -> list[DayStats]:
        buckets: dict[date, list[int]] = defaultdict(lambda: [0, 0])
        for task in self.tasks_between(start, end):
            bucket = buckets[task.scheduled_for]
            bucket[0] += 1
            if task.completed:
                bucket[1] += 1
        return [
            DayStats(day=day, total=buckets[day][0], completed=buckets[day][1])
            for day in day_range(start, end)
        ]

    # -------------------------------------------------------------- streaks

    def streaks(self, today: date | None = None) -> dict:
        """Current and longest run of consistent days.

        The current streak may end on today or yesterday: a day that has not
        happened yet should not break a run the user is still keeping.
        """
        today = today or date.today()
        window_start = today - timedelta(days=365)
        stats = {s.day: s for s in self.day_stats(window_start, today)}

        def consistent(day: date) -> bool:
            stat = stats.get(day)
            return bool(stat and stat.is_consistent)

        cursor = today if consistent(today) else today - timedelta(days=1)
        current = 0
        while consistent(cursor):
            current += 1
            cursor -= timedelta(days=1)

        longest = run = 0
        for day in day_range(window_start, today):
            run = run + 1 if consistent(day) else 0
            longest = max(longest, run)

        return {"current": current, "longest": longest}

    # ------------------------------------------------------------- summary

    def today_summary(self, today: date | None = None) -> dict:
        today = today or date.today()
        tasks = [t for t in self.tasks_between(today, today)]
        completed = sum(1 for t in tasks if t.completed)
        total = len(tasks)
        checkin = DailyCheckIn.query.filter_by(
            user_id=self.user_id, checkin_date=today
        ).first()

        return {
            "date": today.isoformat(),
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": percentage(completed, total),
            "streak": self.streaks(today)["current"],
            "checked_in": checkin is not None,
            "mood": checkin.mood if checkin else None,
            "headline": self._headline(completed, total),
        }

    @staticmethod
    def _headline(completed: int, total: int) -> str:
        if total == 0:
            return "Nothing planned yet."
        rate = completed / total
        if rate >= 0.8:
            return "Strong momentum."
        if rate >= 0.5:
            return "Steady progress."
        if completed:
            return "You showed up."
        return "The day is still open."

    # -------------------------------------------------------------- weekly

    def weekly_report(self, today: date | None = None) -> dict:
        today = today or date.today()
        this_start = week_start(today)
        last_start = this_start - timedelta(days=7)

        # The chart always shows a whole Monday-to-Sunday week so it reads as one,
        # but only days that have actually happened count toward the percentages.
        this_week = self.day_stats(this_start, this_start + timedelta(days=6))
        elapsed = [d for d in this_week if d.day <= today]
        last_week = self.day_stats(last_start, last_start + timedelta(days=6))

        def aggregate(days: list[DayStats]) -> int:
            total = sum(d.total for d in days)
            completed = sum(d.completed for d in days)
            return percentage(completed, total)

        this_rate = aggregate(elapsed)
        last_rate = aggregate(last_week)

        return {
            "week_start": this_start.isoformat(),
            "consistency": this_rate,
            "previous_consistency": last_rate,
            "delta": this_rate - last_rate,
            "days": [
                {
                    "date": d.day.isoformat(),
                    "label": WEEKDAY_LABELS[d.day.weekday()],
                    "total": d.total,
                    "completed": d.completed,
                    "rate": d.rate,
                    "future": d.day > today,
                }
                for d in this_week
            ],
            "best_day": self._best_day(elapsed),
            "rule_breakdown": self.rule_breakdown(this_start, today),
        }

    @staticmethod
    def _best_day(days: list[DayStats]) -> str | None:
        scored = [d for d in days if d.total]
        if not scored:
            return None
        best = max(scored, key=lambda d: (d.rate, d.completed))
        return WEEKDAY_LABELS[best.day.weekday()]

    def rule_breakdown(self, start: date, end: date) -> list[dict]:
        """How reliably each life rule was kept over a window."""
        rules = LifeRule.query.filter_by(user_id=self.user_id, is_active=True).all()
        if not rules:
            return []
        tallies: dict[int, list[int]] = {rule.id: [0, 0] for rule in rules}
        for task in self.tasks_between(start, end):
            if task.life_rule_id in tallies:
                tallies[task.life_rule_id][0] += 1
                if task.completed:
                    tallies[task.life_rule_id][1] += 1
        return [
            {
                "id": rule.id,
                "title": rule.title,
                "emoji": rule.emoji,
                "planned": tallies[rule.id][0],
                "kept": tallies[rule.id][1],
                "rate": percentage(tallies[rule.id][1], tallies[rule.id][0]),
            }
            for rule in rules
        ]

    def rule_streak(self, rule_id: int, today: date | None = None) -> int:
        """Consecutive days a specific rule was kept, ending today or yesterday."""
        today = today or date.today()
        window_start = today - timedelta(days=365)
        kept: set[date] = {
            task.scheduled_for
            for task in self.tasks_between(window_start, today)
            if task.life_rule_id == rule_id and task.completed
        }
        cursor = today if today in kept else today - timedelta(days=1)
        streak = 0
        while cursor in kept:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    # ------------------------------------------------------------- journey

    def journey(self, today: date | None = None) -> dict:
        """A 30-day picture: consistency score, totals and earned identity traits."""
        today = today or date.today()
        start = today - timedelta(days=29)
        days = self.day_stats(start, today)
        planned = sum(d.total for d in days)
        kept = sum(d.completed for d in days)
        active_days = sum(1 for d in days if d.is_consistent)
        streaks = self.streaks(today)

        # Reliability (did you keep what you planned) weighted with presence
        # (did you show up at all). Neither alone describes consistency well.
        reliability = percentage(kept, planned)
        presence = percentage(active_days, len(days))
        score = round(reliability * 0.6 + presence * 0.4)

        return {
            "score": score,
            "reliability": reliability,
            "presence": presence,
            "active_days": active_days,
            "window_days": len(days),
            "tasks_planned": planned,
            "tasks_completed": kept,
            "current_streak": streaks["current"],
            "longest_streak": streaks["longest"],
            "traits": self._traits(score, streaks, self.rule_breakdown(start, today)),
        }

    @staticmethod
    def _traits(score: int, streaks: dict, rules: list[dict]) -> list[str]:
        traits: list[str] = []
        if streaks["current"] >= 3:
            traits.append("🔥 Shows up")
        if score >= 70:
            traits.append("🌱 Reliable")
        if streaks["longest"] >= 14:
            traits.append("🏔️ Endures")
        for rule in sorted(rules, key=lambda r: r["rate"], reverse=True)[:2]:
            if rule["rate"] >= 60 and rule["planned"] >= 3:
                traits.append(f"{rule['emoji'] or '✅'} {rule['title']}")
        return traits or ["🌤️ Just beginning"]
