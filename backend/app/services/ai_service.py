from dataclasses import dataclass

@dataclass(frozen=True)
class Insight:
    title: str
    body: str

class AIService:
    """Provider-independent AI boundary.

    Real provider calls will be implemented behind this interface. Business
    services should depend on this contract rather than an SDK.
    """

    def daily_reflection(self, completed: int, total: int, mood: str | None) -> Insight:
        if total == 0:
            return Insight("Start small", "You had no planned actions today. Pick one meaningful action for tomorrow.")
        ratio = completed / total
        if ratio >= 0.8:
            return Insight("Strong day", "You followed through on most of your intentions. Keep the same level of simplicity.")
        if ratio >= 0.5:
            return Insight("Progress counts", "You completed meaningful actions today. Look for one friction point to make tomorrow easier.")
        return Insight("Reset, don't restart", "Today was lighter than planned. Choose one small win tomorrow rather than compensating with a huge list.")
