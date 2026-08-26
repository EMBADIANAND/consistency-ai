"""Provider-independent AI boundary.

The application never talks to an SDK directly. It asks :class:`AIService` for
an insight, and the configured provider answers. The rule-based provider is
always available and needs no key, so the app is fully functional offline; when
``AI_PROVIDER=anthropic`` and a key is present, the same calls are answered by a
model instead, with an automatic fall back if the call fails.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import asdict, dataclass

from ..core.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are ConsistencyAI, a calm coach inside a habit-tracking app. "
    "You speak to one person about their own recent behaviour. Be specific, "
    "warm and short: at most three sentences, no bullet points, no headings, "
    "no guilt, no exclamation-heavy hype. Never invent numbers that were not "
    "given to you. Prefer one concrete next action over general encouragement."
)

# The prompt above is written for a card on a screen. A conversation needs
# different instructions: it has to hold a thread, vary its openings, and be
# allowed to answer in one line when that is the honest answer.
CHAT_SYSTEM_PROMPT = (
    "You are ConsistencyAI, in an ongoing conversation with one person about "
    "their own life and habits. Talk the way a close friend would if they "
    "happened to know your numbers: warm, plain-spoken, curious, never "
    "clinical. Refer back to what they already told you in this conversation "
    "instead of restarting each time, and vary how you open — do not begin "
    "every reply the same way. Usually two to four sentences; one line is fine "
    "when that says it. Ask a real question back when you genuinely want to "
    "know something, but not in every message. No bullet points, no headings, "
    "no guilt, no hype. You may cite only the numbers in the stats you are "
    "given — never invent, round or estimate one, and if they ask about "
    "something those stats do not cover, say so plainly. If they want to talk "
    "about something other than habits, just talk with them about it."
)


def _days(count: int) -> str:
    """"1 day", not "1 days" — a coach that miscounts its own grammar reads like a form letter."""
    return "1 day" if count == 1 else f"{count} days"


def _chunk(text: str, size: int = 4) -> Iterator[str]:
    """Split a finished answer into stream-sized pieces.

    The rule-based provider knows its whole answer immediately. Emitting it in
    pieces keeps a single streaming contract for both providers, so no screen
    has to know which one is replying.
    """
    words = text.split(" ")
    for start in range(0, len(words), size):
        piece = " ".join(words[start : start + size])
        yield piece if start == 0 else " " + piece


@dataclass(frozen=True)
class Insight:
    title: str
    body: str

    def to_dict(self) -> dict:
        return asdict(self)


GREETINGS = (
    "hi",
    "hii",
    "hey",
    "hello",
    "heya",
    "yo",
    "sup",
    "namaste",
    "good morning",
    "good afternoon",
    "good evening",
    "hey there",
    "morning",
)

GRATITUDE = (
    "thanks",
    "thank you",
    "thankyou",
    "ty",
    "appreciate it",
    "got it",
    "cool",
    "nice",
    "makes sense",
    "fair",
    "true",
)

# Short replies that only mean something in the light of what came before.
FOLLOW_UPS = (
    "why",
    "how",
    "how so",
    "and",
    "so",
    "then",
    "then what",
    "really",
    "more",
    "tell me more",
    "go on",
    "explain",
    "what else",
    "meaning",
    "such as",
    "like what",
    "for example",
    "elaborate",
)


class RuleBasedProvider:
    """Deterministic insights derived from the user's own numbers."""

    name = "mock"

    def daily_reflection(self, completed: int, total: int, mood: str | None) -> Insight:
        if total == 0:
            return Insight(
                "Start small",
                "You had no planned actions today. Pick one meaningful action for tomorrow.",
            )
        ratio = completed / total
        if ratio >= 0.8:
            body = (
                f"You kept {completed} of {total} intentions. Keep the same level of "
                "simplicity tomorrow rather than adding more."
            )
            title = "Strong day"
        elif ratio >= 0.5:
            body = (
                f"You completed {completed} of {total} intentions. Look for one friction "
                "point to make tomorrow easier."
            )
            title = "Progress counts"
        else:
            body = (
                f"Today was lighter than planned ({completed} of {total}). Choose one small "
                "win tomorrow rather than compensating with a huge list."
            )
            title = "Reset, don't restart"
        if mood in {"😔", "😕"}:
            body += " Being honest about a hard day is part of the practice."
        return Insight(title, body)

    def weekly_patterns(self, report: dict) -> list[Insight]:
        insights: list[Insight] = []
        delta = report.get("delta", 0)
        consistency = report.get("consistency", 0)

        if delta > 0:
            insights.append(
                Insight(
                    "📈 You're trending up",
                    f"Consistency rose {delta} points to {consistency}% this week. "
                    "Whatever you changed, change nothing else yet.",
                )
            )
        elif delta < 0:
            insights.append(
                Insight(
                    "🌊 A lighter week",
                    f"Consistency fell {abs(delta)} points to {consistency}%. Dips are data, "
                    "not failure — look at which rule slipped first.",
                )
            )
        else:
            insights.append(
                Insight(
                    "⚖️ Holding steady",
                    f"You're holding at {consistency}%. Steady is underrated; it is what "
                    "compounds.",
                )
            )

        rules = [r for r in report.get("rule_breakdown", []) if r["planned"] >= 2]
        if rules:
            best = max(rules, key=lambda r: r["rate"])
            worst = min(rules, key=lambda r: r["rate"])
            insights.append(
                Insight(
                    "🌱 Your strongest pattern",
                    f"{best['emoji'] or '✅'} {best['title']} held at {best['rate']}% this week. "
                    "It is becoming automatic — protect it.",
                )
            )
            if worst["id"] != best["id"] and worst["rate"] < 60:
                insights.append(
                    Insight(
                        "🔧 Your fragile edge",
                        f"{worst['emoji'] or '⚠️'} {worst['title']} only held at {worst['rate']}%. "
                        "Try moving it earlier in the day rather than adding pressure.",
                    )
                )

        if report.get("best_day"):
            insights.append(
                Insight(
                    "📅 Your best day",
                    f"{report['best_day']} was your most reliable day. Ask what was different "
                    "about how it started.",
                )
            )
        return insights

    def coach_answer(self, question: str, context: dict) -> str:
        q = question.lower()
        streak = context.get("current_streak", 0)
        consistency = context.get("consistency", 0)
        # Only rules the user actually planned this week can be strong or weak;
        # an unplanned rule sits at 0% and would otherwise always "win" as the
        # fragile one, which would be a false observation.
        rules = [r for r in context.get("rule_breakdown", []) if r["planned"] > 0]
        weak = min(rules, key=lambda r: r["rate"]) if rules else None
        strong = max(rules, key=lambda r: r["rate"]) if rules else None

        if any(word in q for word in ("tomorrow", "next", "focus", "should i")):
            if strong:
                return (
                    f"Keep tomorrow small: {strong['emoji'] or ''} {strong['title']} is already "
                    "reliable, so anchor the day on it and add at most two other intentions. "
                    "Three meaningful wins beat a long list."
                )
            return (
                "Keep tomorrow small — one important task, one body or health action, and one "
                "personal rule. Three meaningful wins beat a long list."
            )
        if any(word in q for word in ("losing", "slipping", "struggl", "fail", "weak")):
            if weak and weak["rate"] < 100:
                return (
                    f"{weak['emoji'] or ''} {weak['title']} is the fragile part of your routine "
                    f"right now, held at {weak['rate']}%. Move it earlier in the day rather than "
                    "adding pressure to the evening."
                )
            return (
                "Nothing is clearly slipping in your recent data. Keep planning a small number "
                "of intentions so the signal stays readable."
            )
        if any(word in q for word in ("better", "why", "improv", "progress")):
            return (
                f"You're at {consistency}% consistency with a {streak}-day streak. Your better "
                "stretches come from fewer, clearer intentions rather than bigger plans — "
                "consistency before intensity."
            )
        if any(word in q for word in ("streak", "how long")):
            return (
                f"Your current streak is {_days(streak)}, and your longest is "
                f"{context.get('longest_streak', 0)}. A streak survives on the smallest version "
                "of the habit, so define what 'done' means on a bad day."
            )
        return (
            f"Across your recent activity you're keeping {consistency}% of what you plan. "
            "Protecting your first meaningful block of the day is the pattern that moves that "
            "number most."
        )

    # ------------------------------------------------------------------ chat

    def chat(self, history: list[dict], context: dict, display_name: str = "") -> str:
        """Answer the newest turn in the light of the ones before it.

        Without a key this provider is what the user actually talks to, so it
        has to do the one thing a stateless endpoint could not: notice that
        "why?" is not a question about nothing. It resolves a short follow-up
        against the previous turn, and refuses to repeat an answer the user has
        already read.
        """
        turns = [t for t in history if (t.get("content") or "").strip()]
        latest = turns[-1]["content"].strip() if turns else ""
        normalized = latest.lower().strip(" ?!.,'\"")
        first_name = display_name.strip().split(" ")[0] if display_name else ""

        # "hey" is a turn, but it is not a question — resolving "why?" against it
        # would answer something the user never asked.
        previous_question = next(
            (
                t["content"]
                for t in reversed(turns[:-1])
                if t["role"] == "user"
                and not self._is(t["content"].lower().strip(" ?!.,'\""), GREETINGS)
                and not self._is(t["content"].lower().strip(" ?!.,'\""), GRATITUDE)
            ),
            None,
        )
        previous_answer = next(
            (t["content"] for t in reversed(turns[:-1]) if t["role"] == "assistant"),
            None,
        )

        if self._is(normalized, GREETINGS):
            return self._greeting_reply(first_name, context, previous_answer is None)

        if self._is(normalized, GRATITUDE):
            return (
                "Anytime. I'll be here tomorrow with whatever the numbers say — come "
                "back when you want to look at them together."
            )

        # A short reply with nothing to attach to is just a vague question; a
        # short reply after an answer is a request to go deeper into that answer.
        is_follow_up = self._is(normalized, FOLLOW_UPS) or len(normalized.split()) <= 2
        if is_follow_up and previous_answer:
            if previous_question:
                revisited = self.coach_answer(previous_question, context)
                if revisited.strip() != previous_answer.strip():
                    return revisited
            # Either nothing substantive was asked before, or re-answering it
            # would repeat what they just read. Go deeper instead of looping.
            return "Going one level deeper: " + self._mechanism(context)

        answer = self.coach_answer(latest, context)
        if previous_answer and answer.strip() == previous_answer.strip():
            return "Same picture as a moment ago — " + self._mechanism(context)
        return answer

    def chat_stream(
        self, history: list[dict], context: dict, display_name: str = ""
    ) -> Iterator[str]:
        yield from _chunk(self.chat(history, context, display_name))

    @staticmethod
    def _is(normalized: str, phrases: tuple[str, ...]) -> bool:
        return normalized in phrases

    def _greeting_reply(self, first_name: str, context: dict, opening: bool) -> str:
        hello = f"Hey {first_name}" if first_name else "Hey"
        streak = context.get("current_streak", 0)
        consistency = context.get("consistency", 0)
        if streak:
            return (
                f"{hello} — good to see you. You're {_days(streak)} into a streak and "
                f"holding {consistency}% this week. What's on your mind?"
            )
        if not opening:
            return f"{hello} again. Where do you want to pick up?"
        return (
            f"{hello} — good to see you. Nothing's running yet this week, which is a "
            "fine place to start. What do you want tomorrow to look like?"
        )

    def _mechanism(self, context: dict) -> str:
        """The 'why underneath the why' — a second angle, never the same sentence."""
        rules = [r for r in context.get("rule_breakdown", []) if r["planned"] > 0]
        streak = context.get("current_streak", 0)
        if rules:
            weak = min(rules, key=lambda r: r["rate"])
            return (
                f"the days you miss tend to start with {weak['title'].lower()} slipping, and "
                "once one planned thing goes the rest of the list stops feeling binding. "
                "Protecting that one first is usually what holds the whole day together."
            )
        if streak:
            return (
                f"a {streak}-day streak survives on the smallest version of the habit, not "
                "the best one. Decide now what counts as done on your worst day, and the "
                "streak stops depending on your mood."
            )
        return (
            "consistency is mostly a planning problem rather than a willpower one — a "
            "shorter list you actually finish teaches you that your plan means something, "
            "and that belief is what carries the next day."
        )


class AnthropicProvider:
    """Answers the same questions with a model, falling back on any failure."""

    name = "anthropic"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, settings: Settings, fallback: RuleBasedProvider):
        self.settings = settings
        self.fallback = fallback

    def _complete(self, prompt: str, max_tokens: int = 300) -> str | None:
        body = json.dumps(
            {
                "model": self.settings.ai_model,
                "max_tokens": max_tokens,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        request = urllib.request.Request(
            self.API_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": self.settings.ai_api_key or "",
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read())
            parts = [b.get("text", "") for b in payload.get("content", [])]
            text = "".join(parts).strip()
            return text or None
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            logger.warning("AI provider call failed, using rule-based fallback: %s", exc)
            return None

    def daily_reflection(self, completed: int, total: int, mood: str | None) -> Insight:
        text = self._complete(
            "Write the end-of-day reflection for a user who completed "
            f"{completed} of {total} planned intentions today"
            + (f" and rated their mood {mood}." if mood else ".")
            + " Two sentences."
        )
        if not text:
            return self.fallback.daily_reflection(completed, total, mood)
        return Insight("Your AI reflection", text)

    def weekly_patterns(self, report: dict) -> list[Insight]:
        text = self._complete(
            "Here is one user's week of habit data as JSON:\n"
            f"{json.dumps(report, default=str)}\n"
            "Name the two most useful patterns you can actually see in these numbers. "
            "Reply as two lines, each formatted 'Title :: sentence'.",
            max_tokens=400,
        )
        if not text:
            return self.fallback.weekly_patterns(report)
        insights: list[Insight] = []
        for line in text.splitlines():
            if "::" in line:
                title, _, body = line.partition("::")
                insights.append(Insight(title.strip(" -•"), body.strip()))
        return insights or self.fallback.weekly_patterns(report)

    def coach_answer(self, question: str, context: dict) -> str:
        text = self._complete(
            f"The user's recent stats as JSON:\n{json.dumps(context, default=str)}\n\n"
            f"They asked: {question}\n"
            "Answer them directly, grounded only in those numbers.",
            max_tokens=350,
        )
        return text or self.fallback.coach_answer(question, context)

    # ------------------------------------------------------------------ chat

    def _chat_system(self, context: dict, display_name: str) -> str:
        """Stats live in the system block, not the transcript.

        Putting them in a user turn would let them drift out of the window as
        the conversation grows, and the model would start reasoning from numbers
        it half-remembers. In the system block they are re-stated, current, on
        every single call.
        """
        who = f"\n\nYou are talking with {display_name}." if display_name else ""
        return (
            CHAT_SYSTEM_PROMPT
            + who
            + "\n\nTheir current stats — the only numbers you may cite:\n"
            + json.dumps(context, default=str)
        )

    def _stream_chat(self, history: list[dict], system: str) -> Iterator[str]:
        body = json.dumps(
            {
                "model": self.settings.ai_model,
                "max_tokens": 600,
                "system": system,
                "stream": True,
                "messages": history,
            }
        ).encode()
        request = urllib.request.Request(
            self.API_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": self.settings.ai_api_key or "",
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            for raw in response:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if not data or data == "[DONE]":
                    continue
                event = json.loads(data)
                if event.get("type") == "content_block_delta":
                    text = event.get("delta", {}).get("text")
                    if text:
                        yield text

    def chat_stream(
        self, history: list[dict], context: dict, display_name: str = ""
    ) -> Iterator[str]:
        """Stream the reply, falling back only while that is still honest.

        Once a token has reached the user's screen the rule-based answer can no
        longer be substituted — it would contradict a sentence they have already
        read. So the fallback covers failures *before* the first token, and a
        mid-stream failure ends the reply where it stands.
        """
        system = self._chat_system(context, display_name)
        started = False
        try:
            for chunk in self._stream_chat(history, system):
                started = True
                yield chunk
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning("AI chat stream failed: %s", exc)
            if started:
                return
        if not started:
            logger.info("Falling back to the rule-based provider for this reply")
            yield from self.fallback.chat_stream(history, context, display_name)

    def chat(self, history: list[dict], context: dict, display_name: str = "") -> str:
        return "".join(self.chat_stream(history, context, display_name))


class AIService:
    """Facade the rest of the application depends on."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        rule_based = RuleBasedProvider()
        if self.settings.ai_provider == "anthropic" and self.settings.ai_api_key:
            self.provider = AnthropicProvider(self.settings, rule_based)
        else:
            self.provider = rule_based

    @property
    def provider_name(self) -> str:
        return self.provider.name

    def daily_reflection(self, completed: int, total: int, mood: str | None = None) -> Insight:
        return self.provider.daily_reflection(completed, total, mood)

    def weekly_patterns(self, report: dict) -> list[Insight]:
        return self.provider.weekly_patterns(report)

    def coach_answer(self, question: str, context: dict) -> str:
        return self.provider.coach_answer(question, context)

    def chat(self, history: list[dict], context: dict, display_name: str = "") -> str:
        return self.provider.chat(history, context, display_name)

    def chat_stream(
        self, history: list[dict], context: dict, display_name: str = ""
    ) -> Iterator[str]:
        return self.provider.chat_stream(history, context, display_name)
